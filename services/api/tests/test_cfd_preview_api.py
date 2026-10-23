"""B3A: real migrated, NEW disposable databases; no runtime calculations or saves."""

import asyncio
import json
import subprocess
import sys
from copy import deepcopy
from decimal import Decimal, localcontext
from pathlib import Path
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from app.cfd_practice import create_app
from app.core.cfd_settings import CfdPracticeSettings
from app.database.cfd_session import CfdTargetRejected, new_cfd_workspace
from app.schemas.cfd_api import CfdErrorEnvelope, CfdPreviewCommandV1, CfdStatusV1
from app.services.cfd_canonical import canonical_input
from app.services.cfd_preview import bind_preview

BASE = "http://127.0.0.1:8003"
HEADER = {"X-AVA-Local": "cfd-practice-v1"}
ROOT = "/api/v1/cfd"


@pytest.fixture
def case():
    with new_cfd_workspace() as workspace:
        app = create_app(workspace=workspace, settings=CfdPracticeSettings(enabled=True))
        with TestClient(app, base_url=BASE, client=("127.0.0.1", 50000), headers=HEADER) as client:
            yield workspace, app, client


def body(workspace, symbol="USDJPY"):
    return deepcopy(workspace.samples["previews"][symbol])


def inventory(workspace):
    with workspace.read_session() as session:
        return {
            name: session.execute(text(f'SELECT * FROM "{name}"')).all()
            for name in inspect(session.get_bind()).get_table_names()
        }


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///ava.db",
        "sqlite:///services/api/ava.db",
        "sqlite://",
        "sqlite:///C:/private/backup.db",
        "postgresql+psycopg://unused/unused",
    ],
)
def test_unauthorized_target_rejected_before_connect(case, monkeypatch, url):
    workspace, app, client = case
    with monkeypatch.context() as patch:
        patch.setattr(workspace.engine, "url", make_url(url))
        forbidden = Mock(side_effect=AssertionError("A rejected target must never connect"))
        patch.setattr(workspace.engine, "connect", forbidden)
        response = client.get(ROOT + "/status")
        assert response.status_code == 403
        forbidden.assert_not_called()


def test_actual_dbapi_arguments_checked_before_open(monkeypatch):
    import sqlite3

    from app.database import cfd_session

    def intercepted(url, **kwargs):
        engine = create_engine(url, **kwargs)

        # Register substitution BEFORE the workspace installs its guard.
        # create_connect_args is cached at engine creation, so patching it later
        # would not test a changed actual DBAPI target.
        @event.listens_for(engine, "do_connect")
        def substitute(dialect, record, args, params):
            args[0] = "ava.db"

        return engine

    with monkeypatch.context() as patch:
        patch.setattr(cfd_session, "create_engine", intercepted)
        forbidden = Mock(side_effect=AssertionError("DBAPI connection must never happen"))
        patch.setattr(sqlite3, "connect", forbidden)
        with pytest.raises(CfdTargetRejected):
            with new_cfd_workspace():
                pytest.fail("A substituted target must not be provisioned")
        forbidden.assert_not_called()


def test_registered_target_required_not_just_matching_temp_prefix(case, tmp_path):
    workspace, _, _ = case
    fake = tmp_path / "ava-cfd-practice-fake" / "cfd-practice.db"
    with pytest.raises(CfdTargetRejected):
        workspace.check_target(make_url(f"sqlite:///{fake.as_posix()}"))
    assert not fake.exists()


def test_default_disabled_ignores_enablement_environment(monkeypatch):
    monkeypatch.setenv("CFD_PRACTICE_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///ava.db")
    with TestClient(create_app(), base_url=BASE, headers=HEADER) as client:
        assert client.get(ROOT + "/status").status_code == 404
        assert client.post(ROOT + "/preview", json={}).status_code == 404


def test_setting_alone_cannot_register_workspace():
    app = create_app(settings=CfdPracticeSettings(enabled=True))
    with TestClient(app, base_url=BASE, headers=HEADER) as client:
        assert client.get(ROOT + "/status").status_code == 404


def test_status_schema_reports_no_operational_features(case):
    workspace, _, client = case
    response = client.get(ROOT + "/status")
    assert response.status_code == 200
    status = CfdStatusV1.model_validate(response.json())
    assert not status.can_create and not status.preview_available and not status.host_fallback
    assert status.historical_replay == status.postgresql == "unverified"
    assert str(workspace.directory) not in response.text
    with pytest.raises(ValidationError):
        CfdStatusV1(can_create=True)


@pytest.mark.parametrize("symbol", ["USDJPY", "XAUUSD", "XAGUSD"])
def test_valid_preview_is_runtime_unavailable_and_writes_nothing(case, monkeypatch, symbol):
    from app.analytics import cfd, cfd_positions

    workspace, _, client = case
    before = inventory(workspace)
    forbidden = Mock(side_effect=AssertionError("B3A must not execute host calculations"))
    monkeypatch.setattr(cfd_positions, "calculate_position", forbidden)
    monkeypatch.setattr(cfd, "calculate_cfd", forbidden)
    response = client.post(ROOT + "/preview", json=body(workspace, symbol))
    assert response.status_code == 503, response.text
    error = CfdErrorEnvelope.model_validate(response.json()).error
    assert error.code == "calculation_runtime_unavailable"
    assert "No calculation was run or saved" in error.message
    assert response.headers["cache-control"] == "no-store"
    forbidden.assert_not_called()
    assert inventory(workspace) == before


def test_digest_cannot_activate_a_runtime(case):
    workspace, _, client = case
    data = body(workspace)
    data["release_digest"] = "sha256:" + "a" * 64
    assert (
        client.post(ROOT + "/preview", json=data).json()["error"]["code"]
        == "calculation_runtime_unavailable"
    )


def test_returning_test_provider_cannot_manufacture_success(case, monkeypatch):
    workspace, app, client = case
    before = inventory(workspace)
    provider = Mock(return_value={"saved": True, "profit": "999"})
    monkeypatch.setattr(app.state.runtime, "preview", provider)
    response = client.post(ROOT + "/preview", json=body(workspace))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "calculation_runtime_unavailable"
    validated = provider.call_args.args[0]
    assert validated.trade.account.account_id == workspace.samples["account_id"]
    assert validated.trade.snapshot.snapshot_id == workspace.samples["snapshots"]["USDJPY"]
    assert inventory(workspace) == before


def test_unexpected_provider_error_is_sanitized(case, monkeypatch):
    workspace, app, client = case
    before = inventory(workspace)
    monkeypatch.setattr(
        app.state.runtime, "preview", Mock(side_effect=RuntimeError("PRIVATE-SQL-PATH-SECRET"))
    )
    response = client.post(ROOT + "/preview", json=body(workspace))
    assert response.status_code == 500
    assert "PRIVATE" not in response.text
    assert CfdErrorEnvelope.model_validate(response.json()).error.code == "request_failed"
    assert inventory(workspace) == before


@pytest.mark.parametrize("attribute", ["_directory_identity", "_file_identity"])
def test_changed_owned_identity_rejected_before_connection(case, monkeypatch, attribute):
    workspace, _, client = case
    with monkeypatch.context() as patch:
        patch.setattr(workspace, attribute, (-1, -1))
        forbidden = Mock(side_effect=AssertionError("Changed identity must never connect"))
        patch.setattr(workspace.engine, "connect", forbidden)
        assert client.get(ROOT + "/status").status_code == 403
        forbidden.assert_not_called()


def test_runner_rejects_database_path_argument_before_import_or_provisioning():
    script = Path(__file__).resolve().parents[1] / "scripts" / "cfd_practice.py"
    result = subprocess.run(
        [sys.executable, str(script), "--database", "C:/never-open-this/ava.db"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr
    assert "NEW SYNTHETIC" not in result.stdout


@pytest.mark.parametrize(
    "change,status",
    [
        ("account", 404),
        ("snapshot", 404),
        ("scope", 422),
        ("uuid", 422),
        ("float", 422),
        ("int_money", 422),
        ("bool", 422),
        ("overclose", 422),
        ("time", 422),
        ("naive", 422),
        ("submicrosecond", 422),
        ("stop", 422),
        ("tick", 422),
        ("precision", 422),
        ("fx", 422),
        ("embedded", 422),
        ("key", 422),
        ("duplicate_exit", 422),
        ("release", 422),
        ("timezone_number", 422),
    ],
)
def test_invalid_requests_do_not_reach_runtime_or_write(case, monkeypatch, change, status):
    workspace, app, client = case
    data = body(workspace)
    trade = data["trade"]
    if change == "account":
        data["account_id"] = "unknown"
    if change == "snapshot":
        data["snapshot_id"] = "00000000-0000-4000-8000-000000000000"
    if change == "scope":
        data["account_id"] = workspace.samples["other_account_id"]
    if change == "uuid":
        data["position_reference"] = "invalid"
    if change == "float":
        trade["entry"]["lots"] = 0.1
    if change == "int_money":
        trade["entry"]["price"] = 150
    if change == "bool":
        trade["entry"]["lots"] = True
    if change == "overclose":
        trade["exits"][0]["lots"] = "0.11"
    if change == "time":
        trade["exits"][0]["executed_at"] = "2025-01-01T00:00:00Z"
    if change == "naive":
        data["as_of"] = "2026-10-01T10:00:00"
    if change == "submicrosecond":
        data["as_of"] = "2026-10-01T10:00:00.1234567Z"
    if change == "stop":
        trade["original_stop"] = "151"
    if change == "tick":
        trade["entry"]["price"] = "150.0001"
    if change == "precision":
        data["rounding"]["currencies"] = [dict(currency="USD", decimal_places=2)]
    if change == "fx":
        trade["reporting_policy"] = "explicit_rates"
    if change == "embedded":
        trade["account"] = {"account_id": "pretend"}
    if change == "key":
        data["DO-NOT-ECHO-SECRET"] = "DO-NOT-ECHO-VALUE"
    if change == "duplicate_exit":
        trade["exits"].append(deepcopy(trade["exits"][0]))
    if change == "release":
        data["release_digest"] = "file:///private/image"
    if change == "timezone_number":
        data["as_of"] = 1700000000
    before = inventory(workspace)
    forbidden = Mock(side_effect=AssertionError("Invalid input must not reach runtime"))
    monkeypatch.setattr(app.state.runtime, "preview", forbidden)
    response = client.post(ROOT + "/preview", json=data)
    assert response.status_code == status, response.text
    assert "DO-NOT-ECHO" not in response.text
    CfdErrorEnvelope.model_validate(response.json())
    forbidden.assert_not_called()
    assert inventory(workspace) == before


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://example.com"},
        {"Origin": "http://127.0.0.1:3300"},
        {"Host": "example.com:8003"},
        {"Host": "127.0.0.1:8000"},
        {"X-Forwarded-Host": "127.0.0.1:8003"},
        {"Forwarded": "for=127.0.0.1"},
        {"X-AVA-Local": "journal-v1"},
        {"X-AVA-Local": ""},
    ],
)
def test_network_guards(case, headers):
    workspace, _, client = case
    before = inventory(workspace)
    assert client.get(ROOT + "/status", headers=headers).status_code == 403
    assert inventory(workspace) == before


def test_external_client_and_missing_local_header(case):
    workspace, app, _ = case
    with TestClient(app, base_url=BASE, client=("203.0.113.1", 50000), headers=HEADER) as c:
        assert c.get(ROOT + "/status").status_code == 403
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 50000)) as c:
        assert c.get(ROOT + "/status").status_code == 403


@pytest.mark.parametrize(
    "method,path,expected",
    [
        ("post", "/positions", 405),
        ("get", "/positions", 422),
        ("get", "/positions/anything", 422),
        ("post", "/positions/anything/revisions", 405),
        ("delete", "/positions/anything", 405),
        ("post", "/status", 405),
        ("get", "/preview", 405),
        ("options", "/preview", 405),
        ("get", "/../../docs", 404),
    ],
)
def test_unsupported_operations(case, method, path, expected):
    workspace, _, client = case
    before = inventory(workspace)
    assert client.request(method.upper(), ROOT + path).status_code == expected
    assert inventory(workspace) == before


@pytest.mark.parametrize(
    "content,headers,status",
    [
        ('{"x":1,"x":2}', {}, 400),
        ('{"x":NaN}', {}, 400),
        ("{", {}, 400),
        ('{"x":' + "[" * 20 + "0" + "]" * 20 + "}", {}, 400),
        ("{}", {"Content-Type": "text/plain"}, 415),
        ("{}", {"Content-Encoding": "gzip"}, 415),
        ("{}", {"Content-Length": "-1"}, 400),
        ("{}", {"Content-Length": "99999999"}, 413),
        ("{}", {"Content-Length": "1"}, 400),
    ],
)
def test_framing_and_json_limits(case, content, headers, status):
    _, _, client = case
    headers = {"Content-Type": "application/json", **headers}
    response = client.post(ROOT + "/preview", content=content, headers=headers)
    assert response.status_code == status, response.text
    assert response.headers["cache-control"] == "no-store"


def test_duplicate_headers_rejected(case):
    _, _, client = case
    response = client.get(ROOT + "/status", headers=[("Host", "127.0.0.1:8003"), ("Host", "evil")])
    assert response.status_code == 400


def test_serving_session_is_database_read_only(case):
    workspace, _, _ = case
    with workspace.read_session() as session:
        with pytest.raises(OperationalError, match="readonly"):
            session.execute(text("DELETE FROM journal_accounts"))


def test_rate_limit(case):
    workspace, _, _ = case
    app = create_app(
        workspace=workspace, settings=CfdPracticeSettings(enabled=True, preview_per_minute=1)
    )
    with TestClient(app, base_url=BASE, client=("127.0.0.1", 50000), headers=HEADER) as c:
        assert c.post(ROOT + "/preview", json=body(workspace)).status_code == 503
        response = c.post(ROOT + "/preview", json=body(workspace))
        assert response.status_code == 429
        assert response.headers["retry-after"] == "60"


def test_canonical_input_is_exact_and_preserves_snapshot(case):
    workspace, _, _ = case
    original = body(workspace)
    other = deepcopy(original)
    other["trade"]["entry"]["price"] = "150.00000"
    other["trade"]["entry"]["lots"] = "0.1000"
    other["as_of"] = "2026-10-01T11:00:00+01:00"
    other["rounding"]["currencies"].reverse()
    with workspace.read_session() as session:
        a = bind_preview(session, CfdPreviewCommandV1.model_validate(original))
        b = bind_preview(session, CfdPreviewCommandV1.model_validate(other))
    with localcontext() as context:
        context.prec = 2
        assert canonical_input(a) == canonical_input(b)
        assert json.loads(canonical_input(a))["trade"]["snapshot"] == a.trade.snapshot.model_dump(
            mode="json"
        )
    assert a.trade.snapshot.specification.tick_size == Decimal("0.001")


def test_b3a_compatibility_allowlist_matches_existing_engine():
    from app.analytics.cfd import SUPPORTED_MODES
    from app.services.cfd_preview import SUPPORTED

    assert SUPPORTED == SUPPORTED_MODES


def test_no_openapi_or_normal_app_mount(case):
    from app.main import app as normal_app

    _, app, client = case
    assert client.get("/openapi.json").status_code == 404
    assert all(not getattr(route, "path", "").startswith(ROOT) for route in normal_app.routes)
    assert set(app.openapi()["paths"]) == {
        ROOT + "/status",
        ROOT + "/preview",
        ROOT + "/positions",
        ROOT + "/positions/{position_id}",
        ROOT + "/positions/{position_id}/revisions",
        ROOT + "/positions/{position_id}/revisions/{revision_no}",
    }


def test_streaming_body_limit_without_content_length(case):
    workspace, _, _ = case
    app = create_app(
        workspace=workspace, settings=CfdPracticeSettings(enabled=True, max_body_bytes=8)
    )

    async def run():
        messages = []
        chunks = iter([b'{"x":', b'"0123456789"}'])

        async def receive():
            chunk = next(chunks)
            return {"type": "http.request", "body": chunk, "more_body": chunk == b'{"x":'}

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": ROOT + "/preview",
            "raw_path": b"/",
            "query_string": b"",
            "server": ("127.0.0.1", 8003),
            "client": ("127.0.0.1", 1),
            "headers": [
                (b"host", b"127.0.0.1:8003"),
                (b"x-ava-local", b"cfd-practice-v1"),
                (b"content-type", b"application/json"),
            ],
        }
        await app(scope, receive, send)
        assert messages[0]["status"] == 413

    asyncio.run(run())

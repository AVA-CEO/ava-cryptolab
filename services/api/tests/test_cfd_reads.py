"""B3B-R uses only newly minted databases and explicitly synthetic evidence."""

from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, inspect, select, text

from app.cfd_practice import create_app
from app.core.cfd_settings import CfdPracticeSettings
from app.database.cfd_session import new_cfd_workspace
from app.models.cfd import TABLES
from app.schemas.cfd_reads import CfdPositionPage, CfdReadResponseV1, CfdRevisionPage

ROOT = "/api/v1/cfd/positions"
HEADER = {"X-AVA-Local": "cfd-practice-v1"}


@pytest.fixture
def case():
    with new_cfd_workspace() as workspace:
        app = create_app(workspace=workspace, settings=CfdPracticeSettings(enabled=True))
        with TestClient(
            app, base_url="http://127.0.0.1:8003", client=("127.0.0.1", 50000), headers=HEADER
        ) as client:
            yield workspace, app, client


def reference(workspace, index=0):
    return workspace.samples["read_catalog"][index]


def inventory(workspace):
    with workspace.read_session() as session:
        return {
            name: session.execute(text(f'SELECT * FROM "{name}"')).all()
            for name in inspect(session.get_bind()).get_table_names()
        }


def get(client, ref, suffix="", **params):
    return client.get(
        ROOT + "/" + ref["position_id"] + suffix,
        params=dict(account_id=ref["account_id"], **params),
    )


def test_current_and_historical_preserved_evidence(case):
    workspace, _, client = case
    ref = reference(workspace)
    before = inventory(workspace)
    response = get(client, ref)
    assert response.status_code == 200, response.text
    current = CfdReadResponseV1.model_validate(response.json())
    old_response = get(client, ref, "/revisions/1")
    assert old_response.status_code == 200, old_response.text
    old = CfdReadResponseV1.model_validate(old_response.json())
    assert current.revision_no == 2 and not current.historical
    assert old.revision_no == 1 and old.historical
    assert current.result.native.net_pnl.raw == 2400
    assert old.result.native.net_pnl.raw == 700
    assert current.result.reporting.net_pnl.raw == 12
    assert old.result.reporting.net_pnl.raw == Decimal("3.5")
    assert current.original_risk_sha256 == old.original_risk_sha256
    assert (
        current.result.native.original_planned_risk.raw
        == old.result.native.original_planned_risk.raw
        == 2000
    )
    assert current.provenance.kind == "synthetic_fixture"
    assert (
        not current.provenance.accepted_calculation and not current.provenance.broker_authenticated
    )
    assert (
        current.replay.status == "not_run" and current.replay.availability == "runtime_unavailable"
    )
    assert response.headers["etag"].endswith(current.result_sha256 + '"')
    assert response.headers["cache-control"] == "no-store"
    assert inventory(workspace) == before


def test_position_and_revision_pagination(case):
    workspace, _, client = case
    ref = reference(workspace)
    items, cursor = [], None
    for _ in range(4):
        params = dict(account_id=ref["account_id"], limit=1)
        if cursor:
            params["cursor"] = cursor
        response = client.get(ROOT, params=params)
        assert response.status_code == 200, response.text
        page = CfdPositionPage.model_validate(response.json())
        items.extend(str(item.position_id) for item in page.items)
        cursor = page.next_cursor
        if cursor is None:
            break
    assert len(items) == len(set(items)) == 3
    page = CfdRevisionPage.model_validate(get(client, ref, "/revisions", limit=1).json())
    assert [r.revision_no for r in page.items] == [1]
    second = CfdRevisionPage.model_validate(
        get(client, ref, "/revisions", limit=1, cursor=page.next_cursor).json()
    )
    assert [r.revision_no for r in second.items] == [2] and second.next_cursor is None


@pytest.mark.parametrize("suffix", ["", "/revisions", "/revisions/1"])
def test_foreign_account_matches_missing_resource(case, suffix):
    workspace, _, client = case
    ref = deepcopy(reference(workspace))
    ref["account_id"] = workspace.samples["other_account_id"]
    response = get(client, ref, suffix)
    ref["position_id"] = str(uuid4())
    missing = get(client, ref, suffix)
    assert response.status_code == missing.status_code == 404
    assert response.json()["error"]["code"] == missing.json()["error"]["code"]
    assert "native" not in response.text and "reporting" not in response.text


def test_no_writes_or_calculator_calls_on_all_gets(case, monkeypatch):
    import subprocess

    from app.analytics import cfd, cfd_positions

    workspace, app, client = case
    ref = reference(workspace)
    before = inventory(workspace)
    forbidden = Mock(side_effect=AssertionError("Read must not execute or mutate"))
    monkeypatch.setattr(cfd, "calculate_cfd", forbidden)
    monkeypatch.setattr(cfd_positions, "calculate_position", forbidden)
    monkeypatch.setattr(app.state.runtime, "preview", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    statements = []

    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement.strip().split()[0].upper())

    event.listen(workspace.engine, "before_cursor_execute", capture)
    try:
        for path in ("", "/revisions", "/revisions/1", "/revisions/2"):
            assert get(client, ref, path).status_code == 200
        assert client.get(ROOT, params=dict(account_id=ref["account_id"])).status_code == 200
    finally:
        event.remove(workspace.engine, "before_cursor_execute", capture)
    assert set(statements) <= {"BEGIN", "SELECT", "PRAGMA"}
    forbidden.assert_not_called()
    assert inventory(workspace) == before
    with workspace.read_session() as session:
        assert session.execute(select(TABLES["cfd_requests"])).all() == []


@contextmanager
def attacked(monkeypatch, change):
    from cfd_read_attacks import attack

    from app.services import cfd_read_fixtures

    original = cfd_read_fixtures.seed_read_fixtures

    def seed(workspace, session):
        original(workspace, session)
        attack(workspace, session, change)

    with monkeypatch.context() as patch:
        patch.setattr(cfd_read_fixtures, "seed_read_fixtures", seed)
        with new_cfd_workspace() as workspace:
            app = create_app(workspace=workspace, settings=CfdPracticeSettings(enabled=True))
            with TestClient(
                app, base_url="http://127.0.0.1:8003", client=("127.0.0.1", 50000), headers=HEADER
            ) as client:
                yield workspace, client


@pytest.mark.parametrize(
    "change",
    [
        "snapshot",
        "account_server",
        "account_hash",
        "root_entry",
        "root_stop",
        "risk_hash",
        "risk_redefined",
        "fill",
        "cost",
        "fx",
        "event_key",
        "input_hash",
        "input_rehashed",
        "duplicate_input_key",
        "result_hash",
        "result_rehashed",
        "numeric_result",
        "manifest_hash",
        "manifest_rehashed",
        "unsealed",
        "invalid_head",
        "missing_entry",
    ],
)
def test_tampered_values_withheld_without_repair(monkeypatch, change):
    with attacked(monkeypatch, change) as (workspace, client):
        before = inventory(workspace)
        response = get(client, reference(workspace))
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "integrity_failure"
        assert "native" not in response.text and "reporting" not in response.text
        assert "SYNTHETIC" not in response.text
        # Collection endpoints also withhold the whole page, not a partial result.
        response = client.get(ROOT, params=dict(account_id=reference(workspace)["account_id"]))
        assert response.status_code == 409
        assert inventory(workspace) == before


@pytest.mark.parametrize(
    "change",
    [
        "unsupported_canonicalizer",
        "unsupported_policy",
        "unsupported_request",
        "unsupported_input",
        "unsupported_result",
        "unsupported_manifest",
    ],
)
def test_unsupported_historical_versions_are_not_reinterpreted(monkeypatch, change):
    with attacked(monkeypatch, change) as (workspace, client):
        before = inventory(workspace)
        response = get(client, reference(workspace))
        assert response.status_code == 503, response.text
        assert response.json()["error"]["code"] == "historical_schema_unavailable"
        assert "native" not in response.text
        assert inventory(workspace) == before


def test_unpublished_position_hidden(monkeypatch):
    with attacked(monkeypatch, "unpublished") as (workspace, client):
        ref = reference(workspace)
        assert get(client, ref).status_code == 404
        assert get(client, ref, "/revisions/1").status_code == 404
        page = client.get(ROOT, params=dict(account_id=ref["account_id"])).json()
        assert ref["position_id"] not in [item["position_id"] for item in page["items"]]


def test_unpublished_revision_not_returned(monkeypatch):
    with attacked(monkeypatch, "orphan_revision") as (workspace, client):
        ref = reference(workspace)
        assert get(client, ref).json()["revision_no"] == 2
        assert get(client, ref, "/revisions/3").status_code == 404
        assert [item["revision_no"] for item in get(client, ref, "/revisions").json()["items"]] == [
            1,
            2,
        ]


@pytest.mark.parametrize(
    "params,expected",
    [
        ({}, 422),
        ({"account_id": "unknown"}, 404),
        ({"limit": "0"}, 422),
        ({"limit": "101"}, 422),
        ({"limit": "1.0"}, 422),
        ({"cursor": "not-a-cursor"}, 400),
        ({"cursor": "x" * 801}, 422),
        ({"sort": "secret-unapproved-column"}, 400),
    ],
)
def test_query_validation(case, params, expected):
    workspace, _, client = case
    supplied = {"account_id": reference(workspace)["account_id"], **params} if params else {}
    response = client.get(ROOT, params=supplied)
    assert response.status_code == expected, response.text


@pytest.mark.parametrize(
    "suffix", ["/revisions/0", "/revisions/-1", "/revisions/1.0", "/revisions/999"]
)
def test_invalid_or_missing_revision(case, suffix):
    workspace, _, client = case
    response = get(client, reference(workspace), suffix)
    assert response.status_code == (404 if suffix.endswith("999") else 422)


def test_cursor_bound_to_account_collection_position_limit_and_session(case):
    workspace, _, client = case
    ref = reference(workspace)
    params = dict(account_id=ref["account_id"], limit=1)
    token = client.get(ROOT, params=params).json()["next_cursor"]
    for override in (
        dict(account_id=workspace.samples["other_account_id"]),
        dict(limit=2),
        dict(cursor=token + "x"),
    ):
        assert client.get(ROOT, params={**params, "cursor": token, **override}).status_code == 400
    assert get(client, ref, "/revisions", limit=1, cursor=token).status_code == 400
    rev_token = get(client, ref, "/revisions", limit=1).json()["next_cursor"]
    assert (
        get(client, reference(workspace, 1), "/revisions", limit=1, cursor=rev_token).status_code
        == 400
    )
    other_app = create_app(workspace=workspace, settings=CfdPracticeSettings(enabled=True))
    with TestClient(
        other_app, base_url="http://127.0.0.1:8003", client=("127.0.0.1", 1), headers=HEADER
    ) as other:
        assert other.get(ROOT, params={**params, "cursor": token}).status_code == 400


def test_duplicate_and_oversized_queries_rejected(case):
    workspace, _, client = case
    account = reference(workspace)["account_id"]
    assert (
        client.get(ROOT, params=[("account_id", account), ("account_id", account)]).status_code
        == 400
    )
    assert client.get(ROOT, params=dict(account_id=account, cursor="x" * 3000)).status_code == 400


@pytest.mark.parametrize(
    "method,suffix,expected",
    [
        ("POST", "", 405),
        ("PUT", "", 405),
        ("DELETE", "", 405),
        ("POST", "/revisions", 405),
        ("PATCH", "/revisions/1", 405),
        ("POST", "/void", 404),
        ("POST", "/archive", 404),
        ("POST", "/replace", 404),
    ],
)
def test_mutations_remain_unavailable(case, method, suffix, expected):
    workspace, _, client = case
    ref = reference(workspace)
    before = inventory(workspace)
    url = ROOT if not suffix else ROOT + "/" + ref["position_id"] + suffix
    response = client.request(method, url, json={"profit": "1000000"})
    assert response.status_code == expected
    assert inventory(workspace) == before


def test_new_seed_and_reads_never_execute_calculator(monkeypatch):
    from app.analytics import cfd, cfd_positions

    forbidden = Mock(
        side_effect=AssertionError("No financial calculator during provisioning or GET")
    )
    monkeypatch.setattr(cfd, "calculate_cfd", forbidden)
    monkeypatch.setattr(cfd_positions, "calculate_position", forbidden)
    with new_cfd_workspace() as workspace:
        app = create_app(workspace=workspace, settings=CfdPracticeSettings(enabled=True))
        with TestClient(
            app, base_url="http://127.0.0.1:8003", client=("127.0.0.1", 1), headers=HEADER
        ) as client:
            assert get(client, reference(workspace)).status_code == 200
    forbidden.assert_not_called()


def test_guard_rejects_normal_target_for_every_read_route(case, monkeypatch):
    from sqlalchemy.engine import make_url

    workspace, _, client = case
    ref = reference(workspace)
    with monkeypatch.context() as patch:
        patch.setattr(workspace.engine, "url", make_url("sqlite:///services/api/ava.db"))
        forbidden = Mock(side_effect=AssertionError("Normal target must never connect"))
        patch.setattr(workspace.engine, "connect", forbidden)
        for suffix in ("", "/revisions", "/revisions/1"):
            assert get(client, ref, suffix).status_code == 403
        assert client.get(ROOT, params=dict(account_id=ref["account_id"])).status_code == 403
        forbidden.assert_not_called()


def test_read_transaction_is_physically_read_only_and_consistent(case):
    workspace, _, _ = case
    with workspace.read_session() as session:
        connection = session.connection()
        assert connection.connection.driver_connection.in_transaction is True
        assert connection.exec_driver_sql("PRAGMA query_only").scalar() == 1
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_fixture_provisioning_cannot_reseed_ready_workspace(case):
    from app.database.cfd_session import CfdTargetRejected
    from app.services.cfd_read_fixtures import seed_read_fixtures

    workspace, _, _ = case
    before = inventory(workspace)
    with workspace.read_session() as session:
        with pytest.raises(CfdTargetRejected):
            seed_read_fixtures(workspace, session)
    assert inventory(workspace) == before


def test_status_and_preview_keep_option_a_after_reads(case):
    workspace, _, client = case
    assert get(client, reference(workspace)).status_code == 200
    status = client.get("/api/v1/cfd/status").json()
    assert status["can_read_saved_positions"] is True
    assert status["read_provenance"] == "synthetic_fixture_only"
    assert status["can_create"] is status["preview_available"] is status["host_fallback"] is False
    response = client.post("/api/v1/cfd/preview", json=workspace.samples["previews"]["USDJPY"])
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "calculation_runtime_unavailable"


def test_read_access_guards_reject_before_connection(case, monkeypatch):
    workspace, _, client = case
    ref = reference(workspace)
    with monkeypatch.context() as patch:
        forbidden = Mock(side_effect=AssertionError("Denied request must not connect"))
        patch.setattr(workspace.engine, "connect", forbidden)
        for headers in (
            {"Origin": "https://example.com"},
            {"Host": "example.com:8003"},
            {"X-AVA-Local": ""},
        ):
            for suffix in ("", "/revisions", "/revisions/1"):
                response = client.get(
                    ROOT + "/" + ref["position_id"] + suffix,
                    params=dict(account_id=ref["account_id"]),
                    headers=headers,
                )
                assert response.status_code == 403
        forbidden.assert_not_called()


def test_reads_default_disabled_with_no_database(monkeypatch):
    monkeypatch.setenv("CFD_PRACTICE_ENABLED", "true")
    app = create_app()
    with TestClient(
        app, base_url="http://127.0.0.1:8003", client=("127.0.0.1", 1), headers=HEADER
    ) as client:
        assert client.get(ROOT, params=dict(account_id="unknown")).status_code == 404
        assert (
            client.get(ROOT + "/" + str(uuid4()), params=dict(account_id="unknown")).status_code
            == 404
        )

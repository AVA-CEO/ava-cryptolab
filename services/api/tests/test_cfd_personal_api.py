"""Local P3 HTTP boundary tests, with only newly minted disposable databases."""

from unittest.mock import Mock
from uuid import uuid4

import pytest
import test_cfd_personal_persistence as fixtures
from fastapi.testclient import TestClient

from app.cfd_personal import create_app
from app.core.cfd_errors import CfdProblem
from app.core.cfd_settings import CfdPracticeSettings
from app.schemas.cfd_positions import CfdPositionResult, PositionUnavailable
from app.services.cfd_personal_codec import result_text

personal_runtime = fixtures.personal_runtime
workspace = fixtures.workspace
command, inventory = fixtures.command, fixtures.inventory


@pytest.fixture
def client(workspace, personal_runtime):
    app = create_app(workspace=workspace, runtime=personal_runtime)
    with TestClient(
        app,
        base_url="http://127.0.0.1:8004",
        client=("127.0.0.1", 123),
        headers={"X-AVA-Local": "cfd-practice-v1"},
    ) as value:
        yield value


def draft(workspace, personal_runtime):
    value = command(workspace)
    value["release_digest"] = personal_runtime.release_digest
    return value


def test_http_preview_save_reopen_and_retry(client, workspace, personal_runtime):
    value, key = draft(workspace, personal_runtime), str(uuid4())
    before = inventory(workspace)
    preview = client.post("/api/v1/cfd/preview", json=value)
    assert preview.status_code == 200, preview.text
    assert preview.json()["saved"] is False
    assert preview.json()["accepted_calculation"] is False
    assert inventory(workspace) == before
    saved = client.post("/api/v1/cfd/positions", json=value, headers={"Idempotency-Key": key})
    assert saved.status_code == 201, saved.text
    record = saved.json()
    assert result_text(CfdPositionResult.model_validate(record["result"])) == result_text(
        CfdPositionResult.model_validate(preview.json()["result"])
    )
    assert record["provenance"]["broker_authenticated"] is False
    query = {"account_id": value["account_id"]}
    url = "/api/v1/cfd/positions/" + record["position_id"]
    reopened = client.get(url, params=query)
    assert reopened.status_code == 200 and reopened.json() == record
    assert reopened.headers["cache-control"] == "no-store"
    assert reopened.headers["etag"].startswith('"personal-v1:')
    retried = client.post("/api/v1/cfd/positions", json=value, headers={"Idempotency-Key": key})
    assert retried.status_code == 201 and retried.json() == record
    page = client.get("/api/v1/cfd/positions", params=query)
    assert page.status_code == 200 and len(page.json()["items"]) == 1


@pytest.mark.parametrize(
    "headers",
    [{"Origin": "http://evil.test"}, {"X-AVA-Local": "bad"}, {"X-Forwarded-For": "127.0.0.1"}],
)
def test_untrusted_http_access_rejected(client, headers):
    response = client.get("/api/v1/cfd/positions?account_id=unknown", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "practice_access_denied"


@pytest.mark.parametrize("key", [None, "", "not-a-uuid", "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"])
def test_idempotency_header_required(client, workspace, personal_runtime, key):
    before = inventory(workspace)
    response = client.post(
        "/api/v1/cfd/positions",
        json=draft(workspace, personal_runtime),
        headers={} if key is None else {"Idempotency-Key": key},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_idempotency_key"
    assert inventory(workspace) == before


@pytest.mark.parametrize(
    "query,expected",
    [
        ("", 422),
        ("?limit=3", 422),
        ("?account_id=x&limit=0", 422),
        ("?account_id=x&unknown=true", 400),
        ("?account_id=x&account_id=y", 400),
    ],
)
def test_list_requires_unambiguous_scope(client, query, expected):
    assert client.get("/api/v1/cfd/positions" + query).status_code == expected


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_unsupported_mutations_rejected(client, method, workspace):
    before = inventory(workspace)
    assert (
        client.request(method.upper(), "/api/v1/cfd/positions/" + str(uuid4()), json={}).status_code
        == 405
    )
    assert inventory(workspace) == before


def test_read_survives_runtime_revocation_without_execution(
    client, workspace, personal_runtime, monkeypatch
):
    value = draft(workspace, personal_runtime)
    saved = client.post(
        "/api/v1/cfd/positions", json=value, headers={"Idempotency-Key": str(uuid4())}
    )
    assert saved.status_code == 201, saved.text
    before = inventory(workspace)
    forbidden = Mock(side_effect=AssertionError("Reads never touch current calculator/runtime"))
    for name in ("verify", "preview", "calculate"):
        monkeypatch.setattr(personal_runtime, name, forbidden)
    response = client.get(
        "/api/v1/cfd/positions/" + saved.json()["position_id"],
        params={"account_id": value["account_id"]},
    )
    assert response.status_code == 200 and response.json() == saved.json()
    assert inventory(workspace) == before
    forbidden.assert_not_called()


def test_release_verifier_failure_blocks_save(client, workspace, personal_runtime, monkeypatch):
    before = inventory(workspace)

    def rejected(*args, **kwargs):
        raise CfdProblem(503, "calculation_release_unapproved", "Local release is unavailable.")

    monkeypatch.setattr(personal_runtime, "verify", rejected)
    response = client.post(
        "/api/v1/cfd/positions",
        json=draft(workspace, personal_runtime),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "calculation_release_unapproved"
    assert inventory(workspace) == before


def test_missing_stop_preserves_unavailable_risk(client, workspace, personal_runtime):
    value = draft(workspace, personal_runtime)
    value["trade"]["original_stop"] = None
    response = client.post(
        "/api/v1/cfd/positions", json=value, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 201, response.text
    risk = response.json()["original_risk_basis"]["native"]
    assert risk["raw"] is None and risk["unavailable_reason"] is not None
    assert response.json()["result"]["native"]["realized_r"]["raw"] is None


def test_default_disabled_factory_cannot_be_enabled_by_request(workspace, personal_runtime):
    with pytest.raises(ValueError):
        create_app(workspace=workspace, runtime=personal_runtime, settings=CfdPracticeSettings())


def test_invalid_financial_schema_has_no_rows(client, workspace, personal_runtime):
    before = inventory(workspace)
    value = draft(workspace, personal_runtime)
    value["trade"]["entry"]["lots"] = 0.1
    response = client.post(
        "/api/v1/cfd/positions", json=value, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 422
    assert inventory(workspace) == before


def test_unavailable_calculation_cannot_be_saved(client, workspace, personal_runtime, monkeypatch):
    before = inventory(workspace)
    monkeypatch.setattr(
        personal_runtime,
        "calculate",
        lambda *args, **kwargs: PositionUnavailable(
            reason_code="unsupported_mode", message="Synthetic unsupported mode test."
        ),
    )
    response = client.post(
        "/api/v1/cfd/positions",
        json=draft(workspace, personal_runtime),
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "calculation_unavailable"
    assert inventory(workspace) == before


def test_unpreviewed_release_digest_rejected(client, workspace, personal_runtime):
    before = inventory(workspace)
    value = draft(workspace, personal_runtime)
    value["release_digest"] = "sha256:" + "0" * 64
    response = client.post(
        "/api/v1/cfd/positions", json=value, headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "release_mismatch"
    assert inventory(workspace) == before

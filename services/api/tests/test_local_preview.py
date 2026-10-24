"""Real pinned local worker; fresh disposable ledgers only. No accepted saves."""

from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.cfd_practice import create_app
from app.core.cfd_errors import CfdProblem
from app.core.cfd_settings import CfdPracticeSettings
from app.database.cfd_session import new_cfd_workspace
from app.services.cfd_local_release import LocalPreviewRuntime, prepare_release


@pytest.fixture(scope="module")
def release(tmp_path_factory):
    directory = tmp_path_factory.mktemp("local-release") / "release"
    reference = prepare_release(directory)
    return directory, reference


@pytest.fixture
def local_case(release):
    with new_cfd_workspace() as workspace:
        app = create_app(
            workspace=workspace,
            settings=CfdPracticeSettings(enabled=True),
            local_preview_runtime=LocalPreviewRuntime(*release, test_fixture=True),
        )
        with TestClient(
            app,
            base_url="http://127.0.0.1:8003",
            client=("127.0.0.1", 50000),
            headers={"X-AVA-Local": "cfd-practice-v1"},
        ) as client:
            yield workspace, client


def rows(workspace):
    with workspace.read_session() as session:
        return {
            name: session.execute(text(f'SELECT * FROM "{name}"')).all()
            for name in inspect(session.get_bind()).get_table_names()
        }


@pytest.mark.parametrize(
    "symbol,expected", [("EURUSD", "8"), ("USDJPY", "800"), ("XAUUSD", "8"), ("XAGUSD", "4")]
)
def test_actual_worker_exact_native_and_no_writes(local_case, symbol, expected):
    workspace, client = local_case
    before = rows(workspace)
    response = client.post("/api/v1/cfd/preview", json=workspace.samples["previews"][symbol])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["saved"] is False and body["can_create"] is False
    assert Decimal(body["result"]["native"]["gross_pnl"]["raw"]) == Decimal(expected)
    assert body["result"]["remaining_lots"] == "0.06"
    assert rows(workspace) == before
    assert client.post("/api/v1/cfd/positions", json={}).status_code in (404, 405)


def test_two_exits_and_incurred_once_cost(local_case):
    workspace, client = local_case
    body = deepcopy(workspace.samples["previews"]["EURUSD"])
    body["trade"]["exits"].append(
        dict(execution_id="second-exit", executed_at=body["as_of"], price="1.10300", lots="0.06")
    )
    body["trade"]["adjustments"] = [
        dict(
            adjustment_id="cost",
            kind="commission",
            amount="-4",
            description="Synthetic total cost",
            currency="USD",
            occurred_at=body["trade"]["entry"]["executed_at"],
            source=dict(kind="manual", reference="Synthetic total cost"),
        )
    ]
    response = client.post("/api/v1/cfd/preview", json=body)
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["state"] == "closed"
    assert Decimal(result["native"]["net_pnl"]["raw"]) == 22
    assert Decimal(result["native"]["realized_r"]["raw"]) == Decimal("1.1")


def test_scope_overclosing_and_digest_rejected_no_writes(local_case):
    workspace, client = local_case
    before = rows(workspace)
    original = workspace.samples["previews"]["EURUSD"]
    for field in ("scope", "lots", "release"):
        body = deepcopy(original)
        if field == "scope":
            body["account_id"] = workspace.samples["other_account_id"]
        elif field == "lots":
            body["trade"]["exits"][0]["lots"] = "0.11"
        else:
            body["release_digest"] = "sha256:" + "0" * 64
        assert client.post("/api/v1/cfd/preview", json=body).status_code == 422
    assert rows(workspace) == before


def test_wrong_approval_and_changed_artifact_fail_closed(release, tmp_path):
    import shutil

    with pytest.raises(CfdProblem):
        LocalPreviewRuntime(release[0], "sha256:" + "0" * 64)
    directory = tmp_path / "changed"
    shutil.copytree(release[0], directory)
    worker = directory / "payload" / "worker.py"
    worker.write_text("raise SystemExit(0)", encoding="utf-8")
    with pytest.raises(CfdProblem):
        LocalPreviewRuntime(directory, release[1])


def test_prepare_never_overwrites(release):
    with pytest.raises(ValueError):
        prepare_release(Path(release[0]))

"""P3 accepted-practice persistence: NEW disposable databases and synthetic accounts only."""

import re
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from threading import Barrier
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, inspect, text, update
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.cfd_errors import CfdProblem
from app.database.cfd_personal_session import new_personal_workspace
from app.models.cfd import TABLES
from app.schemas.cfd_api import CfdPreviewCommandV1
from app.services.cfd_personal_codec import canonical, digest
from app.services.cfd_personal_positions import (
    create_position,
    position_page,
    read_position,
)
from app.services.cfd_personal_release import PersonalRuntime, prepare_personal_release
from app.services.cfd_preview import bind_preview


@pytest.fixture(scope="module")
def personal_runtime(tmp_path_factory):
    directory = tmp_path_factory.mktemp("p3-release") / "release"
    release = prepare_personal_release(directory, test_fixture=True)
    return PersonalRuntime(directory, release, test_fixture=True)


@pytest.fixture
def workspace():
    with new_personal_workspace() as value:
        yield value


def command(workspace, symbol="EURUSD", *, full=False):
    value = deepcopy(workspace.samples["previews"][symbol])
    identity = str(uuid4())
    value["position_reference"] = identity
    value["trade"]["entry"]["execution_id"] = "entry-" + identity
    for index, fill in enumerate(value["trade"]["exits"]):
        fill["execution_id"] = f"exit-{index}-{identity}"
        if full:
            fill["lots"] = value["trade"]["entry"]["lots"]
    return value


def inventory(workspace):
    with workspace.read_session() as session:
        return {
            name: session.execute(text(f'SELECT * FROM "{name}"')).all()
            for name in inspect(session.get_bind()).get_table_names()
        }


def wire(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def save(workspace, runtime, value, key=None, **kwargs):
    value = deepcopy(value)
    value["release_digest"] = runtime.release_digest
    return create_position(
        workspace, runtime, CfdPreviewCommandV1.model_validate(value), key or str(uuid4()), **kwargs
    )


def retrieve(workspace, value):
    row = wire(value)
    with workspace.read_session() as session:
        return wire(read_position(session, row["account_id"], str(row["position_id"])))


@pytest.mark.parametrize(
    "symbol,expected,risk",
    [
        ("EURUSD", "8", "20"),
        ("USDJPY", "800", "2000"),
        ("XAUUSD", "8", "20"),
        ("XAGUSD", "4", "10"),
    ],
)
def test_actual_calculation_save_and_reopen(workspace, personal_runtime, symbol, expected, risk):
    body = command(workspace, symbol)
    accepted = wire(save(workspace, personal_runtime, body))
    reopened = retrieve(workspace, accepted)
    assert reopened == accepted
    assert str(accepted["position_id"]) == body["position_reference"]
    assert accepted["revision_no"] == 1
    result = accepted["result"]
    assert isinstance(result["native"]["gross_pnl"]["raw"], str)
    assert Decimal(result["native"]["gross_pnl"]["raw"]) == Decimal(expected)
    assert Decimal(result["native"]["original_planned_risk"]["raw"]) == Decimal(risk)
    assert Decimal(result["native"]["realized_r"]["raw"]) == Decimal("0.4")
    assert result["state"] == "partial" and Decimal(result["remaining_lots"]) == Decimal("0.06")
    assert accepted["provenance"]["broker_authenticated"] is False
    assert accepted["replay"]["status"] == "not_run"
    with workspace.read_session() as session:
        assert session.execute(text("PRAGMA integrity_check")).scalar() == "ok"
        assert session.execute(text("PRAGMA foreign_key_check")).all() == []


def test_multiple_exits_costs_original_risk_and_breakeven(workspace, personal_runtime):
    body = command(workspace)
    body["trade"]["exits"].append(
        dict(
            execution_id="second-" + body["position_reference"],
            lots="0.06",
            price="1.10300",
            executed_at=body["as_of"],
        )
    )
    body["trade"]["adjustments"] = [
        dict(
            adjustment_id=f"cost-{index}-{body['position_reference']}",
            kind=kind,
            amount=amount,
            currency="USD",
            occurred_at=body["trade"]["entry"]["executed_at"],
            description="Synthetic incurred cost",
            source=dict(kind="manual", reference="SYNTHETIC P3 cost"),
        )
        for index, (kind, amount) in enumerate(
            (("commission", "-2"), ("swap", "-1"), ("fee", "-1"))
        )
    ]
    accepted = wire(save(workspace, personal_runtime, body))
    result = accepted["result"]
    assert Decimal(result["native"]["gross_pnl"]["raw"]) == 26
    assert Decimal(result["native"]["net_pnl"]["raw"]) == 22
    assert Decimal(result["native"]["original_planned_risk"]["raw"]) == 20
    assert Decimal(result["native"]["realized_r"]["raw"]) == Decimal("1.1")
    assert result["state"] == "closed" and Decimal(result["remaining_lots"]) == 0
    reopened = retrieve(workspace, accepted)
    assert reopened["original_risk_basis"] == accepted["original_risk_basis"]
    assert len(reopened["input"]["trade"]["adjustments"]) == 3


@pytest.mark.parametrize(
    "direction,price,stop,expected",
    [
        ("sell", "1.09800", "1.10200", "20"),
        ("buy", "1.09800", "1.09800", "-20"),
        ("buy", "1.10000", "1.09800", "0"),
    ],
)
def test_short_loss_and_breakeven(workspace, personal_runtime, direction, price, stop, expected):
    body = command(workspace, full=True)
    body["trade"]["direction"] = direction
    body["trade"]["original_stop"] = stop
    body["trade"]["exits"][0]["price"] = price
    result = wire(save(workspace, personal_runtime, body))["result"]
    assert Decimal(result["native"]["net_pnl"]["raw"]) == Decimal(expected)
    assert result["state"] == "closed"


def test_dated_jpy_conversion_and_signed_cost_evidence(workspace, personal_runtime):
    body = command(workspace, "USDJPY")
    entry_at = body["trade"]["entry"]["executed_at"]
    exit_at = body["trade"]["exits"][0]["executed_at"]
    body["trade"].update(
        reporting_policy="explicit_rates",
        risk_conversion_id="fx-risk",
        conversions=[
            dict(
                conversion_id=identity,
                from_currency="JPY",
                to_currency="USD",
                rate="0.005",
                observed_at=at,
                applies_at=at,
                max_age_seconds=0,
                source=dict(kind="manual", reference="SYNTHETIC historical FX"),
            )
            for identity, at in (("fx-risk", entry_at), ("fx-exit", exit_at))
        ],
        adjustments=[
            dict(
                adjustment_id="jpy-cost",
                kind="commission",
                amount="-100",
                currency="JPY",
                occurred_at=entry_at,
                conversion_id="fx-risk",
                description="Synthetic commission",
                source=dict(kind="manual", reference="SYNTHETIC P3 commission"),
            )
        ],
    )
    body["trade"]["exits"][0]["profit_conversion_id"] = "fx-exit"
    accepted = wire(save(workspace, personal_runtime, body))
    assert Decimal(accepted["result"]["native"]["net_pnl"]["raw"]) == 700
    assert Decimal(accepted["result"]["reporting"]["net_pnl"]["raw"]) == Decimal("3.5")
    assert Decimal(accepted["result"]["native"]["realized_r"]["raw"]) == Decimal("0.35")
    reopened = retrieve(workspace, accepted)
    assert reopened["input"]["trade"]["conversions"] == accepted["input"]["trade"]["conversions"]
    assert (
        reopened["original_risk_basis"]["risk_conversion"]["source"]["reference"]
        == "SYNTHETIC historical FX"
    )


def test_broker_comparison_is_preserved_separately(workspace, personal_runtime):
    body = command(workspace, full=True)
    with workspace.read_session() as session:
        bound = bind_preview(session, CfdPreviewCommandV1.model_validate(body))
    body["broker_evidence"] = [
        dict(
            evidence_id="reported-" + body["position_reference"],
            position_reference=body["position_reference"],
            account_id=body["account_id"],
            instrument_id=bound.trade.snapshot.specification.instrument_id,
            original_lots="0.10",
            exited_lots="0.10",
            state="closed",
            as_of=body["as_of"],
            reported_at=body["as_of"],
            basis="native",
            recognition_policy="incurred_once",
            metric="net_pnl",
            amount="999",
            currency="USD",
            comparison_basis="raw",
            absolute_tolerance="0",
            source=dict(
                kind="statement", reference="SYNTHETIC statement example, not authenticated"
            ),
        )
    ]
    accepted = retrieve(workspace, save(workspace, personal_runtime, body))
    assert Decimal(accepted["result"]["native"]["net_pnl"]["raw"]) == 20
    comparison = accepted["result"]["comparisons"][0]
    assert comparison["status"] == "difference"
    assert Decimal(comparison["evidence"]["amount"]) == 999
    assert accepted["provenance"]["broker_authenticated"] is False


def test_same_key_retry_is_original_receipt_without_runtime(
    workspace, personal_runtime, monkeypatch
):
    body, key = command(workspace), str(uuid4())
    accepted = wire(save(workspace, personal_runtime, body, key))
    before = inventory(workspace)
    forbidden = Mock(
        side_effect=AssertionError("A committed retry must not execute or verify a runtime")
    )
    for name in ("verify", "preview", "calculate"):
        monkeypatch.setattr(personal_runtime, name, forbidden)
    assert wire(save(workspace, personal_runtime, body, key)) == accepted
    forbidden.assert_not_called()
    assert inventory(workspace) == before


@pytest.mark.parametrize(
    "conflict", ["changed_payload", "same_position_new_key", "reused_event_ids"]
)
def test_conflicting_submission_rolls_back(workspace, personal_runtime, conflict):
    body, key = command(workspace), str(uuid4())
    save(workspace, personal_runtime, body, key)
    before = inventory(workspace)
    retry = deepcopy(body)
    if conflict == "changed_payload":
        retry["trade"]["exits"][0]["price"] = "1.10300"
    elif conflict == "same_position_new_key":
        key = str(uuid4())
    else:
        key = str(uuid4())
        retry["position_reference"] = str(uuid4())
    with pytest.raises(CfdProblem) as error:
        save(workspace, personal_runtime, retry, key)
    assert error.value.status == 409
    assert inventory(workspace) == before


@pytest.mark.parametrize(
    "stage", ["children", "calculation", "sealed", "head", "receipt", "before_commit"]
)
def test_injected_failures_are_atomic(workspace, personal_runtime, stage):
    before = inventory(workspace)
    body, key = command(workspace), str(uuid4())
    with pytest.raises(RuntimeError):
        save(workspace, personal_runtime, body, key, fail_at=stage)
    assert inventory(workspace) == before
    with workspace.read_session() as session:
        assert session.execute(text("PRAGMA query_only")).scalar() == 1
        assert session.execute(text("PRAGMA integrity_check")).scalar() == "ok"
    assert (
        str(wire(save(workspace, personal_runtime, body, key))["position_id"])
        == body["position_reference"]
    )


def test_account_isolation_and_no_read_calculation_or_writes(
    workspace, personal_runtime, monkeypatch
):
    accepted = wire(save(workspace, personal_runtime, command(workspace)))
    before = inventory(workspace)
    statements = []

    def record(connection, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    forbidden = Mock(side_effect=AssertionError("GET must not execute the calculator"))
    monkeypatch.setattr(personal_runtime, "calculate", forbidden)
    monkeypatch.setattr(personal_runtime, "preview", forbidden)
    event.listen(workspace.engine, "before_cursor_execute", record)
    try:
        with workspace.read_session() as session:
            read_position(session, accepted["account_id"], accepted["position_id"])
            page = wire(position_page(session, accepted["account_id"], key=b"test-key" * 4))
            assert len(page["items"]) == 1
            other = wire(
                position_page(session, workspace.samples["other_account_id"], key=b"test-key" * 4)
            )
            assert other["items"] == []
            with pytest.raises(CfdProblem) as error:
                read_position(
                    session, workspace.samples["other_account_id"], accepted["position_id"]
                )
            assert error.value.status == 404
    finally:
        event.remove(workspace.engine, "before_cursor_execute", record)
    forbidden.assert_not_called()
    assert all(
        not re.match(r"\s*(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER)", sql, re.I)
        for sql in statements
    )
    assert inventory(workspace) == before


def test_same_key_simultaneous_requests_create_one_position(workspace, personal_runtime):
    body, key = command(workspace), str(uuid4())

    def submit(_):
        try:
            return wire(save(workspace, personal_runtime, body, key))
        except CfdProblem as error:
            # A bounded calculator queue may ask an in-flight duplicate to retry.
            assert error.status == 429 and error.code == "calculation_capacity_exceeded"
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, range(2)))
    assert any(result is not None for result in results)
    results = [result or wire(save(workspace, personal_runtime, body, key)) for result in results]
    assert results[0] == results[1]
    rows = inventory(workspace)
    assert len(rows["cfd_positions"]) == 1 and len(rows["cfd_requests"]) == 1


def test_simultaneous_transactions_share_exact_committed_receipt(
    workspace, personal_runtime, monkeypatch
):
    """Isolate the DB race from the separately tested bounded worker queue."""
    body, key = command(workspace), str(uuid4())
    with workspace.read_session() as session:
        request = bind_preview(session, CfdPreviewCommandV1.model_validate(body))
    calculated = personal_runtime.calculate(request, purpose="accept_save")
    barrier = Barrier(2)

    def simultaneous(*args, **kwargs):
        barrier.wait(timeout=10)
        return calculated

    monkeypatch.setattr(personal_runtime, "calculate", simultaneous)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: wire(save(workspace, personal_runtime, body, key)), range(2))
        )
    assert results[0] == results[1]
    rows = inventory(workspace)
    assert len(rows["cfd_positions"]) == 1 and len(rows["cfd_requests"]) == 1


def test_original_risk_and_sealed_children_remain_immutable(workspace, personal_runtime):
    accepted = wire(save(workspace, personal_runtime, command(workspace)))
    before = inventory(workspace)
    for table, field, value in (
        ("cfd_positions", "original_stop", "1.09000"),
        ("cfd_executions", "lots", "0.09"),
    ):
        with pytest.raises((IntegrityError, OperationalError)):
            with workspace.write_session() as session:
                session.execute(update(TABLES[table]).values(**{field: value}))
        assert inventory(workspace) == before
    assert retrieve(workspace, accepted)["original_risk_basis"] == accepted["original_risk_basis"]


@pytest.mark.parametrize("target", ["input", "result", "manifest", "risk", "normalized_exit"])
def test_privileged_tampering_withholds_values_without_repair(workspace, personal_runtime, target):
    """Drop guards ONLY inside this NEW adversarial database to test read verification."""
    accepted = wire(save(workspace, personal_runtime, command(workspace)))
    name = (
        "cfd_positions"
        if target == "risk"
        else "cfd_executions"
        if target == "normalized_exit"
        else "cfd_calculations"
    )
    with workspace.write_session() as session:
        triggers = (
            session.execute(
                text("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=:name"),
                {"name": name},
            )
            .scalars()
            .all()
        )
        for trigger in triggers:
            assert re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", trigger)
            session.execute(text(f'DROP TRIGGER "{trigger}"'))
        table = TABLES[name]
        if target == "normalized_exit":
            session.execute(
                update(table)
                .where(table.c.position_id == accepted["position_id"], table.c.role == "exit")
                .values(price="1.10400")
            )
        elif target == "risk":
            session.execute(
                update(table)
                .where(table.c.id == accepted["position_id"])
                .values(original_risk_basis='{"tampered":true}')
            )
        else:
            field = {
                "input": "canonical_input",
                "result": "canonical_result",
                "manifest": "manifest",
            }[target]
            session.execute(
                update(table)
                .where(table.c.revision_id == accepted["revision_id"])
                .values(**{field: '{"tampered":true}'})
            )
    corrupt_inventory = inventory(workspace)
    with workspace.read_session() as session, pytest.raises(CfdProblem) as error:
        read_position(session, accepted["account_id"], accepted["position_id"])
    assert error.value.status == 409
    assert error.value.code == "integrity_failure"
    assert inventory(workspace) == corrupt_inventory


def test_missing_and_cross_currency_inputs_reject_without_rows(workspace, personal_runtime):
    before = inventory(workspace)
    for target in ("account", "server", "overclose", "time"):
        body = command(workspace)
        if target == "account":
            body["account_id"] = "unknown-account"
        elif target == "server":
            body["account_id"] = workspace.samples["other_account_id"]
        elif target == "overclose":
            body["trade"]["exits"][0]["lots"] = "0.11"
        elif target == "time":
            body["trade"]["exits"][0]["executed_at"] = "2020-01-01T00:00:00Z"
        with pytest.raises((CfdProblem, ValidationError)) as error:
            save(workspace, personal_runtime, body)
        if isinstance(error.value, CfdProblem):
            assert error.value.status in (404, 422)
        else:
            assert error.value.error_count() > 0
        assert inventory(workspace) == before


def test_missing_fx_preserves_native_amount_and_explicit_unavailable_reporting(
    workspace, personal_runtime
):
    body = command(workspace, "USDJPY")
    accepted = wire(save(workspace, personal_runtime, body))
    assert Decimal(accepted["result"]["native"]["net_pnl"]["raw"]) == 800
    reporting = accepted["result"]["reporting"]["net_pnl"]
    assert reporting["raw"] is None and reporting["unavailable_reason"]
    assert accepted["input"]["trade"]["conversions"] == []
    assert retrieve(workspace, accepted) == accepted
    before = inventory(workspace)
    missing = command(workspace, "USDJPY")
    missing["trade"]["reporting_policy"] = "explicit_rates"
    with pytest.raises(ValidationError):
        save(workspace, personal_runtime, missing)
    assert inventory(workspace) == before


def test_account_scoped_pagination_rejects_replayed_or_tampered_cursor(workspace, personal_runtime):
    first = wire(save(workspace, personal_runtime, command(workspace)))
    second = wire(save(workspace, personal_runtime, command(workspace)))
    key = b"pagination-test-signing-key-32bytes"
    with workspace.read_session() as session:
        page = wire(position_page(session, first["account_id"], limit=1, key=key))
        cursor = page["next_cursor"]
        assert [item["position_id"] for item in page["items"]] == [first["position_id"]]
        following = wire(
            position_page(session, first["account_id"], limit=1, cursor=cursor, key=key)
        )
        assert following["next_cursor"] is None
        assert [item["position_id"] for item in following["items"]] == [second["position_id"]]
        for account, limit, supplied in (
            (workspace.samples["other_account_id"], 1, cursor),
            (first["account_id"], 2, cursor),
            (first["account_id"], 1, "bad" + cursor),
        ):
            with pytest.raises(CfdProblem) as error:
                position_page(session, account, limit=limit, cursor=supplied, key=key)
            assert error.value.status == 400 and error.value.code == "invalid_cursor"


@pytest.mark.parametrize("target", ["canonicalizer", "software_release"])
def test_unknown_historical_versions_withhold_evidence(workspace, personal_runtime, target):
    accepted = wire(save(workspace, personal_runtime, command(workspace)))
    with workspace.write_session() as session:
        for trigger in (
            session.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='trigger' AND tbl_name='cfd_calculations'"
                )
            )
            .scalars()
            .all()
        ):
            assert re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", trigger)
            session.execute(text(f'DROP TRIGGER "{trigger}"'))
        if target == "canonicalizer":
            values = {"canonicalizer_version": "future-canonicalizer-v9"}
        else:
            envelope = deepcopy(accepted["manifest"])
            envelope["software_release"]["schema_version"] = "future-python-release-v9"
            evidence = canonical(envelope)
            values = {"manifest": evidence, "manifest_sha256": digest(evidence)}
        session.execute(update(TABLES["cfd_calculations"]).values(**values))
    corrupted = inventory(workspace)
    with workspace.read_session() as session, pytest.raises(CfdProblem) as error:
        read_position(session, accepted["account_id"], accepted["position_id"])
    assert error.value.status == 503 and error.value.code == "historical_schema_unavailable"
    assert inventory(workspace) == corrupted

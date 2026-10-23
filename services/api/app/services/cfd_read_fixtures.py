"""Hand-declared synthetic pages for NEW owned practice provisioning only.

No calculator import, execution, accepted-release manifest or save API. Numeric
results below are teaching constants, not output produced by an installed runtime.
"""

from uuid import uuid4

from sqlalchemy import insert, select, update

from app.database.cfd_session import CfdTargetRejected
from app.models import InstrumentSnapshot, JournalAccount
from app.models.cfd import TABLES
from app.schemas.cfd_positions import CfdPositionRequest, CfdPositionResult
from app.schemas.cfd_reads import OriginalRiskV1
from app.services.cfd_canonical import canonical_input
from app.services.cfd_integrity import instant
from app.services.cfd_read_codec import CANONICALIZER, MANIFEST, POLICY, canonical, digest
from app.services.management import account_contract
from app.services.multi_asset import store_snapshot

AT = "2026-10-02T00:00:00.000000Z"
T0, T1, T2 = (f"2026-10-01T{hour}:00:00.000000Z" for hour in ("09", "10", "11"))
SOURCE = {"kind": "manual", "reference": "SYNTHETIC B3B-R fixture; not broker evidence"}


def money(raw, rounded, currency):
    return dict(raw=raw, rounded=rounded, currency=currency, unavailable_reason=None)


def result_fixture(request, full):
    """Declare the two golden pages by hand; never calculate them on the host."""
    trade = request.trade
    native_risk, report_risk = money("2000", "2000", "JPY"), money("10", "10.00", "USD")

    def performance(currency, gross, gross_display, costs, costs_display, net, net_display, risk):
        return dict(
            currency=currency,
            gross_pnl=money(gross, gross_display, currency),
            adjustments=money(costs, costs_display, currency),
            net_pnl=money(net, net_display, currency),
            original_planned_risk=risk,
            realized_r=dict(
                raw="1.2" if full else "0.35", rounded="1.200000" if full else "0.350000", unit="R"
            ),
            outcome="win" if full else "unavailable",
        )

    native = performance(
        "JPY",
        "2600" if full else "800",
        "2600" if full else "800",
        "-200" if full else "-100",
        "-200" if full else "-100",
        "2400" if full else "700",
        "2400" if full else "700",
        native_risk,
    )
    reporting = performance(
        "USD",
        "13" if full else "4",
        "13.00" if full else "4.00",
        "-1" if full else "-0.5",
        "-1.00" if full else "-0.50",
        "12" if full else "3.5",
        "12.00" if full else "3.50",
        report_risk,
    )
    exits = [
        dict(
            execution_id=trade.exits[0].execution_id,
            executed_at=T1,
            lots="0.04",
            remaining_lots_after="0.06",
            native_gross=money("800", "800", "JPY"),
            reporting_gross=money("4", "4.00", "USD"),
        )
    ]
    if full:
        exits.append(
            dict(
                execution_id=trade.exits[1].execution_id,
                executed_at=T2,
                lots="0.06",
                remaining_lots_after="0",
                native_gross=money("1800", "1800", "JPY"),
                reporting_gross=money("9", "9.00", "USD"),
            )
        )
    cost_breakdown = []
    for kind in ("commission", "swap", "fee", "other"):
        present = kind == "commission" or (full and kind == "swap")
        cost_breakdown.append(
            dict(
                kind=kind,
                native=money("-100" if present else "0", "-100" if present else "0", "JPY"),
                reporting=money("-0.5" if present else "0", "-0.50" if present else "0.00", "USD"),
            )
        )
    used = {
        trade.risk_conversion_id,
        trade.exits[0].profit_conversion_id,
        trade.adjustments[0].conversion_id,
    }
    if full:
        used.update({trade.exits[1].profit_conversion_id, trade.adjustments[1].conversion_id})
    return CfdPositionResult(
        position_reference=request.position_reference,
        as_of=request.as_of,
        state="closed" if full else "partial",
        eligible_for_closed_trade_statistics=full,
        original_lots="0.1",
        exited_lots="0.1" if full else "0.04",
        remaining_lots="0" if full else "0.06",
        symbol="USDJPY",
        snapshot_id=trade.snapshot.snapshot_id,
        snapshot_sha256=trade.snapshot.content_sha256,
        recognition_policy="incurred_once",
        reporting_policy="explicit_rates",
        native=native,
        reporting=reporting,
        unrealized_pnl=dict(
            raw=None,
            rounded=None,
            currency="JPY",
            unavailable_reason="No valuation-price input; unrealized PnL is not calculated.",
        ),
        exits=exits,
        recognized_adjustments=trade.adjustments if full else trade.adjustments[:1],
        deferred_execution_ids=() if full else (trade.exits[1].execution_id,),
        deferred_adjustment_ids=() if full else (trade.adjustments[1].adjustment_id,),
        adjustments_by_currency=[
            money("-200" if full else "-100", "-200" if full else "-100", "JPY")
        ],
        cost_breakdown=cost_breakdown,
        conversion_evidence=[item for item in trade.conversions if item.conversion_id in used],
        rounding_policy=request.rounding,
    )


def input_fixture(account, snapshot, position_id, full):
    def fx(name, at):
        return dict(
            conversion_id=position_id + ":" + name,
            from_currency="JPY",
            to_currency="USD",
            rate="0.005",
            observed_at=at,
            applies_at=at,
            max_age_seconds=0,
            source=SOURCE,
        )

    conversions = [
        fx(name, at)
        for name, at in (
            ("risk", T0),
            ("commission-fx", T0),
            ("first-fx", T1),
            ("second-fx", T2),
            ("swap-fx", T2),
        )
    ]
    conversions.sort(key=lambda item: item["conversion_id"])
    fills = [
        dict(
            execution_id=position_id + ":" + name,
            executed_at=at,
            price=price,
            lots=lots,
            profit_conversion_id=position_id + ":" + conversion,
        )
        for name, at, price, lots, conversion in (
            ("first", T1, "150.2", "0.04", "first-fx"),
            ("second", T2, "150.3", "0.06", "second-fx"),
        )
    ]
    return CfdPositionRequest(
        position_reference=position_id,
        as_of=T2 if full else T1,
        recognition_policy="incurred_once",
        rounding=dict(
            currencies=[
                dict(currency="JPY", decimal_places=0),
                dict(currency="USD", decimal_places=2),
            ],
            rounding="ROUND_HALF_EVEN",
            ratio_places=6,
            movement_places=6,
        ),
        trade=dict(
            account=account,
            snapshot=dict(
                snapshot_id=snapshot.id,
                content_sha256=snapshot.content_sha256,
                specification=snapshot.specification,
            ),
            direction="buy",
            entry=dict(
                execution_id=position_id + ":entry", executed_at=T0, price="150", lots="0.1"
            ),
            exits=fills,
            original_stop="149.8",
            reporting_policy="explicit_rates",
            conversions=conversions,
            risk_conversion_id=position_id + ":risk",
            adjustments=[
                dict(
                    adjustment_id=position_id + ":" + kind,
                    kind=kind,
                    amount="-100",
                    currency="JPY",
                    occurred_at=at,
                    source=SOURCE,
                    description="SYNTHETIC " + kind,
                    execution_id=position_id + ":entry" if kind == "commission" else None,
                    conversion_id=position_id + ":" + kind + "-fx",
                )
                for kind, at in (("commission", T0), ("swap", T2))
            ],
        ),
    )


def seed_read_fixtures(workspace, session):
    """Not callable against a ready session, existing ledger or arbitrary engine."""
    workspace.check_target(workspace.engine.url)
    if workspace.ready or session.get_bind().engine is not workspace.engine:
        raise CfdTargetRejected("Fixture provisioning requires the new owned engine")
    if session.execute(select(TABLES["cfd_positions"].c.id).limit(1)).first():
        raise CfdTargetRejected("Never reseed an existing ledger")
    samples = workspace.samples
    snapshot = session.get(InstrumentSnapshot, samples["snapshots"]["USDJPY"])
    other_spec = dict(
        snapshot.specification, instrument_id="synthetic-b3-other-USDJPY", venue="SYNTHETIC-OTHER"
    )
    other_snapshot = store_snapshot(session, other_spec)
    catalog = []

    def put(name, values):
        session.execute(insert(TABLES[name]), values)

    for index, account_id in enumerate([samples["account_id"]] * 3 + [samples["other_account_id"]]):
        account = account_contract(session.get(JournalAccount, account_id)).model_dump(mode="json")
        chosen = snapshot if index < 3 else other_snapshot
        position_id = str(uuid4())
        requests = [input_fixture(account, chosen, position_id, full) for full in (False, True)]
        first_result = result_fixture(requests[0], False)
        first = requests[0]
        risk = OriginalRiskV1(
            account_sha256=digest(canonical(account)),
            snapshot_sha256=chosen.content_sha256,
            direction=first.trade.direction,
            entry=first.trade.entry,
            original_stop=first.trade.original_stop,
            rounding=first.rounding,
            reporting_policy=first.trade.reporting_policy,
            recognition_policy=first.recognition_policy,
            risk_conversion_id=first.trade.risk_conversion_id,
            risk_conversion=next(
                item
                for item in first.trade.conversions
                if item.conversion_id == first.trade.risk_conversion_id
            ),
            native=first_result.native.original_planned_risk,
            reporting=first_result.reporting.original_planned_risk,
        ).model_dump(mode="json")
        put(
            "cfd_positions",
            dict(
                id=position_id,
                account_id=account_id,
                broker=account["broker"],
                settlement_currency="USD",
                snapshot_id=chosen.id,
                instrument_id=chosen.instrument_id,
                platform="mt5",
                server=account["server"],
                venue=account["server"],
                product="cfd",
                snapshot_sha256=chosen.content_sha256,
                account_contract=canonical(account),
                account_sha256=digest(canonical(account)),
                direction="buy",
                original_entry_id=first.trade.entry.execution_id,
                entry_at=T0,
                entry_price="150",
                original_lots="0.1",
                original_stop="149.8",
                original_risk_basis=canonical(risk),
                original_risk_sha256=digest(canonical(risk)),
                source=canonical(SOURCE),
                created_at=AT,
            ),
        )
        parent = None
        for number, request in enumerate(requests, 1):
            wire = request.model_dump(mode="json")
            trade = wire["trade"]
            revision = str(uuid4())
            put(
                "cfd_revisions",
                dict(
                    id=revision,
                    position_id=position_id,
                    account_id=account_id,
                    revision_no=number,
                    parent_revision_id=parent,
                    operation="create" if number == 1 else "amend",
                    lifecycle="active",
                    reason="SYNTHETIC history fixture; not an edit API",
                    as_of=T1 if number == 1 else T2,
                    reporting_policy="explicit_rates",
                    recognition_policy="incurred_once",
                    rounding_policy=canonical(wire["rounding"]),
                    changed_event_ids="[]",
                    request_schema_version="cfd-position-v1",
                    created_at=AT,
                ),
            )
            base = dict(revision_id=revision, position_id=position_id, account_id=account_id)
            groups = [
                ("conversion", "cfd_conversions", trade["conversions"]),
                ("execution", "cfd_executions", [trade["entry"], *trade["exits"]]),
                ("adjustment", "cfd_adjustments", trade["adjustments"]),
            ]
            for kind, table, items in groups:
                for ordinal, item in enumerate(items):
                    if number == 1:
                        put(
                            "cfd_event_keys",
                            dict(
                                account_id=account_id,
                                kind=kind,
                                event_id=item[kind + "_id"],
                                position_id=position_id,
                                first_revision_no=1,
                                created_at=AT,
                            ),
                        )
                    row = dict(item)
                    for field, value in row.items():
                        if field.endswith("_at"):
                            row[field] = instant(value)
                    if "source" in row:
                        row["source"] = canonical(row["source"])
                    if kind == "execution":
                        row.update(ordinal=ordinal, role="entry" if ordinal == 0 else "exit")
                    put(table, dict(base, event_kind=kind, **row))
            result = result_fixture(request, number == 2)
            manifest = canonical(MANIFEST)
            put(
                "cfd_calculations",
                dict(
                    revision_id=revision,
                    position_id=position_id,
                    snapshot_sha256=chosen.content_sha256,
                    original_risk_sha256=digest(canonical(risk)),
                    canonical_input=canonical_input(request),
                    input_sha256=digest(canonical_input(request)),
                    canonical_result=canonical(result.model_dump(mode="json")),
                    result_sha256=digest(canonical(result.model_dump(mode="json"))),
                    engine_id="cfd-position-v1",
                    engine_build_sha256=digest(manifest),
                    policy_version=POLICY,
                    canonicalizer_version=CANONICALIZER,
                    manifest=manifest,
                    manifest_sha256=digest(manifest),
                    calculated_at=AT,
                ),
            )
            session.execute(
                update(TABLES["cfd_revisions"])
                .where(TABLES["cfd_revisions"].c.id == revision)
                .values(sealed_at=AT)
            )
            head = dict(revision_id=revision, revision_no=number, row_version=number, updated_at=AT)
            if number == 1:
                put("cfd_position_heads", dict(position_id=position_id, **head))
            else:
                session.execute(
                    update(TABLES["cfd_position_heads"])
                    .where(TABLES["cfd_position_heads"].c.position_id == position_id)
                    .values(**head)
                )
            parent = revision
        catalog.append(
            dict(
                position_id=position_id,
                account_id=account_id,
                revisions=2,
                provenance="synthetic_fixture",
            )
        )
    samples["read_catalog"] = catalog

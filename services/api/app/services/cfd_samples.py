"""Fresh synthetic teaching identities and inputs. No calculator or broker calls."""

from uuid import uuid4

from app.services.multi_asset import store_account, store_snapshot


def seed_samples(session):
    account = dict(
        account_id=str(uuid4()),
        name="SYNTHETIC B3 CFD USD account",
        broker="SYNTHETIC-B3",
        platform="mt5",
        server="SYNTHETIC-B3",
        reporting_currency="USD",
        settlement_currency="USD",
    )
    store_account(session, account)
    other = dict(
        account, account_id=str(uuid4()), name="SYNTHETIC other server", server="SYNTHETIC-OTHER"
    )
    store_account(session, other)
    result = {
        "account_id": account["account_id"],
        "other_account_id": other["account_id"],
        "snapshots": {},
        "previews": {},
    }
    for symbol, mode, category, contract, tick, pip, price, stop, exit_price, profit in [
        (
            "USDJPY",
            "forex",
            "forex",
            "100000",
            "0.001",
            "0.01",
            "150.000",
            "149.800",
            "150.200",
            "JPY",
        ),
        ("XAUUSD", "cfd_linear", "metals", "100", "0.01", None, "2000", "1998", "2002", "USD"),
        ("XAGUSD", "cfd_linear", "metals", "5000", "0.001", None, "25", "24.98", "25.02", "USD"),
    ]:
        row = store_snapshot(
            session,
            dict(
                instrument_id="synthetic-b3-" + symbol,
                symbol=symbol,
                broker=account["broker"],
                venue=account["server"],
                product="cfd",
                market_category=category,
                calculation_mode=mode,
                quantity_unit="lots",
                profit_currency=profit,
                settlement_currency="USD",
                contract_size=contract,
                tick_size=tick,
                pip_size=pip,
                volume_min="0.01",
                volume_step="0.01",
                volume_max="100",
                source=dict(
                    kind="manual",
                    reference="SYNTHETIC teaching rules; NOT Bybit rules",
                    effective_at="2025-01-01T00:00:00Z",
                    captured_at="2025-01-02T00:00:00Z",
                ),
            ),
        )
        result["snapshots"][symbol] = row.id
        currencies = [dict(currency="USD", decimal_places=2)]
        if profit == "JPY":
            currencies.append(dict(currency="JPY", decimal_places=0))
        result["previews"][symbol] = dict(
            schema_version="cfd-api-command-v1",
            account_id=account["account_id"],
            snapshot_id=row.id,
            position_reference=str(uuid4()),
            trade=dict(
                direction="buy",
                entry=dict(
                    execution_id="synthetic-entry",
                    executed_at="2026-10-01T09:00:00Z",
                    price=price,
                    lots="0.10",
                ),
                exits=[
                    dict(
                        execution_id="synthetic-exit",
                        executed_at="2026-10-01T10:00:00Z",
                        price=exit_price,
                        lots="0.04",
                    )
                ],
                original_stop=stop,
                reporting_policy="native_only",
            ),
            rounding=dict(
                currencies=currencies, rounding="ROUND_HALF_EVEN", ratio_places=6, movement_places=6
            ),
            as_of="2026-10-01T10:00:00Z",
            recognition_policy="incurred_once",
        )
    return result

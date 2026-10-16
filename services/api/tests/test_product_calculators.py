"""Keep crypto behavior unchanged and never dispatch CFD inputs into it."""

import subprocess
import sys
from decimal import Decimal

import pytest
from cfd_calculation_examples import calculation_example
from test_journal import trade_data

from app.analytics.cfd import calculate_cfd
from app.analytics.products import calculate_product
from app.analytics.trades import calculate
from app.schemas.trade import TradeInput
from app.services.journal import write_trade


def test_cfd_dispatch_is_explicit_and_pure_import_path_has_no_db_or_network():
    request = calculation_example()
    assert calculate_product("cfd", request) == calculate_cfd(request)
    script = (
        "from app.analytics.products import calculate_product; import sys; "
        "assert not any(name in sys.modules for name in "
        "('app.database.session','app.main','sqlalchemy','httpx','MetaTrader5'))"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("product", ["tradfi_perpetual", "unknown", None])
def test_unsupported_products_are_unavailable(product):
    result = calculate_product(product, calculation_example())
    assert result.status == "unavailable" and result.reason_code == "unsupported_product"


@pytest.mark.parametrize("product", ["crypto_spot", "crypto_linear_futures"])
def test_crypto_rejects_cfd_dictionaries_instead_of_falling_back(product):
    result = calculate_product(product, calculation_example())
    assert result.status == "unavailable" and result.reason_code == "invalid_input"


@pytest.mark.parametrize(
    ("market", "product"), [("spot", "crypto_spot"), ("futures", "crypto_linear_futures")]
)
def test_existing_crypto_calculation_is_returned_unchanged(db, market, product):
    values = trade_data(market=market)
    if market == "futures":
        values.update(margin_type="isolated", leverage="10", funding="-2")
    trade = write_trade(db, TradeInput.model_validate(values))
    db.flush()
    assert calculate_product(product, trade) == calculate(trade)
    other = "crypto_linear_futures" if market == "spot" else "crypto_spot"
    assert calculate_product(other, trade).status == "unavailable"


def test_existing_crypto_leverage_changes_margin_without_multiplying_pnl(db):
    values = trade_data(market="futures", margin_type="isolated", leverage="10", funding="-2")
    trade = write_trade(db, TradeInput.model_validate(values))
    db.flush()
    leveraged = calculate_product("crypto_linear_futures", trade)
    trade.leverage = Decimal(1)
    unleveraged = calculate_product("crypto_linear_futures", trade)
    assert leveraged["gross_pnl"] == unleveraged["gross_pnl"] == "20"
    assert leveraged["net_pnl"] == unleveraged["net_pnl"] == "20"
    assert Decimal(leveraged["estimated_margin"]) == 20
    assert Decimal(unleveraged["estimated_margin"]) == 200

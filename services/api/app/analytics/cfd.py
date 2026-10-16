"""Pure, single-close linear CFD calculator. Never called by legacy journal routes.

Cash products/sums are exact within the bounded input domain at 160 digits.
Division (R and potentially pips) uses that precision, with HALF_EVEN rounding.
Only presentation values are quantized using the caller's explicit policy.
"""

from decimal import (
    ROUND_HALF_EVEN,
    ROUND_HALF_UP,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)

from pydantic import ValidationError

from app.schemas.cfd_results import (
    CalculationUnavailable,
    CfdCalculationRequest,
    CfdCalculationResult,
    CurrencyPerformance,
    InputIssue,
    MoneyResult,
    ScalarResult,
)

SUPPORTED_MODES = {
    "forex": {"forex"},
    "cfd_linear": {"metals", "indices", "energy", "equities", "other"},
    "cfd_index": {"indices"},
}
ROUNDING_MODES = {"ROUND_HALF_EVEN": ROUND_HALF_EVEN, "ROUND_HALF_UP": ROUND_HALF_UP}


def calculate_cfd(payload) -> CfdCalculationResult | CalculationUnavailable:
    """Validate an explicit request; never substitute values or partially close."""
    # A fresh Context avoids inheriting precision, traps or exponent limits.
    with localcontext(
        Context(
            prec=160,
            rounding=ROUND_HALF_EVEN,
            Emin=-999999,
            Emax=999999,
            traps=[InvalidOperation, DivisionByZero, Overflow],
        )
    ):
        try:
            request = CfdCalculationRequest.model_validate(payload)
        except ValidationError as error:
            return CalculationUnavailable(
                reason_code="invalid_input",
                message=(
                    "Financial inputs or rounding policy failed validation; "
                    "no calculation was made."
                ),
                issues=tuple(
                    InputIssue(path=".".join(map(str, item["loc"])), message=item["msg"])
                    for item in error.errors(include_input=False, include_url=False)[:20]
                ),
            )
        unsupported = _check_scope(request)
        if unsupported is not None:
            return unsupported
        try:
            return _calculate(request)
        except DecimalException:
            return CalculationUnavailable(
                reason_code="numeric_error",
                message="Decimal arithmetic could not safely represent the supplied calculation.",
            )


def _check_scope(request):
    trade = request.trade
    spec = trade.snapshot.specification
    if spec.market_category not in SUPPORTED_MODES.get(spec.calculation_mode, set()):
        return CalculationUnavailable(
            reason_code="unsupported_mode",
            message=(
                "Only explicit forex, linear CFD and index CFD mode/category pairs are supported."
            ),
        )
    if len(trade.exits) != 1 or trade.exits[0].lots != trade.entry.lots:
        return CalculationUnavailable(
            reason_code="unsupported_position",
            message=(
                "This engine requires one entry and one exit closing all entry lots. "
                "Partial closures are not implemented."
            ),
        )
    currencies = {spec.profit_currency, trade.account.reporting_currency}
    currencies.update(item.currency for item in trade.adjustments)
    precisions = {item.currency for item in request.rounding.currencies}
    if currencies - precisions:
        return CalculationUnavailable(
            reason_code="missing_currency_precision",
            message=(
                "Supply explicit rounding decimal places for every native, reporting "
                "and adjustment currency."
            ),
        )
    return None


class ResultBuilder:
    """Keep display rounding and missing-data construction out of accounting."""

    def __init__(self, request):
        self.policy = request.rounding
        self.places = {item.currency: item.decimal_places for item in self.policy.currencies}

    def rounded(self, amount, places):
        quantum = Decimal(1).scaleb(-places)
        value = amount.quantize(quantum, rounding=ROUNDING_MODES[self.policy.rounding])
        return value.copy_abs() if value.is_zero() else value

    def money(self, amount, currency, reason=None):
        return MoneyResult(
            currency=currency,
            raw=amount,
            rounded=None if amount is None else self.rounded(amount, self.places[currency]),
            unavailable_reason=reason if amount is None else None,
        )

    def scalar(self, amount, unit, reason=None):
        places = self.policy.ratio_places if unit == "R" else self.policy.movement_places
        return ScalarResult(
            unit=unit,
            raw=amount,
            rounded=None if amount is None else self.rounded(amount, places),
            unavailable_reason=reason if amount is None else None,
        )

    def performance(self, currency, gross, costs, risk):
        net_value = None if gross.raw is None or costs.raw is None else gross.raw + costs.raw
        net_reason = gross.unavailable_reason or costs.unavailable_reason
        net = self.money(net_value, currency, net_reason)
        if net_value is None or risk.raw is None or risk.raw == 0:
            r_multiple = self.scalar(
                None,
                "R",
                net.unavailable_reason or risk.unavailable_reason or "Original risk is zero.",
            )
        else:
            r_multiple = self.scalar(net_value / risk.raw, "R")
        outcome = (
            "unavailable"
            if net_value is None
            else "win"
            if net_value > 0
            else "loss"
            if net_value < 0
            else "breakeven"
        )
        return CurrencyPerformance(
            currency=currency,
            gross_pnl=gross,
            adjustments=costs,
            net_pnl=net,
            original_planned_risk=risk,
            realized_r=r_multiple,
            outcome=outcome,
        )


def _calculate(request):
    trade, build = request.trade, ResultBuilder(request)
    spec = trade.snapshot.specification
    entry, exit = trade.entry, trade.exits[0]
    native_currency, reporting_currency = spec.profit_currency, trade.account.reporting_currency
    sign = Decimal(1) if trade.direction == "buy" else Decimal(-1)
    change = sign * (exit.price - entry.price)
    gross = change * entry.lots * spec.contract_size
    risk = (
        None
        if trade.original_stop is None
        else abs(entry.price - trade.original_stop) * entry.lots * spec.contract_size
    )
    observations = {item.conversion_id: item for item in trade.conversions}

    def to_reporting(amount, currency, reference):
        if currency == reporting_currency:
            return amount
        if trade.reporting_policy == "native_only":
            return None
        # Validation already checked direction, source, time and allowed age.
        return amount * observations[reference].rate

    native_costs = {}
    converted_costs = []
    for item in trade.adjustments:
        native_costs[item.currency] = native_costs.get(item.currency, Decimal(0)) + item.amount
        converted_costs.append(to_reporting(item.amount, item.currency, item.conversion_id))
    costs_reporting = (
        None
        if any(value is None for value in converted_costs)
        else sum(converted_costs, Decimal(0))
    )
    # Never invert an FX observation to invent native-currency costs.
    costs_native = (
        sum(native_costs.values(), Decimal(0))
        if all(currency == native_currency for currency in native_costs)
        else costs_reporting
        if reporting_currency == native_currency
        else None
    )
    native = build.performance(
        native_currency,
        build.money(gross, native_currency),
        build.money(
            costs_native,
            native_currency,
            "Adjustments span currencies without a native-currency conversion policy.",
        ),
        build.money(risk, native_currency, "Original planned stop was not supplied."),
    )
    reporting_gross = to_reporting(gross, native_currency, exit.profit_conversion_id)
    reporting_risk = (
        None if risk is None else to_reporting(risk, native_currency, trade.risk_conversion_id)
    )
    reporting = build.performance(
        reporting_currency,
        build.money(
            reporting_gross,
            reporting_currency,
            "Reporting conversion is disabled by native_only policy.",
        ),
        build.money(
            costs_reporting,
            reporting_currency,
            "Some adjustments need reporting conversion; native_only policy disables it.",
        ),
        build.money(
            reporting_risk,
            reporting_currency,
            "Original planned stop was not supplied."
            if risk is None
            else "Original risk needs entry-time conversion; native_only policy disables it.",
        ),
    )
    return CfdCalculationResult(
        symbol=spec.symbol,
        calculation_mode=spec.calculation_mode,
        snapshot_id=trade.snapshot.snapshot_id,
        snapshot_sha256=trade.snapshot.content_sha256,
        direction=trade.direction,
        entry_price=entry.price,
        exit_price=exit.price,
        lots=entry.lots,
        contract_size=spec.contract_size,
        signed_price_change=build.scalar(change, "price"),
        pips=build.scalar(
            None if spec.pip_size is None else change / spec.pip_size,
            "pips",
            "No pip size was supplied; it is not inferred.",
        ),
        ticks=build.scalar(change / spec.tick_size, "ticks"),
        native=native,
        reporting=reporting,
        adjustments_by_currency=tuple(
            build.money(value, currency) for currency, value in sorted(native_costs.items())
        ),
        conversion_evidence=trade.conversions,
        reporting_policy=trade.reporting_policy,
        rounding_policy=request.rounding,
    )

"""Pure as-of realized accounting for one entry and multiple linear CFD exits."""

from decimal import (
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    localcontext,
)

from pydantic import ValidationError

from app.analytics.cfd import SUPPORTED_MODES, ResultBuilder
from app.analytics.cfd_reconciliation import compare_broker_evidence
from app.schemas.cfd_positions import (
    CfdPositionRequest,
    CfdPositionResult,
    CostKindResult,
    ExitRealization,
    PositionUnavailable,
)
from app.schemas.cfd_results import CurrencyPerformance, InputIssue


def calculate_position(payload):
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
            request = CfdPositionRequest.model_validate(payload)
        except ValidationError as error:
            return PositionUnavailable(
                reason_code="invalid_input",
                message="Position inputs failed validation; no accounting was performed.",
                issues=tuple(
                    InputIssue(
                        path=".".join(map(str, item["loc"])) or "request", message=item["msg"]
                    )
                    for item in error.errors(include_input=False, include_url=False)[:20]
                ),
            )
        spec = request.trade.snapshot.specification
        if spec.market_category not in SUPPORTED_MODES.get(spec.calculation_mode, set()):
            return PositionUnavailable(
                reason_code="unsupported_mode",
                message="This position engine supports explicitly declared linear modes only.",
            )
        needed = {spec.profit_currency, request.trade.account.reporting_currency}
        needed.update(item.currency for item in request.trade.adjustments)
        if needed - {item.currency for item in request.rounding.currencies}:
            return PositionUnavailable(
                reason_code="missing_currency_precision",
                message="Supply rounding places for native, reporting and cost currencies.",
            )
        try:
            result = _calculate(request)
            comparisons = compare_broker_evidence(request, result, ResultBuilder(request))
            return CfdPositionResult(**{**result.model_dump(), "comparisons": comparisons})
        except DecimalException:
            return PositionUnavailable(
                reason_code="numeric_error",
                message="Decimal arithmetic could not safely represent this position.",
            )


def _calculate(request):
    trade, build = request.trade, ResultBuilder(request)
    spec, entry = trade.snapshot.specification, trade.entry
    native, reporting = spec.profit_currency, trade.account.reporting_currency
    fills = tuple(item for item in trade.exits if item.executed_at <= request.as_of)
    costs = tuple(item for item in trade.adjustments if item.occurred_at <= request.as_of)
    observations = {item.conversion_id: item for item in trade.conversions}
    used = set()

    def convert(amount, currency, reference):
        if currency == reporting:
            return amount
        if trade.reporting_policy == "native_only":
            return None
        used.add(reference)
        return amount * observations[reference].rate

    def total(values):
        return None if any(value is None for value in values) else sum(values, Decimal(0))

    def cost_values(items):
        original = {}
        translated = []
        for item in items:
            original[item.currency] = original.get(item.currency, Decimal(0)) + item.amount
            translated.append(convert(item.amount, item.currency, item.conversion_id))
        reporting_cost = total(translated)
        native_cost = (
            sum(original.values(), Decimal(0))
            if all(currency == native for currency in original)
            else reporting_cost
            if native == reporting
            else None
        )
        return original, native_cost, reporting_cost

    closed, gross, realized = Decimal(0), Decimal(0), []
    reporting_gross = []
    sign = Decimal(1) if trade.direction == "buy" else Decimal(-1)
    for fill in fills:
        amount = sign * (fill.price - entry.price) * fill.lots * spec.contract_size
        converted = convert(amount, native, fill.profit_conversion_id)
        gross += amount
        closed += fill.lots
        reporting_gross.append(converted)
        realized.append(
            ExitRealization(
                execution_id=fill.execution_id,
                executed_at=fill.executed_at,
                lots=fill.lots,
                remaining_lots_after=entry.lots - closed,
                native_gross=build.money(amount, native),
                reporting_gross=build.money(
                    converted, reporting, "Reporting FX is disabled by native_only policy."
                ),
            )
        )
    remaining = entry.lots - closed
    state = "closed" if remaining == 0 else "partial" if closed > 0 else "open"
    original_costs, native_cost, reporting_cost = cost_values(costs)
    risk = (
        None
        if trade.original_stop is None
        else abs(entry.price - trade.original_stop) * entry.lots * spec.contract_size
    )
    converted_risk = None if risk is None else convert(risk, native, trade.risk_conversion_id)
    cost_reason = "Adjustments span currencies without a native-currency conversion policy."
    reporting_cost_reason = (
        "Some adjustments need reporting conversion; native_only policy disables it."
    )

    def performance(currency, pnl, adjustments, planned_risk, reason, reporting_basis=False):
        group = build.performance(
            currency,
            build.money(pnl, currency, "Reporting conversion is disabled by native_only policy."),
            build.money(
                adjustments, currency, reporting_cost_reason if reporting_basis else cost_reason
            ),
            build.money(planned_risk, currency, reason),
        )
        if state != "closed":
            return CurrencyPerformance(**{**group.model_dump(), "outcome": "unavailable"})
        return group

    breakdown = []
    for kind in ("commission", "swap", "fee", "other"):
        _, n, r = cost_values(tuple(item for item in costs if item.kind == kind))
        breakdown.append(
            CostKindResult(
                kind=kind,
                native=build.money(n, native, cost_reason),
                reporting=build.money(r, reporting, reporting_cost_reason),
            )
        )
    return CfdPositionResult(
        position_reference=request.position_reference,
        as_of=request.as_of,
        state=state,
        eligible_for_closed_trade_statistics=state == "closed",
        original_lots=entry.lots,
        exited_lots=closed,
        remaining_lots=remaining,
        symbol=spec.symbol,
        snapshot_id=trade.snapshot.snapshot_id,
        snapshot_sha256=trade.snapshot.content_sha256,
        recognition_policy=request.recognition_policy,
        reporting_policy=trade.reporting_policy,
        native=performance(
            native, gross, native_cost, risk, "Original planned stop was not supplied."
        ),
        reporting=performance(
            reporting,
            total(reporting_gross),
            reporting_cost,
            converted_risk,
            "Original planned stop was not supplied."
            if risk is None
            else "Original risk needs entry-time conversion; native_only policy disables it.",
            reporting_basis=True,
        ),
        unrealized_pnl=build.money(
            None, native, "No valuation-price input; unrealized PnL is not calculated."
        ),
        exits=tuple(realized),
        recognized_adjustments=costs,
        deferred_execution_ids=tuple(
            item.execution_id for item in trade.exits if item.executed_at > request.as_of
        ),
        deferred_adjustment_ids=tuple(
            item.adjustment_id for item in trade.adjustments if item.occurred_at > request.as_of
        ),
        adjustments_by_currency=tuple(
            build.money(value, currency) for currency, value in sorted(original_costs.items())
        ),
        cost_breakdown=tuple(breakdown),
        conversion_evidence=tuple(item for item in trade.conversions if item.conversion_id in used),
        rounding_policy=request.rounding,
    )

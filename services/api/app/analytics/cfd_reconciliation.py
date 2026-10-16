"""Compare like-for-like evidence without converting or replacing broker values."""

from app.schemas.cfd_reconciliation import BrokerComparison


def compare_broker_evidence(request, position, build):
    comparisons = []
    trade = request.trade
    for evidence in request.broker_evidence:
        group = position.native if evidence.basis == "native" else position.reporting
        reason = None
        if (
            evidence.position_reference != request.position_reference
            or evidence.account_id != trade.account.account_id
            or evidence.instrument_id != trade.snapshot.specification.instrument_id
        ):
            reason = "Broker evidence does not identify the same position/account/instrument."
        elif (
            evidence.original_lots != position.original_lots
            or evidence.exited_lots != position.exited_lots
        ):
            reason = "Broker quantity coverage is missing or differs from this position."
        elif evidence.as_of != request.as_of or evidence.state != position.state:
            reason = "Broker evidence cutoff or position state differs."
        elif evidence.recognition_policy != request.recognition_policy:
            reason = "Broker accounting basis is unknown or differs from incurred-once recognition."
        elif evidence.currency != group.currency:
            reason = "Broker and calculated currencies differ; no comparison FX is inferred."
        if evidence.metric in ("gross_pnl", "net_pnl", "adjustments"):
            calculated = getattr(group, evidence.metric)
        else:
            component = next(
                item for item in position.cost_breakdown if item.kind == evidence.metric
            )
            calculated = component.native if evidence.basis == "native" else component.reporting
        reason = reason or calculated.unavailable_reason
        if reason is not None:
            comparisons.append(
                BrokerComparison(
                    evidence=evidence,
                    status="unavailable",
                    calculated=build.money(None, group.currency, reason),
                    difference=build.money(None, group.currency, reason),
                    within_tolerance=None,
                    unavailable_reason=reason,
                )
            )
            continue
        selected = calculated.raw if evidence.comparison_basis == "raw" else calculated.rounded
        difference = selected - evidence.amount
        within = abs(difference) <= evidence.absolute_tolerance
        comparisons.append(
            BrokerComparison(
                evidence=evidence,
                status="within_tolerance" if within else "difference",
                calculated=calculated,
                difference=build.money(difference, group.currency),
                within_tolerance=within,
            )
        )
    return tuple(comparisons)

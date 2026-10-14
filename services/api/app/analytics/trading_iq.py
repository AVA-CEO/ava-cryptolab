"""Deterministic descriptive evidence. No signals, AI guesses or causal claims."""

from collections import Counter, defaultdict
from decimal import Decimal, localcontext

from app.analytics.trades import calculate, utc

MIN_CLOSED = 20
MIN_GROUP = 5


def review(trades, currency):
    with localcontext() as context:
        context.prec = 60
        return _review(trades, currency)


def _review(trades, currency):
    selected = [t for t in trades if t.currency == currency]
    closed = [t for t in selected if calculate(t)["status"] == "closed"]
    missing = sum(t.stop_loss is None for t in selected)
    findings = []
    if missing:
        findings.append(
            {
                "kind": "quality",
                "title": "Initial risk is missing",
                "detail": f"{missing} of {len(selected)} trades have no initial stop. "
                "Their R multiples cannot be calculated.",
                "count": missing,
            }
        )
    eligible = len(closed) >= MIN_CLOSED
    if eligible:
        groups = defaultdict(list)
        for t in closed:
            r = calculate(t)["realized_r"]
            if r is not None and t.strategy != "Unspecified":
                groups[t.strategy].append(Decimal(r))
        candidates = [
            (name, sum(values) / len(values), len(values))
            for name, values in groups.items()
            if len(values) >= MIN_GROUP
        ]
        if len(candidates) >= 2 and len({row[1] for row in candidates}) > 1:
            for kind, row in (
                ("strongest", max(candidates, key=lambda r: r[1])),
                ("weakest", min(candidates, key=lambda r: r[1])),
            ):
                findings.append(
                    {
                        "kind": "setup",
                        "title": f"Historically {kind} setup: {row[0]}",
                        "detail": f"Average {row[1]:.2f}R across {row[2]} closed trades. "
                        "Descriptive only; future performance is unknown.",
                        "count": row[2],
                    }
                )
        mistakes = Counter(
            tag
            for t in closed
            for tag in {
                value.strip().casefold() for value in t.mistakes.split(",") if value.strip()
            }
        )
        for tag, count in mistakes.most_common(3):
            if count >= 3:
                findings.append(
                    {
                        "kind": "reflection",
                        "title": f"Recurring logged mistake: {tag}",
                        "detail": f"You recorded this tag {count} times. Review those "
                        "entries; this does not prove it caused a loss.",
                        "count": count,
                    }
                )
        for dimension, getter in (
            ("coin", lambda t: t.pair),
            (
                "period (final exit UTC month)",
                lambda t: max(utc(e.exit_at) for e in t.exits).strftime("%Y-%m"),
            ),
        ):
            grouped = defaultdict(list)
            for t in closed:
                grouped[getter(t)].append(Decimal(calculate(t)["net_pnl"]))
            eligible_groups = [
                (name, sum(values) / len(values), len(values))
                for name, values in grouped.items()
                if len(values) >= MIN_GROUP
            ]
            if len(eligible_groups) >= 2 and len({row[1] for row in eligible_groups}) > 1:
                for label, row in (
                    ("Highest", max(eligible_groups, key=lambda r: r[1])),
                    ("Lowest", min(eligible_groups, key=lambda r: r[1])),
                ):
                    findings.append(
                        {
                            "kind": "comparison",
                            "title": f"{label} average {dimension}: {row[0]}",
                            "detail": f"{row[1]:.2f} {currency} per trade "
                            f"across {row[2]} observations. Position sizes may differ.",
                            "count": row[2],
                        }
                    )
        risks = [Decimal(calculate(t)["planned_risk"]) for t in closed if t.stop_loss]
        if len(risks) >= MIN_CLOSED and min(risks) > 0 and max(risks) / min(risks) > 3:
            findings.append(
                {
                    "kind": "risk",
                    "title": "Planned risk varies substantially",
                    "detail": f"Largest planned risk is {max(risks) / min(risks):.1f}× "
                    "the smallest. Review whether this variation was intentional; "
                    "account-relative risk is not inferred.",
                    "count": len(risks),
                }
            )
    return {
        "version": "rules-v1",
        "currency": currency,
        "eligible": eligible,
        "closed_count": len(closed),
        "minimum_closed": MIN_CLOSED,
        "minimum_group": MIN_GROUP,
        "message": "Historical review; no predictions or causal conclusions."
        if eligible
        else f"Need {MIN_CLOSED} closed trades in {currency} before comparing performance.",
        "findings": findings,
    }

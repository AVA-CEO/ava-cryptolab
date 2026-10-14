from collections import defaultdict
from decimal import Decimal, localcontext

from app.analytics.trades import calculate, utc


def performance(trades, currency="USD", opening_balance=None):
    with localcontext() as context:
        context.prec = 60
        return _performance(trades, currency, opening_balance)


def _performance(trades, currency="USD", opening_balance=None):
    selected = [t for t in trades if t.currency == currency]
    closed = sorted(
        [t for t in selected if calculate(t)["status"] == "closed"],
        key=lambda t: (max(utc(e.exit_at) for e in t.exits), t.id),
    )
    results = [Decimal(calculate(t)["net_pnl"]) for t in closed]
    wins = [p for p in results if p > 0]
    losses = [p for p in results if p < 0]
    risk_results = [
        Decimal(calculate(t)["realized_r"])
        for t in closed
        if calculate(t)["realized_r"] is not None
    ]
    net = sum((Decimal(calculate(t)["net_pnl"]) for t in selected), Decimal(0))
    cumulative = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    max_pct = Decimal(0)
    daily = defaultdict(Decimal)
    curve = [
        {
            "date": "Start",
            "pnl": 0,
            "balance": float(opening_balance) if opening_balance is not None else None,
        }
    ]
    events = defaultdict(Decimal)
    for trade, pnl in zip(closed, results, strict=True):
        events[max(utc(e.exit_at) for e in trade.exits)] += pnl
    # Simultaneous closures are one event; never invent an ordering within a timestamp.
    for timestamp, pnl in sorted(events.items()):
        cumulative += pnl
        peak = max(peak, cumulative)
        max_dd = max(max_dd, peak - cumulative)
        if opening_balance is not None and opening_balance + peak > 0:
            max_pct = max(max_pct, (peak - cumulative) / (opening_balance + peak) * 100)
        date = timestamp.date().isoformat()
        daily[date] += pnl
        curve.append(
            {
                "date": date,
                "pnl": float(cumulative),
                "balance": float(opening_balance + cumulative)
                if opening_balance is not None
                else None,
            }
        )

    def average(values):
        return str(sum(values, Decimal(0)) / len(values)) if values else None

    grouped = defaultdict(list)
    coins = defaultdict(list)
    monthly = defaultdict(Decimal)
    scatter = []
    for t in closed:
        metrics = calculate(t)
        grouped[t.strategy].append(Decimal(metrics["net_pnl"]))
        coins[t.pair].append(Decimal(metrics["net_pnl"]))
        monthly[metrics["last_exit_at"][:7]] += Decimal(metrics["net_pnl"])
        if metrics["realized_r"] is not None:
            scatter.append(
                {
                    "id": t.id,
                    "pair": t.pair,
                    "strategy": t.strategy,
                    "hours": metrics["holding_hours"],
                    "r": float(metrics["realized_r"]),
                    "risk": float(metrics["planned_risk"]),
                    "hour": utc(t.entry_at).hour,
                    "net": float(metrics["net_pnl"]),
                }
            )
    return {
        "currency": currency,
        "total_trades": len(selected),
        "closed_trades": len(closed),
        "open_trades": len(selected) - len(closed),
        "net_pnl": str(net),
        "closed_net_pnl": str(sum(results, Decimal(0))),
        "recorded_balance": str(opening_balance + net) if opening_balance is not None else None,
        "win_rate": len(wins) / len(closed) * 100 if closed else None,
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(results) - len(wins) - len(losses),
        "average_win": average(wins),
        "average_loss": average(losses),
        "expectancy": average(results),
        "average_r": average(risk_results),
        "profit_factor": str(sum(wins, Decimal(0)) / abs(sum(losses, Decimal(0))))
        if losses
        else None,
        "profit_factor_reason": None if losses else "No closed losing trades; ratio undefined.",
        "max_drawdown": str(max_dd) if closed else None,
        "max_drawdown_pct": str(max_pct)
        if closed and opening_balance is not None and opening_balance > 0
        else None,
        "average_holding_hours": sum(calculate(t)["holding_hours"] for t in closed) / len(closed)
        if closed
        else None,
        "r_coverage": len(risk_results),
        "curve": curve if closed else [],
        "daily": [{"date": date, "pnl": float(pnl)} for date, pnl in sorted(daily.items())],
        "monthly": [{"month": month, "pnl": float(pnl)} for month, pnl in sorted(monthly.items())],
        "scatter": scatter,
        "strategies": [
            {
                "name": name,
                "count": len(values),
                "net": float(sum(values)),
                "average": float(sum(values) / len(values)),
            }
            for name, values in sorted(grouped.items())
        ],
        "coins": [
            {"name": name, "count": len(values), "net": float(sum(values))}
            for name, values in sorted(coins.items())
        ],
    }

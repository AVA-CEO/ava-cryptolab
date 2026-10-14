import { BrainCircuit } from "lucide-react";
import { cn } from "@/lib/utils";
import { amount, type Analytics, type Currency } from "./contracts";
export function JournalStats({
  data,
  currency,
}: {
  data: Analytics;
  currency: Currency;
}) {
  return (
    <section className="journal-stat-grid" aria-label="Journal performance">
      {[
        {
          label: "Recorded net PnL",
          value: amount(data.net_pnl, currency),
          note: "All matching trades · incurred costs included",
          positive: Number(data.net_pnl) > 0,
          negative: Number(data.net_pnl) < 0,
        },
        {
          label: "Win rate",
          value: data.win_rate === null ? "—" : `${data.win_rate.toFixed(1)}%`,
          note: `${data.wins} wins / ${data.closed_trades} closed · breakeven included`,
        },
        {
          label: "Expectancy",
          value: amount(data.expectancy, currency),
          note: "Average net PnL per fully closed trade",
        },
        {
          label: "Profit factor",
          value:
            data.profit_factor === null
              ? "—"
              : Number(data.profit_factor).toFixed(2),
          note:
            data.profit_factor_reason ??
            "Net winning PnL ÷ absolute net losing PnL",
        },
        {
          label: "Closed-trade drawdown",
          value: amount(data.max_drawdown, currency),
          note:
            data.max_drawdown_pct === null
              ? "Peak-to-trough amount · no percentage baseline"
              : `${Number(data.max_drawdown_pct).toFixed(2)}% peak-to-trough`,
        },
        {
          label: "Average realized R",
          value:
            data.average_r === null
              ? "—"
              : `${Number(data.average_r).toFixed(2)}R`,
          note: `${data.r_coverage} of ${data.closed_trades} closed trades have initial risk`,
        },
      ].map((stat) => (
        <div className="panel metric-card" key={stat.label}>
          <div className="metric-label">{stat.label}</div>
          <strong
            className={cn(
              "metric-value",
              stat.positive && "positive",
              stat.negative && "negative",
            )}
          >
            {stat.value}
          </strong>
          <span className="metric-detail">{stat.note}</span>
        </div>
      ))}
    </section>
  );
}
export function TradingIQPanel({ data }: { data: Analytics }) {
  return (
    <section className="panel iq-panel">
      <div className="panel-heading">
        <div>
          <h2>
            <BrainCircuit size={19} />
            AVA Trading IQ
          </h2>
          <p>
            Evidence before conclusions. Descriptive review, never a trading
            signal.
          </p>
        </div>
        <span className="badge">{data.iq.version}</span>
      </div>
      <div className="iq-content">
        <p>{data.iq.message}</p>
        <div
          className="iq-progress"
          role="progressbar"
          aria-label="Trading IQ data readiness"
          aria-valuemin={0}
          aria-valuemax={20}
          aria-valuenow={Math.min(data.iq.closed_count, 20)}
        >
          <span
            style={{
              width: `${Math.min(data.iq.closed_count / 20, 1) * 100}%`,
            }}
          />
        </div>
        <small>
          {data.iq.closed_count} closed observations · Minimum 20 overall and 5
          per comparison group. These gates do not guarantee statistical
          significance.
        </small>
        <div className="iq-findings">
          {data.iq.findings.map((finding, i) => (
            <article key={i}>
              <span className="badge">{finding.kind}</span>
              <h3>{finding.title}</h3>
              <p>{finding.detail}</p>
            </article>
          ))}
        </div>
        {data.iq.eligible && !data.iq.findings.length && (
          <p>
            There are no findings supported by the current comparison groups.
          </p>
        )}
      </div>
    </section>
  );
}

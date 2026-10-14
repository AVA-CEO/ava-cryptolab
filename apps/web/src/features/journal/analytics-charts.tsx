"use client";
import { useState } from "react";
import { useReducedMotion } from "motion/react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { amount, type Analytics } from "./contracts";
import { cn } from "@/lib/utils";

const axis = { fill: "var(--muted-foreground)", fontSize: 11 };
const tooltip = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  color: "var(--foreground)",
  borderRadius: 10,
  fontSize: 12,
};
export default function AnalyticsCharts({ data }: { data: Analytics }) {
  const [view, setView] = useState<
    "curve" | "daily" | "monthly" | "strategies"
  >("curve");
  const [x, setX] = useState<"hours" | "risk" | "hour">("hours");
  const reduce = useReducedMotion();
  const hasBalance = data.recorded_balance !== null;
  const chartData: Record<string, string | number | null>[] =
    view === "curve"
      ? data.curve
      : view === "daily"
        ? data.daily
        : view === "monthly"
          ? data.monthly
          : data.strategies;
  const xKey =
    view === "monthly" ? "month" : view === "strategies" ? "name" : "date";
  const yKey =
    view === "curve" && hasBalance
      ? "balance"
      : view === "strategies"
        ? "net"
        : "pnl";
  const xLabel =
    x === "hours"
      ? "Holding duration (hours)"
      : x === "risk"
        ? `Initial planned risk (${data.currency})`
        : "Entry hour (UTC)";
  return (
    <div className="journal-chart-grid">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>
              {view === "curve"
                ? hasBalance
                  ? "Closed-trade balance curve"
                  : "Cumulative closed PnL"
                : view === "daily"
                  ? "Daily closed PnL"
                  : view === "monthly"
                    ? "Monthly closed PnL"
                    : "Strategy performance"}
            </h2>
            <p>
              {data.currency} · Actual recorded trades · After recorded costs
            </p>
          </div>
          <span className="badge">{data.closed_trades} CLOSED</span>
        </div>
        <div className="journal-tabs">
          {(["curve", "daily", "monthly", "strategies"] as const).map((tab) => (
            <button
              key={tab}
              aria-pressed={view === tab}
              className={cn(view === tab && "selected")}
              onClick={() => setView(tab)}
            >
              {
                {
                  curve: "Curve",
                  daily: "Daily",
                  monthly: "Monthly",
                  strategies: "Setups",
                }[tab]
              }
            </button>
          ))}
        </div>
        {chartData.length ? (
          <div
            className="journal-chart"
            aria-label={`${view} chart in ${data.currency}`}
          >
            <ResponsiveContainer width="100%" height="100%">
              {view === "curve" ? (
                <AreaChart
                  data={data.curve}
                  margin={{ top: 12, right: 20, bottom: 10, left: 8 }}
                >
                  <defs>
                    <linearGradient
                      id="journal-curve"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    stroke="var(--border)"
                    vertical={false}
                    strokeDasharray="3 5"
                  />
                  <XAxis dataKey="date" tick={axis} minTickGap={30} />
                  <YAxis tick={axis} width={70} domain={["auto", "auto"]} />
                  <Tooltip
                    contentStyle={tooltip}
                    formatter={(v) => [
                      amount(Number(v), data.currency),
                      hasBalance
                        ? "Closed-trade balance"
                        : "Cumulative net PnL",
                    ]}
                  />
                  <Area
                    dataKey={yKey}
                    stroke="#a78bfa"
                    fill="url(#journal-curve)"
                    strokeWidth={2.5}
                    isAnimationActive={!reduce}
                  />
                </AreaChart>
              ) : (
                <BarChart
                  data={chartData}
                  margin={{ top: 12, right: 20, bottom: 10, left: 8 }}
                >
                  <CartesianGrid
                    stroke="var(--border)"
                    vertical={false}
                    strokeDasharray="3 5"
                  />
                  <XAxis dataKey={xKey} tick={axis} minTickGap={30} />
                  <YAxis tick={axis} width={70} />
                  <ReferenceLine y={0} stroke="var(--muted-foreground)" />
                  <Tooltip
                    contentStyle={tooltip}
                    formatter={(v) => [
                      amount(Number(v), data.currency),
                      "Net PnL",
                    ]}
                  />
                  <Bar
                    dataKey={yKey}
                    radius={[4, 4, 0, 0]}
                    isAnimationActive={!reduce}
                  >
                    {chartData.map((row, i) => (
                      <Cell
                        key={i}
                        fill={
                          Number(
                            (row as unknown as Record<string, number>)[yKey],
                          ) >= 0
                            ? "var(--green)"
                            : "var(--red)"
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
        ) : (
          <ChartEmpty text="Close a trade to start building your performance history." />
        )}
        <p className="chart-footnote">
          Curves and drawdown use fully closed trades at their final exit.
          Partial exits and open costs are included in total recorded net PnL,
          but excluded here. This is not mark-to-market equity.
        </p>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Risk & outcome explorer</h2>
            <p>Realized R versus a recorded trade characteristic.</p>
          </div>
          <span className="badge">{data.r_coverage} WITH R</span>
        </div>
        <div className="journal-tabs">
          {(["hours", "risk", "hour"] as const).map((key) => (
            <button
              key={key}
              aria-pressed={x === key}
              className={cn(x === key && "selected")}
              onClick={() => setX(key)}
            >
              {
                { hours: "Duration", risk: "Planned risk", hour: "Entry hour" }[
                  key
                ]
              }
            </button>
          ))}
        </div>
        {data.scatter.length ? (
          <div className="journal-chart">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart
                margin={{ top: 15, right: 20, bottom: 35, left: 15 }}
              >
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 5" />
                <XAxis
                  type="number"
                  dataKey={x}
                  name={xLabel}
                  tick={axis}
                  label={{
                    value: xLabel,
                    position: "bottom",
                    ...axis,
                    offset: 12,
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="r"
                  name="Realized outcome"
                  unit="R"
                  tick={axis}
                  width={42}
                />
                <ReferenceLine y={0} stroke="var(--muted-foreground)" />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3" }}
                  content={(props) => {
                    const point = props.payload?.[0]?.payload as
                      Analytics["scatter"][number] | undefined;
                    return props.active && point ? (
                      <div className="observation-tooltip">
                        <strong>
                          {point.pair} · {point.strategy}
                        </strong>
                        <span>Realized: {point.r.toFixed(2)}R</span>
                        <span>
                          Planned risk: {amount(point.risk, data.currency)}
                        </span>
                        <span>Duration: {point.hours.toFixed(2)}h</span>
                        <span>Entry hour: {point.hour}:00 UTC</span>
                      </div>
                    ) : null;
                  }}
                />
                <Scatter
                  name="Positive / breakeven R"
                  data={data.scatter.filter((t) => t.r >= 0)}
                  fill="var(--green)"
                  isAnimationActive={!reduce}
                />
                <Scatter
                  name="Negative R"
                  data={data.scatter.filter((t) => t.r < 0)}
                  fill="var(--red)"
                  isAnimationActive={!reduce}
                />
                <Legend wrapperStyle={{ fontSize: 10, paddingTop: 22 }} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <ChartEmpty text="Closed trades with an initial stop populate this view. Missing risk is never guessed." />
        )}
        <p className="chart-footnote">
          Each point is one fully closed trade. Hover for the underlying
          observation. This chart alone establishes neither correlation nor
          causation.
        </p>
      </section>
    </div>
  );
}
function ChartEmpty({ text }: { text: string }) {
  return (
    <div className="small-empty">
      <p>Let your records tell the story.</p>
      <small>{text}</small>
    </div>
  );
}

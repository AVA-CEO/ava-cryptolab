"use client";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { equitySeries, sampleTrades } from "./sample-data";
import { money } from "@/lib/utils";
import { useReducedMotion } from "motion/react";

const tooltip = {
  background: "var(--card)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  color: "var(--foreground)",
  fontSize: 12,
};
const axis = { fill: "var(--muted-foreground)", fontSize: 11 };
export default function Charts({
  trades,
  view,
}: {
  trades: typeof sampleTrades;
  view: "equity" | "daily" | "scatter";
}) {
  const reducedMotion = useReducedMotion();
  if (!trades.length) return <p>No simulated observations in this period.</p>;
  if (view === "scatter")
    return (
      <div
        className="chart-height"
        role="img"
        aria-label="Simulated trade duration in hours versus realized R multiple"
      >
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 15, right: 15, bottom: 28, left: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="3 5" />
            <XAxis
              type="number"
              dataKey="hours"
              name="Duration"
              unit="h"
              tick={axis}
              axisLine={false}
              tickLine={false}
              label={{
                value: "Trade duration (hours)",
                position: "bottom",
                offset: 10,
                ...axis,
              }}
            />
            <YAxis
              type="number"
              dataKey="r"
              name="Realized R"
              unit="R"
              tick={axis}
              axisLine={false}
              tickLine={false}
              width={45}
            />
            <ZAxis range={[65, 65]} />
            <Tooltip
              contentStyle={tooltip}
              cursor={{ strokeDasharray: "3 3" }}
            />
            <ReferenceLine y={0} stroke="var(--muted-foreground)" />
            <Scatter
              isAnimationActive={!reducedMotion}
              name="Positive outcome (simulated)"
              data={trades.filter((t) => t.r > 0)}
              fill="#34d399"
            />
            <Scatter
              isAnimationActive={!reducedMotion}
              name="Negative outcome (simulated)"
              data={trades.filter((t) => t.r <= 0)}
              fill="#fb7185"
            />
            <Legend wrapperStyle={{ paddingTop: 25, fontSize: 11 }} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    );
  return (
    <div
      className="chart-height"
      role="img"
      aria-label={
        view === "equity"
          ? "Simulated recorded equity in US dollars by date"
          : "Simulated daily realized profit and loss in US dollars"
      }
    >
      <ResponsiveContainer width="100%" height="100%">
        {view === "equity" ? (
          <AreaChart
            data={equitySeries(trades)}
            margin={{ top: 10, right: 12, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="equity-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              stroke="var(--border)"
              vertical={false}
              strokeDasharray="3 5"
            />
            <XAxis
              dataKey="label"
              tick={axis}
              axisLine={false}
              tickLine={false}
              minTickGap={45}
            />
            <YAxis
              tick={axis}
              domain={["dataMin - 150", "dataMax + 150"]}
              axisLine={false}
              tickLine={false}
              width={65}
              tickFormatter={(v) => `$${(Number(v) / 1000).toFixed(1)}k`}
            />
            <Tooltip
              contentStyle={tooltip}
              formatter={(v) => [money(Number(v)), "Simulated equity"]}
            />
            <Area
              isAnimationActive={!reducedMotion}
              type="monotone"
              dataKey="equity"
              name="Equity (USD)"
              stroke="#a78bfa"
              strokeWidth={2.5}
              fill="url(#equity-fill)"
            />
          </AreaChart>
        ) : (
          <BarChart
            data={trades}
            margin={{ top: 10, right: 12, left: 0, bottom: 0 }}
          >
            <CartesianGrid
              stroke="var(--border)"
              vertical={false}
              strokeDasharray="3 5"
            />
            <XAxis
              dataKey="label"
              tick={axis}
              axisLine={false}
              tickLine={false}
              minTickGap={45}
            />
            <YAxis
              tick={axis}
              width={65}
              tickFormatter={(v) => `$${v}`}
              axisLine={false}
              tickLine={false}
            />
            <ReferenceLine y={0} stroke="var(--muted-foreground)" />
            <Tooltip
              contentStyle={tooltip}
              formatter={(v) => [money(Number(v)), "Simulated PnL"]}
            />
            <Bar
              isAnimationActive={!reducedMotion}
              dataKey="pnl"
              name="PnL (USD)"
              fill="#22d3ee"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

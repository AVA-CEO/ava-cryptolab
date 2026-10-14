export type Currency = "USD" | "USDT" | "USDC";
export type Exit = {
  exit_at: string;
  price: string;
  quantity: string;
  fees: string;
};
export type Metrics = {
  status: "open" | "partial" | "closed";
  outcome: "win" | "loss" | "breakeven";
  gross_pnl: string;
  net_pnl: string;
  realized_r: string | null;
  planned_risk: string | null;
  notional: string;
  estimated_margin: string;
  remaining_quantity: string;
  closed_quantity: string;
  holding_hours: number | null;
  last_exit_at: string | null;
};
export type Trade = {
  id: string;
  version: number;
  pair: string;
  exchange: string;
  currency: Currency;
  market: "spot" | "futures";
  direction: "buy" | "sell";
  entry_at: string;
  entry_price: string;
  quantity: string;
  stop_loss: string | null;
  take_profit: string | null;
  entry_fees: string;
  funding: string;
  leverage: string;
  margin_type: "cross" | "isolated" | null;
  strategy: string;
  notes: string;
  mistakes: string;
  emotion_before: string;
  emotion_after: string;
  lessons: string;
  exits: Exit[];
  has_screenshot: boolean;
  metrics: Metrics;
};
export type Analytics = {
  currency: Currency;
  total_trades: number;
  closed_trades: number;
  open_trades: number;
  net_pnl: string;
  closed_net_pnl: string;
  recorded_balance: string | null;
  win_rate: number | null;
  wins: number;
  losses: number;
  breakeven: number;
  average_win: string | null;
  average_loss: string | null;
  expectancy: string | null;
  average_r: string | null;
  profit_factor: string | null;
  profit_factor_reason: string | null;
  max_drawdown: string | null;
  max_drawdown_pct: string | null;
  r_coverage: number;
  average_holding_hours: number | null;
  curve: { date: string; pnl: number; balance: number | null }[];
  daily: { date: string; pnl: number }[];
  monthly: { month: string; pnl: number }[];
  scatter: {
    id: string;
    pair: string;
    strategy: string;
    hours: number;
    r: number;
    risk: number;
    hour: number;
    net: number;
  }[];
  strategies: { name: string; count: number; net: number; average: number }[];
  coins: { name: string; count: number; net: number }[];
  iq: {
    version: string;
    eligible: boolean;
    closed_count: number;
    minimum_closed: number;
    minimum_group: number;
    message: string;
    findings: { kind: string; title: string; detail: string; count: number }[];
  };
};
export function amount(
  value: string | number | null,
  currency: Currency = "USD",
) {
  if (value === null) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  const formatted = new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n);
  return currency === "USD"
    ? `${n < 0 ? "−" : ""}$${formatted.replace("-", "")}`
    : `${formatted} ${currency}`;
}
export async function requestJSON<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(url, { ...options, cache: "no-store" });
  const data = await response.json();
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map(
                (e: { loc: string[]; msg: string }) =>
                  `${e.loc.slice(1).join(".")}: ${e.msg}`,
              )
              .join("; ")
          : "The request failed. Try again.",
    );
  }
  return data as T;
}

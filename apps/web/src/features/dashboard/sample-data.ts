// Deterministic educational fixtures. Never persisted or served as market observations.
export const sampleTrades = Array.from({ length: 30 }, (_, i) => {
  const outcomes = [1.2, -1, 2.1, 0.6, -0.7, 1.8, -1, 2.6, 0.4, 1.1];
  const r = outcomes[i % outcomes.length];
  const risk = 45 + (i % 6) * 12;
  return {
    id: i + 1,
    day: i + 1,
    label: `Sep ${i + 1}`,
    coin: ["BTC", "ETH", "SOL"][i % 3],
    hours: 1 + ((i * 7) % 48),
    risk,
    r,
    pnl: Number((risk * r).toFixed(2)),
  };
});
export function sampleForDays(days: number) {
  return sampleTrades.slice(-Math.min(days, 30));
}
export function equitySeries(trades: typeof sampleTrades) {
  let equity = 10000;
  return trades.map((t) => {
    equity += t.pnl;
    return { ...t, equity: Number(equity.toFixed(2)) };
  });
}

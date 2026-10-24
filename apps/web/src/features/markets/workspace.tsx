"use client";
import { useEffect, useState } from "react";
import { Star, Search } from "lucide-react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import Link from "next/link";
import "@/features/product.css";

const examples = [
  {
    symbol: "BTC",
    name: "Bitcoin",
    category: "Payment network",
    cap: 1000,
    change: 2,
    volume: 30,
    volatility: 3,
  },
  {
    symbol: "ETH",
    name: "Ethereum",
    category: "Smart contracts",
    cap: 300,
    change: -1,
    volume: 15,
    volatility: 4,
  },
  {
    symbol: "SOL",
    name: "Solana",
    category: "Smart contracts",
    cap: 60,
    change: 4,
    volume: 4,
    volatility: 7,
  },
  {
    symbol: "LINK",
    name: "Chainlink",
    category: "Oracle network",
    cap: 10,
    change: -3,
    volume: 0.5,
    volatility: 6,
  },
  {
    symbol: "USDC",
    name: "USD Coin",
    category: "Stablecoin",
    cap: 40,
    change: 0.1,
    volume: 5,
    volatility: 0.2,
  },
];
type Sort = "cap" | "change" | "volume" | "volatility";
export function MarketsWorkspace() {
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<Sort>("cap");
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [onlyWatched, setOnlyWatched] = useState(false);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const data = JSON.parse(
          localStorage.getItem("ava-watchlist-v1") ?? "[]",
        );
        if (Array.isArray(data))
          setWatchlist(
            data.filter((x) => examples.some((e) => e.symbol === x)),
          );
      } catch {
        /* Optional browser storage. */
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);
  function toggle(symbol: string) {
    const next = watchlist.includes(symbol)
      ? watchlist.filter((x) => x !== symbol)
      : [...watchlist, symbol];
    setWatchlist(next);
    try {
      localStorage.setItem("ava-watchlist-v1", JSON.stringify(next));
    } catch {
      setNotice(
        "Watchlist changes last for this session only; browser storage is unavailable.",
      );
    }
  }
  const rows = examples
    .filter(
      (e) =>
        `${e.symbol} ${e.name} ${e.category}`
          .toLowerCase()
          .includes(search.toLowerCase()) &&
        (!onlyWatched || watchlist.includes(e.symbol)),
    )
    .sort((a, b) => b[sort] - a[sort]);
  return (
    <div className="page-content product-page">
      <p className="eyebrow">RESEARCH WITH CONTEXT</p>
      <h1>Market research</h1>
      <p className="page-subtitle">
        Build a watchlist. Explore what metrics mean before drawing conclusions.
      </p>
      <div className="product-notice">
        EDUCATIONAL DATA · All figures below are fictional illustrations, not
        current prices or market observations. No live provider is connected.
        There is no live timestamp.
      </div>
      {notice && <p role="status">{notice}</p>}
      <div className="product-grid">
        {[
          {
            title: "Market capitalization",
            text: "Price × circulating supply. A larger market cap does not guarantee liquidity or safety.",
          },
          {
            title: "Trading volume",
            text: "Reported turnover over an interval. It is not the same as executable order-book liquidity.",
          },
          {
            title: "Volatility",
            text: "Price variability depends on the method and observation window. Example percentages here are invented, not estimated from historical prices.",
          },
        ].map((c) => (
          <article className="panel product-card" key={c.title}>
            <h2>{c.title}</h2>
            <p>{c.text}</p>
          </article>
        ))}
      </div>
      <section className="panel product-card">
        <div className="product-fields">
          <label>
            <span>
              <Search size={15} /> Find an asset
            </span>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Name, symbol or category"
            />
          </label>
          <label>
            Sort examples
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as Sort)}
            >
              <option value="cap">Market cap</option>
              <option value="change">Price change</option>
              <option value="volume">Volume</option>
              <option value="volatility">Volatility</option>
            </select>
          </label>
        </div>
        <button
          className="product-choice"
          aria-pressed={onlyWatched}
          onClick={() => setOnlyWatched((x) => !x)}
        >
          {onlyWatched
            ? "Show all examples"
            : `My browser watchlist (${watchlist.length})`}
        </button>
        <div style={{ overflowX: "auto" }}>
          <table className="product-table">
            <caption>
              Fictional market examples · cap and volume in USD billions
            </caption>
            <thead>
              <tr>
                <th>Watch</th>
                <th>Asset</th>
                <th>Example cap</th>
                <th>Example change</th>
                <th>Example volume</th>
                <th>Example volatility</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.symbol}>
                  <td>
                    <button
                      className="product-text-button"
                      aria-label={`Watch ${row.symbol}`}
                      aria-pressed={watchlist.includes(row.symbol)}
                      onClick={() => toggle(row.symbol)}
                    >
                      <Star
                        size={18}
                        fill={
                          watchlist.includes(row.symbol)
                            ? "var(--primary)"
                            : "none"
                        }
                      />
                    </button>
                  </td>
                  <td>
                    <strong>{row.symbol}</strong>
                    <br />
                    <small>
                      {row.name} · {row.category}
                    </small>
                  </td>
                  <td>{row.cap}B</td>
                  <td className={row.change >= 0 ? "positive" : "negative"}>
                    {row.change}%
                  </td>
                  <td>{row.volume}B</td>
                  <td>{row.volatility}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && (
            <p>
              No matching examples. Try another search or add assets to your
              watchlist.
            </p>
          )}
        </div>
      </section>
      <div className="product-columns" style={{ marginTop: 24 }}>
        {[
          {
            x: "cap",
            y: "change",
            title: "Size vs price movement",
            xLabel: "Example cap (USD B)",
            yLabel: "Example change (%)",
          },
          {
            x: "volume",
            y: "volatility",
            title: "Volume vs volatility",
            xLabel: "Example volume (USD B)",
            yLabel: "Example volatility (%)",
          },
        ].map((c) => (
          <section className="panel product-card" key={c.x}>
            <h2>{c.title}</h2>
            <p>
              Fictional observations · descriptive only; no correlation or
              causation claim.
            </p>
            <div style={{ width: "100%", height: 290 }}>
              <ResponsiveContainer>
                <ScatterChart
                  margin={{ top: 15, right: 20, bottom: 35, left: 10 }}
                >
                  <CartesianGrid stroke="var(--border)" />
                  <XAxis
                    type="number"
                    dataKey={c.x}
                    name={c.xLabel}
                    tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                    label={{
                      value: c.xLabel,
                      position: "bottom",
                      fill: "var(--muted-foreground)",
                    }}
                  />
                  <YAxis
                    type="number"
                    dataKey={c.y}
                    name={c.yLabel}
                    tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                  />
                  <Tooltip
                    content={({ active, payload }) =>
                      active && payload?.length ? (
                        <div className="panel" style={{ padding: 12 }}>
                          {payload[0].payload.name}
                          <br />
                          {c.xLabel}: {payload[0].value}
                          <br />
                          {c.yLabel}: {payload[1]?.value}
                        </div>
                      ) : null
                    }
                  />
                  <Scatter
                    name="Fictional examples"
                    data={rows}
                    fill="var(--primary)"
                  />
                </ScatterChart>
              </ResponsiveContainer>
            </div>
            <small>Y axis: {c.yLabel}</small>
          </section>
        ))}
      </div>
      <p className="product-muted">
        Watchlist symbols are stored only in this browser. They are not trades,
        recommendations or broker subscriptions.{" "}
        <Link className="product-link" href="/academy">
          Learn market basics →
        </Link>
      </p>
    </div>
  );
}

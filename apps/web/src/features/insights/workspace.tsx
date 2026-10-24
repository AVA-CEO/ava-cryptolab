"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import {
  JournalStats,
  TradingIQPanel,
} from "@/features/journal/performance-panels";
import type { Analytics, Currency } from "@/features/journal/contracts";
import "@/features/product.css";
const Charts = dynamic(() => import("@/features/journal/analytics-charts"), {
  ssr: false,
});
export function InsightsWorkspace() {
  const [currency, setCurrency] = useState<Currency>("USD");
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    fetch(`/api/journal/analytics?currency=${currency}`, {
      signal: controller.signal,
    })
      .then(async (r) => {
        const body = await r.json();
        if (!r.ok) throw new Error(body.detail ?? "Analytics unavailable.");
        setData(body);
        setError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [currency]);
  return (
    <div className="page-content product-page">
      <p className="eyebrow">EVIDENCE BEFORE CONCLUSIONS</p>
      <h1>AVA Trading IQ</h1>
      <p className="page-subtitle">
        Review your process using recorded trades, clear definitions and honest
        sample sizes.
      </p>
      <label style={{ maxWidth: 240 }}>
        Settlement currency
        <select
          value={currency}
          onChange={(e) => {
            setCurrency(e.target.value as Currency);
            setData(null);
          }}
        >
          {["USD", "USDT", "USDC"].map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </label>
      <div className="product-notice">
        Crypto journal observations only. Currencies stay separate; CFD previews
        are not accepted records and never enter these statistics.
      </div>
      {error && (
        <div role="alert" className="product-error">
          {error} <Link href="/journal">Open the journal</Link>
        </div>
      )}
      {!error && !data && (
        <div className="panel product-card" role="status">
          Loading recorded performance…
        </div>
      )}
      {data && (
        <>
          <JournalStats data={data} currency={currency} />
          <TradingIQPanel data={data} />
          {data.closed_trades ? (
            <Charts data={data} />
          ) : (
            <section className="panel product-card">
              <h2>Your evidence starts with a journal</h2>
              <p>
                No fully closed trades in this currency. Record and review
                trades before drawing performance conclusions.
              </p>
              <Link className="product-link" href="/journal">
                Go to trading journal →
              </Link>
            </section>
          )}
        </>
      )}
      <p className="product-muted">
        Closed-trade drawdown is not intratrade drawdown. A journal balance is
        not a broker reconciliation. Trading IQ describes this sample; it does
        not predict profits.
      </p>
    </div>
  );
}

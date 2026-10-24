"use client";
import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import "@/features/product.css";
const scenes = [
  {
    open: 100,
    close: 104,
    high: 110,
    low: 95,
    move: "bullish",
    explanation:
      "Close is above open. That describes this interval, not the next one.",
  },
  {
    open: 104,
    close: 99,
    high: 108,
    low: 96,
    move: "bearish",
    explanation: "Close is below open. Wick extremes are not forecasts.",
  },
  {
    open: 100,
    close: 100,
    high: 105,
    low: 95,
    move: "unchanged",
    explanation:
      "Open and close match, even though prices moved during the interval.",
  },
];
export function CandleLab() {
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const scene = scenes[index];
  return (
    <div className="page-content product-page">
      <p className="eyebrow">MECHANICS, MADE TANGIBLE</p>
      <h1>Market mechanics lab</h1>
      <p className="page-subtitle">
        A safe place to ask what a market observation actually means.
      </p>
      <div className="product-notice">
        Hypothetical examples only. No market feed, trading signal or order
        execution.
      </div>
      <div className="product-columns">
        <section className="panel product-card">
          <h2>Guess the candle</h2>
          <p>
            Open {scene.open} · High {scene.high} · Low {scene.low} · Close{" "}
            {scene.close}
          </p>
          <div
            role="img"
            aria-label={`Candle opens ${scene.open}, closes ${scene.close}, high ${scene.high}, low ${scene.low}`}
            style={{
              position: "relative",
              height: 180,
              width: 100,
              margin: "0 auto",
            }}
          >
            <span
              style={{
                position: "absolute",
                top: 10,
                bottom: 10,
                width: 2,
                left: 49,
                background: "var(--muted-foreground)",
              }}
            />
            <span
              style={{
                position: "absolute",
                top: 60,
                height: scene.open === scene.close ? 3 : 60,
                width: 44,
                left: 28,
                background:
                  scene.close >= scene.open ? "var(--green)" : "var(--red)",
                borderRadius: 3,
              }}
            />
          </div>
          <p>Is the open-to-close movement bullish, bearish or unchanged?</p>
          {["bullish", "bearish", "unchanged"].map((value) => (
            <button
              key={value}
              className="product-choice"
              aria-pressed={answer === value}
              disabled={!!answer}
              onClick={() => setAnswer(value)}
            >
              {value}
            </button>
          ))}
          {answer && (
            <div role="status" className="product-outcome">
              <h3 className={answer === scene.move ? "positive" : "negative"}>
                {answer === scene.move
                  ? "Correct"
                  : `The movement is ${scene.move}`}
              </h3>
              <p>{scene.explanation}</p>
              <Button
                onClick={() => {
                  setIndex((i) => (i + 1) % scenes.length);
                  setAnswer("");
                }}
              >
                Next candle
              </Button>
            </div>
          )}
          <small>
            Visual is schematic, not a price-scaled financial chart. This
            unscored exercise is checked in your browser.
          </small>
        </section>
        <section className="panel product-card">
          <h2>From observation to understanding</h2>
          <h3>Liquidity & spread</h3>
          <p>
            The best bid is the highest currently quoted buy price; the best ask
            is the lowest quoted sell price. Their difference is the spread. A
            large order may fill across several levels, creating slippage.
            Turnover alone does not tell you that depth.
          </p>
          <h3>Funding & open interest</h3>
          <p>
            Funding transfers can affect perpetual-futures holding costs. Open
            interest counts outstanding contracts, not a guaranteed direction of
            the next move. Neither is a buy/sell instruction.
          </p>
          <h3>Exposure & leverage</h3>
          <p>
            Quantity determines exposure. Leverage changes margin financing, not
            the price PnL formula a second time. Actual liquidation requires the
            broker&apos;s rules and current account state.
          </p>
          <Link className="product-link" href="/cfd-preview">
            Explore an unsaved forex/metals outcome →
          </Link>
          <Link className="product-link" href="/academy">
            Learn risk and contract units →
          </Link>
        </section>
      </div>
    </div>
  );
}

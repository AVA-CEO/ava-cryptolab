"use client";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useState } from "react";
import { motion } from "motion/react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  ChartNoAxesCombined,
  FlaskConical,
  ListPlus,
  Radio,
  Target,
  Trophy,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { DashboardResult } from "@/lib/api";
import {
  FirstStepsCard,
  LearningCard,
  WatchlistPreview,
} from "./dashboard-cards";
import { cn, money } from "@/lib/utils";
import { equitySeries, sampleForDays } from "./sample-data";
import { JournalWorkspace } from "@/features/journal/workspace";

const Charts = dynamic(() => import("./charts"), {
  ssr: false,
  loading: () => (
    <div className="skeleton chart-height" aria-label="Loading sample chart" />
  ),
});

export function Dashboard({ result }: { result: DashboardResult }) {
  const [sample, setSample] = useState(false);
  const [days, setDays] = useState(30);
  const [view, setView] = useState<"equity" | "daily">("equity");
  const trades = sampleForDays(days);
  const equity = equitySeries(trades).at(-1)?.equity ?? 10000;
  const pnl = trades.reduce((sum, t) => sum + t.pnl, 0);
  const wins = trades.filter((t) => t.pnl > 0).length;
  const positives = trades
    .filter((t) => t.pnl > 0)
    .reduce((s, t) => s + t.pnl, 0);
  const losses = Math.abs(
    trades.filter((t) => t.pnl < 0).reduce((s, t) => s + t.pnl, 0),
  );
  const summary = result.status === "connected" ? result.summary : null;
  const stats = [
    {
      label: "Recorded equity",
      value: sample
        ? money(equity)
        : summary?.recorded_equity
          ? money(Number(summary.recorded_equity))
          : "—",
      icon: Wallet,
      detail: sample
        ? "Simulated opening balance: $10,000"
        : "Connect your trading story",
    },
    {
      label: "Realized PnL",
      value: sample ? `${pnl >= 0 ? "+" : ""}${money(pnl)}` : "—",
      icon: ChartNoAxesCombined,
      detail: sample
        ? "Calculated from sample trades"
        : "After fees & funding costs",
      positive: sample && pnl > 0,
    },
    {
      label: "Win rate",
      value: sample ? `${((wins / trades.length) * 100).toFixed(1)}%` : "—",
      icon: Target,
      detail: sample
        ? `${wins} wins across ${trades.length} sample trades`
        : "Your process, in perspective",
    },
    {
      label: "Profit factor",
      value: sample
        ? losses
          ? (positives / losses).toFixed(2)
          : "Undefined"
        : "—",
      icon: Activity,
      detail: sample
        ? "Gross wins ÷ absolute gross losses"
        : "Gross wins ÷ absolute gross losses",
    },
  ];
  if (!sample && summary?.mode === "recorded") {
    return <JournalWorkspace overview onSample={() => setSample(true)} />;
  }
  return (
    <div className="page-content">
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            <span className="tiny-line" />
            YOUR TRADING WORKSPACE
          </p>
          <h1>
            Command Center<span className="heading-dot">.</span>
          </h1>
          <p className="page-subtitle">
            A clearer view of your trades. A smarter path forward.
          </p>
        </div>
        <Button variant="outline" onClick={() => setSample(!sample)}>
          <FlaskConical size={16} />
          {sample ? "Exit sample mode" : "Explore sample data"}
        </Button>
      </div>
      <div className={cn("workspace-status", sample && "sample-status")}>
        <div>
          <span className="status-dot" />
          <span>{sample ? "Sample workspace" : "Personal workspace"}</span>
          <span className="status-divider" />
          <span className="status-description">
            {sample
              ? "SIMULATED DATA · Educational examples only"
              : "Your data stays local. Your progress starts here."}
          </span>
        </div>
        <span className="connection">
          <Radio size={13} />
          {result.status === "connected"
            ? "Local API connected"
            : "Local API unavailable"}
        </span>
      </div>
      {result.status === "unavailable" && (
        <p className="api-notice" role="status">
          The API is offline or needs its database migration. Account data is
          unavailable; sample mode is still available. Start the API using the
          setup guide.
        </p>
      )}
      <section className="metric-grid" aria-label="Performance summary">
        {stats.map((s) => (
          <div className="panel metric-card" key={s.label}>
            <div className="metric-label">
              <span>{s.label}</span>
              <s.icon size={17} />
            </div>
            <strong className={cn("metric-value", s.positive && "positive")}>
              {s.value}
            </strong>
            <span className="metric-detail">
              {s.positive && <ArrowUpRight size={13} />}
              {s.detail}
            </span>
          </div>
        ))}
      </section>
      <div className="dashboard-main-grid">
        <section className="panel performance-panel">
          <div className="panel-heading">
            <div>
              <h2>Performance overview</h2>
              <p>
                {sample
                  ? "A simulated trading journey, never a return forecast."
                  : "Every decision adds to the bigger picture."}
              </p>
            </div>
            <span className="badge">
              {sample ? "SIMULATED" : "NO TRADES YET"}
            </span>
          </div>
          <div className="chart-toolbar">
            <div className="segmented-control">
              <button
                aria-pressed={view === "equity"}
                className={cn(view === "equity" && "selected")}
                onClick={() => setView("equity")}
              >
                Equity curve
              </button>
              <button
                aria-pressed={view === "daily"}
                className={cn(view === "daily" && "selected")}
                onClick={() => setView("daily")}
              >
                Daily PnL
              </button>
            </div>
            <div className="period-control" aria-label="Sample date range">
              {[7, 30, 90].map((d) => (
                <button
                  key={d}
                  aria-pressed={days === d}
                  className={cn(days === d && "selected")}
                  onClick={() => setDays(d)}
                >
                  {d}D
                </button>
              ))}
            </div>
          </div>
          {sample ? (
            <>
              <Charts trades={trades} view={view} />
              <p className="chart-footnote">
                USD · Sample period: September 1–30 ·{" "}
                {days === 90
                  ? "30 days of sample observations available"
                  : `Last ${days} sample days`}
              </p>
            </>
          ) : (
            <div className="empty-chart">
              <div className="empty-grid" />
              <span className="empty-icon">
                <ChartNoAxesCombined size={29} />
              </span>
              <h3>Your story starts with one trade.</h3>
              <p>
                Record your decisions, understand your habits,
                <br />
                and let the data show you where to grow.
              </p>
              <Button onClick={() => setSample(true)}>
                <FlaskConical size={16} />
                Preview a sample journey
                <ArrowRight size={15} />
              </Button>
              <small>No fabricated returns. Just room to begin.</small>
            </div>
          )}
        </section>
        <LearningCard />
      </div>
      <div className="dashboard-bottom-grid">
        <section className="panel journal-panel">
          <div className="panel-heading">
            <div>
              <h2>Recent journal entries</h2>
              <p>Capture the decision, not just the outcome.</p>
            </div>
            <Link href="/journal" className="text-link">
              View journal
              <ArrowUpRight size={14} />
            </Link>
          </div>
          {sample ? (
            <>
              <div className="sample-table-label">
                SIMULATED ENTRIES · NOT SAVED
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Pair</th>
                      <th>Outcome</th>
                      <th>Realized R</th>
                      <th>Duration</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades
                      .slice(-4)
                      .reverse()
                      .map((t) => (
                        <tr key={t.id}>
                          <td>
                            <span
                              className={cn("coin-mark", t.coin.toLowerCase())}
                            >
                              {t.coin[0]}
                            </span>
                            <strong>{t.coin}/USD</strong>
                            <small>Sample #{t.id}</small>
                          </td>
                          <td className={t.pnl > 0 ? "positive" : "negative"}>
                            {t.pnl > 0 ? "+" : ""}
                            {money(t.pnl)}
                          </td>
                          <td>{t.r.toFixed(1)}R</td>
                          <td>{t.hours}h</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="journal-empty">
              <span className="soft-icon">
                <ListPlus size={24} />
              </span>
              <div>
                <h3>A journal for your future self.</h3>
                <p>
                  Your trades and reflections will appear here.
                  <br />
                  Record your first trade in the journal.
                </p>
                <Link href="/journal" className="text-link">
                  Open trading journal
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          )}
        </section>
        <FirstStepsCard />
      </div>
      <div className="dashboard-bottom-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Duration vs. realized outcome</h2>
              <p>Explore holding time and risk-normalized results.</p>
            </div>
            <span className="badge">
              {sample ? "SIMULATED" : "RESEARCH VIEW"}
            </span>
          </div>
          {sample ? (
            <>
              <Charts trades={trades} view="scatter" />
              <p className="chart-footnote">
                R = net outcome ÷ planned initial risk. These fixtures do not
                establish correlation or causation.
              </p>
            </>
          ) : (
            <div className="small-empty">
              <ChartNoAxesCombined size={24} />
              <p>Patterns need observations.</p>
              <small>
                Trades with a planned stop will populate this view in Phase 2.
              </small>
            </div>
          )}
        </section>
        <WatchlistPreview />
      </div>
      <motion.section
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="insight-strip"
      >
        <span className="soft-icon">
          <Trophy size={22} />
        </span>
        <div>
          <strong>Consistency is an edge you can build.</strong>
          <p>
            A thoughtful journal entry. A concept understood. One better
            decision at a time.
          </p>
        </div>
        <span className="badge">ANALYSE. LEARN. TRADE SMARTER.</span>
      </motion.section>
    </div>
  );
}

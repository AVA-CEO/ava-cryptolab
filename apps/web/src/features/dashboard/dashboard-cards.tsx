import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  ChevronRight,
  CircleHelp,
  Compass,
  GraduationCap,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const milestones = [
  { label: "Create your workspace", done: true },
  { label: "Record your first trade", done: false },
  { label: "Learn something new", done: false },
];
export function LearningCard() {
  return (
    <section className="learning-card">
      <div className="learning-top">
        <span className="eyebrow">BUILD YOUR EDGE</span>
        <GraduationCap size={22} />
      </div>
      <h2>
        The best investment?
        <br />
        <span>Your understanding.</span>
      </h2>
      <p>
        From your first Bitcoin to the mechanics behind the market. Learn one
        concept at a time.
      </p>
      <div className="lesson-preview">
        <span className="lesson-icon">
          <BookOpen size={19} />
        </span>
        <div>
          <small>START WITH THE FOUNDATIONS</small>
          <strong>What is cryptocurrency?</strong>
          <span>Level 1 · Beginner path · Phase 4</span>
        </div>
      </div>
      <Button asChild>
        <Link href="/academy">
          Explore the learning path
          <ArrowRight size={16} />
        </Link>
      </Button>
      <div className="learning-footer">
        <span>
          <Compass size={14} />5 learning levels planned
        </span>
        <span>
          <Sparkles size={14} />
          Learn at your pace
        </span>
      </div>
    </section>
  );
}

export function FirstStepsCard() {
  return (
    <section className="panel getting-started">
      <div className="panel-heading">
        <h2>Your first steps</h2>
        <span className="badge">1 OF 3</span>
      </div>
      <div className="progress-track">
        <span />
      </div>
      {milestones.map((m, i) => (
        <div key={m.label} className={cn("step", m.done && "done")}>
          <span className="step-number">{m.done ? "✓" : `0${i + 1}`}</span>
          <span>{m.label}</span>
          {m.done ? (
            <span className="step-status">Complete</span>
          ) : (
            <Link
              href={i === 1 ? "/journal" : "/academy"}
              aria-label={`Preview: ${m.label}`}
            >
              <ChevronRight size={16} />
            </Link>
          )}
        </div>
      ))}
      <p className="first-step-note">
        <CircleHelp size={14} />
        Progress here is an onboarding guide.
      </p>
    </section>
  );
}

export function WatchlistPreview() {
  return (
    <section className="panel watchlist-panel">
      <div className="panel-heading">
        <div>
          <h2>Market watchlist</h2>
          <p>Your research, all in one place.</p>
        </div>
        <span className="badge">PHASE 3</span>
      </div>
      <div className="watchlist-assets">
        {[
          { symbol: "BTC", name: "Bitcoin" },
          { symbol: "ETH", name: "Ethereum" },
          { symbol: "SOL", name: "Solana" },
        ].map((c) => (
          <div key={c.symbol}>
            <span className={cn("coin-mark", c.symbol.toLowerCase())}>
              {c.symbol[0]}
            </span>
            <span>
              <strong>{c.name}</strong>
              <small>{c.symbol} · Asset preview</small>
            </span>
            <span className="no-price">No live data</span>
          </div>
        ))}
      </div>
      <p className="chart-footnote">
        Reference assets only. No saved watchlist or market feed is connected
        yet.
      </p>
      <Link className="text-link" href="/markets">
        Preview market intelligence
        <ArrowRight size={14} />
      </Link>
    </section>
  );
}

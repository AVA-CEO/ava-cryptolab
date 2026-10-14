import { notFound } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Check, LockKeyhole } from "lucide-react";
import { navigation } from "@/lib/navigation";
import { Button } from "@/components/ui/button";

const capabilities: Record<string, string[]> = {
  journal: [
    "Trade records, executions and partial exits",
    "Planned risk, realized R and performance analytics",
    "CSV import and export",
  ],
  markets: [
    "CoinGecko observations with source timestamps",
    "Screening, sorting and personal watchlists",
    "Historical prices and asset detail pages",
  ],
  lab: [
    "Interactive order books, liquidity and slippage",
    "Hypothetical leverage and position sizing",
    "Knowledge checks for each market mechanic",
  ],
  academy: [
    "Five progressive learning levels",
    "Curated lessons with analogies and examples",
    "Saved learning progress",
  ],
  trivia: [
    "Server-validated answers and explanations",
    "XP, achievements and learning streaks",
    "Risk Master and Order Book Challenge",
  ],
};
export default async function ModulePage({
  params,
}: {
  params: Promise<{ module: string }>;
}) {
  const { module } = await params;
  const item = navigation.find((n) => n.href === `/${module}`);
  if (!item) notFound();
  return (
    <div className="page-content">
      <p className="eyebrow">THE WORKSPACE IS TAKING SHAPE</p>
      <h1>{item.label}</h1>
      <p className="page-subtitle">{item.description}</p>
      <section className="panel module-preview">
        <span className="module-symbol">
          <item.icon size={36} />
        </span>
        <span className="badge">
          <LockKeyhole size={12} /> Planned for Phase {item.phase}
        </span>
        <h2>A stronger foundation comes first.</h2>
        <p>
          This module is a roadmap preview. Its features will be implemented in
          the dedicated milestone.
        </p>
        <ul>
          {capabilities[module].map((c) => (
            <li key={c}>
              <Check size={16} />
              {c}
            </li>
          ))}
        </ul>
        <Button asChild>
          <Link href="/">
            <ArrowLeft size={16} />
            Back to Command Center
          </Link>
        </Button>
      </section>
    </div>
  );
}

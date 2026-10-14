"use client";
import { Button } from "@/components/ui/button";
export const defaultFilters = {
  search: "",
  strategy: "",
  exchange: "",
  status: "all",
  outcome: "all",
  start: "",
  end: "",
  sort: "entry_desc",
};
export function JournalFilters({
  filters,
  change,
  period,
  onReset,
}: {
  filters: typeof defaultFilters;
  change: (key: keyof typeof defaultFilters, value: string) => void;
  period: (days: number) => void;
  onReset: () => void;
}) {
  return (
    <section className="panel journal-filters" aria-label="Journal filters">
      <label>
        Search
        <input
          aria-label="Search journal"
          placeholder="Coin, setup, notes…"
          value={filters.search}
          onChange={(e) => change("search", e.target.value)}
        />
      </label>
      <label>
        Setup
        <input
          aria-label="Filter setup"
          placeholder="Exact setup tag"
          value={filters.strategy}
          onChange={(e) => change("strategy", e.target.value)}
        />
      </label>
      <label>
        Exchange
        <input
          aria-label="Filter exchange"
          placeholder="Exact exchange"
          value={filters.exchange}
          onChange={(e) => change("exchange", e.target.value)}
        />
      </label>
      <label>
        Status
        <select
          aria-label="Filter status"
          value={filters.status}
          onChange={(e) => change("status", e.target.value)}
        >
          <option value="all">All statuses</option>
          <option value="open">Open</option>
          <option value="partial">Partial</option>
          <option value="closed">Closed</option>
        </select>
      </label>
      <label>
        Outcome
        <select
          aria-label="Filter outcome"
          value={filters.outcome}
          onChange={(e) => change("outcome", e.target.value)}
        >
          <option value="all">All outcomes</option>
          <option value="win">Win</option>
          <option value="loss">Loss</option>
          <option value="breakeven">Breakeven</option>
        </select>
      </label>
      <label>
        Entry from (UTC)
        <input
          aria-label="Entry from"
          type="date"
          value={filters.start}
          onChange={(e) => change("start", e.target.value)}
        />
      </label>
      <label>
        Entry through (UTC)
        <input
          aria-label="Entry through"
          type="date"
          value={filters.end}
          onChange={(e) => change("end", e.target.value)}
        />
      </label>
      <label>
        Sort
        <select
          aria-label="Sort trades"
          value={filters.sort}
          onChange={(e) => change("sort", e.target.value)}
        >
          <option value="entry_desc">Newest entry</option>
          <option value="entry_asc">Oldest entry</option>
          <option value="pnl_desc">Highest PnL</option>
          <option value="pnl_asc">Lowest PnL</option>
          <option value="pair">Pair A–Z</option>
        </select>
      </label>
      <div className="filter-footer">
        <span>
          Entry dates select a trade cohort; charts follow that same selection.
        </span>
        <div>
          {[7, 30, 90].map((d) => (
            <Button key={d} variant="ghost" size="sm" onClick={() => period(d)}>
              {d} days
            </Button>
          ))}
          <Button variant="ghost" size="sm" onClick={onReset}>
            Reset
          </Button>
        </div>
      </div>
    </section>
  );
}

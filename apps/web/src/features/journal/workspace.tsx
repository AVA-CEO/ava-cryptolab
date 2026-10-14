"use client";
import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  ArrowRight,
  Download,
  Plus,
  RefreshCw,
  Settings2,
  Upload,
  Wallet,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { BalanceDialog } from "./balance-dialog";
import { JournalFilters, defaultFilters } from "./filters";
import { JournalStats, TradingIQPanel } from "./performance-panels";
import { cn } from "@/lib/utils";
import {
  amount,
  requestJSON,
  type Analytics,
  type Currency,
  type Trade,
} from "./contracts";
import { TradeForm } from "./trade-form";
import { TradeDetail } from "./trade-detail";

const AnalyticsCharts = dynamic(() => import("./analytics-charts"), {
  ssr: false,
  loading: () => (
    <div className="skeleton h-80" aria-label="Loading journal charts" />
  ),
});

export function JournalWorkspace({
  overview = false,
  onSample,
}: {
  overview?: boolean;
  onSample?: () => void;
}) {
  const [currency, setCurrency] = useState<Currency>("USD");
  const [filters, setFilters] = useState(defaultFilters);
  const [records, setRecords] = useState<Trade[]>([]);
  const [total, setTotal] = useState(0);
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [page, setPage] = useState(0);
  const [editing, setEditing] = useState<Trade | "new" | null>(null);
  const [detail, setDetail] = useState<Trade | null>(null);
  const [balance, setBalance] = useState(false);
  const [importing, setImporting] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const params = new URLSearchParams({
    currency,
    ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
  }).toString();
  const reload = () => {
    setLoading(true);
    setRefresh((n) => n + 1);
  };
  useEffect(() => {
    const abort = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      setError("");
      Promise.all([
        requestJSON<{ items: Trade[]; total: number }>(
          `/api/journal?${params}&limit=25&offset=${page * 25}`,
          { signal: abort.signal },
        ),
        requestJSON<Analytics>(`/api/journal/analytics?${params}`, {
          signal: abort.signal,
        }),
      ])
        .then(([list, analytics]) => {
          setRecords(list.items);
          setTotal(list.total);
          setData(analytics);
        })
        .catch((e) => {
          if (!abort.signal.aborted) {
            setError(e.message);
            setData(null);
            setRecords([]);
          }
        })
        .finally(() => {
          if (!abort.signal.aborted) setLoading(false);
        });
    }, 200);
    return () => {
      clearTimeout(timer);
      abort.abort();
    };
  }, [params, page, refresh]);
  const change = (key: keyof typeof filters, value: string) => {
    setLoading(true);
    setPage(0);
    setFilters((f) => ({ ...f, [key]: value }));
  };
  async function importFile(file: File) {
    if (file.size > 2_000_000) {
      toast.error("CSV must be smaller than 2 MB.");
      return;
    }
    setImporting(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await requestJSON<{ inserted: number; skipped: number }>(
        "/api/journal/import",
        { method: "POST", body: form },
      );
      toast.success(
        `Imported ${result.inserted} trades; skipped ${result.skipped} duplicates.`,
      );
      setPage(0);
      reload();
    } catch (e) {
      toast.error((e as Error).message, { duration: 8000 });
    } finally {
      setImporting(false);
    }
  }
  function period(days: number) {
    const now = new Date();
    const start = new Date(now.getTime() - (days - 1) * 86400000)
      .toISOString()
      .slice(0, 10);
    setPage(0);
    setFilters((f) => ({ ...f, start, end: now.toISOString().slice(0, 10) }));
  }
  return (
    <div className="page-content journal-workspace">
      <div className="page-heading">
        <div>
          <p className="eyebrow">
            <span className="tiny-line" />
            {overview ? "YOUR TRADING WORKSPACE" : "YOUR DECISIONS. YOUR DATA."}
          </p>
          <h1>
            {overview ? "Command Center" : "Trading Journal"}
            <span className="heading-dot">.</span>
          </h1>
          <p className="page-subtitle">
            {overview
              ? "Real records. Clearer patterns. A smarter path forward."
              : "Record the trade. Understand the decision. Improve the process."}
          </p>
        </div>
        <div className="journal-actions">
          {overview ? (
            <>
              <Button variant="outline" onClick={onSample}>
                Explore sample data
              </Button>
              <Button asChild>
                <Link href="/journal">
                  Open journal
                  <ArrowRight size={15} />
                </Link>
              </Button>
            </>
          ) : (
            <>
              <input
                ref={fileInput}
                type="file"
                accept=".csv,text/csv"
                className="sr-only"
                aria-label="Import journal CSV"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) void importFile(file);
                  e.target.value = "";
                }}
              />
              <Button
                variant="outline"
                onClick={() => fileInput.current?.click()}
                disabled={importing}
              >
                <Upload size={15} />
                {importing ? "Importing…" : "Import CSV"}
              </Button>
              <Button variant="outline" asChild>
                <a href={`/api/journal/export?${params}`}>
                  <Download size={15} />
                  Export CSV
                </a>
              </Button>
              <Button onClick={() => setEditing("new")}>
                <Plus size={16} />
                Record trade
              </Button>
            </>
          )}
        </div>
      </div>
      <div className="journal-context">
        <span className="badge">LOCAL PRIVATE JOURNAL</span>
        <p>
          No live orders. No invented prices. Records stay in your local
          database.
        </p>
        <label>
          View currency
          <select
            aria-label="View currency"
            value={currency}
            onChange={(e) => {
              setCurrency(e.target.value as Currency);
              setLoading(true);
              setPage(0);
            }}
          >
            <option>USD</option>
            <option>USDT</option>
            <option>USDC</option>
          </select>
        </label>
        <Button variant="ghost" size="sm" onClick={() => setBalance(true)}>
          <Settings2 size={15} />
          Opening balance
        </Button>
      </div>
      <JournalFilters
        filters={filters}
        change={change}
        period={period}
        onReset={() => {
          setLoading(true);
          setFilters(defaultFilters);
          setPage(0);
        }}
      />
      {loading && (
        <div className="skeleton h-32 mb-6" aria-label="Loading journal" />
      )}
      {error && (
        <section className="panel journal-error" role="alert">
          <h2>Your journal could not be loaded.</h2>
          <p>{error}</p>
          <Button variant="outline" onClick={reload}>
            <RefreshCw size={15} />
            Try again
          </Button>
        </section>
      )}
      {!loading && data && (
        <>
          <JournalStats data={data} currency={currency} />
          <div className="journal-summary-line">
            <span>
              <Wallet size={15} />
              Recorded balance:{" "}
              <strong>{amount(data.recorded_balance, currency)}</strong>
            </span>
            <span>
              {data.total_trades} trades · {data.closed_trades} closed ·{" "}
              {data.open_trades} open / partial
            </span>
            <span>
              Average win {amount(data.average_win, currency)} · Average loss{" "}
              {amount(data.average_loss, currency)}
            </span>
          </div>
          <AnalyticsCharts data={data} />
          <TradingIQPanel data={data} />
          <section className="panel journal-ledger">
            <div className="panel-heading">
              <div>
                <h2>{overview ? "Recent records" : "Trade ledger"}</h2>
                <p>
                  {total} matching records · Values shown in {currency}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Refresh journal"
                onClick={reload}
              >
                <RefreshCw size={16} />
              </Button>
            </div>
            {records.length ? (
              <>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Trade / setup</th>
                        <th>Entry UTC</th>
                        <th>Status</th>
                        <th>Net PnL</th>
                        <th>Realized R</th>
                        <th>Planned risk</th>
                        <th>Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.map((trade) => (
                        <tr key={trade.id}>
                          <td>
                            <div className="ledger-pair">
                              <strong>{trade.pair}</strong>
                              <span>
                                {trade.strategy} · {trade.market} ·{" "}
                                {trade.direction}
                              </span>
                            </div>
                          </td>
                          <td>
                            {trade.entry_at.slice(0, 16).replace("T", " ")}
                          </td>
                          <td>
                            <span
                              className={cn(
                                "trade-status",
                                trade.metrics.status,
                              )}
                            >
                              {trade.metrics.status}
                            </span>
                          </td>
                          <td
                            className={
                              Number(trade.metrics.net_pnl) >= 0
                                ? "positive"
                                : "negative"
                            }
                          >
                            {amount(trade.metrics.net_pnl, currency)}
                          </td>
                          <td>
                            {trade.metrics.realized_r === null
                              ? "—"
                              : `${Number(trade.metrics.realized_r).toFixed(2)}R`}
                          </td>
                          <td>
                            {amount(trade.metrics.planned_risk, currency)}
                          </td>
                          <td>
                            <Button
                              variant="outline"
                              size="sm"
                              aria-label={`View ${trade.pair} trade`}
                              onClick={() => setDetail(trade)}
                            >
                              View
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="pagination">
                  <span>
                    {page * 25 + 1}–{Math.min((page + 1) * 25, total)} of{" "}
                    {total}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 0}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={(page + 1) * 25 >= total}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </>
            ) : (
              <div className="journal-empty">
                <span className="soft-icon">
                  <Plus size={24} />
                </span>
                <div>
                  <h3>No records match this view.</h3>
                  <p>
                    Record a trade or adjust your filters. We won’t fill this
                    space with pretend profits.
                  </p>
                  <Button size="sm" onClick={() => setEditing("new")}>
                    Record your first trade
                  </Button>
                </div>
              </div>
            )}
          </section>
        </>
      )}
      {!overview && (
        <p className="journal-help">
          CSV uses one row per trade and a JSON <code>exits</code> column for
          partial exits. Imports are validated as a complete batch, and exact
          duplicates are skipped.{" "}
          <a
            href="/api/journal/export?template=true"
            download="ava-journal-template.csv"
          >
            Download an empty template →
          </a>
        </p>
      )}
      {editing && (
        <TradeForm
          trade={editing === "new" ? undefined : editing}
          currency={currency}
          onClose={() => setEditing(null)}
          onSaved={reload}
        />
      )}
      {detail && (
        <TradeDetail
          trade={detail}
          onClose={() => setDetail(null)}
          onEdit={() => {
            setEditing(detail);
            setDetail(null);
          }}
          onDeleted={reload}
          onRefresh={reload}
        />
      )}
      {balance && (
        <BalanceDialog
          currency={currency}
          onClose={() => setBalance(false)}
          onSaved={reload}
        />
      )}
    </div>
  );
}

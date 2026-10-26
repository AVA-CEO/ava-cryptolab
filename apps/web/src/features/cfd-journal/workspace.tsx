"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  CheckCircle2,
  RefreshCw,
  ShieldCheck,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { CfdPreview } from "@/features/cfd-preview/workspace";
import {
  monetary,
  positionPageSchema,
  savedPositionSchema,
  type SavedPosition,
} from "./contracts";
import "./journal.css";

function tone(raw: string | null) {
  if (raw === null || /^-?0(?:\.0+)?(?:e[+-]?\d+)?$/i.test(raw)) return "";
  return raw.startsWith("-") ? "negative" : "positive";
}

async function responseBody(response: Response) {
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      body.error?.message ??
        body.detail ??
        "Saved evidence could not be retrieved.",
    );
  return body;
}

function PositionDetail({
  position,
  onClose,
}: {
  position: SavedPosition;
  onClose: () => void;
}) {
  const trade = position.input.trade;
  return (
    <section
      className="panel product-card cfd-detail"
      aria-label="Saved CFD trade detail"
    >
      <div className="cfd-section-heading">
        <div>
          <span className="badge">SAVED · REVISION {position.revision_no}</span>
          <h2>
            {trade.snapshot.specification.symbol} ·{" "}
            {trade.direction.toUpperCase()}
          </h2>
        </div>
        <button
          className="product-text-button"
          onClick={onClose}
          aria-label="Close trade detail"
        >
          <X size={20} />
        </button>
      </div>
      <div className="product-notice">
        <ShieldCheck size={18} />
        <span>
          Locally accepted calculation · synthetic practice inputs · not
          broker-authenticated · historical replay not run
        </span>
      </div>
      <p>
        These are preserved saved results, returned after verification. Opening
        this screen does not rerun the calculator or replace historical rates.
      </p>
      <div className="cfd-detail-facts">
        <div>
          <small>Entry price</small>
          <strong>{trade.entry.price}</strong>
        </div>
        <div>
          <small>Original lots</small>
          <strong>{position.result.original_lots}</strong>
        </div>
        <div>
          <small>Original stop</small>
          <strong>{trade.original_stop ?? "Not recorded"}</strong>
        </div>
        <div>
          <small>Remaining lots</small>
          <strong>{position.result.remaining_lots}</strong>
        </div>
        <div>
          <small>Position state</small>
          <strong>{position.result.state}</strong>
        </div>
        <div>
          <small>Planned target</small>
          <strong>{trade.planned_take_profit ?? "Not recorded"}</strong>
        </div>
        <div>
          <small>Contract size per lot</small>
          <strong>{trade.snapshot.specification.contract_size}</strong>
        </div>
        <div>
          <small>Native profit currency</small>
          <strong>{trade.snapshot.specification.profit_currency}</strong>
        </div>
        <div>
          <small>Immutable specification</small>
          <strong>{trade.snapshot.snapshot_id}</strong>
        </div>
      </div>
      <div className="product-columns">
        {[position.result.native, position.result.reporting].map(
          (performance, i) => (
            <div className="product-outcome" key={i}>
              <h3>
                {i ? "Reporting" : "Native"} currency · {performance.currency}
              </h3>
              <dl>
                {[
                  ["Gross realized PnL", performance.gross_pnl],
                  ["Net realized PnL", performance.net_pnl],
                  ["Original planned risk", performance.original_planned_risk],
                  ["Realized R", performance.realized_r],
                ].map(([label, value]) => {
                  const item = value as typeof performance.net_pnl;
                  return (
                    <div key={String(label)}>
                      <dt>{String(label)}</dt>
                      <dd
                        className={
                          String(label).includes("PnL") ? tone(item.raw) : ""
                        }
                      >
                        {monetary(item, position.result.rounding_policy)}
                      </dd>
                      {item.unavailable_reason && (
                        <small>{item.unavailable_reason}</small>
                      )}
                    </div>
                  );
                })}
              </dl>
            </div>
          ),
        )}
      </div>
      <div className="cfd-learning-note">
        <h3>Understand the two measuring sticks</h3>
        <p>
          <strong>Realized net PnL</strong> measures closed price outcomes plus
          costs recognized through the chosen cutoff. It excludes unknown
          unrealized price movement. <strong>R</strong> divides that outcome by
          original planned risk. Partial exits do not shrink the original risk
          denominator; missing original risk means R is unavailable.
        </p>
      </div>
      <details>
        <summary>Entry and initial exit history</summary>
        <p>
          Original entry: {trade.entry.lots} lots at {trade.entry.price} ·{" "}
          {trade.entry.executed_at}
        </p>
        {trade.exits.length ? (
          <ul>
            {trade.exits.map((exit) => (
              <li key={exit.execution_id}>
                {exit.lots} lots at {exit.price} · {exit.executed_at}
              </li>
            ))}
          </ul>
        ) : (
          <p>No exit executions were recorded.</p>
        )}
        <p>Financial cutoff: {position.input.as_of}</p>
      </details>
      <details>
        <summary>Commissions, swaps and currency evidence</summary>
        {trade.adjustments.length ? (
          <ul>
            {trade.adjustments.map((cost) => (
              <li key={cost.adjustment_id}>
                {cost.kind}: {cost.amount} {cost.currency} · {cost.occurred_at}{" "}
                · {cost.description}
              </li>
            ))}
          </ul>
        ) : (
          <p>No adjustments were supplied.</p>
        )}
        {trade.conversions.length ? (
          <ul>
            {trade.conversions.map((fx) => (
              <li key={fx.conversion_id}>
                1 {fx.from_currency} = {fx.rate} {fx.to_currency} · observed{" "}
                {fx.observed_at}, applies {fx.applies_at}
              </li>
            ))}
          </ul>
        ) : (
          <p>
            No conversion evidence was supplied. Different currencies are never
            treated as equivalent.
          </p>
        )}
      </details>
      <details>
        <summary>Integrity and release evidence</summary>
        <p>
          Stored-hash and normalized-ledger verification is separate from
          computational replay or broker reconciliation. The local release is
          unsigned. No correction or edit workflow is enabled.
        </p>
        <dl className="cfd-evidence">
          {[
            ["Position", position.position_id],
            ["Account", position.account_id],
            ["Input SHA-256", position.input_sha256],
            ["Result SHA-256", position.result_sha256],
            ["Original risk SHA-256", position.original_risk_sha256],
            ["Evidence manifest SHA-256", position.manifest_sha256],
          ].map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </details>
    </section>
  );
}

export function CfdJournalWorkspace() {
  const [accountId, setAccountId] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [cursor, setCursor] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [items, setItems] = useState<SavedPosition[]>([]);
  const [selected, setSelected] = useState<SavedPosition | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const detailRequest = useRef<AbortController | null>(null);
  const handleAccount = useCallback((id: string) => {
    detailRequest.current?.abort();
    setAccountId(id);
    setItems([]);
    setSelected(null);
    setDetailLoading(false);
    setCursor(null);
    setLoading(true);
    setRefresh((value) => value + 1);
  }, []);
  const handleSaved = useCallback((position: SavedPosition) => {
    detailRequest.current?.abort();
    setDetailLoading(false);
    setSelected(position);
    setCursor(null);
    setLoading(true);
    setRefresh((value) => value + 1);
  }, []);
  useEffect(() => {
    if (!accountId) return;
    const controller = new AbortController();
    const query = new URLSearchParams({
      action: "positions",
      account_id: accountId,
      limit: "20",
    });
    if (cursor) query.set("cursor", cursor);
    fetch(`/api/cfd-journal?${query}`, {
      signal: controller.signal,
      cache: "no-store",
    })
      .then(responseBody)
      .then((raw) => {
        if (controller.signal.aborted) return;
        const page = positionPageSchema.safeParse(raw);
        if (
          !page.success ||
          page.data.account_id !== accountId ||
          page.data.items.some((position) => position.account_id !== accountId)
        )
          throw new Error(
            "Saved page verification failed. Financial values withheld.",
          );
        setItems((previous) =>
          cursor ? [...previous, ...page.data.items] : page.data.items,
        );
        setNextCursor(page.data.next_cursor);
        setError("");
        setLoading(false);
      })
      .catch((error) => {
        if (error.name !== "AbortError") {
          setItems([]);
          setSelected(null);
          setError(error.message);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [accountId, cursor, refresh]);
  useEffect(() => () => detailRequest.current?.abort(), []);
  async function open(positionId: string) {
    detailRequest.current?.abort();
    const controller = new AbortController();
    detailRequest.current = controller;
    setDetailLoading(true);
    setSelected(null);
    setError("");
    const query = new URLSearchParams({
      action: "positions",
      account_id: accountId,
      position_id: positionId,
    });
    try {
      const raw = await responseBody(
        await fetch(`/api/cfd-journal?${query}`, {
          signal: controller.signal,
          cache: "no-store",
        }),
      );
      if (controller.signal.aborted) return;
      const parsed = savedPositionSchema.safeParse(raw);
      if (
        !parsed.success ||
        parsed.data.account_id !== accountId ||
        parsed.data.position_id !== positionId
      )
        throw new Error(
          "Saved trade verification failed. Financial values withheld.",
        );
      setSelected(parsed.data);
    } catch (error) {
      if (!(error instanceof Error && error.name === "AbortError"))
        setError(
          error instanceof Error
            ? error.message
            : "Saved evidence unavailable.",
        );
    } finally {
      if (!controller.signal.aborted) setDetailLoading(false);
    }
  }
  return (
    <>
      <CfdPreview journalMode onAccount={handleAccount} onSaved={handleSaved} />
      <div className="page-content product-page cfd-saved-workspace">
        <section className="panel product-card" aria-label="Saved CFD journal">
          <div className="cfd-section-heading">
            <div>
              <p className="eyebrow">CALCULATED. SAVED. REOPENED.</p>
              <h2>Your CFD practice journal</h2>
              <p>
                Saved positions survive browser refresh within this running
                disposable session. Stopping the session removes its temporary
                dataset.
              </p>
            </div>
            <Button
              variant="outline"
              disabled={!accountId || loading}
              onClick={() => {
                setCursor(null);
                setLoading(true);
                setRefresh((value) => value + 1);
              }}
            >
              <RefreshCw size={16} /> Refresh saved trades
            </Button>
          </div>
          {accountId && (
            <span className="badge">
              Account scope: {accountId.slice(0, 8)} · local synthetic practice
            </span>
          )}
          {error && (
            <div className="product-error" role="alert">
              {error}
            </div>
          )}
          {loading && (
            <p role="status">
              Loading this account&apos;s verified saved positions…
            </p>
          )}
          {!accountId && (
            <p>
              Connect the new isolated session above to view its saved practice
              positions.
            </p>
          )}
          {!!accountId && !loading && !items.length && !error && (
            <div className="cfd-empty">
              <ArrowDownToLine size={30} />
              <h3>Your first preserved calculation starts here</h3>
              <p>
                Calculate a supported trade above, review its original risk and
                costs, then save. This journal does not import or reassign
                existing crypto trades.
              </p>
            </div>
          )}
          {!!items.length && (
            <div className="cfd-table-scroll">
              <table className="product-table">
                <caption>
                  Locally accepted calculations using synthetic practice inputs
                  — not broker statements
                </caption>
                <thead>
                  <tr>
                    <th>Instrument</th>
                    <th>Direction</th>
                    <th>State</th>
                    <th>Original lots</th>
                    <th>Remaining</th>
                    <th>Native net PnL</th>
                    <th>Realized R</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((position) => (
                    <tr key={position.position_id}>
                      <td>
                        <strong>
                          {position.input.trade.snapshot.specification.symbol}
                        </strong>
                        <br />
                        <small>{position.input.trade.entry.executed_at}</small>
                      </td>
                      <td>{position.input.trade.direction.toUpperCase()}</td>
                      <td>
                        <span className="badge">{position.result.state}</span>
                      </td>
                      <td>{position.result.original_lots}</td>
                      <td>{position.result.remaining_lots}</td>
                      <td className={tone(position.result.native.net_pnl.raw)}>
                        {monetary(
                          position.result.native.net_pnl,
                          position.result.rounding_policy,
                        )}
                      </td>
                      <td>
                        {monetary(
                          position.result.native.realized_r,
                          position.result.rounding_policy,
                        )}
                      </td>
                      <td>
                        <button
                          className="product-text-button"
                          onClick={() => open(position.position_id)}
                          aria-label={`Open ${position.input.trade.snapshot.specification.symbol} position ${position.position_id.slice(0, 8)}`}
                        >
                          <CheckCircle2 size={16} /> Open trade
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {nextCursor && (
            <Button
              variant="outline"
              disabled={loading}
              onClick={() => {
                setCursor(nextCursor);
                setLoading(true);
              }}
            >
              Load more saved positions
            </Button>
          )}
        </section>
        {detailLoading && (
          <section className="panel product-card" role="status">
            Verifying preserved trade evidence…
          </section>
        )}
        {selected && (
          <PositionDetail
            position={selected}
            onClose={() => setSelected(null)}
          />
        )}
      </div>
    </>
  );
}

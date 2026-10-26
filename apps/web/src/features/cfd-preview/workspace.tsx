"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Calculator, Plus, Trash2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  savedPositionSchema,
  type SavedPosition,
} from "@/features/cfd-journal/contracts";
import "@/features/product.css";

type Execution = {
  execution_id: string;
  executed_at: string;
  price: string;
  lots: string;
  profit_conversion_id?: string;
};
type Command = {
  schema_version: string;
  account_id: string;
  snapshot_id: string;
  position_reference: string;
  trade: {
    direction: string;
    entry: Execution;
    exits: Execution[];
    original_stop: string | null;
    planned_take_profit?: string | null;
    reporting_policy: string;
    adjustments?: object[];
    conversions?: object[];
    risk_conversion_id?: string;
  };
  rounding: object;
  as_of: string;
  recognition_policy: string;
  release_digest?: string;
  broker_evidence?: { evidence_id: string; [key: string]: unknown }[];
};
type Measurement = {
  raw: string | null;
  rounded: string | null;
  unavailable_reason?: string | null;
  currency?: string;
};
type Performance = {
  currency: string;
  gross_pnl: Measurement;
  net_pnl: Measurement;
  original_planned_risk: Measurement;
  realized_r: Measurement;
};
type Result = {
  status: string;
  message?: string;
  state?: string;
  original_lots?: string;
  remaining_lots?: string;
  native?: Performance;
  reporting?: Performance;
};
function show(value: Measurement | undefined, unit = "") {
  return value?.rounded === null || !value
    ? "Unavailable"
    : `${value.rounded} ${value.currency ?? unit}`;
}

function freshDraft(
  command: Command,
  reference = crypto.randomUUID(),
): Command {
  const value = structuredClone(command);
  value.position_reference = reference;
  value.trade.entry.execution_id = `${reference}:entry`;
  value.trade.exits.forEach((exit, i) => {
    exit.execution_id = `${reference}:exit:${i}`;
  });
  value.broker_evidence?.forEach((evidence, i) => {
    evidence.evidence_id = `${reference}:evidence:${i}`;
  });
  return value;
}

export function CfdPreview({
  journalMode = false,
  onSaved,
  onAccount,
}: {
  journalMode?: boolean;
  onSaved?: (position: SavedPosition) => void;
  onAccount?: (accountId: string) => void;
}) {
  const endpoint = journalMode
    ? "/api/cfd-journal?action=preview"
    : "/api/cfd-preview";
  const examplesEndpoint = journalMode
    ? "/api/cfd-journal?action=examples"
    : "/api/cfd-preview?view=examples";
  const [examples, setExamples] = useState<Record<string, Command>>({});
  const [symbol, setSymbol] = useState("EURUSD");
  const [draft, setDraft] = useState<Command | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(false);
  const [cost, setCost] = useState("0");
  const [swap, setSwap] = useState("0");
  const [fee, setFee] = useState("0");
  const [rate, setRate] = useState("");
  const [canCreate, setCanCreate] = useState(false);
  const [releaseDigest, setReleaseDigest] = useState("");
  const [ticket, setTicket] = useState<{
    command: Command;
    key: string;
  } | null>(null);
  const [savedId, setSavedId] = useState("");
  const saving = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    const load = async (url: string) => {
      const response = await fetch(url, {
        signal: controller.signal,
        cache: "no-store",
      });
      const body = await response.json();
      if (!response.ok)
        throw new Error(
          body.detail ?? body.error?.message ?? "Preview unavailable.",
        );
      return body;
    };
    Promise.all([
      load(examplesEndpoint),
      load(journalMode ? "/api/cfd-journal?action=status" : "/api/cfd-preview"),
    ])
      .then(([body, status]) => {
        setExamples(body);
        const initial = {
          ...body.EURUSD,
          release_digest: status?.release_digest,
        };
        setDraft(journalMode ? freshDraft(initial) : structuredClone(initial));
        setCanCreate(journalMode && status?.can_create === true);
        setReleaseDigest(status?.release_digest ?? "");
        onAccount?.(body.EURUSD.account_id);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [examplesEndpoint, journalMode, onAccount]);
  function changed() {
    if (journalMode) {
      const reference = crypto.randomUUID();
      setDraft((previous) =>
        previous ? freshDraft(previous, reference) : previous,
      );
      setTicket(null);
      setSavedId("");
    }
    setStale(true);
  }
  function edit(change: (value: Command) => void) {
    const reference = journalMode ? crypto.randomUUID() : undefined;
    setDraft((previous) => {
      if (!previous) return previous;
      const next = structuredClone(previous);
      change(next);
      return journalMode ? freshDraft(next, reference) : next;
    });
    setTicket(null);
    setSavedId("");
    setStale(true);
  }
  async function calculate() {
    if (!draft) return;
    setBusy(true);
    setError("");
    const request = structuredClone(draft);
    const adjustments = (
      [
        ["commission", cost],
        ["swap", swap],
        ["fee", fee],
      ] as const
    )
      .filter(([, amount]) => amount && amount !== "0")
      .map(([kind, amount]) => ({
        adjustment_id: journalMode
          ? `${request.position_reference}:cost:${kind}`
          : `preview-${kind}`,
        kind,
        amount,
        currency: symbol === "USDJPY" ? "JPY" : "USD",
        occurred_at:
          kind === "commission"
            ? request.trade.entry.executed_at
            : request.as_of,
        description: `Hypothetical ${kind}`,
        source: { kind: "manual", reference: "Unverified preview cost" },
        conversion_id: undefined as string | undefined,
      }));
    request.trade.adjustments = adjustments;
    if (symbol === "USDJPY" && rate) {
      request.trade.reporting_policy = "explicit_rates";
      const observations: object[] = [];
      const conversion = (id: string, at: string) => {
        const reference = journalMode
          ? `${request.position_reference}:${id}`
          : id;
        observations.push({
          conversion_id: reference,
          from_currency: "JPY",
          to_currency: "USD",
          rate,
          observed_at: at,
          applies_at: at,
          max_age_seconds: 0,
          source: {
            kind: "manual",
            reference: "Hypothetical same-time FX observation, not live data",
          },
        });
        return reference;
      };
      if (request.trade.original_stop)
        request.trade.risk_conversion_id = conversion(
          "fx-risk",
          request.trade.entry.executed_at,
        );
      request.trade.exits.forEach((exit, i) => {
        exit.profit_conversion_id = conversion(
          `fx-exit-${i}`,
          exit.executed_at,
        );
      });
      adjustments.forEach((item) => {
        item.conversion_id = conversion(
          `fx-${item.adjustment_id}`,
          item.occurred_at,
        );
      });
      request.trade.conversions = observations;
    }
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });
      const body = await response.json();
      if (!response.ok)
        throw new Error(
          [
            body.error?.message ?? body.detail ?? "Calculation unavailable",
            ...(body.error?.issues ?? []).map(
              (x: { message: string }) => x.message,
            ),
          ].join(" · "),
        );
      setResult(body.result);
      setStale(false);
      if (journalMode) {
        const eligible =
          canCreate &&
          body.can_create === true &&
          body.result?.status === "calculated";
        const command = {
          ...structuredClone(request),
          release_digest: body.release_digest,
        };
        const key = crypto.randomUUID();
        setTicket((previous) =>
          eligible && /^sha256:[0-9a-f]{64}$/.test(body.release_digest)
            ? previous &&
              JSON.stringify(previous.command) === JSON.stringify(command)
              ? previous
              : { command, key }
            : null,
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Calculation unavailable");
      setStale(true);
    } finally {
      setBusy(false);
    }
  }
  async function save() {
    if (!ticket || stale || !canCreate || savedId || saving.current) return;
    saving.current = true;
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/cfd-journal?action=positions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": ticket.key,
        },
        body: JSON.stringify(ticket.command),
      });
      const raw = await response.json();
      if (!response.ok)
        throw new Error(
          raw.error?.message ??
            raw.detail ??
            "Save unavailable. Retry this unchanged draft with its existing receipt key.",
        );
      const parsed = savedPositionSchema.safeParse(raw);
      if (
        !parsed.success ||
        parsed.data.account_id !== ticket.command.account_id ||
        parsed.data.position_id !== ticket.command.position_reference ||
        parsed.data.input.trade.snapshot.snapshot_id !==
          ticket.command.snapshot_id
      )
        throw new Error(
          "Saved response could not be verified; financial values withheld. Reload the journal or retry this unchanged draft.",
        );
      const position = parsed.data;
      setSavedId(position.position_id);
      onSaved?.(position);
    } catch (error) {
      setError(
        error instanceof Error
          ? `${error.message} The receipt key is retained for an unchanged retry.`
          : "Save response unavailable. Retry without changing this draft.",
      );
    } finally {
      saving.current = false;
      setBusy(false);
    }
  }
  return (
    <div className="page-content product-page">
      <p className="eyebrow">AVA TRADING LAB</p>
      <h1>
        {journalMode ? "Record a CFD position" : "Forex & metals preview"}
      </h1>
      <p className="page-subtitle">
        Understand the trade before you record it. Exact Python calculations,
        transparent currencies.
      </p>
      <div className="product-notice">
        <ShieldCheck size={18} />
        <span>
          Local practice · synthetic contract specifications, not Bybit rules ·
          unsigned pinned release ·{" "}
          {journalMode ? "new disposable journal session" : "no saving"}
        </span>
      </div>
      {error && (
        <div className="product-error" role="alert">
          {error}
        </div>
      )}
      {!draft && (
        <section className="panel product-card">
          <h2>Connect your verified local calculator</h2>
          <p>
            Prepare and review the preview release, then explicitly approve its
            exact digest using the practice runner. The existing crypto journal
            stays independent.
          </p>
          <Link className="product-link" href="/journal">
            Open crypto journal →
          </Link>
        </section>
      )}
      {draft && (
        <div className="product-columns">
          <section className="panel product-card">
            <fieldset className="product-form" disabled={busy}>
              <legend className="sr-only">Trade inputs</legend>
              <h2>
                <Calculator size={20} /> Trade inputs
              </h2>
              <div className="product-fields">
                <label>
                  Teaching instrument
                  <select
                    value={symbol}
                    onChange={(e) => {
                      setSymbol(e.target.value);
                      const next = {
                        ...examples[e.target.value],
                        release_digest: releaseDigest || undefined,
                      };
                      setDraft(
                        journalMode ? freshDraft(next) : structuredClone(next),
                      );
                      onAccount?.(examples[e.target.value].account_id);
                      setTicket(null);
                      setSavedId("");
                      setResult(null);
                      setCost("0");
                      setSwap("0");
                      setFee("0");
                      setRate("");
                      setStale(false);
                    }}
                  >
                    {Object.keys(examples).map((x) => (
                      <option key={x}>{x}</option>
                    ))}
                  </select>
                </label>
                <label>
                  Direction
                  <select
                    value={draft.trade.direction}
                    onChange={(e) =>
                      edit((d) => {
                        d.trade.direction = e.target.value;
                      })
                    }
                  >
                    <option value="buy">BUY / Long</option>
                    <option value="sell">SELL / Short</option>
                  </select>
                </label>
                <label>
                  Original lots
                  <input
                    inputMode="decimal"
                    value={draft.trade.entry.lots}
                    onChange={(e) =>
                      edit((d) => {
                        d.trade.entry.lots = e.target.value;
                      })
                    }
                  />
                </label>
                <label>
                  Entry price
                  <input
                    inputMode="decimal"
                    value={draft.trade.entry.price}
                    onChange={(e) =>
                      edit((d) => {
                        d.trade.entry.price = e.target.value;
                      })
                    }
                  />
                </label>
                <label>
                  Original stop
                  <input
                    inputMode="decimal"
                    value={draft.trade.original_stop ?? ""}
                    onChange={(e) =>
                      edit((d) => {
                        d.trade.original_stop = e.target.value || null;
                      })
                    }
                  />
                </label>
                <label>
                  Planned target
                  <input
                    inputMode="decimal"
                    value={draft.trade.planned_take_profit ?? ""}
                    onChange={(e) =>
                      edit((d) => {
                        d.trade.planned_take_profit = e.target.value || null;
                      })
                    }
                  />
                </label>
                <label>
                  Entry time (ISO with timezone)
                  <input
                    value={draft.trade.entry.executed_at}
                    onChange={(e) =>
                      edit((d) => {
                        d.trade.entry.executed_at = e.target.value;
                      })
                    }
                  />
                </label>
                <label>
                  Calculation cutoff (ISO)
                  <input
                    value={draft.as_of}
                    onChange={(e) =>
                      edit((d) => {
                        d.as_of = e.target.value;
                      })
                    }
                  />
                </label>
              </div>
              <h3>Exit executions</h3>
              <p className="product-muted">
                Exit lots can be less than original lots. Remove all exits to
                preview an open position.
              </p>
              {draft.trade.exits.map((exit, i) => (
                <fieldset key={i} className="product-exit">
                  <legend>Exit {i + 1}</legend>
                  <div className="product-fields">
                    <label>
                      Exit lots
                      <input
                        inputMode="decimal"
                        value={exit.lots}
                        onChange={(e) =>
                          edit((d) => {
                            d.trade.exits[i].lots = e.target.value;
                          })
                        }
                      />
                    </label>
                    <label>
                      Exit price
                      <input
                        inputMode="decimal"
                        value={exit.price}
                        onChange={(e) =>
                          edit((d) => {
                            d.trade.exits[i].price = e.target.value;
                          })
                        }
                      />
                    </label>
                    <label>
                      Exit time (ISO)
                      <input
                        value={exit.executed_at}
                        onChange={(e) =>
                          edit((d) => {
                            d.trade.exits[i].executed_at = e.target.value;
                          })
                        }
                      />
                    </label>
                    <button
                      className="product-text-button"
                      aria-label={`Remove exit ${i + 1}`}
                      onClick={() =>
                        edit((d) => {
                          d.trade.exits.splice(i, 1);
                        })
                      }
                    >
                      <Trash2 size={16} /> Remove
                    </button>
                  </div>
                </fieldset>
              ))}
              <Button
                variant="outline"
                onClick={() =>
                  edit((d) => {
                    d.trade.exits.push({
                      execution_id: crypto.randomUUID(),
                      executed_at: d.as_of,
                      lots: "0.01",
                      price: d.trade.entry.price,
                    });
                  })
                }
              >
                <Plus size={16} /> Add exit
              </Button>
              <div className="product-fields">
                <label>
                  Signed commission ({symbol === "USDJPY" ? "JPY" : "USD"})
                  <input
                    inputMode="decimal"
                    value={cost}
                    onChange={(e) => {
                      setCost(e.target.value);
                      changed();
                    }}
                  />
                  <small>
                    Negative = charge; positive = credit. Recognized once at
                    entry.
                  </small>
                </label>
                <label>
                  Signed swap ({symbol === "USDJPY" ? "JPY" : "USD"})
                  <input
                    inputMode="decimal"
                    value={swap}
                    onChange={(e) => {
                      setSwap(e.target.value);
                      changed();
                    }}
                  />
                  <small>Recognized once at the calculation cutoff.</small>
                </label>
                <label>
                  Other signed fee ({symbol === "USDJPY" ? "JPY" : "USD"})
                  <input
                    inputMode="decimal"
                    value={fee}
                    onChange={(e) => {
                      setFee(e.target.value);
                      changed();
                    }}
                  />
                </label>
                {symbol === "USDJPY" && (
                  <label>
                    Hypothetical USD per 1 JPY (optional)
                    <input
                      inputMode="decimal"
                      placeholder="No rate is assumed"
                      value={rate}
                      onChange={(e) => {
                        setRate(e.target.value);
                        changed();
                      }}
                    />
                    <small>
                      Blank retains native JPY results with USD unavailable.
                      Supplied rate is explicitly hypothetical at each event
                      time.
                    </small>
                  </label>
                )}
              </div>
              <details>
                <summary>Specification and accounting policy</summary>
                <p>
                  Contract size:{" "}
                  {symbol === "XAUUSD"
                    ? "100 ounces"
                    : symbol === "XAGUSD"
                      ? "5,000 ounces"
                      : "100,000 underlying units"}{" "}
                  per lot. Synthetic only. Tick:{" "}
                  {symbol === "EURUSD"
                    ? "0.00001"
                    : symbol === "XAUUSD"
                      ? "0.01"
                      : "0.001"}
                  . Lots step 0.01. Original risk excludes future costs.
                  Arithmetic: 160-digit Decimal; explicit HALF_EVEN
                  presentation. No live FX or unrealized valuation.
                </p>
              </details>
              <Button disabled={busy} onClick={calculate}>
                {busy
                  ? "Verifying & calculating…"
                  : "Calculate unsaved preview"}
              </Button>
            </fieldset>
          </section>
          <section
            className="panel product-card product-result"
            aria-live="polite"
          >
            <span className="badge">
              {savedId ? "SAVED · LOCAL PRACTICE" : "UNSAVED PREVIEW"}
            </span>
            <h2>Your hypothetical outcome</h2>
            {stale && result && (
              <p className="product-notice">
                Inputs changed. Recalculate before using these results.
              </p>
            )}
            {!result && (
              <p>
                Enter your trade and calculate. No financial values are invented
                while the calculator is unavailable.
              </p>
            )}
            {result?.status === "unavailable" && (
              <p role="alert">{result.message}</p>
            )}
            {result?.native && (
              <>
                <p className="badge">
                  {result.state} · {result.remaining_lots} lots remaining
                </p>
                {[result.native, result.reporting]
                  .filter((v): v is Performance => !!v)
                  .map((p, i) => (
                    <div key={i} className="product-outcome">
                      <h3>
                        {i ? "Account reporting" : "Native profit currency"} ·{" "}
                        {p.currency}
                      </h3>
                      <dl>
                        {[
                          ["Gross PnL", p.gross_pnl],
                          ["Net PnL", p.net_pnl],
                          ["Original planned risk", p.original_planned_risk],
                          ["Realized R", p.realized_r],
                        ].map(([label, value]) => (
                          <div key={String(label)}>
                            <dt>{String(label)}</dt>
                            <dd
                              className={
                                String(label).includes("PnL") &&
                                (value as Measurement).raw
                                  ? (value as Measurement).raw?.startsWith("-")
                                    ? "negative"
                                    : "positive"
                                  : ""
                              }
                            >
                              {show(value as Measurement, "R")}
                            </dd>
                            {(value as Measurement).unavailable_reason && (
                              <small>
                                {(value as Measurement).unavailable_reason}
                              </small>
                            )}
                          </div>
                        ))}
                      </dl>
                    </div>
                  ))}
              </>
            )}
            <p className="product-muted">
              Original quantity and original stop remain the risk basis after a
              partial exit. Leverage does not multiply profit again. This is not
              a broker statement, margin calculation or liquidation estimate.
            </p>
            {journalMode && (
              <div className="product-outcome">
                <h3>
                  {savedId ? "Position saved" : "Calculate, review, then save"}
                </h3>
                <p>
                  {savedId
                    ? "This locally accepted calculation is saved in this disposable session. Refresh and reopen it in the journal below. It is not broker-authenticated evidence."
                    : "R compares realized net PnL with original planned risk. Your original entry, lots, stop, specification and dated currency evidence will be preserved with the saved calculation."}
                </p>
                {!canCreate && (
                  <p>
                    Saving is locked until the local release and persistence
                    safeguards are qualified.
                  </p>
                )}
                <Button
                  onClick={save}
                  disabled={busy || !ticket || stale || !canCreate || !!savedId}
                >
                  {savedId
                    ? "Saved — reopen below"
                    : busy
                      ? "Working…"
                      : "Save verified position"}
                </Button>
                {savedId && (
                  <Button
                    variant="outline"
                    onClick={() => {
                      const reference = crypto.randomUUID();
                      setDraft((previous) =>
                        previous ? freshDraft(previous, reference) : previous,
                      );
                      setResult(null);
                      setTicket(null);
                      setSavedId("");
                      setStale(false);
                      setError("");
                    }}
                  >
                    Start another practice trade
                  </Button>
                )}
                <small>
                  Retries reuse the same receipt key and exact reviewed inputs.
                  Editing an already saved position is not available.
                </small>
              </div>
            )}
            <Link className="product-link" href="/academy">
              Learn lots, leverage and risk →
            </Link>
          </section>
        </div>
      )}
    </div>
  );
}

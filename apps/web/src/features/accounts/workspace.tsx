"use client";

import { useEffect, useState } from "react";
import { WalletCards, ShieldCheck, FileCheck2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  accountInput,
  specificationInput,
  type Account,
  type Snapshot,
} from "./contracts";
import "./accounts.css";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/management/${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      [
        data.detail,
        ...(data.errors ?? []).map(
          (item: { path: string; message: string }) =>
            `${item.path}: ${item.message}`,
        ),
      ]
        .filter(Boolean)
        .join(" "),
    );
  return data;
}

export function AccountsWorkspace() {
  const [status, setStatus] = useState<
    "loading" | "enabled" | "disabled" | "error"
  >("loading");
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountTotal, setAccountTotal] = useState(0);
  const [selected, setSelected] = useState<Account | null>(null);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [snapshotTotal, setSnapshotTotal] = useState(0);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogVersion, setCatalogVersion] = useState(0);
  const [reviewedSnapshot, setReviewedSnapshot] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [json, setJson] = useState("");
  async function load() {
    try {
      const state = await api<{ enabled: boolean }>("status");
      if (!state.enabled) {
        setStatus("disabled");
        return;
      }
      const data = await api<{ items: Account[]; total: number }>("accounts");
      setAccounts(data.items);
      setAccountTotal(data.total);
      setStatus("enabled");
      setError("");
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to load accounts.",
      );
      setStatus("error");
    }
  }
  useEffect(() => {
    const controller = new AbortController();
    api<{ enabled: boolean }>("status", { signal: controller.signal })
      .then(async (state) => {
        if (!state.enabled) {
          setStatus("disabled");
          return;
        }
        const data = await api<{ items: Account[]; total: number }>(
          "accounts",
          { signal: controller.signal },
        );
        if (!controller.signal.aborted) {
          setAccounts(data.items);
          setAccountTotal(data.total);
          setStatus("enabled");
        }
      })
      .catch((cause: Error) => {
        if (!controller.signal.aborted) {
          setError(cause.message);
          setStatus("error");
        }
      });
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    api<{ items: Snapshot[]; total: number }>(
      `accounts/${selected.account_id}/snapshots`,
      { signal: controller.signal },
    )
      .then((data) => {
        setSnapshots(data.items);
        setSnapshotTotal(data.total);
      })
      .catch((cause) => {
        if (!controller.signal.aborted) setError(cause.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setCatalogLoading(false);
      });
    return () => controller.abort();
  }, [selected, catalogVersion]);
  function choose(account: Account) {
    setReviewedSnapshot(null);
    setSelected(account);
    setSnapshots([]);
    setSnapshotTotal(0);
    setCatalogLoading(true);
    setError("");
    setNotice("");
    setJson("");
  }
  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    setError("");
    setNotice("");
    setBusy(true);
    try {
      const fields = Object.fromEntries(new FormData(form));
      const result = accountInput.safeParse({
        ...fields,
        server: fields.server || null,
        broker_account_ref: fields.broker_account_ref || null,
      });
      if (!result.success)
        throw new Error(
          result.error.issues
            .map((issue) => `${issue.path.join(".")}: ${issue.message}`)
            .join(" "),
        );
      const account = await api<Account>("accounts", {
        method: "POST",
        body: JSON.stringify(result.data),
      });
      await load();
      choose(account);
      setNotice(
        "Practice account created. No historical trades were assigned.",
      );
      form.reset();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Account could not be created.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function register(event: React.FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const specification = specificationInput(json, selected);
      await api<Snapshot>(`accounts/${selected.account_id}/snapshots`, {
        method: "POST",
        body: JSON.stringify({ specification }),
      });
      setCatalogLoading(true);
      setCatalogVersion((version) => version + 1);
      setNotice(
        "Specification saved. Identical content reuses its snapshot; previous versions remain intact.",
      );
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Specification could not be saved.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="accounts-workspace">
      <header className="accounts-heading">
        <span className="eyebrow">YOUR TRADING FOUNDATION</span>
        <h1>Trading Accounts.</h1>
        <p>Separate accounts. Explicit currencies. A clearer trading record.</p>
        <span className="accounts-badge">
          <ShieldCheck size={16} /> Local practice only · No broker connection
        </span>
      </header>
      {error && (
        <div
          className="accounts-error"
          role="alert"
          aria-label="Account management error"
        >
          {error}
        </div>
      )}
      {notice && (
        <p className="accounts-success" role="status">
          {notice}
        </p>
      )}
      {status === "loading" && (
        <p className="accounts-panel" role="status">
          Loading practice workspace…
        </p>
      )}
      {(status === "disabled" || status === "error") && (
        <section className="accounts-panel">
          <h2>Open an isolated practice workspace</h2>
          <p>
            Account management is disabled for the normal journal. Use the
            documented practice runner and a separate frontend to try these
            features safely.
          </p>
          <Button onClick={() => void load()}>Retry connection</Button>
        </section>
      )}
      {status === "enabled" && (
        <>
          <div className="accounts-grid">
            <section className="accounts-panel">
              <h2>
                <WalletCards size={20} /> Your practice accounts
              </h2>
              <p>
                Showing {accounts.length} of {accountTotal}. Compatible accounts
                share a broker specification catalog.
              </p>
              {accounts.length === 0 && (
                <p>No accounts yet. Create your first practice account.</p>
              )}
              <div className="accounts-list">
                {accounts.map((account) => (
                  <button
                    key={account.account_id}
                    className="account-choice"
                    aria-pressed={selected?.account_id === account.account_id}
                    onClick={() => choose(account)}
                  >
                    <strong>{account.name}</strong>
                    <span>
                      {account.broker} · {account.platform.toUpperCase()}
                    </span>
                    <span>
                      Reporting {account.reporting_currency} · Settlement{" "}
                      {account.settlement_currency}
                    </span>
                  </button>
                ))}
              </div>
              {accountTotal > accounts.length && (
                <p>
                  Only the first 100 accounts are displayed. The API supports
                  offset pagination.
                </p>
              )}
            </section>
            <section className="accounts-panel">
              <h2>Add a practice account</h2>
              <p>
                Enter identity details only. Never enter passwords, API keys or
                broker credentials.
              </p>
              <form onSubmit={create} className="accounts-form">
                <label>
                  Account name
                  <input name="name" required maxLength={100} />
                </label>
                <label>
                  Broker
                  <input name="broker" required maxLength={100} />
                </label>
                <label>
                  Platform
                  <select name="platform" aria-label="Platform">
                    <option value="manual">Manual / practice</option>
                    <option value="bybit">Bybit crypto</option>
                    <option value="mt5">MT5 CFD</option>
                  </select>
                </label>
                <label>
                  Server / venue (required for MT5)
                  <input name="server" maxLength={100} />
                </label>
                <label>
                  Reporting currency
                  <input
                    name="reporting_currency"
                    placeholder="USD"
                    required
                    maxLength={12}
                  />
                </label>
                <label>
                  Settlement currency
                  <input
                    name="settlement_currency"
                    placeholder="USD"
                    required
                    maxLength={12}
                  />
                </label>
                <label>
                  Non-secret account reference (optional)
                  <input name="broker_account_ref" maxLength={100} />
                </label>
                <Button disabled={busy} type="submit">
                  Create practice account
                </Button>
              </form>
            </section>
          </div>
          <section className="accounts-panel">
            <h2>
              <FileCheck2 size={20} /> Instrument specification review
            </h2>
            {!selected ? (
              <p>
                Select an account to review compatible instrument
                specifications.
              </p>
            ) : (
              <>
                <h3>{selected.name}</h3>
                <p>
                  {selected.server ?? "No server recorded"} · Reporting{" "}
                  {selected.reporting_currency} / settlement{" "}
                  {selected.settlement_currency}. Currency conversion is never
                  assumed.
                </p>
                <p>
                  Account ID: <code>{selected.account_id}</code>
                </p>
                {catalogLoading ? (
                  <p role="status">Loading specifications…</p>
                ) : (
                  <p>
                    Showing {snapshots.length} of {snapshotTotal} compatible
                    specification versions. Selecting an account only changes
                    this view.
                  </p>
                )}
                {!catalogLoading && snapshots.length === 0 && (
                  <p>
                    No specifications recorded. Supply documented values below.
                  </p>
                )}
                <div className="accounts-specs">
                  {snapshots.map((snapshot) => (
                    <article
                      className="account-spec"
                      key={snapshot.snapshot_id}
                    >
                      <h3>
                        {snapshot.specification.symbol} ·{" "}
                        {snapshot.specification.product}
                      </h3>
                      <p>
                        {snapshot.specification.market_category} ·{" "}
                        {snapshot.specification.calculation_mode}
                      </p>
                      <p>
                        Tick size {snapshot.specification.tick_size} · Minimum{" "}
                        {snapshot.specification.volume_min}{" "}
                        {snapshot.specification.quantity_unit}
                      </p>
                      {snapshot.specification.product === "cfd" && (
                        <p>
                          Contract size {snapshot.specification.contract_size} ·
                          Pip size{" "}
                          {snapshot.specification.pip_size ?? "Not supplied"}
                        </p>
                      )}
                      <p>
                        {snapshot.specification.source.kind}:{" "}
                        {snapshot.specification.source.reference}
                      </p>
                      <p>
                        Effective {snapshot.specification.source.effective_at}
                      </p>
                      <details>
                        <summary>Review immutable snapshot and source</summary>
                        <pre>{JSON.stringify(snapshot, null, 2)}</pre>
                      </details>
                      <Button
                        variant="outline"
                        aria-pressed={reviewedSnapshot === snapshot.snapshot_id}
                        onClick={() =>
                          setReviewedSnapshot(snapshot.snapshot_id)
                        }
                      >
                        {reviewedSnapshot === snapshot.snapshot_id
                          ? "Selected for review"
                          : "Select specification for review"}
                      </Button>
                    </article>
                  ))}
                </div>
                {reviewedSnapshot && (
                  <p role="status">
                    Review selection: {reviewedSnapshot}. This temporary
                    selection does not assign any journal trade.
                  </p>
                )}
                <form onSubmit={register} className="accounts-form">
                  <label>
                    Documented specification JSON
                    <textarea
                      value={json}
                      onChange={(event) => setJson(event.target.value)}
                      required
                      rows={12}
                      spellCheck={false}
                      aria-describedby="spec-help"
                    />
                  </label>
                  <p id="spec-help">
                    Paste one instrument specification with its source and
                    timezone-aware dates. Decimal amounts must be strings.
                    Manual sources are user supplied, not independently broker
                    verified. Saving adds history; it does not enable trading or
                    attach a trade.
                  </p>
                  <Button disabled={busy || catalogLoading} type="submit">
                    Register specification
                  </Button>
                </form>
              </>
            )}
          </section>
        </>
      )}
    </div>
  );
}

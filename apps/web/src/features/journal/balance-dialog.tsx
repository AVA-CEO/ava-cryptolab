"use client";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { requestJSON, type Currency } from "./contracts";
export function BalanceDialog({
  currency,
  onClose,
  onSaved,
}: {
  currency: Currency;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    requestJSON<{ opening_balance: string | null }>(
      `/api/journal/account?currency=${currency}`,
      { signal: abort.signal },
    )
      .then((data) => setValue(data.opening_balance ?? ""))
      .catch((e) => {
        if (!abort.signal.aborted) setError(e.message);
      });
    return () => abort.abort();
  }, [currency]);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await requestJSON("/api/journal/account", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ currency, opening_balance: value }),
      });
      toast.success("Opening balance saved");
      onSaved();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <DialogContent className="balance-dialog">
        <DialogTitle className="dialog-title">
          Your starting point<span className="heading-dot">.</span>
        </DialogTitle>
        <DialogDescription className="dialog-description">
          Enter the {currency} balance before your journal history starts. We
          never invent a starting balance.
        </DialogDescription>
        <form onSubmit={save}>
          <label className="form-field">
            <span>Opening balance ({currency})</span>
            <input
              aria-label="Opening balance amount"
              inputMode="decimal"
              required
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
          </label>
          <p className="form-note">
            Recorded balance = opening balance + recorded net PnL. Deposits,
            withdrawals and unrealized market values are not tracked yet.
            Filtered views show a cohort balance, not the full account.
          </p>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="dialog-footer">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={busy}
            >
              Cancel
            </Button>
            <Button disabled={busy}>
              {busy ? "Saving…" : "Save opening balance"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

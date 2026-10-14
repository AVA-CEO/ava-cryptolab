"use client";
import Image from "next/image";
import { Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { amount, requestJSON, type Trade } from "./contracts";

export function TradeDetail({
  trade,
  onClose,
  onEdit,
  onDeleted,
  onRefresh,
}: {
  trade: Trade;
  onClose: () => void;
  onEdit: () => void;
  onDeleted: () => void;
  onRefresh: () => void;
}) {
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function deleteTrade() {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `/api/journal/${trade.id}?version=${trade.version}`,
        { method: "DELETE" },
      );
      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail);
      }
      toast.success("Trade deleted");
      onDeleted();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function removeScreenshot() {
    setBusy(true);
    try {
      await requestJSON(
        `/api/journal/${trade.id}/screenshot?version=${trade.version}`,
        { method: "DELETE" },
      );
      toast.success("Screenshot removed");
      onRefresh();
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
      <DialogContent>
        <DialogTitle className="dialog-title">
          {trade.pair}
          <span className="heading-dot">.</span>
        </DialogTitle>
        <DialogDescription className="dialog-description">
          {trade.exchange} · {trade.market} · {trade.strategy} ·{" "}
          {trade.metrics.status}
        </DialogDescription>
        <div className="detail-metrics">
          {[
            ["Net PnL", amount(trade.metrics.net_pnl, trade.currency)],
            [
              "Realized R",
              trade.metrics.realized_r === null
                ? "Not available"
                : `${Number(trade.metrics.realized_r).toFixed(2)}R`,
            ],
            [
              "Initial planned risk",
              amount(trade.metrics.planned_risk, trade.currency),
            ],
            [
              "Notional exposure",
              amount(trade.metrics.notional, trade.currency),
            ],
            [
              "Estimated margin",
              amount(trade.metrics.estimated_margin, trade.currency),
            ],
            ["Remaining quantity", trade.metrics.remaining_quantity],
          ].map(([label, value]) => (
            <div key={label}>
              <small>{label}</small>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
        <p className="form-note">
          Margin is a simple entry notional ÷ leverage estimate. It is not
          exchange collateral, liquidation price or cross-margin account risk.
        </p>
        <dl className="trade-facts">
          {[
            ["Entry / inventory cost", trade.entry_price],
            ["Original quantity", trade.quantity],
            [
              "Entry time (UTC)",
              new Date(trade.entry_at).toISOString().replace("T", " "),
            ],
            ["Initial stop", trade.stop_loss ?? "Not recorded"],
            ["Planned target", trade.take_profit ?? "Not recorded"],
            ["Entry fees", amount(trade.entry_fees, trade.currency)],
            ["Funding (paid positive)", amount(trade.funding, trade.currency)],
            [
              "Leverage / margin type",
              `${trade.leverage}× / ${trade.margin_type ?? "no margin"}`,
            ],
            [
              "Before / after emotion",
              `${trade.emotion_before || "—"} / ${trade.emotion_after || "—"}`,
            ],
            ["Mistake tags", trade.mistakes || "None recorded"],
          ].map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <h3 className="form-section-title">Exit executions</h3>
        {trade.exits.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>UTC time</th>
                  <th>Price</th>
                  <th>Quantity</th>
                  <th>Fees</th>
                </tr>
              </thead>
              <tbody>
                {trade.exits.map((e, i) => (
                  <tr key={i}>
                    <td>
                      {new Date(e.exit_at)
                        .toISOString()
                        .replace("T", " ")
                        .slice(0, 19)}
                    </td>
                    <td>{e.price}</td>
                    <td>{e.quantity}</td>
                    <td>{e.fees}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="form-note">This trade has no recorded exits.</p>
        )}
        <h3 className="form-section-title">Rationale & notes</h3>
        <p className="reflection-text">{trade.notes || "No notes recorded."}</p>
        <h3 className="form-section-title">Lessons</h3>
        <p className="reflection-text">
          {trade.lessons || "No lessons recorded."}
        </p>
        {trade.has_screenshot && (
          <div className="screenshot-preview">
            <Image
              unoptimized
              src={`/api/journal/${trade.id}/screenshot?v=${trade.version}`}
              alt={`Journal screenshot for ${trade.pair}`}
              width={800}
              height={500}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={removeScreenshot}
              disabled={busy}
            >
              Remove screenshot
            </Button>
          </div>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {confirm ? (
          <div className="delete-confirm">
            <strong>Delete this trade and its screenshot?</strong>
            <p>This permanently removes the journal record.</p>
            <div>
              <Button
                variant="outline"
                onClick={() => setConfirm(false)}
                disabled={busy}
              >
                Keep trade
              </Button>
              <Button
                className="danger-button"
                onClick={deleteTrade}
                disabled={busy}
              >
                {busy ? "Deleting…" : "Confirm delete"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="dialog-footer">
            <Button
              variant="outline"
              onClick={() => setConfirm(true)}
              disabled={busy}
            >
              <Trash2 size={15} />
              Delete trade
            </Button>
            <Button onClick={onEdit} disabled={busy}>
              <Pencil size={15} />
              Edit trade
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

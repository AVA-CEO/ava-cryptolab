"use client";
import { useState } from "react";
import { useFieldArray, useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { requestJSON, type Currency, type Trade } from "./contracts";

const positive = z
  .string()
  .trim()
  .regex(
    /^\d+(\.\d{1,10})?$/,
    "Use a positive decimal, at most 10 decimal places.",
  )
  .refine(
    (s) => Number(s) > 0 && Number(s) <= 1e12,
    "Enter an amount above zero, up to 1 trillion.",
  );
const nonnegative = z
  .string()
  .trim()
  .regex(/^\d+(\.\d{1,10})?$/, "Enter zero or a positive decimal.");
const optionalPrice = z.union([z.literal(""), positive]);
const formSchema = z
  .object({
    pair: z
      .string()
      .trim()
      .toUpperCase()
      .regex(
        /^[A-Z0-9]+\/(USD|USDT|USDC)$/,
        "Use a pair such as BTC/USD or ETH/USDT.",
      ),
    exchange: z.string().trim().min(1, "Enter the exchange.").max(80),
    currency: z.enum(["USD", "USDT", "USDC"]),
    market: z.enum(["spot", "futures"]),
    direction: z.enum(["buy", "sell"]),
    entry_at: z.string().min(1, "Choose the entry date and time."),
    entry_price: positive,
    quantity: positive,
    stop_loss: optionalPrice,
    take_profit: optionalPrice,
    entry_fees: nonnegative,
    funding: z
      .string()
      .regex(
        /^-?\d+(\.\d{1,10})?$/,
        "Use a signed decimal. Positive = paid; negative = received.",
      ),
    leverage: z
      .string()
      .refine(
        (v) => Number(v) >= 1 && Number(v) <= 125,
        "Use leverage between 1 and 125.",
      ),
    margin_type: z.enum(["isolated", "cross"]),
    strategy: z.string().max(100),
    notes: z.string().max(10000),
    mistakes: z.string().max(1000),
    emotion_before: z.string().max(100),
    emotion_after: z.string().max(100),
    lessons: z.string().max(10000),
    exits: z
      .array(
        z.object({
          exit_at: z.string().min(1, "Choose an exit timestamp."),
          price: positive,
          quantity: positive,
          fees: nonnegative,
        }),
      )
      .max(100),
  })
  .superRefine((data, ctx) => {
    if (data.pair.split("/")[1] !== data.currency)
      ctx.addIssue({
        code: "custom",
        path: ["currency"],
        message: "Choose the same currency as the pair’s quote.",
      });
    const long = data.market === "spot" || data.direction === "buy";
    if (
      data.stop_loss &&
      (long
        ? Number(data.stop_loss) >= Number(data.entry_price)
        : Number(data.stop_loss) <= Number(data.entry_price))
    )
      ctx.addIssue({
        code: "custom",
        path: ["stop_loss"],
        message: "Put the initial stop on the loss side of entry.",
      });
    if (
      data.take_profit &&
      (long
        ? Number(data.take_profit) <= Number(data.entry_price)
        : Number(data.take_profit) >= Number(data.entry_price))
    )
      ctx.addIssue({
        code: "custom",
        path: ["take_profit"],
        message: "Put the target on the profit side of entry.",
      });
  });
type Values = z.infer<typeof formSchema>;
const utcInput = (timestamp: string) =>
  new Date(timestamp).toISOString().slice(0, 19);
const iso = (input: string) => new Date(`${input}Z`).toISOString();

export function TradeForm({
  trade,
  currency,
  onClose,
  onSaved,
}: {
  trade?: Trade;
  currency: Currency;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<Values>({
    resolver: zodResolver(formSchema),
    defaultValues: trade
      ? {
          ...trade,
          entry_at: utcInput(trade.entry_at),
          stop_loss: trade.stop_loss ?? "",
          take_profit: trade.take_profit ?? "",
          margin_type: trade.margin_type ?? "isolated",
          exits: trade.exits.map((e) => ({
            ...e,
            exit_at: utcInput(e.exit_at),
          })),
        }
      : {
          pair: `BTC/${currency}`,
          currency,
          market: "spot",
          direction: "buy",
          exchange: "",
          entry_at: utcInput(new Date().toISOString()),
          entry_price: "",
          quantity: "",
          stop_loss: "",
          take_profit: "",
          entry_fees: "0",
          funding: "0",
          leverage: "1",
          margin_type: "isolated",
          strategy: "",
          notes: "",
          mistakes: "",
          emotion_before: "",
          emotion_after: "",
          lessons: "",
          exits: [],
        },
  });
  const { fields, append, remove } = useFieldArray({ control, name: "exits" });
  const market = useWatch({ control, name: "market" });
  const direction = useWatch({ control, name: "direction" });
  async function submit(values: Values) {
    setError("");
    try {
      const payload = {
        ...values,
        entry_at: iso(values.entry_at),
        stop_loss: values.stop_loss || null,
        take_profit: values.take_profit || null,
        leverage: market === "spot" ? "1" : values.leverage,
        funding: market === "spot" ? "0" : values.funding,
        margin_type: market === "spot" ? null : values.margin_type,
        exits: values.exits.map((e) => ({ ...e, exit_at: iso(e.exit_at) })),
        ...(trade ? { version: trade.version } : {}),
      };
      const saved = await requestJSON<Trade>(
        `/api/journal${trade ? `/${trade.id}` : ""}`,
        {
          method: trade ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      if (file) {
        const form = new FormData();
        form.append("file", file);
        try {
          await requestJSON(
            `/api/journal/${saved.id}/screenshot?version=${saved.version}`,
            { method: "POST", body: form },
          );
        } catch (e) {
          toast.warning(
            `Trade saved. Screenshot was not attached: ${(e as Error).message}`,
          );
        }
      }
      toast.success(trade ? "Trade updated" : "Trade recorded");
      onSaved();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function close() {
    if (isSubmitting) return;
    if ((isDirty || file) && !window.confirm("Discard your unsaved changes?"))
      return;
    onClose();
  }
  const field = (
    name: keyof Omit<Values, "exits">,
    label: string,
    type = "text",
    help?: string,
  ) => (
    <label className="form-field">
      <span>{label}</span>
      <input
        type={type}
        aria-label={label}
        step={type === "datetime-local" ? 1 : undefined}
        {...register(name)}
        aria-invalid={!!errors[name]}
        inputMode={
          type === "text" &&
          [
            "entry_price",
            "quantity",
            "stop_loss",
            "take_profit",
            "entry_fees",
            "funding",
            "leverage",
          ].includes(name)
            ? "decimal"
            : undefined
        }
      />
      {help && <small>{help}</small>}
      {errors[name] && <em role="alert">{errors[name]?.message}</em>}
    </label>
  );
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) close();
      }}
    >
      <DialogContent className="trade-dialog">
        <DialogTitle className="dialog-title">
          {trade ? "Edit trade" : "Record a trade"}
          <span className="heading-dot">.</span>
        </DialogTitle>
        <DialogDescription className="dialog-description">
          Save the facts, the plan, and what you learned. All times below are
          UTC.
        </DialogDescription>
        <form onSubmit={handleSubmit(submit)} noValidate>
          <h3 className="form-section-title">01 · The position</h3>
          <div className="form-grid">
            {field(
              "pair",
              "Trading pair",
              "text",
              "Linear quote-settled records: USD, USDT or USDC.",
            )}
            {field("exchange", "Exchange")}
            <label className="form-field">
              <span>Market</span>
              <select {...register("market")}>
                <option value="spot">Spot</option>
                <option value="futures">Linear futures</option>
              </select>
            </label>
            <label className="form-field">
              <span>Direction</span>
              <select {...register("direction")}>
                <option value="buy">Buy / Long</option>
                <option value="sell">
                  {market === "spot"
                    ? "Sell existing inventory"
                    : "Sell / Short"}
                </option>
              </select>
            </label>
            <label className="form-field">
              <span>Settlement currency</span>
              <select {...register("currency")}>
                <option>USD</option>
                <option>USDT</option>
                <option>USDC</option>
              </select>
              {errors.currency && <em>{errors.currency.message}</em>}
            </label>
            {field(
              "entry_at",
              market === "spot" && direction === "sell"
                ? "Acquisition time (UTC)"
                : "Entry time (UTC)",
              "datetime-local",
            )}
            {field(
              "entry_price",
              market === "spot" && direction === "sell"
                ? "Inventory cost basis per unit"
                : "Entry price",
            )}
            {field(
              "quantity",
              "Original quantity",
              "text",
              "Base asset units, not margin dollars.",
            )}
          </div>
          {market === "spot" && direction === "sell" && (
            <p className="form-note">
              A spot sale disposes of inventory. Record its acquisition cost
              here, then the sale as an exit below. It is not a short position.
            </p>
          )}
          <h3 className="form-section-title">02 · Risk & costs</h3>
          <div className="form-grid">
            {field(
              "stop_loss",
              "Initial stop loss (optional)",
              "text",
              "No initial stop means no R multiple. Keep the original plan.",
            )}
            {field("take_profit", "Planned take profit (optional)")}
            {field("entry_fees", "Entry fees paid")}
            {market === "futures" && (
              <>
                {field(
                  "funding",
                  "Funding paid / received",
                  "text",
                  "Positive = paid. Negative = received. Total recorded to date.",
                )}
                {field("leverage", "Leverage (×)")}
                <label className="form-field">
                  <span>Margin type</span>
                  <select {...register("margin_type")}>
                    <option value="isolated">Isolated</option>
                    <option value="cross">Cross</option>
                  </select>
                </label>
              </>
            )}
          </div>
          <div className="form-section-row">
            <h3 className="form-section-title">03 · Exit executions</h3>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() =>
                append({
                  exit_at: utcInput(new Date().toISOString()),
                  price: "",
                  quantity: "",
                  fees: "0",
                })
              }
            >
              <Plus size={14} />
              Add exit
            </Button>
          </div>
          <p className="form-note">
            No exits = open. Exiting less than the original quantity = partially
            closed. Add each actual exit separately.
          </p>
          {fields.map((f, index) => (
            <div className="exit-row" key={f.id}>
              <div className="form-grid">
                {(["exit_at", "price", "quantity", "fees"] as const).map(
                  (key) => (
                    <label className="form-field" key={key}>
                      <span>
                        {
                          {
                            exit_at: "Exit time (UTC)",
                            price: "Exit price",
                            quantity: "Exit quantity",
                            fees: "Exit fees",
                          }[key]
                        }
                      </span>
                      <input
                        type={key === "exit_at" ? "datetime-local" : "text"}
                        step={key === "exit_at" ? 1 : undefined}
                        {...register(`exits.${index}.${key}`)}
                        aria-invalid={!!errors.exits?.[index]?.[key]}
                      />
                      {errors.exits?.[index]?.[key] && (
                        <em>{errors.exits[index]?.[key]?.message}</em>
                      )}
                    </label>
                  ),
                )}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`Remove exit ${index + 1}`}
                onClick={() => remove(index)}
              >
                <Trash2 size={16} />
              </Button>
            </div>
          ))}
          <h3 className="form-section-title">04 · The reflection</h3>
          <div className="form-grid">
            {field("strategy", "Strategy / setup tag")}
            {field(
              "mistakes",
              "Mistake tags",
              "text",
              "Separate repeated tags with commas.",
            )}
            {field("emotion_before", "Emotion before")}
            {field("emotion_after", "Emotion after")}
          </div>
          <label className="form-field">
            <span>Rationale & notes</span>
            <textarea rows={3} {...register("notes")} />
          </label>
          <label className="form-field">
            <span>Lessons learned</span>
            <textarea rows={2} {...register("lessons")} />
          </label>
          <label className="form-field">
            <span>Screenshot (optional)</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => {
                const image = e.target.files?.[0];
                if (image && image.size > 5_000_000) {
                  toast.error("Choose an image smaller than 5 MB.");
                  e.target.value = "";
                  setFile(null);
                } else setFile(image ?? null);
              }}
            />
            <small>
              PNG, JPEG or WebP. Images are re-saved without metadata. Existing
              screenshot is kept unless replaced.
            </small>
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="dialog-footer">
            <Button
              type="button"
              variant="outline"
              onClick={close}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : trade ? "Save changes" : "Save trade"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

import { z } from "zod";
import type {
  Instrument,
  AccountContract,
} from "@/features/journal/multi-asset-contracts";

const identity = z.string().trim().min(1).max(100);
const currency = z
  .string()
  .regex(
    /^[A-Z][A-Z0-9]{1,11}$/,
    "Use an uppercase currency code, for example USD.",
  );
export const accountInput = z
  .object({
    name: identity,
    broker: identity,
    platform: z.enum(["manual", "bybit", "mt5"]),
    server: identity.nullable(),
    broker_account_ref: identity.nullable(),
    reporting_currency: currency,
    settlement_currency: currency,
  })
  .strict()
  .superRefine((value, ctx) => {
    if (value.platform === "mt5" && !value.server)
      ctx.addIssue({
        code: "custom",
        path: ["server"],
        message: "MT5 accounts require a server.",
      });
  });
export type AccountInput = z.infer<typeof accountInput>;
export type Account = AccountContract;
export type Snapshot = {
  snapshot_id: string;
  content_sha256: string;
  created_at: string;
  specification: Instrument;
};

// This boundary checks relationships and preserves decimal strings. Python owns
// complete financial validation; JavaScript must not round contract values.
export function specificationInput(text: string, account: Account): unknown {
  const value: unknown = JSON.parse(text);
  const common = z
    .object({
      broker: identity,
      venue: identity,
      settlement_currency: currency,
      product: z.enum([
        "crypto_spot",
        "crypto_linear_futures",
        "cfd",
        "tradfi_perpetual",
      ]),
    })
    .passthrough()
    .parse(value);
  if (
    common.broker !== account.broker ||
    common.settlement_currency !== account.settlement_currency ||
    (account.server && common.venue !== account.server)
  )
    throw new Error(
      "Broker, settlement currency and server must match the selected account.",
    );
  if (
    (account.platform === "mt5" && common.product !== "cfd") ||
    (account.platform === "bybit" && common.product === "cfd")
  )
    throw new Error(
      "This product is incompatible with the selected account platform.",
    );
  function exact(item: unknown): void {
    if (typeof item === "number" || typeof item === "boolean")
      throw new Error(
        'Write financial values as decimal strings, for example "0.01".',
      );
    if (item && typeof item === "object") Object.values(item).forEach(exact);
  }
  exact(value);
  return value;
}

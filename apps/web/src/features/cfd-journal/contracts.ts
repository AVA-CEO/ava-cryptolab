import { z } from "zod";

const decimal = z
  .string()
  .max(1024)
  .regex(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/);
const measurement = z.object({
  raw: decimal.nullable(),
  rounded: decimal.nullable(),
  unavailable_reason: z.string().nullable().optional(),
  currency: z.string().optional(),
});
const performance = z.object({
  currency: z.string().min(2).max(12),
  gross_pnl: measurement,
  net_pnl: measurement,
  original_planned_risk: measurement,
  realized_r: measurement,
});
const execution = z
  .object({
    execution_id: z.string(),
    executed_at: z.string(),
    price: decimal,
    lots: decimal,
  })
  .passthrough();
const rounding = z.object({
  currencies: z.array(
    z.object({ currency: z.string(), decimal_places: z.int().min(0).max(18) }),
  ),
  rounding: z.enum(["ROUND_HALF_EVEN", "ROUND_HALF_UP"]),
  ratio_places: z.int().min(0).max(18),
  movement_places: z.int().min(0).max(18),
});
export const savedPositionSchema = z
  .object({
    position_id: z.uuid(),
    account_id: z.string().min(1),
    revision_id: z.uuid(),
    revision_no: z.literal(1),
    input: z
      .object({
        as_of: z.string(),
        trade: z
          .object({
            direction: z.enum(["buy", "sell"]),
            entry: execution,
            exits: z.array(execution),
            original_stop: decimal.nullable(),
            planned_take_profit: decimal.nullable().optional(),
            snapshot: z
              .object({
                snapshot_id: z.string(),
                specification: z
                  .object({
                    symbol: z.string(),
                    contract_size: decimal,
                    profit_currency: z.string(),
                    source: z.unknown().optional(),
                  })
                  .passthrough(),
              })
              .passthrough(),
            adjustments: z.array(
              z
                .object({
                  adjustment_id: z.string(),
                  kind: z.string(),
                  amount: decimal,
                  currency: z.string(),
                  occurred_at: z.string(),
                  description: z.string(),
                })
                .passthrough(),
            ),
            conversions: z.array(
              z
                .object({
                  conversion_id: z.string(),
                  from_currency: z.string(),
                  to_currency: z.string(),
                  rate: decimal,
                  observed_at: z.string(),
                  applies_at: z.string(),
                })
                .passthrough(),
            ),
          })
          .passthrough(),
      })
      .passthrough(),
    result: z
      .object({
        status: z.literal("calculated"),
        state: z.enum(["open", "partial", "closed"]),
        original_lots: decimal,
        remaining_lots: decimal,
        native: performance,
        reporting: performance,
        rounding_policy: rounding,
      })
      .passthrough(),
    original_risk_basis: z
      .object({
        schema_version: z.literal("cfd-risk-anchor-v1"),
        direction: z.enum(["buy", "sell"]),
        entry: execution,
        original_stop: decimal.nullable(),
        native: measurement,
        reporting: measurement,
      })
      .passthrough(),
    integrity: z.object({
      stored_hashes: z.literal("verified"),
      normalized_input: z.literal("verified"),
      original_risk: z.literal("verified"),
      result_correspondence: z.literal("structural_checks_only"),
      financial_recalculation: z.literal("not_performed"),
    }),
    provenance: z
      .object({
        kind: z.literal("local_personal"),
        input_kind: z.literal("synthetic_practice"),
        accepted_calculation: z.literal(true),
        broker_authenticated: z.literal(false),
      })
      .passthrough(),
    replay: z.object({ status: z.literal("not_run") }).passthrough(),
    input_sha256: z.string().regex(/^[0-9a-f]{64}$/),
    result_sha256: z.string().regex(/^[0-9a-f]{64}$/),
    original_risk_sha256: z.string().regex(/^[0-9a-f]{64}$/),
    manifest_sha256: z.string().regex(/^[0-9a-f]{64}$/),
  })
  .passthrough();
export type SavedPosition = z.infer<typeof savedPositionSchema>;
export const positionPageSchema = z.object({
  account_id: z.string().min(1),
  items: z.array(savedPositionSchema),
  next_cursor: z.string().nullable(),
});

export function monetary(
  value: { rounded: string | null; currency?: string },
  policy: z.infer<typeof rounding>,
) {
  if (value.rounded === null) return "Unavailable";
  const places = value.currency
    ? policy.currencies.find((item) => item.currency === value.currency)
        ?.decimal_places
    : policy.ratio_places;
  // The engine already rounded this value. Restore presentation zeros only;
  // never parse a financial amount as Number or recalculate a stored result.
  const [whole, fraction = ""] = value.rounded.split(".");
  const formatted =
    places !== undefined &&
    !/[eE]/.test(value.rounded) &&
    fraction.length <= places
      ? `${whole}${places ? `.${fraction.padEnd(places, "0")}` : ""}`
      : value.rounded;
  return `${formatted} ${value.currency ?? "R"}`;
}

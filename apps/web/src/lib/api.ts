import { z } from "zod";

const summarySchema = z.object({
  mode: z.literal("empty"),
  currency: z.string(),
  recorded_equity: z.string().nullable(),
  realized_pnl: z.string().nullable(),
  total_trades: z.number().int().nonnegative(),
  win_rate: z.number().nullable(),
  profit_factor: z.number().nullable(),
  message: z.string(),
});
export type Summary = z.infer<typeof summarySchema>;
export type DashboardResult =
  { status: "connected"; summary: Summary } | { status: "unavailable" };
export async function getDashboard(): Promise<DashboardResult> {
  try {
    const response = await fetch(
      `${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/v1/dashboard`,
      { cache: "no-store", signal: AbortSignal.timeout(3000) },
    );
    if (!response.ok) return { status: "unavailable" };
    return {
      status: "connected",
      summary: summarySchema.parse(await response.json()),
    };
  } catch {
    return { status: "unavailable" };
  }
}

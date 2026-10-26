import { NextRequest } from "next/server";
import { limitedBody } from "@/lib/limited-body";

const UUID =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

async function proxy(request: NextRequest) {
  const fail = (detail: string, status: number) =>
    Response.json(
      { detail },
      { status, headers: { "Cache-Control": "no-store" } },
    );
  if (process.env.VERCEL)
    return fail(
      "CFD saving is disabled on Vercel until authenticated durable storage is approved.",
      403,
    );
  try {
    const publicUrl = new URL(
      `${request.nextUrl.protocol}//${request.headers.get("host") ?? "invalid"}`,
    );
    if (!["127.0.0.1", "localhost"].includes(publicUrl.hostname))
      return fail("CFD journal access is local practice only.", 403);
    const origin = request.headers.get("origin");
    if (origin && origin !== publicUrl.origin)
      return fail("Untrusted request origin.", 403);
    const target = process.env.CFD_JOURNAL_API_BASE_URL;
    if (
      target !== "http://127.0.0.1:8004" &&
      !(process.env.AVA_E2E === "1" && target === "http://127.0.0.1:8014")
    )
      return fail(
        "Start the NEW P3 practice runner and configure CFD_JOURNAL_API_BASE_URL=http://127.0.0.1:8004. No fallback database is used.",
        503,
      );
    const params = request.nextUrl.searchParams;
    if (params.toString().length > 2048)
      return fail("Journal query is too large.", 400);
    const keys = ["action", "account_id", "position_id", "cursor", "limit"];
    if (
      [...params.keys()].some(
        (key) => !keys.includes(key) || params.getAll(key).length !== 1,
      )
    )
      return fail("Invalid journal query.", 400);
    const action = params.get("action") ?? "status";
    const allowed =
      request.method === "GET"
        ? ["status", "examples", "positions"]
        : ["preview", "positions"];
    if (!allowed.includes(action))
      return fail("Unsupported CFD journal operation.", 404);
    const upstream = new URL(`${target}/api/v1/cfd/${action}`);
    const headers: Record<string, string> = {
      "X-AVA-Local": "cfd-practice-v1",
      "Content-Type": "application/json",
    };
    if (request.method === "GET" && action === "positions") {
      const account = params.get("account_id");
      if (!account || account.length > 100 || /[\u0000-\u001f]/.test(account))
        return fail("An explicit account scope is required.", 400);
      upstream.searchParams.set("account_id", account);
      const position = params.get("position_id");
      if (position) {
        if (!UUID.test(position))
          return fail("Invalid position reference.", 400);
        upstream.pathname += `/${position}`;
      }
      for (const key of ["cursor", "limit"]) {
        const value = params.get(key);
        if (value) {
          if (value.length > 800)
            return fail("Pagination input is too large.", 400);
          upstream.searchParams.set(key, value);
        }
      }
    } else if ([...params.keys()].some((key) => key !== "action"))
      return fail("Unexpected operation query.", 400);
    if (request.method === "POST" && action === "positions") {
      const idempotency = request.headers.get("idempotency-key");
      if (!idempotency || !UUID.test(idempotency))
        return fail(
          "A stable UUID Idempotency-Key is required for saving.",
          400,
        );
      headers["Idempotency-Key"] = idempotency;
    }
    const bytes =
      request.method === "POST"
        ? await limitedBody(request, 4 * 1024 * 1024)
        : undefined;
    const response = await fetch(upstream, {
      method: request.method,
      headers,
      body: bytes ? new Uint8Array(bytes).buffer : undefined,
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.timeout(30000),
    });
    const outgoing = new Headers({
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    });
    for (const header of ["etag", "idempotency-replayed", "retry-after"]) {
      const value = response.headers.get(header);
      if (value) outgoing.set(header, value);
    }
    return new Response(response.body, {
      status: response.status,
      headers: outgoing,
    });
  } catch (error) {
    return fail(
      error instanceof RangeError
        ? "Request too large."
        : "The isolated CFD journal is unavailable. If a save response was lost, retry the same unchanged draft before starting another trade.",
      error instanceof RangeError ? 413 : 503,
    );
  }
}
export const GET = proxy;
export const POST = proxy;

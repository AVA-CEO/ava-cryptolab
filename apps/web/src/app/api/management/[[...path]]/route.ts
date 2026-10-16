import { NextRequest } from "next/server";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
) {
  const { path = [] } = await context.params;
  const route = path.join("/");
  const fail = (detail: string, status: number) =>
    Response.json(
      { detail },
      { status, headers: { "Cache-Control": "no-store" } },
    );
  try {
    const publicUrl = new URL(
      `${request.nextUrl.protocol}//${request.headers.get("host") ?? request.nextUrl.host}`,
    );
    if (!["localhost", "127.0.0.1"].includes(publicUrl.hostname))
      return fail("Account access is local-only.", 403);
    const origin = request.headers.get("origin");
    if (origin && origin !== publicUrl.origin)
      return fail("Untrusted request origin.", 403);
    const allowed =
      request.method === "GET"
        ? /^(status|accounts(?:\/[a-zA-Z0-9-]+(?:\/snapshots(?:\/[a-zA-Z0-9-]+)?)?)?)$/
        : /^(accounts|accounts\/[a-zA-Z0-9-]+\/snapshots)$/;
    if (!allowed.test(route)) return fail("Unknown management operation.", 404);
    const target = new URL(process.env.API_BASE_URL ?? "http://127.0.0.1:8000");
    if (
      target.protocol !== "http:" ||
      !["localhost", "127.0.0.1"].includes(target.hostname) ||
      target.username ||
      target.password ||
      target.pathname !== "/" ||
      target.search ||
      target.hash
    )
      return fail("A local API address is required.", 503);
    if (Number(request.headers.get("content-length") ?? 0) > 64000)
      return fail("Specification too large.", 413);
    const body =
      request.method === "GET" ? undefined : await request.arrayBuffer();
    if (body && body.byteLength > 64000)
      return fail("Specification too large.", 413);
    const response = await fetch(
      `${target.origin}/api/v1/management/${route}${request.nextUrl.search}`,
      {
        method: request.method,
        body,
        headers: {
          "X-AVA-Local": "journal-v1",
          "Content-Type": "application/json",
        },
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(15000),
      },
    );
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return fail(
      "The practice API is unavailable. Start the isolated accounts runner and retry.",
      503,
    );
  }
}
export const GET = proxy;
export const POST = proxy;

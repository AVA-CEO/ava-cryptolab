import { NextRequest } from "next/server";

async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path?: string[] }> },
) {
  const { path = [] } = await context.params;
  const publicUrl = new URL(
    `${request.nextUrl.protocol}//${request.headers.get("host") ?? request.nextUrl.host}`,
  );
  if (!["localhost", "127.0.0.1"].includes(publicUrl.hostname)) {
    return Response.json(
      {
        detail:
          "Journal access is local-only until authentication is implemented.",
      },
      { status: 403 },
    );
  }
  const origin = request.headers.get("origin");
  if (request.method !== "GET" && origin && origin !== publicUrl.origin) {
    return Response.json(
      { detail: "Untrusted request origin." },
      { status: 403 },
    );
  }
  if (path.some((segment) => !/^[a-zA-Z0-9-]+$/.test(segment))) {
    return Response.json({ detail: "Invalid journal path." }, { status: 400 });
  }
  const declaredLength = Number(request.headers.get("content-length") ?? 0);
  if (!Number.isFinite(declaredLength) || declaredLength > 6_000_000) {
    return Response.json({ detail: "Request too large." }, { status: 413 });
  }
  try {
    const body =
      request.method === "GET" ? undefined : await request.arrayBuffer();
    if (body && body.byteLength > 6_000_000)
      return Response.json({ detail: "Request too large." }, { status: 413 });
    const headers: Record<string, string> = { "X-AVA-Local": "journal-v1" };
    const contentType = request.headers.get("content-type");
    if (contentType) headers["Content-Type"] = contentType;
    const response = await fetch(
      `${process.env.API_BASE_URL ?? "http://127.0.0.1:8000"}/api/v1/journal${path.length ? `/${path.join("/")}` : ""}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body,
        cache: "no-store",
        signal: AbortSignal.timeout(15000),
      },
    );
    const outgoing = new Headers({
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    });
    for (const header of [
      "content-type",
      "content-disposition",
      "retry-after",
    ]) {
      const value = response.headers.get(header);
      if (value) outgoing.set(header, value);
    }
    return new Response(response.body, {
      status: response.status,
      headers: outgoing,
    });
  } catch {
    return Response.json(
      {
        detail:
          "The local API is unavailable. Start it and apply the database migrations, then try again.",
      },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;

import { NextRequest } from "next/server";
import { limitedBody } from "@/lib/limited-body";

async function proxy(request: NextRequest) {
  const host = new URL(`http://${request.headers.get("host") ?? "invalid"}`)
    .hostname;
  if (process.env.VERCEL || !["localhost", "127.0.0.1"].includes(host))
    return Response.json(
      { detail: "Financial previews are local practice only." },
      { status: 403 },
    );
  if (
    request.headers.get("origin") &&
    request.headers.get("origin") !==
      `${request.nextUrl.protocol}//${request.headers.get("host")}`
  )
    return Response.json(
      { detail: "Untrusted request origin." },
      { status: 403 },
    );
  if (
    !["http://127.0.0.1:8003", "http://127.0.0.1:8004"].includes(
      process.env.CFD_API_BASE_URL ?? "",
    ) &&
    !(
      process.env.AVA_E2E === "1" &&
      process.env.CFD_API_BASE_URL === "http://127.0.0.1:8013"
    )
  )
    return Response.json(
      {
        detail:
          "Start the verified preview runner and set CFD_API_BASE_URL=http://127.0.0.1:8003. Saving remains disabled.",
      },
      { status: 503 },
    );
  const endpoint =
    request.method === "POST"
      ? "preview"
      : request.nextUrl.searchParams.get("view") === "examples"
        ? "examples"
        : "status";
  try {
    const bytes =
      request.method === "POST"
        ? await limitedBody(request, 4 * 1024 * 1024)
        : undefined;
    const body = bytes ? new Uint8Array(bytes).buffer : undefined;
    if (body && body.byteLength > 4 * 1024 * 1024)
      return Response.json({ detail: "Request too large." }, { status: 413 });
    const response = await fetch(
      `${process.env.CFD_API_BASE_URL}/api/v1/cfd/${endpoint}`,
      {
        method: request.method,
        body,
        headers: {
          "X-AVA-Local": "cfd-practice-v1",
          "Content-Type": "application/json",
        },
        cache: "no-store",
        redirect: "error",
        signal: AbortSignal.timeout(30000),
      },
    );
    return new Response(response.body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (error) {
    if (error instanceof RangeError)
      return Response.json({ detail: "Request too large." }, { status: 413 });
    return Response.json(
      {
        detail:
          "The isolated preview API is offline. Your journal is unaffected.",
      },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;

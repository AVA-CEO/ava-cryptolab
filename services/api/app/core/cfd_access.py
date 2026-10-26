"""B3A loopback, framing, body, rate and exact-target boundary. Not authentication."""

import asyncio
import json
import re
from collections import deque
from ipaddress import ip_address
from time import monotonic
from uuid import uuid4

from starlette.datastructures import Headers

from app.core.cfd_errors import CfdProblem, error_response
from app.database.cfd_session import CfdTargetRejected


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key")
        value[key] = item
    return value


def _constant(value):
    raise ValueError("Nonfinite JSON constant")


def validate_json(body, max_depth):
    value = json.loads(body.decode("utf-8"), object_pairs_hook=_object, parse_constant=_constant)
    pending = [(value, 1)]
    while pending:
        item, depth = pending.pop()
        if depth > max_depth:
            raise ValueError("JSON nesting limit")
        children = (
            item.values() if isinstance(item, dict) else item if isinstance(item, list) else ()
        )
        pending.extend((child, depth + 1) for child in children)


class CfdAccessMiddleware:
    def __init__(self, app, *, workspace, settings):
        self.app, self.workspace, self.settings = app, workspace, settings
        self.reads, self.previews = deque(), deque()
        self.preview_slot = asyncio.Semaphore(1)
        self.pending_previews = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["cfd_request_id"] = request_id
        started = False
        personal_save = False

        async def safe_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.lower() not in {b"cache-control", b"x-content-type-options"}
                ]
                message["headers"] = headers + [
                    (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"),
                ]
            await send(message)

        async def respond(status, code, text, headers=None):
            await error_response(status, code, text, request_id, headers=headers)(
                scope, receive, safe_send
            )

        try:
            if not self.settings.enabled or self.workspace is None:
                await respond(404, "cfd_disabled", "CFD practice is disabled.")
                return
            headers = Headers(scope=scope)
            critical = {
                "host",
                "origin",
                "x-ava-local",
                "content-length",
                "content-type",
                "content-encoding",
                "transfer-encoding",
                "idempotency-key",
            }
            if any(len(headers.getlist(key)) > 1 for key in critical):
                await respond(400, "ambiguous_headers", "Supply unambiguous request headers.")
                return
            client = scope.get("client")
            try:
                local = bool(client and ip_address(client[0]).is_loopback)
            except ValueError:
                local = False
            if (
                not local
                or headers.get("host", "").lower()
                not in {
                    f"localhost:{self.settings.api_port}",
                    f"127.0.0.1:{self.settings.api_port}",
                }
                or headers.get("x-ava-local") != "cfd-practice-v1"
                or "origin" in headers
                or any(
                    k.lower().startswith((b"x-forwarded-", b"forwarded"))
                    for k, v in scope["headers"]
                )
            ):
                await respond(
                    403,
                    "practice_access_denied",
                    "CFD access requires the isolated local practice session.",
                )
                return
            self.workspace.check_target(self.workspace.engine.url)
            if not self.workspace.ready:
                raise CfdTargetRejected("Workspace not ready")
            path, method = scope["path"], scope["method"]
            allowed = {
                "/api/v1/cfd/status": "GET",
                "/api/v1/cfd/preview": "POST",
                "/api/v1/cfd/examples": "GET",
            }
            if re.fullmatch(
                r"/api/v1/cfd/positions(?:/[^/]{1,100}(?:/revisions(?:/[^/]{1,9})?)?)?", path
            ):
                allowed[path] = "GET"
            if path not in allowed:
                await respond(404, "route_not_found", "CFD operation is not available.")
                return
            personal_save = (
                path == "/api/v1/cfd/positions"
                and method == "POST"
                and self.settings.allow_creation
                and getattr(self.workspace, "personal_writes", False)
                and self.settings.api_port in {8004, 8014}
            )
            if method != allowed[path] and not personal_save:
                await respond(
                    405,
                    "method_not_allowed",
                    "This CFD method is not available.",
                    {"Allow": allowed[path]},
                )
                return
            if len(scope.get("query_string", b"")) > 2048:
                await respond(400, "invalid_query", "The CFD query exceeds its size limit.")
                return
            preview = method == "POST"
            queue = self.previews if preview else self.reads
            limit = self.settings.preview_per_minute if preview else self.settings.reads_per_minute
            now = monotonic()
            while queue and queue[0] <= now - 60:
                queue.popleft()
            if len(queue) >= limit or (preview and self.pending_previews >= 3):
                await respond(
                    429, "rate_limited", "Try the CFD request again later.", {"Retry-After": "60"}
                )
                return
            queue.append(now)
            if preview:
                content_type = headers.get("content-type", "").lower().replace(" ", "")
                if content_type not in {"application/json", "application/json;charset=utf-8"}:
                    await respond(415, "json_required", "Use UTF-8 application/json.")
                    return
                if headers.get("content-encoding", "identity").lower() != "identity":
                    await respond(
                        415, "encoding_not_supported", "Compressed CFD requests are not supported."
                    )
                    return
                if "content-length" in headers and "transfer-encoding" in headers:
                    await respond(400, "ambiguous_headers", "Supply unambiguous request framing.")
                    return
                length = headers.get("content-length")
                if length is not None and (
                    len(length) > 10 or not length.isascii() or not length.isdigit()
                ):
                    await respond(400, "invalid_content_length", "Use a valid content length.")
                    return
                if length is not None and int(length) > self.settings.max_body_bytes:
                    await respond(413, "payload_too_large", "CFD request exceeds the body limit.")
                    return

            async def dispatch():
                forwarded = receive
                if preview:
                    body = bytearray()
                    while True:
                        message = await receive()
                        if message["type"] != "http.request":
                            raise CfdProblem(
                                400, "incomplete_body", "The CFD request body was incomplete."
                            )
                        body.extend(message.get("body", b""))
                        if len(body) > self.settings.max_body_bytes:
                            raise CfdProblem(
                                413, "payload_too_large", "CFD request exceeds the body limit."
                            )
                        if not message.get("more_body", False):
                            break
                    if length is not None and len(body) != int(length):
                        raise CfdProblem(
                            400,
                            "invalid_content_length",
                            "Content length does not match the request.",
                        )
                    try:
                        validate_json(body, self.settings.max_json_depth)
                    except (ValueError, UnicodeError, RecursionError):
                        raise CfdProblem(
                            400, "invalid_json", "Use valid, bounded JSON without duplicate keys."
                        ) from None

                    async def buffered():
                        return {"type": "http.request", "body": bytes(body), "more_body": False}

                    forwarded = buffered
                await self.app(scope, forwarded, safe_send)

            if preview:
                self.pending_previews += 1
                try:
                    async with asyncio.timeout(self.settings.request_timeout_seconds):
                        async with self.preview_slot:
                            await dispatch()
                finally:
                    self.pending_previews -= 1
            else:
                async with asyncio.timeout(self.settings.request_timeout_seconds):
                    await dispatch()
        except TimeoutError:
            if not started:
                await respond(
                    503,
                    "request_timeout",
                    (
                        "The save response timed out; its outcome is unconfirmed. "
                        "Retry the unchanged draft with the same Idempotency-Key."
                        if personal_save
                        else "The CFD request timed out. No calculation was accepted."
                    ),
                )
        except (CfdTargetRejected, OSError):
            if not started:
                await respond(
                    403,
                    "practice_access_denied",
                    "CFD access requires the isolated local practice session.",
                )
        except CfdProblem as error:
            if not started:
                await respond(error.status, error.code, error.message)
        except Exception:
            if not started:
                await respond(500, "request_failed", "The CFD request could not be completed.")

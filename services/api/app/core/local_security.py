from collections import defaultdict, deque
from time import monotonic

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class LocalSecurityMiddleware(BaseHTTPMiddleware):
    """Local browser boundary and bounded in-process mutation rate limits; not authentication."""

    def __init__(self, app):
        super().__init__(app)
        self.mutations = defaultdict(deque)

    async def dispatch(self, request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("origin")
            if origin and origin not in ("http://localhost:3000", "http://127.0.0.1:3000"):
                return JSONResponse({"detail": "Untrusted browser origin."}, status_code=403)
            if request.headers.get("x-ava-local") != "journal-v1":
                return JSONResponse({"detail": "Local journal header required."}, status_code=403)
            try:
                length = int(request.headers.get("content-length", "0"))
            except ValueError:
                return JSONResponse({"detail": "Invalid content length."}, status_code=400)
            if length < 0 or length > 6_000_000:
                return JSONResponse({"detail": "Request too large."}, status_code=413)
            key = request.client.host if request.client else "unknown"
            queue = self.mutations[key]
            now = monotonic()
            while queue and queue[0] < now - 60:
                queue.popleft()
            if len(queue) >= 120:
                return JSONResponse(
                    {"detail": "Too many edits. Try again in a minute."},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            queue.append(now)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

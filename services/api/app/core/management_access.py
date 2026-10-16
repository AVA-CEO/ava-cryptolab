"""Practice-only boundary, not production authentication."""

from ipaddress import ip_address
from pathlib import Path
from tempfile import gettempdir

from fastapi import HTTPException, Request


def local_management_access(request: Request):
    try:
        local = request.client is not None and ip_address(request.client.host).is_loopback
    except ValueError:
        local = False
    if not local or request.url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(403, "Account management is loopback-only until authentication exists.")
    if request.headers.get("x-ava-local") != "journal-v1":
        raise HTTPException(403, "Local management header required.")
    origin = request.headers.get("origin")
    if origin and origin not in {"http://localhost:3000", "http://127.0.0.1:3000"}:
        raise HTTPException(403, "Untrusted browser origin.")


def practice_database(session, settings):
    if not settings.account_management_enabled:
        return False
    url = session.get_bind().url  # Inspect the actual target, without opening it.
    if url.drivername != "sqlite" or not url.database:
        return False
    path = Path(url.database)
    if not path.is_absolute():
        return False
    path = path.resolve()
    return (
        path.is_relative_to(Path(gettempdir()).resolve())
        and path.parent.name.startswith(("ava-accounts-", "ava-browser-"))
        and path.name in {"practice.db", "tests.db"}
    )

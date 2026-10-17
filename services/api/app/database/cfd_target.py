"""Fail closed before connecting/migrating; no normal or practice journal targets."""

from pathlib import Path
from tempfile import gettempdir


def require_disposable_cfd(url, *, legacy_accounts=False):
    if url.drivername != "sqlite" or not url.database:
        raise RuntimeError(
            "CFD migration requires an explicitly supported disposable SQLite target."
        )
    path = Path(url.database)
    if not path.is_absolute():
        raise RuntimeError("CFD migration rejects relative database paths.")
    resolved = path.resolve()
    temp = Path(gettempdir()).resolve()
    parts = resolved.relative_to(temp).parts if resolved.is_relative_to(temp) else ()
    allowed = any(
        p.startswith(("ava-cfd-", "ava-migration-", "ava-browser-", "pytest-")) for p in parts[:-1]
    )
    accounts = any(p.startswith("ava-accounts-") for p in parts[:-1])
    allowed = (allowed or (legacy_accounts and accounts)) and (legacy_accounts or not accounts)
    if not allowed or resolved.suffix != ".db":
        raise RuntimeError(
            "CFD migration rejects normal, backup and existing Accounts practice paths."
        )
    return resolved

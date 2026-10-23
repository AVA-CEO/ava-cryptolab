"""Bounded, signed session-local keyset cursors; not user authentication."""

import base64
import hashlib
import hmac
import json

from app.core.cfd_errors import CfdProblem
from app.services.cfd_read_codec import canonical


def encode(key, scope, last):
    raw = canonical(dict(version=1, scope=scope, last=last)).encode()
    payload = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    signature = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
    return payload + "." + signature


def decode(key, scope, token):
    try:
        if len(token) > 800 or not token.isascii():
            raise ValueError
        payload, signature = token.split(".")
        expected = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        raw = base64.b64decode(payload + "=" * (-len(payload) % 4), altchars=b"-_", validate=True)
        data = json.loads(raw)
        if data != dict(version=1, scope=scope, last=data["last"]):
            raise ValueError
        return data["last"]
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise CfdProblem(
            400, "invalid_cursor", "Invalid page cursor; reload the first page."
        ) from None

"""Versioned synthetic read evidence only; not an accepted-release serializer."""

import hashlib
import json

from app.core.cfd_errors import CfdProblem

CANONICALIZER = "synthetic-read-json-v1"
POLICY = "incurred-once-v1"
MAX_EVIDENCE_BYTES = 32 * 1024 * 1024
MANIFEST = {
    "schema_version": "cfd-synthetic-manifest-v1",
    "fixture_id": "ava-cfd-read-fixture-v1",
    "provenance": "synthetic_fixture",
    "accepted_release": False,
    "broker_authenticated": False,
    "runtime": "not_executed",
    "engine_id": "cfd-position-v1",
    "input_schema_version": "cfd-position-v1",
    "result_schema_version": "cfd-position-result-v1",
    "risk_schema_version": "cfd-risk-anchor-v1",
    "canonicalizer_version": CANONICALIZER,
    "policy_version": POLICY,
}


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def corrupt():
    raise CfdProblem(409, "integrity_failure", "CFD evidence verification failed; values withheld.")


def unsupported():
    raise CfdProblem(
        503, "historical_schema_unavailable", "This historical evidence version cannot be verified."
    )


def document(text, expected_hash=None):
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_EVIDENCE_BYTES:
        corrupt()
    try:
        value = json.loads(text)
        # Reject duplicate keys, whitespace/noncanonical spellings and NaN/Infinity.
        if not isinstance(value, dict) or canonical(value) != text:
            corrupt()
    except (ValueError, TypeError, RecursionError):
        corrupt()
    if expected_hash is not None and digest(text) != expected_hash:
        corrupt()
    return value

"""Accepted local evidence codec; no imports of a calculator or runtime execution."""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.core.cfd_errors import CfdProblem
from app.schemas.cfd_personal_release import CalculationEvidence, LocalReleaseManifest
from app.services import cfd_canonical
from app.services.cfd_canonical import canonical_input

CANONICALIZER = "local-personal-json-v1"
POLICY = "local-personal-incurred-once-v1"

# Import-time baselines distinguish code already loaded into this process from
# later disk edits. Paths stay private; portable manifests contain only hashes.
SERIALIZER_SOURCE_IDENTITIES = {
    relative: (path, hashlib.sha256(path.read_bytes()).hexdigest())
    for relative, path in (
        ("app/services/cfd_personal_codec.py", Path(__file__).resolve()),
        ("app/services/cfd_canonical.py", Path(cfd_canonical.__file__).resolve()),
    )
}


def _check(value, depth=0):
    if depth > 64:
        raise ValueError("JSON nesting exceeds limits")
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("String JSON keys required")
        for item in value.values():
            _check(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _check(item, depth + 1)
    elif value is None or isinstance(value, (str, bool)):
        return
    elif isinstance(value, int) and -(2**63) <= value < 2**63:
        return
    else:
        raise ValueError("Only exact JSON values are supported; no floats")


def canonical(value):
    _check(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def document(text, expected_hash=None, *, limit=32 * 1024 * 1024):
    if not isinstance(text, str) or len(text.encode("utf-8")) > limit:
        raise ValueError("Evidence size/type limit")
    result = json.loads(text, object_pairs_hook=_pairs)
    if not isinstance(result, dict) or canonical(result) != text:
        raise ValueError("Canonical object required")
    if expected_hash is not None and digest(text) != expected_hash:
        raise ValueError("Evidence hash mismatch")
    return result


def normalize(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Finite Decimal required")
        if not value:
            return "0"
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Timezone required")
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [normalize(item) for item in value]
    return value


def input_text(request):
    return canonical_input(request)


def financial_text(model):
    return canonical(normalize(model.model_dump(mode="python")))


model_text = financial_text


def result_text(result):
    return financial_text(result)


def validate_release_manifest(manifest):
    if len(canonical(manifest).encode("utf-8")) > 1024 * 1024:
        raise ValueError("Manifest exceeds size limit")
    value = LocalReleaseManifest.model_validate(manifest)
    # Strict JSON validation also excludes float/int confusion before coercion.
    canonical(manifest)
    return value.model_dump(mode="json")


def verify_evidence_envelope(envelope, expected_build_sha256):
    """Stored evidence checks only: never execute or resolve a release from disk."""
    try:
        parsed = CalculationEvidence.model_validate(envelope)
        canonical(envelope)
        software = parsed.software_release.model_dump(mode="json")
        software_hash = digest(canonical(software))
        build_hash = digest(canonical(software["build"]))
        if (
            parsed.release_manifest_sha256 != software_hash
            or parsed.execution.release_digest != "sha256:" + software_hash
            or parsed.execution.build_sha256 != build_hash
            or expected_build_sha256 != build_hash
            or parsed.execution.approved_at < parsed.software_release.created_at
            or (
                parsed.software_release.build.source.dirty
                and parsed.execution.input_provenance != "synthetic_example"
            )
        ):
            raise ValueError("Release/evidence identity mismatch")
        return parsed.model_dump(mode="json")
    except (ValueError, TypeError, KeyError, RecursionError) as error:
        raise CfdProblem(
            409, "integrity_failure", "Local CFD evidence failed verification."
        ) from error


def make_evidence_envelope(runtime, calculated_at, input_provenance="synthetic_example"):
    runtime.verify(purpose="accept_save")
    at = normalize(calculated_at)
    envelope = {
        "schema_version": "ava-local-calculation-evidence-v1",
        "software_release": runtime.release_manifest,
        "release_manifest_sha256": runtime.release_digest.removeprefix("sha256:"),
        "execution": {
            "profile": "local_personal",
            "execution_kind": "host_pinned_python",
            "purpose": "accept_save",
            "release_digest": runtime.release_digest,
            "build_sha256": runtime.build_sha256,
            "signature_status": "unsigned",
            "registry_generation": runtime.approval["registry_generation"],
            "approval_reference": runtime.approval["approval_reference"],
            "approved_at": runtime.approval["approved_at"],
            "executed_at": at,
            "input_provenance": input_provenance,
            "broker_authenticated": False,
        },
    }
    return verify_evidence_envelope(envelope, runtime.build_sha256)

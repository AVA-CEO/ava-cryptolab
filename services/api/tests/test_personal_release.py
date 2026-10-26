"""Qualified local release/evidence tests: only new private temporary directories."""

import hashlib
import json
import shutil
import time
import zipfile
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from app.core.cfd_errors import CfdProblem
from app.schemas.cfd_positions import CfdPositionRequest
from app.services import cfd_personal_release as release_module
from app.services.cfd_personal_codec import (
    canonical,
    digest,
    document,
    input_text,
    make_evidence_envelope,
    normalize,
    result_text,
    validate_release_manifest,
    verify_evidence_envelope,
)
from app.services.cfd_personal_release import PersonalRuntime, prepare_personal_release


@pytest.fixture(scope="module")
def qualified(tmp_path_factory):
    directory = tmp_path_factory.mktemp("personal-release") / "release"
    reference = prepare_personal_release(directory, test_fixture=True)
    runtime = PersonalRuntime(directory, reference, test_fixture=True)
    return directory, reference, runtime


@pytest.fixture
def request_model():
    path = Path(__file__).parent / "fixtures" / "cfd-position-costs.synthetic.json"
    return CfdPositionRequest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def clone(qualified, tmp_path):
    directory = tmp_path / "release"
    shutil.copytree(
        qualified[0], directory, ignore=shutil.ignore_patterns("approval-registry.json")
    )
    return directory


def write_json(path, value):
    path.write_text(canonical(value), encoding="utf-8")


def test_independent_golden_real_frozen_worker(qualified, request_model):
    runtime = qualified[2]
    result = runtime.calculate(request_model, purpose="accept_save")
    assert result.status == "calculated"
    assert result.state == "closed"
    assert result.remaining_lots == 0
    assert result.native.gross_pnl.raw == Decimal("26")
    assert result.native.net_pnl.raw == Decimal("22")
    assert result.native.original_planned_risk.raw == Decimal("20")
    assert result.native.realized_r.raw == Decimal("1.1")
    assert document(input_text(request_model))["schema_version"] == "cfd-position-v1"
    assert document(result_text(result))["native"]["net_pnl"]["raw"] == "22"
    assert runtime.build_sha256 == digest(canonical(runtime.release_manifest["build"]))
    assert runtime.release_digest == "sha256:" + digest(canonical(runtime.release_manifest))
    assert not (qualified[0] / "no-bytecode").exists()
    assert not list((qualified[0] / "payload").rglob("*.pyc"))


def test_preserved_envelope_verifies_without_runtime_or_calculation(qualified, monkeypatch):
    runtime = qualified[2]
    envelope = make_evidence_envelope(runtime, datetime.now(timezone.utc))

    def forbidden(*args, **kwargs):
        raise AssertionError("Stored evidence verification must not access runtime/artifacts")

    monkeypatch.setattr(release_module, "_execute", forbidden)
    monkeypatch.setattr(release_module, "_runtime_inventory", forbidden)
    assert verify_evidence_envelope(envelope, runtime.build_sha256) == envelope
    assert envelope["execution"]["signature_status"] == "unsigned"
    assert envelope["execution"]["broker_authenticated"] is False
    assert envelope["execution"]["input_provenance"] == "synthetic_example"


@pytest.mark.parametrize("field", ["release", "build", "manifest", "schema", "purpose", "auth"])
def test_envelope_tamper_is_withheld(qualified, field):
    runtime = qualified[2]
    envelope = make_evidence_envelope(runtime, datetime.now(timezone.utc))
    if field == "release":
        envelope["execution"]["release_digest"] = "sha256:" + "0" * 64
    elif field == "build":
        envelope["execution"]["build_sha256"] = "0" * 64
    elif field == "manifest":
        envelope["software_release"]["release_id"] = "changed"
    elif field == "schema":
        envelope["schema_version"] = "unknown"
    elif field == "purpose":
        envelope["execution"]["purpose"] = "preview"
    else:
        envelope["execution"]["broker_authenticated"] = True
    with pytest.raises(CfdProblem) as error:
        verify_evidence_envelope(envelope, runtime.build_sha256)
    assert (error.value.status, error.value.code) == (409, "integrity_failure")


@pytest.mark.parametrize("target", ["manifest.json", "payload.zip", "runtime.json", "files.json"])
def test_changed_artifacts_rejected_before_execution(qualified, tmp_path, monkeypatch, target):
    directory = clone(qualified, tmp_path)
    with (directory / target).open("ab") as stream:
        stream.write(b"tamper")
    monkeypatch.setattr(release_module, "_execute", lambda *args: pytest.fail("Worker executed"))
    with pytest.raises(CfdProblem) as error:
        PersonalRuntime(directory, qualified[1], test_fixture=True)
    assert error.value.code == "calculation_release_integrity_failure"


@pytest.mark.parametrize(
    "target", ["worker/preview.py", "app/analytics/cfd_positions.py", "extra.py"]
)
def test_changed_or_extra_payload_rejected(qualified, tmp_path, target):
    directory = clone(qualified, tmp_path)
    (directory / "payload" / target).write_text("raise SystemExit(0)", encoding="utf-8")
    with pytest.raises(CfdProblem):
        PersonalRuntime(directory, qualified[1], test_fixture=True)


@pytest.mark.parametrize("field", ["unknown", "decimal", "mode", "duplicate_dependency", "version"])
def test_strict_manifest_known_contracts(qualified, field):
    manifest = deepcopy(qualified[2].release_manifest)
    if field == "unknown":
        manifest["unknown"] = "not accepted"
    elif field == "decimal":
        manifest["build"]["decimal"]["prec"] = 28
    elif field == "mode":
        manifest["build"]["supported_modes"]["crypto"] = ["spot"]
    elif field == "duplicate_dependency":
        manifest["build"]["dependencies"].append(manifest["build"]["dependencies"][0])
    else:
        manifest["schema_version"] = "ava-local-python-release-v99"
    with pytest.raises(ValueError):
        validate_release_manifest(manifest)


def test_explicit_digest_and_preserve_existing_directory(qualified):
    with pytest.raises(CfdProblem):
        PersonalRuntime(qualified[0], "sha256:" + "0" * 64, test_fixture=True)
    with pytest.raises(ValueError, match="Preserve"):
        prepare_personal_release(qualified[0], test_fixture=True)


@pytest.mark.parametrize(
    "relative", ["app/services/cfd_personal_codec.py", "app/services/cfd_canonical.py"]
)
def test_host_canonicalizer_must_match_retained_and_loaded_bytes(
    qualified, request_model, tmp_path, monkeypatch, relative
):
    path, expected_hash = release_module.SERIALIZER_SOURCE_IDENTITIES[relative]
    assert (qualified[0] / "payload" / relative).read_bytes() == path.read_bytes()
    fake_path = tmp_path / "changed-canonicalizer.py"
    fake_path.write_bytes(path.read_bytes() + b"\n# unauthorized update\n")
    identities = dict(release_module.SERIALIZER_SOURCE_IDENTITIES)
    identities[relative] = fake_path, expected_hash
    monkeypatch.setattr(release_module, "SERIALIZER_SOURCE_IDENTITIES", identities)
    monkeypatch.setattr(release_module, "_execute", lambda *args: pytest.fail("Worker executed"))
    with pytest.raises(CfdProblem) as error:
        qualified[2].calculate(request_model)
    assert error.value.code == "calculation_release_integrity_failure"


def test_preview_only_registry_cannot_accept_or_replay(qualified, tmp_path):
    directory = clone(qualified, tmp_path)
    runtime = PersonalRuntime(directory, qualified[1], test_fixture=True)
    registry = document((directory / "approval-registry.json").read_text(encoding="utf-8"))
    registry["entries"][0]["purposes"] = ["preview"]
    registry["decisions"][0]["purposes"] = ["preview"]
    write_json(directory / "approval-registry.json", registry)
    runtime.verify("preview")
    for purpose in ("accept_save", "replay", "unknown"):
        with pytest.raises(CfdProblem) as error:
            runtime.verify(purpose)
        assert error.value.code == "calculation_release_unapproved"


@pytest.mark.parametrize("field", ["state", "history", "generation", "paths", "unknown"])
def test_registry_tamper_fails_closed(qualified, tmp_path, field):
    directory = clone(qualified, tmp_path)
    runtime = PersonalRuntime(directory, qualified[1], test_fixture=True)
    registry = document((directory / "approval-registry.json").read_text(encoding="utf-8"))
    if field == "state":
        registry["entries"][0]["state"] = "revoked"
    elif field == "history":
        registry["decisions"][0]["old_state"] = "active"
    elif field == "generation":
        registry["generation"] = 2
    elif field == "paths":
        registry["entries"][0]["payload_location"] = "unapproved"
    else:
        registry["entries"][0]["secret"] = "extra"
    write_json(directory / "approval-registry.json", registry)
    with pytest.raises(CfdProblem) as error:
        runtime.verify()
    assert error.value.code == "calculation_release_unapproved"


@pytest.mark.parametrize("text", ['{"a":1,"a":1}', '{"a":1.0}', '{ "a":1}', '{"a":NaN}'])
def test_exact_canonical_json_rejects_duplicates_floats_spacing(text):
    with pytest.raises(ValueError):
        document(text)


def test_decimal_canonical_vectors():
    assert (
        canonical(normalize({"z": Decimal("-0.00"), "a": Decimal("1.2300")}))
        == '{"a":"1.23","z":"0"}'
    )
    assert digest("{}") == "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    with pytest.raises(ValueError):
        normalize(Decimal("Infinity"))
    with pytest.raises(ValueError):
        canonical({"amount": 0.1})


def test_unsafe_archive_rejected_before_extraction(tmp_path):
    path = tmp_path / "bad.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("../outside.py", "unsafe")
    with pytest.raises(ValueError, match="Unsafe"):
        release_module._validate_archive(path, {"files": []})
    assert not (tmp_path.parent / "outside.py").exists()


def test_dirty_source_requires_explicit_synthetic_qualification(tmp_path, monkeypatch):
    def git(command, **kwargs):
        return "a" * 40 if command[1] == "rev-parse" else " M services/api/app/test.py"

    monkeypatch.setattr(release_module.subprocess, "check_output", git)
    directory = tmp_path / "release"
    with pytest.raises(ValueError, match="Commit reviewed"):
        prepare_personal_release(directory)
    assert not directory.exists()


def test_committed_closure_rejects_missing_or_different_source(tmp_path, monkeypatch):
    source = tmp_path / "module.py"
    source.write_bytes(b"approved-source\n")
    identity = hashlib.sha1(b"blob 16\0approved-source\n").hexdigest()
    monkeypatch.setattr(
        release_module.subprocess,
        "check_output",
        lambda *args, **kwargs: f"100644 blob {identity}\tmodule.py\n",
    )
    release_module._verify_committed_source(tmp_path, "a" * 40, [source])
    source.write_bytes(b"changed-source\n")
    with pytest.raises(ValueError, match="differs"):
        release_module._verify_committed_source(tmp_path, "a" * 40, [source])
    monkeypatch.setattr(release_module.subprocess, "check_output", lambda *args, **kwargs: "")
    with pytest.raises(ValueError, match="uncommitted"):
        release_module._verify_committed_source(tmp_path, "a" * 40, [source])


def test_measured_verified_worker_api_deadline(qualified, request_model, monkeypatch):
    timings = {}
    for name in ("_runtime_inventory", "_inventory", "_validate_archive", "_hash_file"):
        original = getattr(release_module, name)

        def measured(*args, function=original, label=name, **kwargs):
            started = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                timings[label] = timings.get(label, 0) + time.perf_counter() - started

        monkeypatch.setattr(release_module, name, measured)
    started = time.perf_counter()
    qualified[2].verify()
    verify_seconds = time.perf_counter() - started
    started = time.perf_counter()
    result = qualified[2].calculate(request_model)
    calculate_seconds = time.perf_counter() - started
    assert result.status == "calculated"
    assert calculate_seconds < 30, "Strict verified execution exceeds its API deadline"
    print("\nstrict-verifier-seconds", round(verify_seconds, 3))
    print("verified-worker-seconds", round(calculate_seconds, 3))
    print(
        "aggregate-components-seconds", {name: round(value, 3) for name, value in timings.items()}
    )

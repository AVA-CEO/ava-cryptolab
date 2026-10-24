"""Explicit preview-only local releases. Never a fallback or financial save service."""

import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import threading
from pathlib import Path

from app.core.cfd_errors import CfdProblem

DEPENDENCIES = (
    "pydantic",
    "pydantic_core",
    "annotated_types",
    "typing_extensions",
    "typing_inspection",
)
DECIMAL_CONTEXT = {
    "precision": 160,
    "rounding": "ROUND_HALF_EVEN",
    "Emin": -999999,
    "Emax": 999999,
    "capitals": 1,
    "clamp": 0,
    "traps": ["DivisionByZero", "InvalidOperation", "Overflow"],
}


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    )


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    return {
        p.relative_to(root).as_posix(): digest(p.read_bytes())
        for p in sorted(root.rglob("*"))
        if p.is_file() and "__pycache__" not in p.parts
    }


def environment_identity():
    """No paths/usernames in the portable identity. Verify interpreter and stdlib bytes."""
    stdlib = Path(sysconfig.get_path("stdlib"))
    files = {}
    for p in stdlib.rglob("*"):
        relative = p.relative_to(stdlib)
        if {"site-packages", "test", "tests", "__pycache__"}.intersection(relative.parts):
            continue
        if p.is_file() and p.suffix in {".py", ".pyd", ".dll", ".zip", ".so"}:
            files[relative.as_posix()] = digest(p.read_bytes())
    native = Path(sys.base_prefix)
    for p in sorted(native.glob("*.dll")):
        files["runtime/" + p.name] = digest(p.read_bytes())
    for p in sorted((native / "DLLs").glob("*")):
        if p.is_file() and p.suffix in {".dll", ".pyd"}:
            files["DLLs/" + p.name] = digest(p.read_bytes())
    return {
        "implementation": sys.implementation.name,
        "version": sys.version.split()[0],
        "cache_tag": sys.implementation.cache_tag,
        "platform": sys.platform,
        "executable_sha256": digest(Path(sys.executable).read_bytes()),
        "stdlib_sha256": digest(canonical(files).encode()),
    }


def prepare_release(destination: Path):
    """Create NEW private artifacts only; this does not approve or run the release."""
    if destination.exists():
        raise ValueError(
            "Release directory already exists; preserve it and review before replacing."
        )
    destination.mkdir(parents=True)
    source = Path(__file__).resolve().parents[1]
    repo = Path(__file__).resolve().parents[4]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain", "--", "services/api/app"], cwd=repo, text=True
        ).strip()
    )
    payload = destination / "payload"
    (payload / "app").mkdir(parents=True)
    (payload / "app" / "__init__.py").write_text("", encoding="utf-8")
    for name in ("analytics", "schemas"):
        shutil.copytree(
            source / name, payload / "app" / name, ignore=shutil.ignore_patterns("__pycache__")
        )
    dependencies = []
    for name in DEPENDENCIES:
        distribution = importlib.metadata.distribution(name)
        for relative in distribution.files or ():
            if (
                Path(relative).is_absolute()
                or ".." in relative.parts
                or "__pycache__" in relative.parts
            ):
                continue
            path = Path(distribution.locate_file(relative))
            if path.is_file() and path.suffix not in {".pyc", ".exe"}:
                target = payload / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        dependencies.append({"name": name, "version": distribution.version})
    shutil.copyfile(Path(__file__).with_name("cfd_local_worker.py"), payload / "worker.py")
    manifest = {
        "schema_version": "ava-local-preview-build-v1",
        "profile": "local_personal",
        "purpose": "preview",
        "signature_status": "unsigned",
        "engine_id": "cfd-position-v1",
        "source_commit": commit,
        "source_dirty": dirty,
        "policy_version": "local-personal-incurred-once-v1",
        "canonicalizer_version": "local-personal-json-v1",
        "canonicalizer_sha256": digest(Path(__file__).with_name("cfd_canonical.py").read_bytes()),
        "python": environment_identity(),
        "dependencies": dependencies,
        "files": inventory(payload),
        "decimal": DECIMAL_CONTEXT,
    }
    text = canonical(manifest)
    (destination / "manifest.json").write_text(text, encoding="utf-8")
    return "sha256:" + digest(text.encode())


class LocalPreviewRuntime:
    """The exact digest must be explicitly supplied by the owner at startup."""

    def __init__(self, directory: Path, approved_digest: str, *, test_fixture=False):
        self.directory = directory.resolve()
        self.approved_digest = approved_digest
        self.test_fixture = test_fixture
        self.verify()

    def verify(self):
        try:
            text = (self.directory / "manifest.json").read_text(encoding="utf-8")
            value = json.loads(text)
            payload = self.directory / "payload"
            if (
                any(
                    p.is_symlink() or p.is_junction() or "__pycache__" in p.parts
                    for p in self.directory.rglob("*")
                )
                or (self.directory / "bytecode-disabled").exists()
            ):
                raise ValueError("Linked release")
            if (
                len(text) > 4 * 1024 * 1024
                or canonical(value) != text
                or "sha256:" + digest(text.encode()) != self.approved_digest
                or value["schema_version"] != "ava-local-preview-build-v1"
                or value["profile"] != "local_personal"
                or value["purpose"] != "preview"
                or (value["source_dirty"] and not self.test_fixture)
                or value["engine_id"] != "cfd-position-v1"
                or value["policy_version"] != "local-personal-incurred-once-v1"
                or value["canonicalizer_sha256"]
                != digest(Path(__file__).with_name("cfd_canonical.py").read_bytes())
                or value["decimal"] != DECIMAL_CONTEXT
                or value["python"] != environment_identity()
                or value["files"] != inventory(payload)
            ):
                raise ValueError("Release identity changed")
        except (OSError, ValueError, KeyError) as error:
            raise CfdProblem(
                503,
                "calculation_release_integrity_failure",
                "Local release verification failed; no values returned.",
            ) from error

    def preview(self, request):
        self.verify()
        from app.services.cfd_canonical import canonical_input

        body = canonical_input(request).encode()
        if len(body) > 4 * 1024 * 1024:
            raise CfdProblem(413, "request_too_large", "Calculation input exceeds its limit.")
        process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                "-X",
                "pycache_prefix=" + str(self.directory / "bytecode-disabled"),
                str(self.directory / "payload" / "worker.py"),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={key: os.environ[key] for key in ("SystemRoot", "WINDIR") if key in os.environ},
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        output = {}

        def read(pipe, key, limit):
            output[key] = pipe.read(limit + 1)
            if len(output[key]) > limit:
                process.kill()

        readers = [
            threading.Thread(target=read, args=(process.stdout, "out", 32 * 1024 * 1024)),
            threading.Thread(target=read, args=(process.stderr, "err", 65536)),
        ]
        for reader in readers:
            reader.start()
        try:
            process.stdin.write(body)
            process.stdin.close()
            process.wait(timeout=10)
        except (subprocess.TimeoutExpired, BrokenPipeError):
            process.kill()
            process.wait()
        finally:
            for reader in readers:
                reader.join(timeout=2)
        self.verify()
        if (
            process.returncode
            or output.get("err")
            or len(output.get("out", b"")) > 32 * 1024 * 1024
        ):
            raise CfdProblem(
                503,
                "calculation_execution_unavailable",
                "The bounded calculation could not complete.",
            )
        try:
            from app.schemas.cfd_positions import CfdPositionResult, PositionUnavailable

            raw = json.loads(output["out"])
            model = CfdPositionResult if raw.get("status") == "calculated" else PositionUnavailable
            return model.model_validate(raw)
        except (ValueError, KeyError) as error:
            raise CfdProblem(
                503, "calculation_execution_unavailable", "Invalid calculation output withheld."
            ) from error

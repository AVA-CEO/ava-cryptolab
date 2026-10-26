"""Qualified local-personal releases for NEW isolated practice persistence only.

Explicit digest approval is not a signature, broker authentication or a sandbox.
No ordinary app startup, GET or missing container may select this runtime.
"""

import ast
import hashlib
import importlib.metadata
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import sysconfig
import threading
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from email.parser import Parser
from pathlib import Path

from app.core.cfd_errors import CfdProblem
from app.schemas.cfd_personal_release import ApprovalRegistry
from app.schemas.cfd_positions import CfdPositionResult, PositionUnavailable
from app.services.cfd_local_release import DEPENDENCIES
from app.services.cfd_personal_codec import (
    SERIALIZER_SOURCE_IDENTITIES,
    canonical,
    digest,
    document,
    input_text,
    validate_release_manifest,
)

DECIMAL = {
    "prec": 160,
    "rounding": "ROUND_HALF_EVEN",
    "Emin": -999999,
    "Emax": 999999,
    "capitals": 1,
    "clamp": 0,
    "traps": ["DivisionByZero", "InvalidOperation", "Overflow"],
}
LIMITS = {
    "input_bytes": 4194304,
    "output_bytes": 33554432,
    "stderr_bytes": 65536,
    "execution_seconds": 10,
    "queue_wait_seconds": 2,
    "active_workers": 1,
    "queued_requests": 2,
    "api_seconds": 30,
}
MODES = {
    "forex": ["forex"],
    "cfd_linear": ["metals", "indices", "energy", "equities", "other"],
    "cfd_index": ["indices"],
}


def instant():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _fail(code="calculation_release_integrity_failure"):
    raise CfdProblem(503, code, "The approved local calculation release is unavailable.")


def _hash_file(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(65536), b""):
            result.update(data)
    return result.hexdigest()


def _linked(path):
    return path.is_symlink() or path.is_junction()


def _inventory(root):
    """All files count, including unexpected bytecode; no links may escape a release."""
    files, total = [], 0
    if _linked(root):
        raise ValueError("Linked artifact root")
    for current, directories, names in os.walk(root, followlinks=False):
        for name in directories:
            if _linked(Path(current) / name):
                raise ValueError("Linked artifact directory")
        for name in names:
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if _linked(path) or "__pycache__" in path.parts or path.suffix == ".pyc":
                raise ValueError("Linked or cached artifact")
            size = path.stat().st_size
            total += size
            if total > 256 * 1024 * 1024 or len(files) >= 20000:
                raise ValueError("Expanded payload exceeds bounds")
            files.append({"path": relative, "bytes": size, "sha256": _hash_file(path)})
    files.sort(key=lambda item: item["path"])
    if len({item["path"].casefold() for item in files}) != len(files):
        raise ValueError("Case-insensitive path collision")
    return {"schema_version": "ava-local-file-inventory-v1", "files": files}


def _write(path, value):
    text = canonical(value)
    path.write_text(text, encoding="utf-8")
    return digest(text)


def _read(path, limit):
    if _linked(path) or path.stat().st_size > limit:
        raise ValueError("Artifact type/size mismatch")
    return document(path.read_text(encoding="utf-8"), limit=limit)


def _runtime_inventory():
    stdlib = Path(sysconfig.get_path("stdlib"))
    records = []
    for current, directories, names in os.walk(stdlib, followlinks=False):
        directories[:] = [d for d in directories if d not in {"site-packages", "__pycache__"}]
        if any(_linked(Path(current) / name) for name in directories):
            raise ValueError("Linked standard-library directory")
        for name in names:
            path = Path(current) / name
            if path.suffix == ".pyc":
                continue
            if _linked(path):
                raise ValueError("Linked standard-library file")
            records.append(
                {
                    "path": "stdlib/" + path.relative_to(stdlib).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _hash_file(path),
                }
            )
    base = Path(sys.base_prefix)
    for path in sorted(base.glob("python*.zip")):
        if _linked(path):
            raise ValueError("Linked standard-library ZIP")
        records.append(
            {"path": "zip/" + path.name, "bytes": path.stat().st_size, "sha256": _hash_file(path)}
        )
    native_files = set(base.glob("*.dll")) | set(base.glob("python*.exe"))
    if (base / "DLLs").is_dir():
        native_files.update(p for p in (base / "DLLs").rglob("*") if p.is_file())
    for path in sorted(native_files):
        if _linked(path):
            raise ValueError("Linked runtime file")
        records.append(
            {
                "path": "native/" + path.relative_to(base).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _hash_file(path),
            }
        )
    records.append(
        {
            "path": "executable",
            "bytes": Path(sys.executable).stat().st_size,
            "sha256": _hash_file(Path(sys.executable)),
        }
    )
    return {
        "schema_version": "ava-local-runtime-inventory-v1",
        "files": sorted(records, key=lambda r: r["path"]),
    }


def _platform_identity():
    if sys.platform == "win32":
        version = sys.getwindowsversion()
        build = f"{version.major}.{version.minor}.{version.build}"
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        ) as key:
            build += "." + str(winreg.QueryValueEx(key, "UBR")[0])
        system = "windows"
    elif sys.platform == "linux":
        system, build = "linux", platform.release()
    else:
        raise ValueError("Local platform is not qualified")
    architecture = {"AMD64": "amd64", "x86_64": "amd64", "ARM64": "arm64", "aarch64": "arm64"}.get(
        platform.machine()
    )
    if architecture is None:
        raise ValueError("Unqualified architecture")
    return {
        "os": system,
        "architecture": architecture,
        "qualification_os_build": build,
        "compatibility_policy": "exact-recorded-environment-v1",
    }


def _closure(source, payload):
    pending = ["app.analytics.cfd_positions", "app.services.cfd_canonical"]
    seen = set()
    copied_sources = []
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        seen.add(module)
        if module.startswith(("app.database", "app.models", "app.main", "app.api")):
            raise ValueError("Financial worker cannot import persistence/application modules")
        relative = Path(*module.split(".")[1:]).with_suffix(".py")
        path = source / relative
        if not path.is_file() or _linked(path):
            raise ValueError("Unknown application import closure")
        target = payload / "app" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        copied_sources.append(path)
        package = target.parent
        while package != payload:
            (package / "__init__.py").touch(exist_ok=True)
            package = package.parent
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
                pending.append(node.module)
            if isinstance(node, ast.Import):
                pending.extend(item.name for item in node.names if item.name.startswith("app."))
    worker = payload / "worker" / "preview.py"
    worker.parent.mkdir()
    shutil.copyfile(Path(__file__).with_name("cfd_personal_worker.py"), worker)
    copied_sources.append(Path(__file__).with_name("cfd_personal_worker.py"))
    # The API serializes results/risk with this exact versioned codec. Retain it
    # as evidence, but do not import its HTTP-facing integrity checks in worker.
    codec = Path(__file__).with_name("cfd_personal_codec.py")
    shutil.copyfile(codec, payload / "app" / "services" / codec.name)
    copied_sources.append(codec)
    return copied_sources


def _verify_committed_source(repo, commit, sources):
    """Check measured source bytes, including untracked/ignored imports, against HEAD blobs."""
    paths = sorted(path.relative_to(repo).as_posix() for path in sources)
    tree = subprocess.check_output(
        ["git", "ls-tree", "-r", commit, "--", *paths], cwd=repo, text=True
    )
    recorded = {}
    for row in tree.splitlines():
        identity, name = row.split("\t", 1)
        mode, kind, object_hash = identity.split()
        if mode not in {"100644", "100755"} or kind != "blob":
            raise ValueError("Source must be an ordinary committed file")
        recorded[name] = object_hash
    if set(recorded) != set(paths):
        raise ValueError("Calculator import closure contains uncommitted files")
    for path in sources:
        content = path.read_bytes()
        object_hash = recorded[path.relative_to(repo).as_posix()]
        algorithm = hashlib.sha1 if len(object_hash) == 40 else hashlib.sha256
        if (
            algorithm(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
            != object_hash
        ):
            raise ValueError("Calculator source differs from its reviewed commit")


def _zip(path, root, paths):
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(paths):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (root / name).read_bytes())


def _validate_archive(path, expected):
    if path.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("Archive exceeds bounds")
    expected = {row["path"]: row for row in expected["files"]}
    seen, folded, expanded = set(), set(), 0
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            name = item.filename
            if (
                name in seen
                or name.casefold() in folded
                or Path(name).is_absolute()
                or ":" in name
                or "\\" in name
                or any(part in {"", ".", ".."} for part in name.split("/"))
                or stat.S_ISLNK(item.external_attr >> 16)
                or name not in expected
            ):
                raise ValueError("Unsafe archive path")
            expanded += item.file_size
            if expanded > 256 * 1024 * 1024 or len(seen) >= 20000:
                raise ValueError("Expanded archive exceeds bounds")
            row = expected[name]
            if item.file_size != row["bytes"]:
                raise ValueError("Archive size mismatch")
            from hashlib import sha256

            if sha256(archive.read(item)).hexdigest() != row["sha256"]:
                raise ValueError("Archive content mismatch")
            seen.add(name)
            folded.add(name.casefold())
    if seen != set(expected):
        raise ValueError("Incomplete archive")


def _execute(directory, body):
    if len(body) > LIMITS["input_bytes"]:
        raise ValueError("Calculation input exceeds bounds")
    process = subprocess.Popen(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-X",
            "pycache_prefix=" + str(directory / "no-bytecode"),
            str(directory / "payload" / "worker" / "preview.py"),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={k: os.environ[k] for k in ("SystemRoot", "WINDIR") if k in os.environ},
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    output = {}

    def read(pipe, name, limit):
        output[name] = pipe.read(limit + 1)
        if len(output[name]) > limit:
            process.kill()

    def write():
        try:
            process.stdin.write(body)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass

    threads = [
        threading.Thread(
            target=read, args=(process.stdout, "out", LIMITS["output_bytes"]), daemon=True
        ),
        threading.Thread(
            target=read, args=(process.stderr, "err", LIMITS["stderr_bytes"]), daemon=True
        ),
        threading.Thread(target=write, daemon=True),
    ]
    for thread in threads:
        thread.start()
    try:
        process.wait(timeout=LIMITS["execution_seconds"])
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    for thread in threads:
        thread.join(timeout=2)
    if (
        any(thread.is_alive() for thread in threads)
        or process.returncode
        or output.get("err")
        or len(output.get("out", b"")) > LIMITS["output_bytes"]
    ):
        raise ValueError("Bounded worker could not complete")
    import json

    raw = json.loads(output["out"])
    result = CfdPositionResult if raw.get("status") == "calculated" else PositionUnavailable
    return result.model_validate(raw)


def prepare_personal_release(destination: Path, *, test_fixture=False):
    """Stage/qualify NEW artifacts only. Does not register approval or save a position."""
    if destination.exists() or _linked(destination):
        raise ValueError("Preserve existing release directory")
    source = Path(__file__).resolve().parents[1]
    repo = Path(__file__).resolve().parents[4]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain", "--", "services/api/app"], cwd=repo, text=True
        ).strip()
    )
    if dirty and not test_fixture:
        raise ValueError("Commit reviewed calculator source before preparing a personal release")
    if shutil.disk_usage(destination.parent).free < 512 * 1024 * 1024:
        raise ValueError("Insufficient artifact staging headroom")
    destination.mkdir()
    payload = destination / "payload"
    payload.mkdir()
    copied_sources = _closure(source, payload)
    if not test_fixture:
        _verify_committed_source(repo, commit, copied_sources)
    dependencies = []
    for name in sorted(DEPENDENCIES):
        dist = importlib.metadata.distribution(name)
        normalized = re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower()
        copied, metadata_files = [], []
        for relative in dist.files or ():
            if (
                Path(relative).is_absolute()
                or ".." in relative.parts
                or "__pycache__" in relative.parts
            ):
                continue
            path = Path(dist.locate_file(relative))
            if path.is_file() and path.suffix not in {".pyc", ".exe"}:
                if _linked(path):
                    raise ValueError("Linked dependency")
                target = payload / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                record = {
                    "path": relative.as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _hash_file(path),
                }
                copied.append(record)
                if any(part.endswith(".dist-info") for part in relative.parts):
                    metadata_files.append(record)
        dep_inventory = {
            "schema_version": "ava-local-dependency-inventory-v1",
            "files": sorted(copied, key=lambda r: r["path"]),
        }
        metadata_inventory = {
            "schema_version": "ava-local-metadata-inventory-v1",
            "files": sorted(metadata_files, key=lambda r: r["path"]),
        }
        archive = destination / (normalized + ".zip")
        _zip(archive, payload, [item["path"] for item in copied])
        dependencies.append(
            {
                "name": normalized,
                "version": dist.version,
                "origin_kind": "retained_installed_tree",
                "distribution_metadata_sha256": _write(
                    destination / (normalized + ".metadata.json"), metadata_inventory
                ),
                "installed_files_sha256": _write(
                    destination / (normalized + ".files.json"), dep_inventory
                ),
                "retained_artifact_sha256": _hash_file(archive),
            }
        )
    dependencies.sort(key=lambda item: item["name"])
    files = _inventory(payload)
    files_hash = _write(destination / "files.json", files)
    archive = destination / "payload.zip"
    _zip(archive, payload, [item["path"] for item in files["files"]])
    if archive.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("Payload archive exceeds bounds")
    _validate_archive(archive, files)
    runtime = _runtime_inventory()
    runtime_hash = _write(destination / "runtime.json", runtime)
    import json

    from app.schemas.cfd_positions import CfdPositionRequest

    golden = CfdPositionRequest.model_validate(
        json.loads(
            (
                source.parents[0] / "tests" / "fixtures" / "cfd-position-costs.synthetic.json"
            ).read_text(encoding="utf-8")
        )
    )
    golden_text = input_text(golden)
    (destination / "golden.json").write_text(golden_text, encoding="utf-8")
    expected = {
        "state": "closed",
        "gross": "26",
        "net": "22",
        "risk": "20",
        "r": "1.1",
        "remaining": "0",
    }
    expected_hash = _write(destination / "expected.json", expected)
    result = _execute(destination, golden_text.encode())
    if result.status != "calculated" or result.state != expected["state"]:
        raise ValueError("Golden qualification failed")
    if any(
        Decimal(value) != actual
        for value, actual in [
            (expected["gross"], result.native.gross_pnl.raw),
            (expected["net"], result.native.net_pnl.raw),
            (expected["risk"], result.native.original_planned_risk.raw),
            (expected["r"], result.native.realized_r.raw),
            (expected["remaining"], result.remaining_lots),
        ]
    ):
        raise ValueError("Independent golden arithmetic failed")
    if _inventory(payload) != files:
        raise ValueError("Qualification changed payload")
    report = {
        "schema_version": "ava-local-qualification-v1",
        "status": "passed",
        "synthetic": True,
        "payload_archive_sha256": _hash_file(archive),
        "input_sha256": digest(golden_text),
        "expected_sha256": expected_hash,
        "runtime_inventory_sha256": runtime_hash,
        "platform": _platform_identity(),
        "canonicalizer_version": "local-personal-json-v1",
        "policy_version": "local-personal-incurred-once-v1",
    }
    build = {
        "descriptor_version": "ava-local-python-build-v1",
        "source": {
            "repository_id": "ava-cryptolab",
            "commit": commit,
            "calculator_tree_sha256": digest(
                canonical(
                    {
                        r["path"]: r["sha256"]
                        for r in files["files"]
                        if r["path"].startswith(("app/", "worker/"))
                    }
                )
            ),
            "dirty": dirty,
        },
        "platform": _platform_identity(),
        "python": {
            "implementation": "CPython",
            "version": platform.python_version(),
            "cache_tag": sys.implementation.cache_tag,
            "executable_sha256": _hash_file(Path(sys.executable)),
            "runtime_inventory_sha256": runtime_hash,
            "abi_tag": sysconfig.get_config_var("SOABI") or sys.implementation.cache_tag,
        },
        "payload": {
            "format": "zip",
            "archive_sha256": _hash_file(archive),
            "archive_bytes": archive.stat().st_size,
            "expanded_bytes": sum(r["bytes"] for r in files["files"]),
            "files_inventory_sha256": files_hash,
            "worker_entry": "worker/preview.py",
        },
        "dependencies": dependencies,
        "contracts": {
            "engine_id": "cfd-position-v1",
            "input": "cfd-position-v1",
            "result": "cfd-position-result-v1",
            "risk": "cfd-risk-anchor-v1",
            "snapshot": "instrument-specification-v1",
        },
        "canonicalizer_version": "local-personal-json-v1",
        "policy_version": "local-personal-incurred-once-v1",
        "decimal": DECIMAL,
        "limits": LIMITS,
        "supported_modes": MODES,
        "qualification": {
            "golden_set_sha256": digest(golden_text),
            "expected_results_sha256": expected_hash,
            "report_sha256": _write(destination / "qualification.json", report),
        },
    }
    manifest = validate_release_manifest(
        {
            "schema_version": "ava-local-python-release-v1",
            "release_id": "cfd-local-personal/1.0.0",
            "profile": "local_personal",
            "execution_kind": "host_pinned_python",
            "approval_scope": "local_personal",
            "signature_status": "unsigned",
            "created_at": instant(),
            "build": build,
        }
    )
    return "sha256:" + _write(destination / "manifest.json", manifest)


class PersonalRuntime:
    def __init__(self, directory: Path, approved_digest: str, *, test_fixture=False):
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", approved_digest):
            _fail("calculation_release_unapproved")
        if _linked(directory):
            _fail()
        self.directory, self.release_digest = directory.resolve(), approved_digest
        self.approved_digest = approved_digest
        self.test_fixture = test_fixture
        self._slots = threading.BoundedSemaphore(1)
        self._queue_lock = threading.Lock()
        self._requests = 0
        self._verify_artifacts()
        registry = self.directory / "approval-registry.json"
        if not registry.exists():
            at = instant()
            decision = {
                "sequence": 1,
                "release_digest": approved_digest,
                "old_state": None,
                "old_purposes": [],
                "new_state": "active",
                "purposes": ["preview", "accept_save"],
                "at": at,
                "approval_reference": "owner-approved-p3-disposable-practice",
            }
            entry = {
                "profile": "local_personal",
                "release_digest": approved_digest,
                "build_sha256": self.build_sha256,
                "release_manifest_sha256": approved_digest[7:],
                "manifest_location": str(self.directory / "manifest.json"),
                "payload_location": str(self.directory / "payload"),
                "runtime_root": sys.base_prefix,
                "state": "active",
                "purposes": ["preview", "accept_save"],
                "approval_reference": decision["approval_reference"],
                "approved_at": at,
            }
            _write(
                registry,
                {
                    "registry_version": "ava-local-release-registry-v1",
                    "generation": 1,
                    "entries": [entry],
                    "decisions": [decision],
                },
            )
        self.verify()

    def _verify_artifacts(self):
        try:
            directory = self.directory
            if (
                _linked(directory)
                or any(_linked(p) for p in directory.rglob("*"))
                or (directory / "no-bytecode").exists()
            ):
                raise ValueError("Linked/cached release")
            manifest = _read(directory / "manifest.json", 1024 * 1024)
            if digest(canonical(manifest)) != self.release_digest[7:]:
                raise ValueError("Manifest hash mismatch")
            manifest = validate_release_manifest(manifest)
            build = manifest["build"]
            if not self.test_fixture and build["platform"] != {
                **build["platform"],
                "os": "windows",
                "architecture": "amd64",
            }:
                raise ValueError("Only the reviewed Windows amd64 environment is qualified")
            if build["source"]["dirty"] and not self.test_fixture:
                raise ValueError("Uncommitted release is synthetic-test only")
            if build["platform"] != _platform_identity():
                raise ValueError("Platform qualification changed")
            actual_runtime = _runtime_inventory()
            if actual_runtime != _read(directory / "runtime.json", 4 * 1024 * 1024):
                raise ValueError("Interpreter runtime changed")
            actual_python = {
                "implementation": "CPython",
                "version": platform.python_version(),
                "cache_tag": sys.implementation.cache_tag,
                "executable_sha256": _hash_file(Path(sys.executable)),
                "runtime_inventory_sha256": digest(canonical(actual_runtime)),
                "abi_tag": sysconfig.get_config_var("SOABI") or sys.implementation.cache_tag,
            }
            if build["python"] != actual_python:
                raise ValueError("Python identity changed")
            files = _inventory(directory / "payload")
            files_by_path = {row["path"]: row for row in files["files"]}
            if (
                files != _read(directory / "files.json", 4 * 1024 * 1024)
                or digest(canonical(files)) != build["payload"]["files_inventory_sha256"]
            ):
                raise ValueError("Payload files changed")
            for relative, (host_path, loaded_hash) in SERIALIZER_SOURCE_IDENTITIES.items():
                expected = files_by_path.get(relative)
                if (
                    expected is None
                    or _linked(host_path)
                    or expected["sha256"] != loaded_hash
                    or _hash_file(host_path) != loaded_hash
                ):
                    raise ValueError("Loaded/host canonicalizer differs from the approved release")
            artifact = directory / "payload.zip"
            if (
                artifact.stat().st_size != build["payload"]["archive_bytes"]
                or _hash_file(artifact) != build["payload"]["archive_sha256"]
            ):
                raise ValueError("Payload archive changed")
            _validate_archive(artifact, files)
            if sum(row["bytes"] for row in files["files"]) != build["payload"]["expanded_bytes"]:
                raise ValueError("Expanded payload size changed")
            tree_hash = digest(
                canonical(
                    {
                        r["path"]: r["sha256"]
                        for r in files["files"]
                        if r["path"].startswith(("app/", "worker/"))
                    }
                )
            )
            if build["source"]["calculator_tree_sha256"] != tree_hash:
                raise ValueError("Source tree identity changed")
            for dep in build["dependencies"]:
                if dep["origin_kind"] != "retained_installed_tree":
                    raise ValueError("Dependency artifact kind has not been qualified")
                name = dep["name"]
                installed = _read(directory / (name + ".files.json"), 4 * 1024 * 1024)
                metadata = _read(directory / (name + ".metadata.json"), 4 * 1024 * 1024)
                if (
                    digest(canonical(installed)) != dep["installed_files_sha256"]
                    or digest(canonical(metadata)) != dep["distribution_metadata_sha256"]
                ):
                    raise ValueError("Dependency inventory changed")
                if any(files_by_path.get(row["path"]) != row for row in installed["files"]):
                    raise ValueError("Dependency no longer matches payload")
                actual_metadata = [
                    row
                    for row in installed["files"]
                    if any(part.endswith(".dist-info") for part in Path(row["path"]).parts)
                ]
                if metadata != {
                    "schema_version": "ava-local-metadata-inventory-v1",
                    "files": actual_metadata,
                }:
                    raise ValueError("Dependency metadata coverage mismatch")
                metadata_headers = [
                    row for row in actual_metadata if row["path"].endswith("/METADATA")
                ]
                if len(metadata_headers) != 1:
                    raise ValueError("One distribution identity is required")
                headers = Parser().parsestr(
                    (directory / "payload" / metadata_headers[0]["path"]).read_text(
                        encoding="utf-8"
                    )
                )
                if (
                    re.sub(r"[-_.]+", "-", headers["Name"]).lower() != dep["name"]
                    or headers["Version"] != dep["version"]
                ):
                    raise ValueError("Dependency version/identity mismatch")
                dep_archive = directory / (name + ".zip")
                if _hash_file(dep_archive) != dep["retained_artifact_sha256"]:
                    raise ValueError("Retained dependency changed")
                _validate_archive(dep_archive, installed)
            for name, expected in [
                ("golden.json", build["qualification"]["golden_set_sha256"]),
                ("expected.json", build["qualification"]["expected_results_sha256"]),
                ("qualification.json", build["qualification"]["report_sha256"]),
            ]:
                if _hash_file(directory / name) != expected:
                    raise ValueError("Qualification artifact changed")
            self.release_manifest = manifest
            self.build_sha256 = digest(canonical(build))
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
            _fail()

    def verify(self, purpose="accept_save"):
        self._verify_artifacts()
        try:
            registry = _read(self.directory / "approval-registry.json", 1024 * 1024)
            registry = ApprovalRegistry.model_validate(registry).model_dump(mode="json")
            if set(registry) != {"registry_version", "generation", "entries", "decisions"}:
                raise ValueError("Registry schema mismatch")
            if (
                registry["registry_version"] != "ava-local-release-registry-v1"
                or len(registry["entries"]) != 1
            ):
                raise ValueError("Registry identity mismatch")
            entry = registry["entries"][0]
            decisions = registry["decisions"]
            if registry["generation"] != len(decisions) or [
                d["sequence"] for d in decisions
            ] != list(range(1, len(decisions) + 1)):
                raise ValueError("Approval history mismatch")
            if (
                entry["profile"] != "local_personal"
                or entry["release_digest"] != self.release_digest
                or entry["build_sha256"] != self.build_sha256
                or entry["release_manifest_sha256"] != self.release_digest[7:]
                or entry["state"] != "active"
                or purpose not in entry["purposes"]
                or purpose not in {"preview", "accept_save"}
                or entry["manifest_location"] != str(self.directory / "manifest.json")
                or entry["payload_location"] != str(self.directory / "payload")
                or entry["runtime_root"] != sys.base_prefix
                or decisions[-1]["release_digest"] != self.release_digest
                or decisions[-1]["new_state"] != entry["state"]
                or decisions[-1]["purposes"] != entry["purposes"]
                or entry["approved_at"] < self.release_manifest["created_at"]
            ):
                raise ValueError("Release not approved for this purpose")
            self.approval = {
                "registry_generation": registry["generation"],
                "approval_reference": entry["approval_reference"],
                "approved_at": entry["approved_at"],
            }
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            _fail("calculation_release_unapproved")

    def preview(self, request, *, purpose="preview"):
        with self._queue_lock:
            if self._requests >= 1 + LIMITS["queued_requests"]:
                raise CfdProblem(
                    429, "calculation_capacity_exceeded", "The calculation worker is busy."
                )
            self._requests += 1
        acquired = self._slots.acquire(timeout=LIMITS["queue_wait_seconds"])
        try:
            if not acquired:
                raise CfdProblem(
                    429, "calculation_capacity_exceeded", "The calculation worker is busy."
                )
            self.verify(purpose)
            generation = dict(self.approval)
            try:
                result = _execute(self.directory, input_text(request).encode())
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
                _fail("calculation_execution_unavailable")
            self.verify(purpose)
            if generation != self.approval:
                _fail("calculation_release_unapproved")
            if result.status == "calculated" and (
                result.position_reference != request.position_reference
                or result.snapshot_sha256 != request.trade.snapshot.content_sha256
                or result.as_of != request.as_of
            ):
                _fail("calculation_execution_unavailable")
            return result
        finally:
            if acquired:
                self._slots.release()
            with self._queue_lock:
                self._requests -= 1

    def calculate(self, request, *, purpose="accept_save"):
        return self.preview(request, purpose=purpose)

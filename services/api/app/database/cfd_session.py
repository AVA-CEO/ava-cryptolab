"""New, process-registered disposable targets only; no caller database path."""

import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import gettempdir, mkdtemp
from weakref import WeakSet

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

_OWNED = WeakSet()
_MINT = object()


class CfdTargetRejected(RuntimeError):
    pass


def _identity(path):
    value = path.stat(follow_symlinks=False)
    return value.st_dev, value.st_ino


def _link(path):
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


class CfdWorkspace:
    def __init__(self, token):
        if token is not _MINT:
            raise CfdTargetRejected("Use fresh disposable provisioning only")
        self.directory = Path(mkdtemp(prefix="ava-cfd-practice-")).resolve()
        self.path = self.directory / "cfd-practice.db"
        self._directory_identity = _identity(self.directory)
        self._file_identity = None
        self.active, self.ready = True, False
        _OWNED.add(self)
        url = URL.create("sqlite", database=self.path.as_posix())
        self.check_target(url)
        self.engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 5})

        @event.listens_for(self.engine, "do_connect")
        def before_connect(dialect, record, args, params):
            self.check_target(self.engine.url)
            if not args or Path(args[0]) != self.path or params.get("uri"):
                raise CfdTargetRejected("Unexpected SQLite connection arguments")

        @event.listens_for(self.engine, "checkout")
        def checked_out(dbapi, record, proxy):
            self.check_target(self.engine.url)
            dbapi.execute("PRAGMA foreign_keys=ON")
            if self.ready:
                # All serving connections are read-only, including pooled ones.
                dbapi.execute("PRAGMA query_only=ON")

    def check_target(self, url):
        # Compare URL/path strings BEFORE resolving/stat-ing any caller target.
        if (
            self not in _OWNED
            or not self.active
            or url.drivername != "sqlite"
            or not url.database
            or url.query
            or not Path(url.database).is_absolute()
            or Path(url.database) != self.path
        ):
            raise CfdTargetRejected("Unregistered CFD target")
        if (
            _link(self.directory)
            or self.directory.parent != Path(gettempdir()).resolve()
            or not self.directory.name.startswith("ava-cfd-practice-")
            or self.directory.resolve() != self.directory
            or _identity(self.directory) != self._directory_identity
            or _link(self.path)
        ):
            raise CfdTargetRejected("CFD directory identity changed")
        if self._file_identity is not None and _identity(self.path) != self._file_identity:
            raise CfdTargetRejected("CFD database identity changed")

    @contextmanager
    def read_session(self):
        if not self.ready:
            raise CfdTargetRejected("CFD workspace is not provisioned")
        self.check_target(self.engine.url)
        with self.engine.connect() as connection:
            # SQLite legacy transaction mode does not BEGIN on SELECT. Explicitly
            # hold one read snapshot for the head, children, hashes and response.
            connection.exec_driver_sql("BEGIN")
            if connection.exec_driver_sql("PRAGMA query_only").scalar() != 1:
                raise CfdTargetRejected("CFD serving connection must be read-only")
            if connection.exec_driver_sql("PRAGMA foreign_keys").scalar() != 1:
                raise CfdTargetRejected("CFD foreign keys must be enabled")
            revision = connection.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar()
            if revision != "0004":
                raise CfdTargetRejected("CFD schema revision is not 0004")
            with Session(bind=connection) as session:
                yield session

    def cleanup(self):
        self.engine.dispose()
        # Verify the exact minted absolute directory before recursive deletion.
        if (
            _link(self.directory)
            or self.directory.resolve() != self.directory
            or _identity(self.directory) != self._directory_identity
        ):
            raise CfdTargetRejected("Preserve changed disposable directory")
        for child in self.directory.rglob("*"):
            if _link(child) or not child.resolve().is_relative_to(self.directory):
                raise CfdTargetRejected("Preserve linked disposable diagnostic directory")
        self.active = False
        _OWNED.discard(self)
        shutil.rmtree(self.directory)


def provision(workspace, *, include_read_fixtures=True):
    """Explicit runner provisioning, never API startup; only newly minted DBs."""
    from alembic import command
    from alembic.config import Config

    from app.services.cfd_read_fixtures import seed_read_fixtures
    from app.services.cfd_samples import seed_samples

    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("prepend_sys_path", str(root))
    workspace.check_target(workspace.engine.url)
    with workspace.engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0004")
    with workspace.engine.begin() as connection:
        with Session(bind=connection) as session, session.begin():
            workspace.samples = seed_samples(session)
            if include_read_fixtures:
                seed_read_fixtures(workspace, session)
        if connection.exec_driver_sql("PRAGMA integrity_check").scalar() != "ok":
            raise CfdTargetRejected("New synthetic fixture database failed integrity validation")
        if connection.exec_driver_sql("PRAGMA foreign_key_check").all():
            raise CfdTargetRejected("New synthetic fixture database failed foreign key validation")
    workspace._file_identity = _identity(workspace.path)
    workspace.ready = True


@contextmanager
def new_cfd_workspace():
    workspace = CfdWorkspace(_MINT)
    try:
        provision(workspace)
        yield workspace
    except BaseException as error:
        workspace.engine.dispose()
        workspace.active = False
        _OWNED.discard(workspace)
        # Preserve this new synthetic directory for failure diagnosis.
        error.add_note(f"New synthetic CFD diagnostics retained at {workspace.directory}")
        raise
    else:
        workspace.cleanup()

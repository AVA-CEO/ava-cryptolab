"""A separately minted P3 workspace. Existing serving engines remain read-only."""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.database.cfd_session import _MINT, _OWNED, CfdTargetRejected, CfdWorkspace, provision


class PersonalWorkspace(CfdWorkspace):
    def __init__(self):
        super().__init__(_MINT)
        self.personal_writes = False
        self.write_engine = create_engine(
            self.engine.url, connect_args={"check_same_thread": False, "timeout": 5}
        )

        @event.listens_for(self.write_engine, "do_connect")
        def before_connect(dialect, record, args, params):
            self.check_target(self.write_engine.url)
            if not args or Path(args[0]) != self.path or params.get("uri"):
                raise CfdTargetRejected("Unexpected P3 connection arguments")

        @event.listens_for(self.write_engine, "checkout")
        def checked_out(dbapi, record, proxy):
            self.check_target(self.write_engine.url)
            if not self.ready or not self.personal_writes:
                raise CfdTargetRejected("P3 writes are not enabled for this new workspace")
            dbapi.execute("PRAGMA foreign_keys=ON")
            dbapi.execute("PRAGMA query_only=OFF")

    @contextmanager
    def write_session(self):
        if not self.ready or not self.personal_writes:
            raise CfdTargetRejected("Only a newly qualified P3 workspace may write")
        self.check_target(self.write_engine.url)
        with self.write_engine.connect() as connection:
            try:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                if connection.exec_driver_sql("PRAGMA foreign_keys").scalar() != 1:
                    raise CfdTargetRejected("P3 foreign keys must be enabled")
                if (
                    connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
                    != "0004"
                ):
                    raise CfdTargetRejected("P3 requires the disposable 0004 schema")
                with Session(bind=connection) as session:
                    yield session
                    session.flush()
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.exec_driver_sql("PRAGMA query_only=ON")

    def cleanup(self):
        self.write_engine.dispose()
        super().cleanup()


@contextmanager
def new_personal_workspace():
    workspace = PersonalWorkspace()
    try:
        # No old session is opened; the ledger starts empty, with new synthetic identities.
        provision(workspace, include_read_fixtures=False)
        workspace.personal_writes = True
        yield workspace
    except BaseException:
        workspace.write_engine.dispose()
        workspace.engine.dispose()
        workspace.active = False
        _OWNED.discard(workspace)
        raise
    else:
        workspace.cleanup()

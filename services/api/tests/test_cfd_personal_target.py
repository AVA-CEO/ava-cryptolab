"""Writer target checks reject unapproved URL strings before any DBAPI connection."""

from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.engine import URL

from app.database.cfd_personal_session import PersonalWorkspace, new_personal_workspace
from app.database.cfd_session import CfdTargetRejected


def test_personal_workspace_cannot_take_a_database_path():
    with pytest.raises(TypeError):
        PersonalWorkspace("not-an-approved-target.db")


@pytest.mark.parametrize("kind", ["normal", "relative", "memory", "query", "other_driver"])
def test_write_target_rejected_before_connection(kind):
    with new_personal_workspace() as workspace:
        original = workspace.write_engine.url
        targets = {
            # Constructing this string does not inspect/open the protected file.
            "normal": URL.create("sqlite", database=str(Path.cwd() / "services/api/ava.db")),
            "relative": URL.create("sqlite", database="ava.db"),
            "memory": URL.create("sqlite", database=":memory:"),
            "query": original.update_query_dict({"mode": "rwc"}),
            "other_driver": URL.create("postgresql", database="not-a-test-target"),
        }
        attempts = []

        def connect(*args):
            attempts.append(True)
            raise AssertionError("An unapproved DBAPI connection was attempted")

        event.listen(workspace.write_engine, "do_connect", connect)
        workspace.write_engine.url = targets[kind]
        try:
            with pytest.raises(CfdTargetRejected):
                with workspace.write_session():
                    pytest.fail("An unapproved writer was opened")
            assert attempts == []
        finally:
            workspace.write_engine.url = original
            event.remove(workspace.write_engine, "do_connect", connect)


def test_disabled_writer_is_rejected_and_approved_writer_restores_read_only():
    with new_personal_workspace() as workspace:
        workspace.personal_writes = False
        with pytest.raises(CfdTargetRejected):
            with workspace.write_session():
                pytest.fail("Disabled writes must fail before connecting")
        workspace.personal_writes = True
        returned = []

        def checked_in(connection, record):
            if connection is not None:
                returned.append(connection.execute("PRAGMA query_only").fetchone()[0])

        event.listen(workspace.write_engine, "checkin", checked_in)
        with workspace.write_session() as session:
            assert session.connection().exec_driver_sql("PRAGMA query_only").scalar() == 0
        assert returned == [1]
        with workspace.read_session() as session:
            assert session.connection().exec_driver_sql("PRAGMA query_only").scalar() == 1

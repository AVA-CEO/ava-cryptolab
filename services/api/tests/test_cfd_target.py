"""Test migration routing without ever opening a protected database."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import pytest
import sqlalchemy
from alembic import command
from sqlalchemy.engine import make_url

from app.database.cfd_target import require_disposable_cfd
from app.database.rehearsal import migration_config


@pytest.mark.parametrize("operation", ["check", "current", "upgrade", "downgrade", "stamp"])
@pytest.mark.parametrize("target", ["sqlite:///ava.db", "sqlite:///services/api/ava.db"])
def test_normal_target_rejected_before_engine_creation(monkeypatch, operation, target):
    config = migration_config()
    config.attributes["database_url"] = target

    def forbidden(*args, **kwargs):
        pytest.fail("A rejected target must not create an engine or open a database")

    monkeypatch.setattr(sqlalchemy, "create_engine", forbidden)
    args = ("0003",) if operation in {"upgrade", "downgrade", "stamp"} else ()
    with pytest.raises(RuntimeError, match="CFD migration"):
        getattr(command, operation)(config, *args)


def test_supplied_protected_connection_is_rejected_without_use():
    config = migration_config()
    # No real connection exists: any method access other than engine.url fails.
    config.attributes["connection"] = SimpleNamespace(
        engine=SimpleNamespace(url=make_url("sqlite:///ava.db"))
    )
    with pytest.raises(RuntimeError, match="CFD migration"):
        command.check(config)


def test_disposable_cli_style_commands_without_destination(tmp_path):
    config = migration_config()
    path = tmp_path / "command-check.db"
    config.attributes["database_url"] = f"sqlite:///{path.as_posix()}"
    command.upgrade(config, "head")
    command.current(config)
    command.heads(config)
    command.check(config)


def test_guard_does_not_create_allowed_file(tmp_path):
    path = tmp_path / "not-created.db"
    assert require_disposable_cfd(make_url(f"sqlite:///{path.as_posix()}")) == path.resolve()
    assert not path.exists()


def test_absolute_normal_path_is_rejected_without_access():
    # Construct only the path string. Do not stat, connect or read the journal.
    path = Path(__file__).absolute().parents[1] / "ava.db"
    with pytest.raises(RuntimeError, match="CFD migration"):
        require_disposable_cfd(make_url(f"sqlite:///{path.as_posix()}"))


def test_fresh_accounts_bootstrap_stays_at_0003_and_rejects_cfd_upgrade():
    with TemporaryDirectory(prefix="ava-accounts-") as directory:
        config = migration_config()
        path = Path(directory) / "new-synthetic-practice.db"
        config.attributes["database_url"] = f"sqlite:///{path.as_posix()}"
        command.upgrade(config, "0003")
        before = path.read_bytes()
        for operation in [command.check, lambda c: command.upgrade(c, "head")]:
            with pytest.raises(RuntimeError, match="CFD migration"):
                operation(config)
            assert path.read_bytes() == before

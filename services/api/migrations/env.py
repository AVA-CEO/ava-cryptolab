from alembic import context
from sqlalchemy import create_engine, event, pool

from app.core.config import get_settings
from app.database.session import Base
from app.models import TradingAccount  # noqa: F401

target_metadata = Base.metadata


def run_online(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        transactional_ddl=True if connection.dialect.name == "sqlite" else None,
    )
    with context.begin_transaction():
        # Also protect externally supplied SQLAlchemy connections using sqlite3's
        # legacy transaction mode: DDL must not escape rollback.
        if connection.dialect.name == "sqlite":
            raw = connection.connection.driver_connection
            if not raw.in_transaction:
                connection.exec_driver_sql("BEGIN")
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=context.config.attributes.get("database_url") or get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get("connection") is not None:
    # Rehearsals supply a connection; never fall back to the personal database URL.
    run_online(context.config.attributes["connection"])
else:
    engine = create_engine(get_settings().database_url, poolclass=pool.NullPool)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def explicit_transactions(dbapi_connection, connection_record):
            dbapi_connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def begin(connection):
            connection.exec_driver_sql("BEGIN")

    try:
        with engine.connect() as connection:
            run_online(connection)
    finally:
        engine.dispose()

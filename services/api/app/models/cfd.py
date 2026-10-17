"""Ten ledger models, no CFD persistence API or calculator integration."""

from sqlalchemy import event, inspect

from app.database.cfd_guards_v1 import install
from app.database.cfd_schema_v1 import NAMES, tables
from app.database.session import Base

TABLES = tables(Base.metadata)


class CfdPosition(Base):
    __table__ = TABLES["cfd_positions"]


class CfdRevision(Base):
    __table__ = TABLES["cfd_revisions"]


class CfdPositionHead(Base):
    __table__ = TABLES["cfd_position_heads"]


class CfdEventKey(Base):
    __table__ = TABLES["cfd_event_keys"]


class CfdExecution(Base):
    __table__ = TABLES["cfd_executions"]


class CfdAdjustment(Base):
    __table__ = TABLES["cfd_adjustments"]


class CfdConversion(Base):
    __table__ = TABLES["cfd_conversions"]


class CfdBrokerEvidence(Base):
    __table__ = TABLES["cfd_broker_evidence"]


class CfdCalculation(Base):
    __table__ = TABLES["cfd_calculations"]


class CfdRequest(Base):
    __table__ = TABLES["cfd_requests"]


@event.listens_for(Base.metadata, "after_create")
def guards_after_create(metadata, connection, **kwargs):
    created = {table.name for table in kwargs.get("tables", ())}
    if created.intersection(NAMES):
        if not set(NAMES).issubset(inspect(connection).get_table_names()):
            raise RuntimeError("Create the complete disposable CFD schema before installing guards")
        install(connection, metadata)

"""Add the versioned CFD ledger on explicitly disposable targets only."""

import sqlalchemy as sa
from alembic import op

from app.database.cfd_guards_v1 import install, remove
from app.database.cfd_schema_v1 import NAMES, migration_tables
from app.database.cfd_target import require_disposable_cfd

TABLES = migration_tables()

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    require_disposable_cfd(connection.engine.url)
    for name in NAMES:
        TABLES[name].create(connection)
    install(connection, TABLES["cfd_positions"].metadata)


def downgrade():
    connection = op.get_bind()
    require_disposable_cfd(connection.engine.url)
    if any(
        connection.execute(sa.select(sa.func.count()).select_from(TABLES[n])).scalar()
        for n in NAMES
    ):
        raise RuntimeError("Downgrade refused: CFD ledger contains retained evidence.")
    remove(connection, TABLES["cfd_positions"].metadata)
    for name in reversed(NAMES):
        TABLES[name].drop(connection)

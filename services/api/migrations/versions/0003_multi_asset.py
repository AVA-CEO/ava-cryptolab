"""Add multi-asset identity and provenance without altering legacy records."""

import sqlalchemy as sa
from alembic import op

from app.database.integrity import install_snapshot_guards_v1

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

NEW_TABLES = (
    "journal_accounts",
    "instruments",
    "instrument_snapshots",
    "broker_import_batches",
    "trade_contexts",
)


def upgrade():
    op.create_table(
        "journal_accounts",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("broker", sa.String(100), nullable=False),
        sa.Column("platform", sa.String(10), nullable=False),
        sa.Column("server", sa.String(100)),
        sa.Column("broker_account_ref", sa.String(100)),
        sa.Column("reporting_currency", sa.String(12), nullable=False),
        sa.Column("settlement_currency", sa.String(12), nullable=False),
        sa.UniqueConstraint("id", "broker", "settlement_currency", name="uq_account_scope"),
        sa.UniqueConstraint(
            "broker", "platform", "server", "broker_account_ref", name="uq_broker_account"
        ),
        sa.CheckConstraint("platform IN ('manual','bybit','mt5')", name="ck_account_platform"),
        sa.CheckConstraint("platform != 'mt5' OR server IS NOT NULL", name="ck_mt5_server"),
        sa.CheckConstraint(
            "length(trim(name)) > 0 AND length(trim(broker)) > 0", name="ck_account_labels"
        ),
        sa.CheckConstraint(
            "length(reporting_currency) BETWEEN 2 AND 12 "
            "AND reporting_currency = upper(reporting_currency) "
            "AND length(settlement_currency) BETWEEN 2 AND 12 "
            "AND settlement_currency = upper(settlement_currency)",
            name="ck_account_currencies",
        ),
    )
    op.create_index(
        "uq_account_without_server",
        "journal_accounts",
        ["broker", "platform", "broker_account_ref"],
        unique=True,
        sqlite_where=sa.text("server IS NULL"),
        postgresql_where=sa.text("server IS NULL"),
    )
    op.create_table(
        "instruments",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("broker", sa.String(100), nullable=False),
        sa.Column("venue", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(60), nullable=False),
        sa.Column("product", sa.String(32), nullable=False),
        sa.Column("market_category", sa.String(12), nullable=False),
        sa.Column("settlement_currency", sa.String(12), nullable=False),
        sa.UniqueConstraint("id", "broker", "settlement_currency", name="uq_instrument_scope"),
        sa.UniqueConstraint("broker", "venue", "symbol", "product", name="uq_instrument_identity"),
        sa.CheckConstraint(
            "(market_category = 'crypto' "
            "AND product IN ('crypto_spot','crypto_linear_futures')) OR "
            "(market_category IN ('forex','metals','indices','energy','equities','other') "
            "AND product IN ('cfd','tradfi_perpetual'))",
            name="ck_instrument_product_market",
        ),
    )
    op.create_table(
        "instrument_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instrument_id", sa.String(100), nullable=False),
        sa.Column("broker", sa.String(100), nullable=False),
        sa.Column("settlement_currency", sa.String(12), nullable=False),
        sa.Column("specification", sa.JSON, nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["instrument_id", "broker", "settlement_currency"],
            ["instruments.id", "instruments.broker", "instruments.settlement_currency"],
            ondelete="RESTRICT",
            name="fk_snapshot_instrument",
        ),
        sa.UniqueConstraint(
            "id", "instrument_id", "broker", "settlement_currency", name="uq_snapshot_scope"
        ),
        sa.UniqueConstraint("instrument_id", "content_sha256", name="uq_snapshot_content"),
        sa.CheckConstraint("length(content_sha256) = 64", name="ck_snapshot_hash"),
    )
    op.create_table(
        "broker_import_batches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("adapter_version", sa.String(100), nullable=False),
        sa.Column("source_kind", sa.String(20), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["journal_accounts.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("id", "account_id", name="uq_import_account"),
        sa.UniqueConstraint(
            "account_id", "adapter_version", "source_sha256", name="uq_import_source"
        ),
        sa.CheckConstraint("length(source_sha256) = 64", name="ck_import_hash"),
        sa.CheckConstraint(
            "source_kind IN ('statement','broker_api','terminal','manual')", name="ck_import_kind"
        ),
    )
    op.create_table(
        "trade_contexts",
        sa.Column("trade_id", sa.String(36), primary_key=True),
        sa.Column("account_id", sa.String(100), nullable=False),
        sa.Column("instrument_id", sa.String(100), nullable=False),
        sa.Column("snapshot_id", sa.String(36), nullable=False),
        sa.Column("broker", sa.String(100), nullable=False),
        sa.Column("settlement_currency", sa.String(12), nullable=False),
        sa.Column("import_batch_id", sa.String(36)),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["account_id", "broker", "settlement_currency"],
            [
                "journal_accounts.id",
                "journal_accounts.broker",
                "journal_accounts.settlement_currency",
            ],
            ondelete="RESTRICT",
            name="fk_context_account",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "instrument_id", "broker", "settlement_currency"],
            [
                "instrument_snapshots.id",
                "instrument_snapshots.instrument_id",
                "instrument_snapshots.broker",
                "instrument_snapshots.settlement_currency",
            ],
            ondelete="RESTRICT",
            name="fk_context_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id", "account_id"],
            ["broker_import_batches.id", "broker_import_batches.account_id"],
            ondelete="RESTRICT",
            name="fk_context_import",
        ),
    )
    op.create_index("ix_trade_contexts_account_id", "trade_contexts", ["account_id"])
    install_snapshot_guards_v1(op.get_bind())


def downgrade():
    # Refuse loss of adopted accounts/snapshots/provenance, even if unreferenced.
    for name in NEW_TABLES:
        if op.get_bind().execute(sa.text(f"SELECT 1 FROM {name} LIMIT 1")).first():
            raise RuntimeError(
                "Downgrade refused: multi-asset data exists. Restore a reviewed backup."
            )
    for name in reversed(NEW_TABLES):
        op.drop_table(name)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION ava_snapshot_immutable_v1()")

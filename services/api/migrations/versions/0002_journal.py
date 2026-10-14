"""Trade plans and partial exit executions."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def amount(precision=28, scale=10):
    return sa.String(80) if op.get_bind().dialect.name == "sqlite" else sa.Numeric(precision, scale)


def upgrade():
    with op.batch_alter_table("trading_accounts") as batch:
        batch.alter_column("currency", existing_type=sa.String(3), type_=sa.String(4))
        batch.alter_column("opening_balance", existing_type=sa.Numeric(20, 8), type_=amount(20, 8))
    op.create_table(
        "trades",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pair", sa.String(30), nullable=False),
        sa.Column("exchange", sa.String(80), nullable=False),
        sa.Column("currency", sa.String(4), nullable=False),
        sa.Column("market", sa.String(10), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("entry_at", sa.DateTime(timezone=True), nullable=False),
        *[
            sa.Column(name, amount(), nullable=name in ("stop_loss", "take_profit"))
            for name in (
                "entry_price",
                "quantity",
                "stop_loss",
                "take_profit",
                "entry_fees",
                "funding",
            )
        ],
        sa.Column("leverage", amount(10, 2), nullable=False),
        sa.Column("margin_type", sa.String(10)),
        sa.Column("strategy", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text, nullable=False),
        sa.Column("mistakes", sa.String(1000), nullable=False),
        sa.Column("emotion_before", sa.String(100), nullable=False),
        sa.Column("emotion_after", sa.String(100), nullable=False),
        sa.Column("lessons", sa.Text, nullable=False),
        sa.Column("screenshot", sa.String(100)),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "trade_exits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "trade_id",
            sa.String(36),
            sa.ForeignKey("trades.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("exit_at", sa.DateTime(timezone=True), nullable=False),
        *[sa.Column(name, amount(), nullable=False) for name in ("price", "quantity", "fees")],
    )
    op.create_index("ix_trade_exits_trade_id", "trade_exits", ["trade_id"])


def downgrade():
    op.drop_table("trade_exits")
    op.drop_table("trades")
    with op.batch_alter_table("trading_accounts") as batch:
        batch.alter_column("currency", existing_type=sa.String(4), type_=sa.String(3))
        batch.alter_column("opening_balance", existing_type=amount(20, 8), type_=sa.Numeric(20, 8))

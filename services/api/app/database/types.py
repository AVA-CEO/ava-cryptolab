from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.types import TypeDecorator


class ExactDecimal(TypeDecorator):
    """PostgreSQL NUMERIC; lossless decimal text in SQLite (which has no decimal type)."""

    impl = Numeric
    cache_ok = True

    def __init__(self, precision=28, scale=10):
        self.precision = precision
        self.scale = scale
        super().__init__()

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(80))
        return dialect.type_descriptor(Numeric(self.precision, self.scale))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value) if dialect.name == "sqlite" else Decimal(value)

    def process_result_value(self, value, dialect):
        return Decimal(value) if value is not None else None

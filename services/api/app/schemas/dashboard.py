from typing import Literal

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    mode: Literal["empty"] = "empty"
    currency: str = "USD"
    recorded_equity: str | None = None
    realized_pnl: str | None = None
    total_trades: int = 0
    win_rate: float | None = None
    profit_factor: float | None = None
    message: str = "Create a trading account and record trades in Phase 2."

"""Option A: deliberately unavailable. No host imports, runtime probe or execution."""

from typing import Protocol

from app.core.cfd_errors import CfdProblem
from app.schemas.cfd_positions import CfdPositionRequest


class PreviewRuntime(Protocol):
    def preview(self, request: CfdPositionRequest) -> None: ...


class UnavailableRuntime:
    def preview(self, request: CfdPositionRequest) -> None:
        raise CfdProblem(
            503,
            "calculation_runtime_unavailable",
            "An approved container calculation release is unavailable. "
            "No calculation was run or saved.",
        )

"""B3A status/preview only. No positions, saved reads or host fallback."""

from fastapi import APIRouter, Request

from app.core.cfd_errors import CfdProblem
from app.schemas.cfd_api import CfdPreviewCommandV1, CfdPreviewResponseV1, CfdStatusV1
from app.services.cfd_preview import bind_preview

router = APIRouter(prefix="/api/v1/cfd", tags=["Isolated CFD practice boundary"])


@router.get("/status", response_model=CfdStatusV1)
def status(request: Request):
    with request.app.state.workspace.read_session():
        return CfdStatusV1()


@router.post("/preview", response_model=CfdPreviewResponseV1)
def preview(command: CfdPreviewCommandV1, request: Request):
    with request.app.state.workspace.read_session() as session:
        validated = bind_preview(session, command)
    # No DB transaction/connection is held while calling the provider boundary.
    request.app.state.runtime.preview(validated)
    # Even an accidentally returning provider cannot manufacture a B3A success.
    raise CfdProblem(
        503,
        "calculation_runtime_unavailable",
        "An approved container calculation release is unavailable. "
        "No calculation was run or saved.",
    )

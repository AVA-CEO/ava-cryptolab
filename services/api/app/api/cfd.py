"""B3A status/preview only. No positions, saved reads or host fallback."""

from fastapi import APIRouter, Request

from app.core.cfd_errors import CfdProblem
from app.schemas.cfd_api import (
    CfdLocalPreviewV2,
    CfdLocalStatusV2,
    CfdPreviewCommandV1,
    CfdPreviewResponseV1,
    CfdStatusV1,
)
from app.services.cfd_preview import bind_preview

router = APIRouter(prefix="/api/v1/cfd", tags=["Isolated CFD practice boundary"])
local_router = APIRouter(prefix="/api/v1/cfd", tags=["Explicit local preview examples"])


@router.get("/status", response_model=CfdStatusV1 | CfdLocalStatusV2)
def status(request: Request):
    with request.app.state.workspace.read_session():
        if getattr(request.app.state, "local_preview", False):
            request.app.state.runtime.verify()
            return {
                "schema_version": "cfd-status-v2",
                "execution_kind": "local_personal",
                "preview_available": True,
                "can_create": False,
                "release_digest": request.app.state.runtime.approved_digest,
            }
        return CfdStatusV1()


@local_router.get("/examples")
def examples(request: Request):
    if not getattr(request.app.state, "local_preview", False):
        raise CfdProblem(404, "resource_not_found", "Preview examples are unavailable.")
    with request.app.state.workspace.read_session():
        return request.app.state.workspace.samples["previews"]


@router.post("/preview", response_model=CfdPreviewResponseV1 | CfdLocalPreviewV2)
def preview(command: CfdPreviewCommandV1, request: Request):
    with request.app.state.workspace.read_session() as session:
        validated = bind_preview(session, command)
    # No DB transaction/connection is held while calling the provider boundary.
    if getattr(request.app.state, "local_preview", False):
        runtime = request.app.state.runtime
        if command.release_digest and command.release_digest != runtime.approved_digest:
            raise CfdProblem(422, "release_mismatch", "Use the selected approved preview release.")
        result = runtime.preview(validated)
        return {
            "schema_version": "cfd-preview-response-v2",
            "saved": False,
            "can_create": False,
            "execution_kind": "local_personal",
            "signature_status": "unsigned",
            "accepted_calculation": False,
            "broker_authenticated": False,
            "release_digest": runtime.approved_digest,
            "result": result,
        }
    request.app.state.runtime.preview(validated)
    # Even an accidentally returning provider cannot manufacture a B3A success.
    raise CfdProblem(
        503,
        "calculation_runtime_unavailable",
        "An approved container calculation release is unavailable. "
        "No calculation was run or saved.",
    )

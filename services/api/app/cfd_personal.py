"""Explicitly qualified NEW local practice app. No ordinary journal target is accepted."""

from secrets import token_bytes
from uuid import UUID

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.cfd_reads import query
from app.core.cfd_access import CfdAccessMiddleware
from app.core.cfd_errors import CfdProblem, error_response, validation_issues
from app.core.cfd_settings import CfdPracticeSettings
from app.database.cfd_personal_session import PersonalWorkspace
from app.database.cfd_session import CfdTargetRejected
from app.schemas.cfd_api import CfdPreviewCommandV1
from app.schemas.cfd_personal import (
    CfdPersonalPage,
    CfdPersonalRead,
    PersonalPreview,
    PersonalStatus,
)
from app.schemas.cfd_positions import CfdPositionResult
from app.services.cfd_personal_positions import create_position, position_page, read_position
from app.services.cfd_personal_release import PersonalRuntime
from app.services.cfd_preview import bind_preview


def create_app(*, workspace, runtime, settings=None):
    settings = settings or CfdPracticeSettings(enabled=True, api_port=8004, allow_creation=True)
    if (
        not isinstance(workspace, PersonalWorkspace)
        or not workspace.personal_writes
        or not isinstance(runtime, PersonalRuntime)
        or not settings.enabled
        or not settings.allow_creation
        or settings.api_port not in {8004, 8014}
    ):
        raise ValueError("A newly minted P3 workspace and qualified personal release are required")
    workspace.check_target(workspace.engine.url)
    runtime.verify(purpose="accept_save")
    app = FastAPI(
        title="AVA local-personal disposable CFD journal",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.workspace, app.state.runtime = workspace, runtime
    app.state.cursor_key = token_bytes(32)
    app.add_middleware(CfdAccessMiddleware, workspace=workspace, settings=settings)

    def fail(request, status, code, message, issues=()):
        return error_response(status, code, message, request.state.cfd_request_id, issues)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def invalid(request: Request, error):
        return fail(
            request,
            422,
            "invalid_financial_input",
            "Check the CFD request fields.",
            validation_issues(error),
        )

    @app.exception_handler(CfdProblem)
    async def problem(request: Request, error):
        return fail(request, error.status, error.code, error.message)

    @app.exception_handler(CfdTargetRejected)
    async def target(request: Request, error):
        return fail(
            request, 403, "practice_access_denied", "The new isolated CFD session is required."
        )

    @app.exception_handler(SQLAlchemyError)
    async def database(request: Request, error):
        return fail(
            request, 503, "database_unavailable", "The isolated CFD database is unavailable."
        )

    @app.get("/api/v1/cfd/status", response_model=PersonalStatus)
    def status():
        with workspace.read_session():
            runtime.verify(purpose="accept_save")
            return PersonalStatus(release_digest=runtime.release_digest)

    @app.get("/api/v1/cfd/examples", response_model=dict[str, CfdPreviewCommandV1])
    def examples():
        with workspace.read_session():
            return workspace.samples["previews"]

    @app.post("/api/v1/cfd/preview", response_model=PersonalPreview)
    def preview(command: CfdPreviewCommandV1):
        with workspace.read_session() as session:
            validated = bind_preview(session, command)
        if command.release_digest != runtime.release_digest:
            raise CfdProblem(409, "release_mismatch", "Use the selected local release.")
        result = runtime.preview(validated)
        if not isinstance(result, CfdPositionResult):
            raise CfdProblem(
                422,
                "calculation_unavailable",
                "Required financial evidence is unavailable. Nothing was saved.",
            )
        return PersonalPreview(release_digest=runtime.release_digest, result=result)

    @app.post("/api/v1/cfd/positions", response_model=CfdPersonalRead, status_code=201)
    def save(command: CfdPreviewCommandV1, request: Request):
        if request.query_params:
            raise CfdProblem(400, "invalid_query", "Position saves do not accept query parameters.")
        return create_position(workspace, runtime, command, request.headers.get("idempotency-key"))

    @app.get("/api/v1/cfd/positions", response_model=CfdPersonalPage)
    def positions(request: Request):
        args = query(request, paged=True)
        with workspace.read_session() as session:
            return position_page(
                session, args.account_id, args.limit, args.cursor, app.state.cursor_key
            )

    @app.get("/api/v1/cfd/positions/{position_id}", response_model=CfdPersonalRead)
    def position(request: Request, response: Response, position_id: UUID):
        args = query(request)
        with workspace.read_session() as session:
            record = read_position(session, args.account_id, position_id)
        response.headers["ETag"] = f'"personal-v1:{record.position_id}:1:{record.result_sha256}"'
        return record

    return app

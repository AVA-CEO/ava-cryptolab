"""Isolated synthetic CFD app. Default disabled; normal app/routes are untouched."""

from secrets import token_bytes

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.cfd import local_router, router
from app.api.cfd_reads import router as reads_router
from app.core.cfd_access import CfdAccessMiddleware
from app.core.cfd_errors import CfdProblem, error_response, validation_issues
from app.core.cfd_settings import CfdPracticeSettings
from app.database.cfd_session import CfdTargetRejected
from app.services.cfd_runtime import UnavailableRuntime


def create_app(*, workspace=None, settings=None, local_preview_runtime=None):
    settings = settings or CfdPracticeSettings()
    app = FastAPI(
        title="AVA CFD practice boundary (runtime unavailable)",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.workspace = workspace
    app.state.runtime = UnavailableRuntime()
    app.state.local_preview = False
    if local_preview_runtime is not None:
        from app.services.cfd_local_release import LocalPreviewRuntime

        if (
            not settings.enabled
            or workspace is None
            or not isinstance(local_preview_runtime, LocalPreviewRuntime)
        ):
            raise ValueError("Explicit registered local preview configuration required")
        local_preview_runtime.verify()
        app.state.runtime = local_preview_runtime
        app.state.local_preview = True
        app.include_router(local_router)
    app.state.cursor_key = token_bytes(32)
    app.add_middleware(CfdAccessMiddleware, workspace=workspace, settings=settings)
    app.include_router(router)
    app.include_router(reads_router)

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
        return fail(request, 403, "practice_access_denied", "The isolated CFD target is required.")

    @app.exception_handler(SQLAlchemyError)
    async def database(request: Request, error):
        return fail(
            request, 503, "database_unavailable", "The isolated CFD database is unavailable."
        )

    return app

"""Separate B3A app factory. Default disabled; normal app/routes are untouched."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.cfd import router
from app.core.cfd_access import CfdAccessMiddleware
from app.core.cfd_errors import CfdProblem, error_response, validation_issues
from app.core.cfd_settings import CfdPracticeSettings
from app.database.cfd_session import CfdTargetRejected
from app.services.cfd_runtime import UnavailableRuntime


def create_app(*, workspace=None, settings=None):
    settings = settings or CfdPracticeSettings()
    app = FastAPI(
        title="AVA CFD practice boundary (runtime unavailable)",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.workspace = workspace
    app.state.runtime = UnavailableRuntime()
    app.add_middleware(CfdAccessMiddleware, workspace=workspace, settings=settings)
    app.include_router(router)

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

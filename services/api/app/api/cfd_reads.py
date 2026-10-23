"""Only the four approved GET operations. No accepted-save route."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Request, Response

from app.core.cfd_errors import CfdProblem
from app.schemas.cfd_reads import CfdPositionPage, CfdReadQuery, CfdReadResponseV1, CfdRevisionPage
from app.services.cfd_records import position_page, read_position, revision_page

router = APIRouter(prefix="/api/v1/cfd/positions", tags=["Synthetic CFD reads"])


def query(request, *, paged=False):
    allowed = {"account_id", "limit", "cursor"} if paged else {"account_id"}
    params = request.query_params
    if any(key not in allowed or len(params.getlist(key)) != 1 for key in params):
        raise CfdProblem(400, "invalid_query", "Supply only the documented query parameters once.")
    if "limit" in params and (not params["limit"].isascii() or not params["limit"].isdigit()):
        raise CfdProblem(422, "invalid_query", "Page limit must be an integer from 1 to 100.")
    return CfdReadQuery.model_validate(dict(params))


@router.get("", response_model=CfdPositionPage)
def positions(request: Request):
    args = query(request, paged=True)
    with request.app.state.workspace.read_session() as session:
        return position_page(
            session, args.account_id, args.limit, args.cursor, request.app.state.cursor_key
        )


def record(request, response, position_id, revision_no=None):
    args = query(request)
    with request.app.state.workspace.read_session() as session:
        result = read_position(session, args.account_id, position_id, revision_no)
    response.headers["ETag"] = (
        f'"cfd-v1:{result.position_id}:{result.revision_no}:{result.result_sha256}"'
    )
    return result


@router.get("/{position_id}", response_model=CfdReadResponseV1)
def current(request: Request, response: Response, position_id: UUID):
    return record(request, response, position_id)


@router.get("/{position_id}/revisions", response_model=CfdRevisionPage)
def revisions(request: Request, position_id: UUID):
    args = query(request, paged=True)
    with request.app.state.workspace.read_session() as session:
        return revision_page(
            session,
            args.account_id,
            position_id,
            args.limit,
            args.cursor,
            request.app.state.cursor_key,
        )


@router.get("/{position_id}/revisions/{revision_no}", response_model=CfdReadResponseV1)
def historical(
    request: Request,
    response: Response,
    position_id: UUID,
    revision_no: Annotated[str, Path(pattern=r"^[1-9][0-9]{0,8}$")],
):
    return record(request, response, position_id, int(revision_no))

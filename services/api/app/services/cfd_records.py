"""Account-scoped published reads only. No save service, engine or write statements."""

from uuid import UUID

from sqlalchemy import and_, or_, select

from app.core.cfd_errors import CfdProblem
from app.models import JournalAccount
from app.models.cfd import TABLES
from app.schemas.cfd_reads import (
    CfdPositionPage,
    CfdReadSummary,
    CfdRevisionPage,
    CfdRevisionSummary,
)
from app.services import cfd_cursor
from app.services.cfd_integrity import instant, lineage, verify_record
from app.services.cfd_read_codec import corrupt


def missing():
    raise CfdProblem(404, "resource_not_found", "Published CFD resource not found in this account.")


def account_scope(session, account_id):
    if session.get(JournalAccount, account_id) is None:
        missing()


def published(session, account_id, position_id):
    root = (
        session.execute(
            select(TABLES["cfd_positions"]).filter_by(id=str(position_id), account_id=account_id)
        )
        .mappings()
        .one_or_none()
    )
    if root is None:
        missing()
    try:
        chain = lineage(session, root)
    except (ValueError, TypeError, KeyError):
        corrupt()
    if not chain:
        missing()
    return root, chain


def read_position(session, account_id, position_id, revision_no=None):
    root, chain = published(session, account_id, position_id)
    selected = (
        next((row for row in chain if row["revision_no"] == revision_no), None)
        if revision_no
        else chain[0]
    )
    if selected is None:
        missing()
    # The initial published page is an independent check on the root's frozen
    # risk amounts; a later page cannot redefine the root and its own risk together.
    if selected["revision_no"] != 1:
        verify_record(session, root, chain[-1], chain[0]["revision_no"])
    return verify_record(session, root, selected, chain[0]["revision_no"])


def position_page(session, account_id, limit, cursor, key):
    account_scope(session, account_id)
    root, head = TABLES["cfd_positions"], TABLES["cfd_position_heads"]
    scope = dict(kind="positions", account_id=account_id, position_id=None, limit=limit)
    query = (
        select(root)
        .join(head, head.c.position_id == root.c.id)
        .where(root.c.account_id == account_id)
    )
    if cursor:
        last = cfd_cursor.decode(key, scope, cursor)
        try:
            if (
                not isinstance(last, list)
                or len(last) != 2
                or instant(last[0]) != last[0]
                or str(UUID(last[1])) != last[1]
            ):
                raise ValueError
        except (TypeError, ValueError, AttributeError):
            raise CfdProblem(
                400, "invalid_cursor", "Invalid page cursor; reload the first page."
            ) from None
        query = query.where(
            or_(
                root.c.created_at > last[0], and_(root.c.created_at == last[0], root.c.id > last[1])
            )
        )
    rows = (
        session.execute(query.order_by(root.c.created_at, root.c.id).limit(limit + 1))
        .mappings()
        .all()
    )
    items = []
    for row in rows[:limit]:
        record = read_position(session, account_id, row["id"])
        items.append(
            CfdReadSummary(
                position_id=record.position_id,
                account_id=account_id,
                revision_id=record.revision_id,
                revision_no=record.revision_no,
                created_at=record.created_at,
                symbol=record.result.symbol,
                state=record.result.state,
                lifecycle=record.lifecycle,
                native_net=record.result.native.net_pnl,
                reporting_net=record.result.reporting.net_pnl,
            )
        )
    next_cursor = (
        cfd_cursor.encode(key, scope, [rows[limit - 1]["created_at"], rows[limit - 1]["id"]])
        if len(rows) > limit
        else None
    )
    return CfdPositionPage(account_id=account_id, items=items, next_cursor=next_cursor)


def revision_page(session, account_id, position_id, limit, cursor, key):
    root, chain = published(session, account_id, position_id)
    verify_record(session, root, chain[-1], chain[0]["revision_no"])
    scope = dict(kind="revisions", account_id=account_id, position_id=str(position_id), limit=limit)
    last = cfd_cursor.decode(key, scope, cursor) if cursor else 0
    if type(last) is not int or not 0 <= last <= 1000:
        raise CfdProblem(400, "invalid_cursor", "Invalid page cursor; reload the first page.")
    rows = sorted(
        (row for row in chain if row["revision_no"] > last), key=lambda row: row["revision_no"]
    )
    items = []
    for row in rows[:limit]:
        record = verify_record(session, root, row, chain[0]["revision_no"])
        items.append(
            CfdRevisionSummary(
                revision_id=record.revision_id,
                revision_no=record.revision_no,
                historical=record.historical,
                as_of=record.result.as_of,
                lifecycle=record.lifecycle,
                result_sha256=record.result_sha256,
            )
        )
    next_cursor = (
        cfd_cursor.encode(key, scope, rows[limit - 1]["revision_no"]) if len(rows) > limit else None
    )
    return CfdRevisionPage(
        account_id=account_id, position_id=position_id, items=items, next_cursor=next_cursor
    )

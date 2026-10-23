"""Trusted reference binding and validation only. No engine execution or persistence."""

from pydantic import ValidationError

from app.core.cfd_errors import CfdProblem
from app.models import JournalAccount
from app.schemas.cfd_api import CfdPreviewCommandV1
from app.schemas.cfd_positions import CfdPositionRequest
from app.services.cfd_canonical import input_document
from app.services.management import account_contract
from app.services.multi_asset import load_snapshot

# Runtime compatibility allowlist, not calculation formulas.
SUPPORTED = {
    "forex": {"forex"},
    "cfd_linear": {"metals", "indices", "energy", "equities", "other"},
    "cfd_index": {"indices"},
}


def bind_preview(session, command: CfdPreviewCommandV1):
    row = session.get(JournalAccount, command.account_id)
    if row is None:
        raise CfdProblem(404, "resource_not_found", "Compatible practice resource not found.")
    try:
        spec = load_snapshot(session, str(command.snapshot_id))
    except ValueError:
        raise CfdProblem(
            404, "resource_not_found", "Compatible practice resource not found."
        ) from None
    account = account_contract(row)
    if (
        account.platform not in {"manual", "mt5"}
        or not account.server
        or spec.product != "cfd"
        or account.server != spec.venue
        or account.broker != spec.broker
        or account.settlement_currency != spec.settlement_currency
    ):
        raise CfdProblem(
            422, "incompatible_scope", "Account, server and CFD specification must match."
        )
    if spec.market_category not in SUPPORTED.get(spec.calculation_mode, set()):
        raise CfdProblem(422, "unsupported_mode", "This CFD calculation mode is unsupported.")
    from app.models import InstrumentSnapshot

    snapshot = session.get(InstrumentSnapshot, str(command.snapshot_id))
    payload = dict(
        position_reference=str(command.position_reference),
        trade=dict(
            command.trade.model_dump(),
            account=account.model_dump(),
            snapshot=dict(
                snapshot_id=snapshot.id,
                content_sha256=snapshot.content_sha256,
                specification=spec.model_dump(),
            ),
        ),
        rounding=command.rounding,
        as_of=command.as_of,
        recognition_policy=command.recognition_policy,
        broker_evidence=command.broker_evidence,
    )
    request = CfdPositionRequest.model_validate(payload)
    needed = {spec.profit_currency, account.reporting_currency}
    needed.update(item.currency for item in request.trade.adjustments)
    if needed - {item.currency for item in request.rounding.currencies}:
        raise CfdProblem(
            422, "missing_currency_precision", "Supply rounding places for every currency."
        )
    # Normalization is revalidated under the same immutable snapshot hash.
    try:
        return CfdPositionRequest.model_validate(input_document(request))
    except ValidationError:
        raise CfdProblem(
            422, "invalid_financial_input", "Check the exact financial inputs."
        ) from None

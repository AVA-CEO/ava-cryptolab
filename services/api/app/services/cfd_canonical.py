"""B3A deterministic input normalization; no calculation, risk freezing or save."""

import json
from datetime import datetime, timezone
from decimal import Decimal

from app.schemas.cfd_positions import CfdPositionRequest


def _normal(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Finite Decimal required")
        if not value:
            return "0"
        text = format(value, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("Timezone required")
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(value, dict):
        return {key: _normal(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_normal(item) for item in value]
    return value


def input_document(request: CfdPositionRequest):
    value = _normal(request.model_dump(mode="python", exclude={"trade": {"snapshot"}}))
    # Preserve immutable specification v1 spelling and its existing hash.
    value["trade"]["snapshot"] = request.trade.snapshot.model_dump(mode="json")
    for name, key in [("adjustments", "adjustment_id"), ("conversions", "conversion_id")]:
        value["trade"][name].sort(key=lambda item: item[key])
    value["broker_evidence"].sort(key=lambda item: item["evidence_id"])
    value["rounding"]["currencies"].sort(key=lambda item: item["currency"])
    return value


def canonical_input(request: CfdPositionRequest):
    return json.dumps(
        input_document(request),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )

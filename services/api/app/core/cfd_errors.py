"""Safe CFD errors contain no request values, SQL, paths or exception text."""

from uuid import uuid4

from starlette.responses import JSONResponse


class CfdProblem(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def error_response(status, code, message, request_id=None, issues=(), headers=None):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id or str(uuid4()),
                "issues": list(issues),
            }
        },
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            **(headers or {}),
        },
    )


def validation_issues(error):
    # Locations may contain attacker-controlled unknown keys. Never echo them.
    known = {
        "body",
        "trade",
        "account_id",
        "snapshot_id",
        "position_reference",
        "schema_version",
        "direction",
        "entry",
        "exits",
        "price",
        "lots",
        "executed_at",
        "execution_id",
        "original_stop",
        "planned_take_profit",
        "adjustments",
        "adjustment_id",
        "kind",
        "amount",
        "currency",
        "occurred_at",
        "source",
        "reference",
        "description",
        "conversion_id",
        "conversions",
        "profit_conversion_id",
        "risk_conversion_id",
        "reporting_policy",
        "rounding",
        "currencies",
        "decimal_places",
        "ratio_places",
        "movement_places",
        "as_of",
        "recognition_policy",
        "broker_evidence",
        "release_digest",
        "from_currency",
        "to_currency",
        "rate",
        "observed_at",
        "applies_at",
        "max_age_seconds",
    }
    return [
        {
            "path": ".".join(
                str(v) if isinstance(v, int) or v in known else "field" for v in issue["loc"]
            ),
            "code": issue["type"],
            "message": "Check this field and the execution, risk and currency-evidence rules.",
        }
        for issue in error.errors()[:20]
    ]

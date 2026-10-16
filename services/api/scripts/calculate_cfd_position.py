"""Read a local CFD ledger request; no database, broker or order access."""

import argparse
import json
import sys
from pathlib import Path

from app.analytics.cfd_positions import calculate_position


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        print("Cannot read a valid UTF-8 JSON request.", file=sys.stderr)
        return 1
    result = calculate_position(payload)
    if args.json:
        print(result.model_dump_json(indent=2))
    elif result.status == "unavailable":
        print(f"Unavailable ({result.reason_code}): {result.message}", file=sys.stderr)
        for issue in result.issues:
            print(f"{issue.path}: {issue.message}", file=sys.stderr)
    else:
        print(f"{result.symbol}: {result.state} as of {result.as_of.isoformat()}")
        print(
            f"Lots: original {result.original_lots}; exited {result.exited_lots}; "
            f"remaining {result.remaining_lots}"
        )
        for fill in result.exits:
            print(
                f"Exit {fill.execution_id}: {fill.lots} lots; "
                f"gross {fill.native_gross.rounded:f} {fill.native_gross.currency}; "
                f"remaining {fill.remaining_lots_after}"
            )
        for label, group in (("Native", result.native), ("Reporting", result.reporting)):
            print(f"{label} ({group.currency}):")
            for field in (
                "gross_pnl",
                "adjustments",
                "net_pnl",
                "original_planned_risk",
                "realized_r",
            ):
                value = getattr(group, field)
                unit = "R" if field == "realized_r" else group.currency
                text = (
                    f"{value.rounded:f} {unit}"
                    if value.raw is not None
                    else f"unavailable - {value.unavailable_reason}"
                )
                print(f"  {field.replace('_', ' ')}: {text}")
        print(
            f"Recognized adjustments: {len(result.recognized_adjustments)}; policy: incurred_once"
        )
        print("Unrealized PnL: unavailable; no valuation-price input.")
        for comparison in result.comparisons:
            print(f"Evidence {comparison.evidence.evidence_id}: {comparison.status}")
        print("Only supplied ledger/specifications/rates used; no database or broker writes.")
    return 0 if result.status == "calculated" else 1


if __name__ == "__main__":
    raise SystemExit(main())

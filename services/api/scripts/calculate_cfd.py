"""Calculate one closed synthetic/manual CFD position without DB/broker access."""

import argparse
import json
import sys
from pathlib import Path

from app.analytics.cfd import calculate_cfd


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 JSON with trade and rounding policy")
    parser.add_argument("--json", action="store_true", help="Include raw values and FX evidence")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        print("Cannot read a valid UTF-8 JSON request.", file=sys.stderr)
        return 1
    result = calculate_cfd(payload)
    if args.json:
        print(result.model_dump_json(indent=2))
    elif result.status == "unavailable":
        print(f"Unavailable ({result.reason_code}): {result.message}", file=sys.stderr)
        for issue in result.issues:
            print(f"{issue.path}: {issue.message}", file=sys.stderr)
    else:
        print(
            f"{result.symbol} {result.direction}: {result.lots} lots x "
            f"{result.contract_size} units/lot"
        )
        print(f"Entry {result.entry_price}; exit {result.exit_price}")
        for label, measurement in (
            ("Directional price change", result.signed_price_change),
            ("Pips", result.pips),
            ("Ticks", result.ticks),
        ):
            show(label, measurement, measurement.unit)
        for label, group in (("Native", result.native), ("Account reporting", result.reporting)):
            print(f"{label} ({group.currency}):")
            for name in (
                "gross_pnl",
                "adjustments",
                "net_pnl",
                "original_planned_risk",
                "realized_r",
            ):
                measurement = getattr(group, name)
                show(
                    f"  {name.replace('_', ' ')}",
                    measurement,
                    "R" if name == "realized_r" else group.currency,
                )
        print(
            f"Rounding: {result.rounding_policy.rounding}; "
            f"internal precision: {result.precision_digits} digits"
        )
        print(
            "Only supplied specifications/rates used. No database, broker call or order execution."
        )
    return 0 if result.status == "calculated" else 1


def show(label, measurement, unit):
    if measurement.raw is None:
        print(f"{label}: unavailable - {measurement.unavailable_reason}")
    else:
        print(f"{label}: {measurement.rounded:f} {unit}")


if __name__ == "__main__":
    raise SystemExit(main())

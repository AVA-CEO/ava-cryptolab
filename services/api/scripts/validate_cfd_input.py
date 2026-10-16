"""Validate a JSON input without importing the application, DB or a broker SDK."""

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError

from app.schemas.cfd import CfdTradeInput


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON with decimal amounts encoded as strings")
    args = parser.parse_args(argv)
    try:
        payload = CfdTradeInput.model_validate_json(args.input.read_text(encoding="utf-8"))
    except (OSError, UnicodeError):
        print("Cannot read the input as a UTF-8 JSON file.", file=sys.stderr)
        return 1
    except ValidationError as error:
        for item in error.errors(include_input=False, include_url=False):
            location = ".".join(str(part) for part in item["loc"]) or "trade"
            print(f"{location}: {item['msg']}", file=sys.stderr)
        return 1
    print(f"Valid CFD inputs ({payload.reporting_policy}). No PnL calculated or records saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

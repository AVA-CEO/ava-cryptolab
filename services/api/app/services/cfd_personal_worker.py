"""Frozen local calculator entry. No database, network, registry or broker access."""

import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
# -I -S startup omits user/site hooks. Only the verified payload is added.
sys.path.insert(0, str(root))

from app.analytics.cfd_positions import calculate_position  # noqa: E402

if __name__ == "__main__":
    raw = sys.stdin.buffer.read(4194305)
    if len(raw) > 4194304:
        raise SystemExit(2)
    result = calculate_position(json.loads(raw))
    sys.stdout.write(result.model_dump_json())

"""Fixed pure-calculator entry, copied into an explicitly verified preview release."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.analytics.cfd_positions import calculate_position  # noqa: E402

if __name__ == "__main__":
    request = sys.stdin.buffer.read(4 * 1024 * 1024 + 1)
    if len(request) > 4 * 1024 * 1024:
        raise SystemExit(2)
    result = calculate_position(json.loads(request))
    sys.stdout.write(result.model_dump_json())

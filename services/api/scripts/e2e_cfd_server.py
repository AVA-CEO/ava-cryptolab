"""Synthetic browser-test worker. NEW temporary release/database; no personal records."""

import argparse
import os
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, choices=[8003, 8013], default=8003)
    args = parser.parse_args()
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["APP_ENV"] = "local"
    os.environ["ACCOUNT_MANAGEMENT_ENABLED"] = "false"
    import uvicorn

    from app.cfd_practice import create_app
    from app.core.cfd_settings import CfdPracticeSettings
    from app.database.cfd_session import new_cfd_workspace
    from app.services.cfd_local_release import LocalPreviewRuntime, prepare_release

    with tempfile.TemporaryDirectory(prefix="ava-preview-browser-") as directory:
        release = Path(directory) / "release"
        approved = prepare_release(release)
        with new_cfd_workspace() as workspace:
            app = create_app(
                workspace=workspace,
                settings=CfdPracticeSettings(enabled=True, api_port=args.port),
                local_preview_runtime=LocalPreviewRuntime(release, approved, test_fixture=True),
            )
            uvicorn.run(
                app, host="127.0.0.1", port=args.port, access_log=False, proxy_headers=False
            )


if __name__ == "__main__":
    main()

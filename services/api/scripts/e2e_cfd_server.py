"""Synthetic browser-test worker. NEW temporary release/database; no personal records."""

import os
import tempfile
from pathlib import Path


def main():
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
                settings=CfdPracticeSettings(enabled=True),
                local_preview_runtime=LocalPreviewRuntime(release, approved, test_fixture=True),
            )
            uvicorn.run(app, host="127.0.0.1", port=8003, access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()

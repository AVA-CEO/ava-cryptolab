"""Fresh disposable P3 browser-test database and explicitly synthetic release qualification."""

import os
import tempfile
from pathlib import Path


def main():
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["APP_ENV"] = "local"
    os.environ["ACCOUNT_MANAGEMENT_ENABLED"] = "false"
    import uvicorn

    from app.cfd_personal import create_app
    from app.core.cfd_settings import CfdPracticeSettings
    from app.database.cfd_personal_session import new_personal_workspace
    from app.services.cfd_personal_release import PersonalRuntime, prepare_personal_release

    with tempfile.TemporaryDirectory(prefix="ava-personal-browser-") as directory:
        release = Path(directory) / "release"
        approved = prepare_personal_release(release, test_fixture=True)
        runtime = PersonalRuntime(release, approved, test_fixture=True)
        with new_personal_workspace() as workspace:
            app = create_app(
                workspace=workspace,
                runtime=runtime,
                settings=CfdPracticeSettings(enabled=True, api_port=8014, allow_creation=True),
            )
            uvicorn.run(app, host="127.0.0.1", port=8014, access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()

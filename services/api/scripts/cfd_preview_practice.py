"""Prepare a pinned release, then explicitly approve its digest for NEW practice previews."""

import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--approve-release")
    args = parser.parse_args()
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["APP_ENV"] = "local"
    os.environ["ACCOUNT_MANAGEMENT_ENABLED"] = "false"
    from app.services.cfd_local_release import LocalPreviewRuntime, prepare_release

    directory = Path(__file__).resolve().parents[3] / ".local-cfd-preview"
    if args.prepare:
        print("Preview-only unsigned release prepared; NOT activated:")
        print(prepare_release(directory))
        print(
            "Review .local-cfd-preview/manifest.json; "
            "then run --approve-release with that exact digest."
        )
        return
    if not args.approve_release:
        parser.error(
            "First --prepare; review the manifest; then explicitly --approve-release sha256:..."
        )
    runtime = LocalPreviewRuntime(directory, args.approve_release)
    import uvicorn

    from app.cfd_practice import create_app
    from app.core.cfd_settings import CfdPracticeSettings
    from app.database.cfd_session import new_cfd_workspace

    with new_cfd_workspace() as workspace:
        app = create_app(
            workspace=workspace,
            settings=CfdPracticeSettings(enabled=True),
            local_preview_runtime=runtime,
        )
        print("NEW disposable preview API: http://127.0.0.1:8003; no accepted saves.")
        uvicorn.run(app, host="127.0.0.1", port=8003, access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()

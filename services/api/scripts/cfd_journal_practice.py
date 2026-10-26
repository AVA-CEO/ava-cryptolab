"""Prepare/explicitly approve a local-personal release for a NEW disposable P3 session."""

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
    from app.services.cfd_personal_release import PersonalRuntime, prepare_personal_release

    directory = Path(__file__).resolve().parents[3] / ".local-cfd-personal"
    if args.prepare:
        print("NEW local-personal release prepared; not activated:")
        print(prepare_personal_release(directory))
        print("Review .local-cfd-personal/manifest.json, then --approve-release that exact digest.")
        return
    if not args.approve_release:
        parser.error("First --prepare; then explicitly --approve-release sha256:...")
    runtime = PersonalRuntime(directory, args.approve_release)
    import uvicorn

    from app.cfd_personal import create_app
    from app.database.cfd_personal_session import new_personal_workspace

    with new_personal_workspace() as workspace:
        app = create_app(workspace=workspace, runtime=runtime)
        print(
            "NEW disposable journal API http://127.0.0.1:8004; "
            "synthetic inputs, local acceptance only."
        )
        print(
            "Refresh retains this session's saves. "
            "Stopping the runner removes this disposable database."
        )
        uvicorn.run(app, host="127.0.0.1", port=8004, access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()

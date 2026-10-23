"""Explicit fresh B3A runner. No path argument, host calculator or saved positions."""

import argparse
import json
import os


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    # Do not inherit the normal DB or enable its management routes on this app.
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["ACCOUNT_MANAGEMENT_ENABLED"] = "false"
    os.environ["APP_ENV"] = "local"
    import uvicorn

    from app.cfd_practice import create_app
    from app.core.cfd_settings import CfdPracticeSettings
    from app.database.cfd_session import new_cfd_workspace

    with new_cfd_workspace() as workspace:
        for symbol, body in workspace.samples["previews"].items():
            path = workspace.directory / ("preview-" + symbol.lower() + ".json")
            path.write_text(json.dumps(body, indent=2), encoding="utf-8")
        print("NEW SYNTHETIC CFD workspace, revision 0004:", workspace.directory)
        print("API: http://127.0.0.1:8003/api/v1/cfd/status")
        print("Required header: X-AVA-Local: cfd-practice-v1 (local boundary, not authentication)")
        print("Valid previews return 503: no approved runtime, no host fallback, no saving.")
        print("Request samples: preview-usdjpy.json, preview-xauusd.json, preview-xagusd.json")
        print("Only this new workspace is removed on a normal stop. No existing session is loaded.")
        uvicorn.run(
            create_app(workspace=workspace, settings=CfdPracticeSettings(enabled=True)),
            host="127.0.0.1",
            port=8003,
            proxy_headers=False,
            access_log=False,
        )


if __name__ == "__main__":
    main()

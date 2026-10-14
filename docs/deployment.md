# Deployment preparation

Phase 1 is a local foundation, not a public launch.

## Frontend / Vercel

Use the monorepo with root directory `apps/web`. Install workspace dependencies from the repository lockfile and use the Next.js preset (`next build`). Set server-only `API_BASE_URL` to the future backend HTTPS origin. No market secrets belong in browser-visible variables. Offline backend state displays safely; it does not synthesize user financials.

## Backend / compatible Python host

The service is a standard ASGI application. A future container or managed Python host can install the locked requirements and project, then launch `uvicorn app.main:app --host 0.0.0.0 --port PORT`. Configure a managed PostgreSQL connection and apply migrations as a release job before readiness checks. Use `/api/v1/health` for liveness and `/api/v1/ready` for readiness.

This launch command is preparation only: Phase 1 deliberately requires `APP_ENV=local`. Authentication, ownership authorization, rate limiting, HTTPS, production settings, secret management and upload security must precede public private-data access. Production must not run with `APP_ENV=local` to bypass this restriction. No hosting account, remote repository or deployment is created here.

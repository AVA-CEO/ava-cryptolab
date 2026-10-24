# Deployment preparation

The web app targets Vercel; no Android/native distribution is planned. This is deployment preparation, not permission to deploy. The [working web delivery guide](web-product-delivery.md) defines the current safe educational frontend preview and remaining financial-production requirements.

## Frontend / Vercel

Use the monorepo with root directory `apps/web`, its workspace lockfile and the Next.js preset (`next build`). Current Vercel mode explicitly disables financial API bridges and server-side journal retrieval. Do not set a personal backend URL or upload financial data to this preview. Educational pages, stateless quiz grading and clearly simulated market/dashboard examples need no financial database. No secrets belong in browser-visible variables.

Vercel filesystem/SQLite storage is not a persistent financial database. Public financial functionality requires authenticated ownership, durable database/attachment storage, a separately hosted secure Python API and a future reviewed bridge configuration. No current production-finance configuration is provided.

## Backend / compatible Python host

The service is a standard ASGI application. A future container or managed Python host can install the locked requirements and project, then launch `uvicorn app.main:app --host 0.0.0.0 --port PORT`. Configure a managed PostgreSQL connection and apply migrations as a release job before readiness checks. Use `/api/v1/health` for liveness and `/api/v1/ready` for readiness.

This launch command is preparation only: Phase 1 deliberately requires `APP_ENV=local`. Authentication, ownership authorization, rate limiting, HTTPS, production settings, secret management and upload security must precede public private-data access. Production must not run with `APP_ENV=local` to bypass this restriction. No hosting account, remote repository or deployment is created here.

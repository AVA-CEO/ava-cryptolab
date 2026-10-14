# Developer setup

Use the root README commands. Backend commands must run in `services/api`, ensuring SQLite and Alembic use the same location. On macOS/Linux substitute `.venv/bin/python` for `.venv\Scripts\python.exe`.

## Environment

| Variable       | Location              | Default                 | Purpose                      |
| -------------- | --------------------- | ----------------------- | ---------------------------- |
| `API_BASE_URL` | `apps/web/.env.local` | `http://127.0.0.1:8000` | Server-only backend address  |
| `DATABASE_URL` | `services/api/.env`   | `sqlite:///./ava.db`    | SQLAlchemy connection string |
| `APP_ENV`      | `services/api/.env`   | `local`                 | Local-only guard             |

Do not use `NEXT_PUBLIC_` for backend credentials. Next.js reads its environment file; Python settings read the backend `.env`. The root `.env.example` is a reference, not loaded automatically by either service.

For PostgreSQL set `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/ava` and run `alembic upgrade head` against an empty target database. This changes the connection, not existing data; moving records requires an explicit data migration. PostgreSQL runtime validation is a later check; SQLite is tested locally in Phase 1.

## Development commands

Root: `npm run dev`, `npm run lint`, `npm run typecheck`, `npm run build`.

Backend directory: `../../.venv/Scripts/python.exe -m uvicorn app.main:app --reload` and `../../.venv/Scripts/python.exe -m alembic upgrade head`.

Create migrations with `alembic revision --autogenerate -m "describe the schema change"`. Review generated SQL, run upgrade and check before committing. Only use downgrade on disposable development databases.

If port 3000 is occupied, run `npm run dev --workspace @ava/web -- --port 3001`. Browser tests use 3000, so free that port before tests or update their configuration deliberately. If port 8000 changes, update `API_BASE_URL` and restart Next.js.

## Adding UI

`apps/web/components.json` configures the shadcn/ui aliases and Tailwind v4 stylesheet. Reusable primitives go in `src/components/ui`; feature calculations and screens go in their own feature folder. Lightweight Charts, React Hook Form, Pandas and NumPy will be installed when their real feature implementations need them.

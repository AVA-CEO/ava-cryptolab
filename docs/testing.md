# Testing

Backend tests use an isolated in-memory SQLite database and dependency overrides. They cover health, schema readiness, empty financials, stored balances and unsupported currency aggregation. They never use local trading records.

Playwright covers empty onboarding, entering/exiting labelled sample mode, date selection, chart selection, theme persistence, module navigation and page overflow at desktop and mobile dimensions. The web server is started automatically. An API is not required for these UI flows; offline status is an intentional supported state. Live API connectivity is checked separately.

Run the commands in the README. Install Chromium with `npx playwright install chromium` in `apps/web` once. CI uses `--with-deps` on Linux.

Frontend linting uses ESLint directly (not the removed `next lint` command). TypeScript checks run separately from production builds. Ruff checks Python imports and lint rules. `alembic check` detects differences between model metadata and the upgraded schema.

Financial analytics and external-provider tests are added with Phases 2 and 3. Do not claim those features are verified by the Phase 1 fixture charts. Production deployment, PostgreSQL concurrency and multi-user security are outside current verification.

Visual QA should check 390px, tablet and desktop widths, both themes, keyboard focus, mobile navigation, chart tooltips, sample labels and reduced-motion preferences. CI complements manual review; it does not prove perfect accessibility or visual quality.

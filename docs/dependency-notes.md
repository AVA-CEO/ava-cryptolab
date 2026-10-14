# Dependency review

Phase 1 installs stable npm releases and locks exact resolved versions. Python versions are captured in `services/api/requirements.lock`.

`npm audit --omit=dev` reports zero runtime dependency vulnerabilities for the Phase 1 lockfile. The complete development dependency audit remains affected by the finding below.

## Unresolved development advisory

`npm audit` reports five high-severity entries through a single dependency chain:

`eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch → braces`.

The underlying [GHSA-vfj7-8cjw-p6xm advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) affects braces through 3.0.3 and lists no patched release. Latest braces resolved as 3.0.3 during this milestone. Do not run `npm audit fix --force`: its proposed older Next lint configuration would break framework alignment without fixing the underlying package generally.

This chain is development tooling, not part of the deployed dashboard runtime dependency graph. Restrict lint patterns to trusted repository configuration; do not accept externally supplied glob expressions. Monitor upstream patches and rerun the full audit after updates. This is an unresolved finding, not a clean audit.

Backend tests also emit a Starlette deprecation warning for HTTPX TestClient usage. Tests pass; HTTPX remains the chosen external-provider client. Revisit TestClient transport compatibility in the next dependency update.

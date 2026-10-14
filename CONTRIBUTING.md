# Contributing

Keep changes scoped to a milestone. Describe the concrete behavior changed and include actual validation results. Use descriptive commits such as `feat(journal): add trade execution records` or `fix(analytics): handle missing initial risk`.

Before proposing a change, run web lint/type/build checks and relevant backend tests. Add meaningful tests for financial calculations, provider failure paths and authorization when those features are introduced. Keep fixtures deterministic and visibly labelled; never substitute fixtures for failed live market observations.

Never commit credentials, personal trade records, uploads or database files. Keep external data integration behind provider interfaces. No exchange order execution or trading-permission requests belong in this project.

Accessibility, readable explanations, empty states and honest metric definitions are product requirements. Document schema changes and review migration SQL. Project licensing remains pending owner approval.

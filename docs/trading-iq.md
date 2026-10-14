# AVA Trading IQ architecture

Trading IQ is a deterministic evidence service, not an AI-generated trading signal. `analytics/trading_iq.py` produces structured findings with a kind, title, explanation, observation count and rule version. Its input is the same currency-filtered trade cohort used by the dashboard. The UI shows the evidence gate and empty explanations instead of invented conclusions.

`rules-v1` requires at least 20 fully closed trades before performance comparisons and at least 5 observations in each comparable group. These are product safeguards, not proof of statistical significance. Initial-risk coverage warnings can appear sooner because they describe missing records, not performance.

Current foundations:

- Strongest/weakest recorded setups by average realized R, comparing eligible setup groups.
- Repeated user-logged mistake tags, with explicit non-causal wording.
- Best/worst eligible coins and periods by average net outcome in one settlement currency; size differences are disclosed.
- A review flag when at least 20 known initial risks span more than a 3× range. It asks whether the variation was intentional; it does not assume a risk budget or infer account-relative percentages.
- Missing-stop warnings as concrete areas for record-quality improvement.

Later extensions should add account-size history, richer setup taxonomy, session definitions, duplicate-controlled observations, uncertainty intervals, minimum meaningful effect sizes and multiple-comparison controls. Never treat a high average from five trades as predictive evidence. Future findings should retain observation IDs, filter context, sample size, null coverage and rule version so users can inspect and reproduce the result.

Keep findings separate from data providers, chart rendering and optional language-model explanations. A future language model may explain validated findings but must not invent prices, inferred motives or unsupported rankings. Raw private trade data must stay within the authenticated owner boundary.

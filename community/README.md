# Community Forecasting Layer

The community layer sits above, and cannot rewrite, the research data.

| Layer | Role |
| --- | --- |
| Research | Auditable prospective protocol and amendments |
| Dataset | Versioned announcements, actions, contexts, evidence, and adjudication |
| Forecast | Immutable statistical and LLM probabilities |
| Tournament | Models, LLMs, independent players, and crowd scored on common windows |
| Audit | Whether resets arrived and whether hard/banked behavior matched |
| Dashboard | Probabilities, evidence, coverage, and historical performance without winner claims before stopping |

## Comparison classes

| Predictor | Role |
| --- | --- |
| Global event rate | Weak reference |
| Recent 30-day rate | Strong naive reference |
| Renewal hazard | Time-since-last-event regularity |
| Calendar M2 | Calendar and policy cycles |
| Theory M3-lite | Official incidents, attention, and event strength |
| LLM forecaster | Reads a frozen public-context packet |
| Independent player | Individual judgment |
| Crowd aggregate | Equal-weight logit pool of eligible players |

Player forecasts must be submitted before the round deadline. The crowd requires at least three
distinct active players and excludes statistical models and the LLM, so it measures actual community
aggregation rather than model ensembling. Missing forecasts remain missing; no backfilling.

Formal ranking uses scheduled rounds only and reports Brier, Log Loss, coverage, and skill against
the recent-30-day baseline. The existing v1.1 stopping rule still governs model claims.

Operational instructions are in `PLAYER_AND_AUDIT_GUIDE_V1.md`. The fixed LLM instruction is
`LLM_FORECAST_PROMPT_V1.md`; every accepted submission is hash-locked under `community/locked/`.

The LLM class currently contains five separately ranked forecasters: DeepSeek V4 Pro,
Qwen 3.5 397B, Kimi K2.5, MiniMax M2.7, and Step 3.5 Flash. They receive the same frozen evidence
packet and never contribute to the human-only Crowd aggregate. Selection and bootstrap details are
recorded in `reports/llm_tournament_v1.md`.

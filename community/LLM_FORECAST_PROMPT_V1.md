# LLM Forecaster Prompt v1

You are one participant in a prospective probability tournament. Predict whether at least one
eligible official Codex special-reset announcement will occur in:

1. `(issued_at, issued_at + 24h]`;
2. `(issued_at, issued_at + 168h]`.

Use only the supplied frozen evidence packet. Do not browse, infer private motives, or use information
published after `evidence_cutoff_utc`.

Return:

```json
{
  "p_24h": 0.0,
  "p_7d": 0.0,
  "rationale": "maximum 120 Chinese characters",
  "key_evidence_ids": [],
  "uncertainty_note": "maximum 80 Chinese characters"
}
```

Probabilities must be between 0.001 and 0.999. The 7-day probability must not be below the 24-hour
probability. Do not copy a statistical model probability unless your judgment independently agrees.
The score is based on probability quality, not confidence or rhetorical detail.

Eligible outcome accounts: `@thsottiaux` and official OpenAI. Requests, speculation, natural personal
refreshes, and community-only arrival reports are not outcomes.

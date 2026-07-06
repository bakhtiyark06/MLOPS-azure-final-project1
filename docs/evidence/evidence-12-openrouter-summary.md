# OpenRouter Evaluation Summary (local demo)

Quality gate **PASSED** (F1: 0.99, Accuracy: 0.99).

The outage prediction model meets deployment thresholds. Monitor `latency_p95_ms` — Evidently drift check flagged this feature in the current snapshot vs reference baseline.

**Recommendation:** Model is approved for staging. Schedule drift remediation if production traffic shifts.

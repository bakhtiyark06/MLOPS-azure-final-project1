# Evaluation Summary

OpenRouter API key was not configured, so this report was generated locally.

## Executive Summary

Local MLOps evaluation summary compiled from project artifacts (eval metrics, drift summary, dataset hash).

## Model Metrics

- **Accuracy:** 0.9950
- **F1 Score:** 0.9928
- **Quality Gate:** PASSED

## Dataset

- **Dataset Hash:** d197fe3f6309e92f4a99f8aaf7e9d03df064be303cec0b4ade2f55c735000269

## Drift Status

- **Drift Detected:** PASSED
- **Drift Score:** 0.1429
- **Drift Summary:** Moderate drift detected across 1 of 7 features: latency_p95_ms.
- **Drift HTML Report:** available

## Drifted Columns

- latency_p95_ms

## Deployment Recommendation

Hold deployment — investigate drifted features and refresh baseline if needed.

## Risks

- Data drift detected — feature distributions may have shifted.

## Next Actions

- Investigate drifted columns and refresh reference baseline if needed.

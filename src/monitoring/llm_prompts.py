# Author: Member D — OpenRouter prompt templates
# Purpose: Build LLM prompts from evaluation and drift artifacts

"""Prompt builders for OpenRouter LLM reports."""

from __future__ import annotations

import json
from typing import Any


def build_eval_prompt(metrics: dict[str, Any], drift: dict[str, Any] | None) -> str:
    """Build prompt for evaluation summary report."""
    drift_section = ""
    if drift:
        drift_section = f"""
Data drift status:
- drift_detected: {drift.get('drift_detected')}
- summary: {drift.get('summary')}
- column_drifts: {json.dumps(drift.get('column_drifts', {}), indent=2)}
"""

    return f"""You are an MLOps engineer writing a concise evaluation report for a website outage prediction model.

Model evaluation metrics:
{json.dumps(metrics, indent=2)}
{drift_section}
Write a clear markdown report with:
1. Executive summary (2-3 sentences)
2. Metric interpretation vs thresholds
3. Gate pass/fail recommendation
4. Any data drift concerns (if drift data provided)
5. Recommended next steps

Keep the report under 400 words. Use markdown headings."""


def build_failure_prompt(metrics: dict[str, Any], drift: dict[str, Any] | None) -> str:
    """Build prompt for failure analysis report."""
    drift_section = ""
    if drift and drift.get("drift_detected"):
        drift_section = f"\nDrift context: {drift.get('summary')}"

    return f"""You are an MLOps engineer analyzing why a model quality gate failed.

Evaluation results:
{json.dumps(metrics, indent=2)}
{drift_section}
Write a markdown failure analysis with:
1. Root cause summary
2. Which thresholds failed and by how much
3. Whether this looks like a data issue, model issue, or demo flag
4. Concrete remediation steps before redeploying

Keep under 350 words. Use markdown headings."""

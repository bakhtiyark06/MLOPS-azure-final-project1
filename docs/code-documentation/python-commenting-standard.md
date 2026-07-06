# Python Commenting Standard

This project follows the course submission guide for code documentation.

## Requirements

### 1. Author tag (every Python file)

First lines of each `.py` file:

```python
# Author: [Team Member Name]
# Responsibility: [Pipeline Stage]
# Last Reviewed: [YYYY-MM-DD]
```

See [author-tags.md](author-tags.md) for the full template.

### 2. Module docstring

Every module should have a triple-quoted docstring immediately after the author block explaining the file's role in the pipeline.

### 3. Function and class docstrings

Every public function and class needs a docstring with:

- What it does
- Key parameters and return value
- How it connects to upstream/downstream stages (when non-obvious)

### 4. Inline comments

Meaningful lines should have inline comments that explain:

- **What** the line does
- **Why** it exists
- **How** it connects to the MLOps pipeline

Avoid stating the obvious (`i += 1  # increment i`). Prefer pipeline context (`# Block deploy when quality gate failed`).

### 5. Student responsibility

Each team member must **read and understand** comments in files they own. Comments are for learning and demo defense — not generated filler.

## Audit

Run:

```powershell
py scripts/audit_python_docs.py
```

Review [audit-report.md](audit-report.md) for per-file gaps.

## Ownership

Track review status in [file-ownership.md](file-ownership.md).

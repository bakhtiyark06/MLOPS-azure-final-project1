# Author Tags — Template

Copy this block to the top of every Python file (after shebang if present):

```python
# Author: [Team Member Name]
# Responsibility: [Pipeline Stage — e.g. Data Ingestion, Training, API, Deployment]
# Demo Owner: [Yes/No]
# Last Reviewed: [YYYY-MM-DD]
```

## Extended template (optional)

```python
# Author: [Team Member Name]
# Responsibility: [Pipeline Stage]
# Demo Owner: [Yes/No]
# Last Reviewed: [YYYY-MM-DD]
# Related docs: docs/pipeline/0N-*.md
# Key outputs: path/to/artifact
```

## Member mapping (suggested)

| Member | Typical responsibility tag |
|--------|---------------------------|
| A | Data Ingestion / DVC |
| B | Training / Quality Gate / Registry |
| C | API / Docker / CI |
| D | Deployment / Monitoring / Drift / OpenRouter |

## Placeholder for unassigned files

```python
# Author: TODO - Team Member Name
# Responsibility: TODO - Pipeline Stage
# Last Reviewed: TODO
```

Replace TODOs before final submission.

# Stage: Premium Architecture Explorer

Presentation-ready architecture pages for demo day. No backend pipeline changes — routes serve HTML/CSS/JS only.

## Open the pages

```powershell
py scripts/run_local.py
```

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/demo | Demo hub — links to architecture, dashboard, Swagger |
| http://127.0.0.1:8000/demo/flow | Premium architecture explorer with 8 sections, SVG connections, and Live Flow |

From the main dashboard (`/`), use **Demo Hub** or **Architecture** in the top navigation.

## Presenting the explorer

### Infrastructure sections (8)

The canvas groups components into large Azure-style sections:

1. **USER** — browser, dashboard, Swagger entry points
2. **WEBSITE MONITORING** — URL input, health analyzer, SSL/DNS, feature generation
3. **ML PIPELINE** — data ingestion through quality gate and registry
4. **CI/CD** — GitHub Actions, Docker, ACR, AKS
5. **SERVING** — FastAPI and predict/health/URL endpoints
6. **MONITORING** — App Insights, drift, alerts, Teams
7. **AI REPORTING** — OpenRouter summaries and demo explanations
8. **DATA FLOW** — prepared features bridge

Click a **stage tab** to focus one section; others dim. Presenter notes appear below the diagram.

### 14-step timeline

The horizontal timeline shows the professional story:

User → Website URL → Feature Generation → Data Validation → Model Prediction → Quality Gate → Registry → Docker → ACR → AKS → FastAPI → Dashboard → Drift Detection → OpenRouter

Use **◀** / **▶** (or arrow keys) to step through the timeline when Live Flow is not running.

### Live Flow (immersive tour)

1. Click **Live Flow** — the diagram walks through all 23 `liveFlow` steps (~1.5s each).
2. Animated packets travel along SVG edges; nodes glow active (bright), complete (soft), or dimmed (upcoming).
3. Use **Pause** / **Resume**, **Reset**, or **◀** / **▶** to control pacing during the tour.

### Accessibility

- All nodes are keyboard-focusable buttons with `aria-label`.
- Timeline steps are focusable; active step uses `aria-current="step"`.
- When the OS **prefers-reduced-motion** setting is on, particle background and packet animations are disabled; state changes are instant.

## Data source

All nodes, sections, edges, `liveFlow` (23 steps), `timelineFlow` (14 steps), and presenter notes live in:

`src/api/static/architecture-nodes.json`

Static Mermaid/PNG exports remain in `docs/architecture/` for slide decks.

## Presenter tips

- Start with **Live Flow** for a full-system walkthrough, then reset and use stage tabs for deep dives.
- Focus **ML PIPELINE** when discussing quality gate and registry rubric items.
- Focus **MONITORING** + **AI REPORTING** for drift detection and OpenRouter explanations.
- The timeline is ideal for a concise 14-step narrative; Live Flow adds CI/CD and intermediate training detail.

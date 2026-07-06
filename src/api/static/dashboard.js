(function () {
  "use strict";

  const HEALTHY = {
    response_time_ms: 220,
    status_code: 200,
    error_rate: 0.01,
    latency_p95_ms: 280,
    request_count: 300,
    cpu_usage_percent: 35,
    memory_usage_percent: 42,
  };

  const OUTAGE = {
    response_time_ms: 3100,
    status_code: 500,
    error_rate: 0.18,
    latency_p95_ms: 4500,
    request_count: 1200,
    cpu_usage_percent: 94,
    memory_usage_percent: 91,
  };

  const FIELDS = [
    "response_time_ms",
    "status_code",
    "error_rate",
    "latency_p95_ms",
    "request_count",
    "cpu_usage_percent",
    "memory_usage_percent",
  ];

  const DEFAULT_LABELS = {
    response_time_ms: "Response time",
    status_code: "HTTP status",
    error_rate: "Error rate",
    latency_p95_ms: "P95 latency",
    cpu_usage_percent: "CPU usage",
    memory_usage_percent: "Memory usage",
    request_count: "Request volume",
  };

  const RISK_RULES = [
    {
      id: "response_time_ms",
      check: (v) => v > 1000,
      message: "High response time — site is responding slowly",
    },
    {
      id: "status_code",
      check: (v) => v >= 500,
      message: "Bad HTTP status code — server error detected",
    },
    {
      id: "status_code_client",
      field: "status_code",
      check: (v) => v >= 400 && v < 500,
      message: "Client/request error — HTTP 4xx status code",
      cardId: "explain-status_code",
    },
    {
      id: "error_rate",
      check: (v) => v >= 0.05,
      message: "High error rate — many requests are failing",
    },
    {
      id: "latency_p95_ms",
      check: (v) => v > 1500,
      message: "High P95 latency — tail latency is elevated",
    },
    {
      id: "cpu_usage_percent",
      check: (v) => v > 80,
      message: "High CPU usage — server may be overloaded",
    },
    {
      id: "memory_usage_percent",
      check: (v) => v > 80,
      message: "High memory usage — resource pressure detected",
    },
    {
      id: "request_count",
      check: (v) => v > 1000,
      message: "Heavy traffic load — high request volume",
    },
  ];

  function getFormValues() {
    const data = {};
    for (const field of FIELDS) {
      data[field] = parseFloat(document.getElementById(field).value);
    }
    return data;
  }

  function setFormValues(payload) {
    for (const field of FIELDS) {
      document.getElementById(field).value = payload[field];
    }
    updateExplainCards(getFormValues());
  }

  function clearForm() {
    for (const field of FIELDS) {
      document.getElementById(field).value = "";
    }
    hideResult();
    hideError("error-msg");
  }

  function hideResult() {
    const panel = document.getElementById("result-panel");
    panel.classList.remove("visible", "safe", "warn", "danger");
    const placeholder = document.getElementById("result-placeholder");
    if (placeholder) placeholder.style.display = "";
  }

  function hideError(id) {
    const el = document.getElementById(id);
    if (el) el.classList.remove("visible");
  }

  function showError(id, message) {
    const el = document.getElementById(id);
    el.textContent = message;
    el.classList.add("visible");
  }

  function setLoading(id, visible) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("visible", visible);
  }

  function updateExplainCards(values) {
    for (const field of FIELDS) {
      const card = document.getElementById("explain-" + field);
      if (card) {
        card.className = "explain-card ok";
        card.textContent = DEFAULT_LABELS[field];
      }
    }

    for (const rule of RISK_RULES) {
      const field = rule.field || rule.id;
      const cardId = rule.cardId || "explain-" + rule.id;
      const card = document.getElementById(cardId);
      if (!card) continue;
      const val = values[field];
      if (Number.isNaN(val)) continue;
      if (rule.check(val)) {
        card.className = "explain-card triggered";
        card.textContent = rule.message;
      }
    }
  }

  function riskLevel(probability) {
    if (probability < 0.35) return "safe";
    if (probability < 0.65) return "warn";
    return "danger";
  }

  function showResult(data) {
    hideError("error-msg");
    const panel = document.getElementById("result-panel");
    const pct = Math.round(data.outage_probability * 1000) / 10;
    const level = riskLevel(data.outage_probability);
    const badge = document.getElementById("result-badge");
    const label = data.outage_predicted ? "Outage Risk" : "Healthy";

    panel.className = "result-panel visible " + level;
    badge.className = "result-badge " + level;
    badge.textContent = label;

    document.getElementById("result-probability").textContent = pct + "%";
    document.getElementById("result-detail").textContent = data.outage_predicted
      ? "The model predicts elevated outage risk based on these monitoring metrics."
      : "The model indicates the website metrics look stable.";

    document.getElementById("result-placeholder").style.display = "none";

    const fill = document.getElementById("risk-meter-fill");
    fill.style.width = pct + "%";
    fill.style.background =
      level === "safe"
        ? "linear-gradient(90deg, #22c55e, #16a34a)"
        : level === "warn"
          ? "linear-gradient(90deg, #f59e0b, #d97706)"
          : "linear-gradient(90deg, #ef4444, #dc2626)";
  }

  async function predict() {
    hideError("error-msg");
    hideResult();
    const btn = document.getElementById("btn-predict");

    let payload;
    try {
      payload = getFormValues();
      for (const field of FIELDS) {
        if (Number.isNaN(payload[field])) {
          showError("error-msg", "Please fill in all metric fields with valid numbers.");
          return;
        }
      }
    } catch (_) {
      showError("error-msg", "Invalid form input. Check all fields.");
      return;
    }

    setLoading("loading", true);
    btn.disabled = true;

    try {
      const resp = await fetch("/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        let msg = "Prediction failed. Run the local pipeline first if the model is not loaded.";
        try {
          const err = await resp.json();
          if (err.detail) {
            msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
          }
        } catch (_) { /* default */ }
        showError("error-msg", msg);
        return;
      }
      const data = await resp.json();
      showResult(data);
      updateExplainCards(payload);
      updateTimelineStep("predict", true);
      loadDriftSummary();
    } catch (_) {
      showError("error-msg", "Could not reach the prediction API. Is the server still running?");
    } finally {
      setLoading("loading", false);
      btn.disabled = false;
    }
  }

  function yn(value) {
    return value ? "Yes" : "No";
  }

  function updateTimelineStep(step, active) {
    const el = document.querySelector('.timeline-step[data-step="' + step + '"]');
    if (el) el.classList.toggle("done", active);
  }

  function renderSystemStatus(data) {
    document.getElementById("ss-api").textContent = data.api_health || "—";
    document.getElementById("ss-api").className = "value " + (data.api_health === "ok" ? "ok" : "warn");
    document.getElementById("ss-model").textContent = yn(data.model_loaded);
    document.getElementById("ss-data").textContent = yn(data.data_exists);
    document.getElementById("ss-model-file").textContent = yn(data.model_file_exists);
    document.getElementById("ss-eval").textContent = data.eval_status || "—";
    document.getElementById("ss-eval").className =
      "value " + (data.eval_status === "passed" ? "ok" : data.eval_status === "failed" ? "warn" : "");

    updateTimelineStep("health", data.api_health === "ok");
    updateTimelineStep("data", data.data_exists);
    updateTimelineStep("model", data.model_loaded && data.model_file_exists);
    updateTimelineStep("eval", data.eval_status === "passed");
  }

  async function refreshStatus() {
    hideError("pipeline-error");
    setLoading("status-loading", true);
    try {
      const resp = await fetch("/system-status");
      if (!resp.ok) throw new Error("Status request failed");
      renderSystemStatus(await resp.json());
    } catch (_) {
      showError("pipeline-error", "Could not refresh system status.");
    } finally {
      setLoading("status-loading", false);
    }
  }

  function renderPipelineResult(data) {
    const container = document.getElementById("pipeline-steps");
    container.innerHTML = "";
    (data.steps || []).forEach(function (step) {
      const div = document.createElement("div");
      div.className = "pipeline-step " + step.status;
      div.textContent = step.name + " — " + step.status + (step.detail ? " (" + step.detail + ")" : "");
      container.appendChild(div);
    });

    const msg = document.getElementById("pipeline-message");
    msg.textContent = data.message || data.error || "";

    if (data.status === "success") {
      hideError("pipeline-error");
      refreshStatus();
    } else {
      showError("pipeline-error", data.error || "Pipeline failed.");
    }
  }

  async function runPipeline() {
    hideError("pipeline-error");
    document.getElementById("pipeline-message").textContent = "";
    document.getElementById("pipeline-steps").innerHTML = "";
    const btn = document.getElementById("btn-run-pipeline");
    setLoading("pipeline-loading", true);
    btn.disabled = true;

    try {
      const resp = await fetch("/run-local-pipeline", { method: "POST" });
      const data = await resp.json();
      renderPipelineResult(data);
    } catch (_) {
      showError("pipeline-error", "Could not run the local pipeline.");
    } finally {
      setLoading("pipeline-loading", false);
      btn.disabled = false;
    }
  }

  async function checkUrl() {
    hideError("url-error");
    document.getElementById("url-note").textContent = "";
    const url = document.getElementById("website-url").value.trim();
    if (!url) {
      showError("url-error", "Please enter a website URL.");
      return;
    }

    const btn = document.getElementById("btn-check-url");
    setLoading("url-loading", true);
    btn.disabled = true;

    try {
      const resp = await fetch("/check-url-metrics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url }),
      });
      if (!resp.ok) {
        let msg = "Could not check the website URL.";
        try {
          const err = await resp.json();
          if (err.detail) msg = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
        } catch (_) { /* default */ }
        showError("url-error", msg);
        return;
      }
      const data = await resp.json();
      setFormValues(data);
      document.getElementById("url-note").textContent = data.note || "";
      await loadUrlHistory();
      loadDriftSummary();
      showPanel("dashboard", "predict");
    } catch (_) {
      showError("url-error", "Could not reach the URL check service.");
    } finally {
      setLoading("url-loading", false);
      btn.disabled = false;
    }
  }

  function formatCheckedAt(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleString();
    } catch (_) {
      return iso;
    }
  }

  function renderUrlHistory(items) {
    const section = document.getElementById("url-history-section");
    const list = document.getElementById("url-history-list");
    if (!section || !list) return;

    list.innerHTML = "";
    if (!items || items.length === 0) {
      section.hidden = true;
      return;
    }

    section.hidden = false;
    items.forEach(function (item) {
      const li = document.createElement("li");
      li.className = "url-history-item";
      li.setAttribute("role", "button");
      li.setAttribute("tabindex", "0");
      li.setAttribute("aria-label", "Load metrics for " + item.url);

      const urlSpan = document.createElement("span");
      urlSpan.className = "url-history-url";
      urlSpan.textContent = item.url;

      const metaSpan = document.createElement("span");
      metaSpan.className = "url-history-meta";
      const status = item.status_code != null ? String(item.status_code) : "—";
      const rt = item.response_time_ms != null ? Math.round(item.response_time_ms) + " ms" : "—";
      metaSpan.textContent = formatCheckedAt(item.checked_at) + " · HTTP " + status + " · " + rt;

      li.appendChild(urlSpan);
      li.appendChild(metaSpan);

      function selectHistory() {
        document.getElementById("website-url").value = item.url;
        setFormValues(item);
        document.getElementById("url-note").textContent = item.note || "";
        hideError("url-error");
      }

      li.addEventListener("click", selectHistory);
      li.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          selectHistory();
        }
      });

      list.appendChild(li);
    });
  }

  async function loadUrlHistory() {
    try {
      const resp = await fetch("/url-check-history");
      if (!resp.ok) return;
      const data = await resp.json();
      renderUrlHistory(data.items || []);
    } catch (_) {
      /* ignore */
    }
  }

  async function clearUrlHistory() {
    try {
      await fetch("/url-check-history", { method: "DELETE" });
      renderUrlHistory([]);
    } catch (_) {
      /* ignore */
    }
  }

  const PANEL_IDS = ["dashboard", "system-apis", "about"];
  const DASHBOARD_SECTIONS = ["system-status", "drift-summary", "openrouter-summary", "pipeline", "url-check", "predict"];

  function scrollToSection(sectionId) {
    const el = document.getElementById(sectionId);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  }

  function showPanel(panelId, sectionId) {
    if (PANEL_IDS.indexOf(panelId) < 0) return;

    PANEL_IDS.forEach(function (id) {
      const panel = document.getElementById(id);
      if (panel) panel.classList.toggle("active", id === panelId);
    });

    document.querySelectorAll(".tab-nav__link[data-section]").forEach(function (tab) {
      const href = tab.getAttribute("href");
      const isPanel = href === "#" + panelId;
      const isSection = sectionId && href === "#" + sectionId;
      tab.classList.toggle("active", isPanel || isSection);
    });

    const hash = sectionId && DASHBOARD_SECTIONS.indexOf(sectionId) >= 0
      ? sectionId
      : panelId;
    history.replaceState(null, "", "#" + hash);

    if (panelId === "dashboard" && sectionId && DASHBOARD_SECTIONS.indexOf(sectionId) >= 0) {
      scrollToSection(sectionId);
    }
  }

  function resolvePanelFromHash(hash) {
    if (PANEL_IDS.indexOf(hash) >= 0) {
      return { panel: hash, section: null };
    }
    if (DASHBOARD_SECTIONS.indexOf(hash) >= 0) {
      return { panel: "dashboard", section: hash };
    }
    return { panel: "dashboard", section: null };
  }

  function formatDriftTime(iso) {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString();
    } catch (_) {
      return iso;
    }
  }

  function renderDriftSummary(data) {
    const insufficientEl = document.getElementById("drift-insufficient");
    const insufficientText = document.getElementById("drift-insufficient-text");

    if (data.insufficient_data) {
      if (insufficientEl) insufficientEl.hidden = false;
      const count = data.observation_count != null ? data.observation_count : "?";
      const msg = data.message || "At least 5 observations are required for drift analysis.";
      if (insufficientText) {
        insufficientText.textContent = msg + " (" + count + " logged so far)";
      }
      const overall = document.getElementById("drift-overall");
      if (overall) {
        overall.textContent = "Insufficient data";
        overall.className = "value";
      }
      const scoreEl = document.getElementById("drift-score");
      if (scoreEl) scoreEl.textContent = "—";
      hideError("drift-error");
      return;
    }

    if (insufficientEl) insufficientEl.hidden = true;

    const detected = data.drift_detected || data.dataset_drift;
    const overall = document.getElementById("drift-overall");
    if (overall) {
      overall.textContent = detected ? "Drift Detected" : "No Drift";
      overall.className = "value " + (detected ? "warn" : "ok");
    }

    const scoreEl = document.getElementById("drift-score");
    if (scoreEl) {
      const score = typeof data.drift_score === "number" ? data.drift_score : 0;
      scoreEl.textContent = (score * 100).toFixed(1) + "%";
    }

    const recEl = document.getElementById("drift-recommendation");
    if (recEl) recEl.textContent = data.recommendation || "—";

    const genEl = document.getElementById("drift-generated");
    if (genEl) genEl.textContent = formatDriftTime(data.generated_at);

    const refEl = document.getElementById("drift-ref-rows");
    if (refEl) refEl.textContent = data.reference_rows != null ? String(data.reference_rows) : "—";

    const curEl = document.getElementById("drift-cur-rows");
    if (curEl) curEl.textContent = data.current_rows != null ? String(data.current_rows) : "—";

    const list = document.getElementById("drift-columns-list");
    if (list) {
      list.innerHTML = "";
      const cols = data.drifted_columns || [];
      if (cols.length === 0) {
        const li = document.createElement("li");
        li.textContent = "None";
        list.appendChild(li);
      } else {
        cols.forEach(function (col) {
          const li = document.createElement("li");
          li.textContent = col;
          list.appendChild(li);
        });
      }
    }

    const summaryText = document.getElementById("drift-summary-text");
    if (summaryText) summaryText.textContent = data.summary || "";

    hideError("drift-error");
  }

  async function loadDriftSummary() {
    setLoading("drift-loading", true);
    hideError("drift-error");
    try {
      const resp = await fetch("/drift");
      if (!resp.ok) {
        const err = await resp.json().catch(function () { return {}; });
        throw new Error(err.detail || "Drift request failed");
      }
      renderDriftSummary(await resp.json());
    } catch (err) {
      showError("drift-error", err.message || "Could not load drift summary.");
    } finally {
      setLoading("drift-loading", false);
    }
  }

  async function refreshDriftAnalysis() {
    const btn = document.getElementById("btn-refresh-drift");
    setLoading("drift-loading", true);
    hideError("drift-error");
    if (btn) btn.disabled = true;
    try {
      const resp = await fetch("/drift/run", { method: "POST" });
      if (!resp.ok) {
        const err = await resp.json().catch(function () { return {}; });
        throw new Error(err.detail || "Drift refresh failed");
      }
      renderDriftSummary(await resp.json());
    } catch (err) {
      showError("drift-error", err.message || "Could not refresh drift analysis.");
    } finally {
      setLoading("drift-loading", false);
      if (btn) btn.disabled = false;
    }
  }

  function renderOpenRouterSummary(data) {
    const generatedEl = document.getElementById("or-generated");
    const generatedAtEl = document.getElementById("or-generated-at");
    const sourceEl = document.getElementById("or-source");
    const previewEl = document.getElementById("or-preview");
    const viewBtn = document.getElementById("btn-view-openrouter");
    const heroLabel = document.getElementById("hero-openrouter-label");

    if (!data.exists) {
      if (generatedEl) generatedEl.textContent = "No";
      if (generatedAtEl) generatedAtEl.textContent = "—";
      if (sourceEl) sourceEl.textContent = "—";
      if (previewEl) previewEl.textContent = data.message || "Not generated yet.";
      if (viewBtn) viewBtn.hidden = true;
      if (heroLabel) heroLabel.textContent = "Not generated";
      hideError("openrouter-error");
      return;
    }

    if (generatedEl) generatedEl.textContent = "Yes";
    if (generatedAtEl) generatedAtEl.textContent = formatDriftTime(data.generated_at);
    const sourceLabel = data.openrouter_api_used ? "OpenRouter API" : "Local fallback";
    if (sourceEl) sourceEl.textContent = sourceLabel;
    if (previewEl) previewEl.textContent = data.preview || data.content || "—";
    if (viewBtn) viewBtn.hidden = false;
    if (heroLabel) {
      heroLabel.textContent = data.openrouter_api_used
        ? "Generated (OpenRouter)"
        : "Generated (local fallback)";
    }
    hideError("openrouter-error");
  }

  async function loadOpenRouterSummary() {
    setLoading("openrouter-loading", true);
    hideError("openrouter-error");
    try {
      const resp = await fetch("/reports/openrouter");
      if (!resp.ok) {
        const err = await resp.json().catch(function () { return {}; });
        throw new Error(err.detail || "OpenRouter request failed");
      }
      renderOpenRouterSummary(await resp.json());
    } catch (err) {
      showError("openrouter-error", err.message || "Could not load OpenRouter report.");
    } finally {
      setLoading("openrouter-loading", false);
    }
  }

  async function generateOpenRouterSummary() {
    const btn = document.getElementById("btn-generate-openrouter");
    setLoading("openrouter-loading", true);
    hideError("openrouter-error");
    if (btn) btn.disabled = true;
    try {
      const resp = await fetch("/reports/openrouter/run", { method: "POST" });
      if (!resp.ok) {
        const err = await resp.json().catch(function () { return {}; });
        throw new Error(err.detail || "OpenRouter generation failed");
      }
      const result = await resp.json();
      renderOpenRouterSummary({
        exists: true,
        generated_at: result.generated_at,
        source: result.source,
        openrouter_api_used: result.openrouter_api_used,
        preview: result.preview,
        content: result.preview,
        message: result.message,
      });
    } catch (err) {
      showError("openrouter-error", err.message || "Could not generate OpenRouter summary.");
    } finally {
      setLoading("openrouter-loading", false);
      if (btn) btn.disabled = false;
    }
  }

  function initTabs() {
    document.querySelectorAll(".tab-nav__link[data-section]").forEach(function (tab) {
      tab.addEventListener("click", function (e) {
        e.preventDefault();
        const target = tab.getAttribute("href");
        if (target && target.charAt(0) === "#") {
          const hash = target.slice(1);
          const resolved = resolvePanelFromHash(hash);
          showPanel(resolved.panel, resolved.section);
        }
      });
    });

    window.addEventListener("hashchange", function () {
      const resolved = resolvePanelFromHash(window.location.hash.replace("#", ""));
      showPanel(resolved.panel, resolved.section);
    });

    const initialHash = window.location.hash.replace("#", "");
    const resolved = resolvePanelFromHash(initialHash);
    showPanel(resolved.panel, resolved.section);
  }

  document.getElementById("btn-healthy").addEventListener("click", function () { setFormValues(HEALTHY); });
  document.getElementById("btn-outage").addEventListener("click", function () { setFormValues(OUTAGE); });
  document.getElementById("btn-clear").addEventListener("click", clearForm);
  document.getElementById("btn-predict").addEventListener("click", predict);
  document.getElementById("btn-refresh-status").addEventListener("click", refreshStatus);
  document.getElementById("btn-refresh-drift").addEventListener("click", refreshDriftAnalysis);
  document.getElementById("btn-generate-openrouter").addEventListener("click", generateOpenRouterSummary);
  document.getElementById("btn-run-pipeline").addEventListener("click", runPipeline);
  document.getElementById("btn-check-url").addEventListener("click", checkUrl);
  document.getElementById("btn-clear-url-history").addEventListener("click", clearUrlHistory);

  FIELDS.forEach(function (field) {
    document.getElementById(field).addEventListener("input", function () {
      updateExplainCards(getFormValues());
    });
  });

  initTabs();
  refreshStatus();
  loadDriftSummary();
  loadOpenRouterSummary();
  loadUrlHistory();
})();

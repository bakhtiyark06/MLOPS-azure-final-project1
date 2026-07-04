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
      const predictSection = document.getElementById("predict");
      if (predictSection) predictSection.scrollIntoView({ behavior: "smooth" });
    } catch (_) {
      showError("url-error", "Could not reach the URL check service.");
    } finally {
      setLoading("url-loading", false);
      btn.disabled = false;
    }
  }

  function initTabs() {
    const hash = window.location.hash;
    document.querySelectorAll(".tab-nav a[data-section]").forEach(function (tab) {
      tab.addEventListener("click", function (e) {
        e.preventDefault();
        const target = tab.getAttribute("href");
        document.querySelectorAll(".tab-nav a[data-section]").forEach(function (t) {
          t.classList.remove("active");
        });
        tab.classList.add("active");
        const el = document.querySelector(target);
        if (el) el.scrollIntoView({ behavior: "smooth" });
        history.replaceState(null, "", target);
      });
    });

    if (hash && document.querySelector('.tab-nav a[href="' + hash + '"]')) {
      document.querySelectorAll(".tab-nav a[data-section]").forEach(function (t) {
        t.classList.toggle("active", t.getAttribute("href") === hash);
      });
    }
  }

  document.getElementById("btn-healthy").addEventListener("click", function () { setFormValues(HEALTHY); });
  document.getElementById("btn-outage").addEventListener("click", function () { setFormValues(OUTAGE); });
  document.getElementById("btn-clear").addEventListener("click", clearForm);
  document.getElementById("btn-predict").addEventListener("click", predict);
  document.getElementById("btn-refresh-status").addEventListener("click", refreshStatus);
  document.getElementById("btn-run-pipeline").addEventListener("click", runPipeline);
  document.getElementById("btn-check-url").addEventListener("click", checkUrl);

  FIELDS.forEach(function (field) {
    document.getElementById(field).addEventListener("input", function () {
      updateExplainCards(getFormValues());
    });
  });

  initTabs();
  refreshStatus();
})();

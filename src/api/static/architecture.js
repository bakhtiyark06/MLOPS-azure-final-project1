/**
 * Premium Architecture Explorer — sections, SVG edges, Live Flow, timeline.
 */
(function () {
  "use strict";

  const FLOW_INTERVAL_MS = 1500;
  const DATA_URL = "/static/architecture-nodes.json";
  const PARTICLE_COUNT = 30;

  let data = null;
  let flowIndex = -1;
  let timelineIndex = -1;
  let flowTimer = null;
  let flowPaused = false;
  let liveFlowActive = false;
  let activeStageId = null;
  let selectedNodeId = null;
  let reducedMotion = false;
  let nodeAnchors = {};
  let edgeElements = [];
  let packetEl = null;
  let packetRaf = null;
  let packetStart = 0;
  let activeEdgeKey = null;
  let resizeObserver = null;
  let particlesRaf = null;

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const SECTION_ICONS = {
    user: "👤",
    monitor: "🌐",
    ml: "⚙",
    cicd: "🔄",
    serving: "⚡",
    obs: "📊",
    ai: "🤖",
    flow: "→",
  };

  async function init() {
    if (!$("#arch-canvas")) return;

    reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) document.body.classList.add("reduced-motion");

    try {
      const res = await fetch(DATA_URL);
      data = await res.json();
    } catch (e) {
      $("#arch-subtitle").textContent = "Failed to load architecture data.";
      return;
    }

    $("#arch-title").textContent = data.title || "Full System Architecture";
    $("#arch-subtitle").textContent = data.subtitle || "";

    renderStageTabs();
    renderSections();
    renderTimeline();
    bindControls();
    setupLayoutEngine();
    initParticles();
    updateProgress();
  }

  function nodeById(id) {
    return data.nodes.find((n) => n.id === id);
  }

  function sectionForNode(nodeId) {
    return data.sections?.find((s) => s.nodeIds?.includes(nodeId));
  }

  function laneClass(swimlane) {
    const map = {
      user: "lane-user",
      ml: "lane-ml",
      deploy: "lane-deploy",
      monitor: "lane-monitor",
      ai: "lane-ai",
    };
    return map[swimlane] || "";
  }

  function stageForSection(sectionId) {
    return data.presentationStages?.find(
      (s) => s.id === sectionId || s.swimlane === sectionId
    );
  }

  function renderStageTabs() {
    const container = $("#stage-tabs");
    if (!container) return;
    const stages = data.presentationStages || data.sections || [];
    container.innerHTML = "";

    stages.forEach((stage) => {
      const sectionId = stage.swimlane || stage.id;
      const section = data.sections?.find((s) => s.id === sectionId);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "stage-tab";
      btn.dataset.stage = sectionId;
      btn.textContent = section?.label || stage.title;
      btn.addEventListener("click", () => focusStage(sectionId));
      container.appendChild(btn);
    });
  }

  function renderSections() {
    const container = $("#arch-sections");
    if (!container) return;
    container.innerHTML = "";

    const sections = data.sections || [];
    sections.forEach((section) => {
      const sectionEl = document.createElement("div");
      sectionEl.className = "arch-section";
      sectionEl.dataset.section = section.id;

      const header = document.createElement("div");
      header.className = "arch-section-header";
      const icon = document.createElement("span");
      icon.className = "arch-section-icon";
      icon.textContent = SECTION_ICONS[section.icon] || "●";
      const title = document.createElement("span");
      title.textContent = section.label;
      header.appendChild(icon);
      header.appendChild(title);

      const nodesWrap = document.createElement("div");
      nodesWrap.className = "arch-section-nodes";

      section.nodeIds.forEach((nodeId) => {
        const node = nodeById(nodeId);
        if (!node) return;

        const el = document.createElement("div");
        el.className = `arch-node ${laneClass(node.swimlane)}`;
        if (node.id === "blocked") el.classList.add("lane-fail");
        el.dataset.nodeId = node.id;
        el.setAttribute("aria-label", node.label);
        el.textContent = node.label;

        nodesWrap.appendChild(el);
      });

      sectionEl.appendChild(header);
      sectionEl.appendChild(nodesWrap);
      container.appendChild(sectionEl);
    });
  }

  function renderTimeline() {
    const container = $("#arch-timeline");
    if (!container || !data.timelineFlow) return;
    container.innerHTML = "";

    data.timelineFlow.forEach((step, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "arch-timeline-step";
      btn.dataset.step = String(idx);
      btn.dataset.nodeId = step.nodeId;
      btn.setAttribute("aria-label", `Step ${step.step}: ${step.label}`);

      const dot = document.createElement("span");
      dot.className = "arch-timeline-dot";
      const label = document.createElement("span");
      label.className = "arch-timeline-label";
      label.textContent = step.label;

      btn.appendChild(dot);
      btn.appendChild(label);
      btn.addEventListener("click", () => goToTimelineStep(idx));
      container.appendChild(btn);
    });
  }

  function updateTimelineUI() {
    $$(".arch-timeline-step").forEach((el, idx) => {
      el.classList.toggle("is-active", idx === timelineIndex);
      el.classList.toggle("is-complete", timelineIndex >= 0 && idx < timelineIndex);
      el.setAttribute("aria-current", idx === timelineIndex ? "step" : "false");
    });
  }

  function setupLayoutEngine() {
    const canvas = $("#arch-canvas");
    if (!canvas) return;

    const recompute = () => {
      requestAnimationFrame(() => {
        computeNodeAnchors();
        renderEdges();
      });
    };

    resizeObserver = new ResizeObserver(recompute);
    resizeObserver.observe(canvas);
    window.addEventListener("resize", recompute);
    recompute();
  }

  function computeNodeAnchors() {
    const canvas = $("#arch-canvas");
    if (!canvas) return;
    const canvasRect = canvas.getBoundingClientRect();
    nodeAnchors = {};

    $$(".arch-node").forEach((el) => {
      const rect = el.getBoundingClientRect();
      const id = el.dataset.nodeId;
      nodeAnchors[id] = {
        cx: rect.left + rect.width / 2 - canvasRect.left,
        cy: rect.top + rect.height / 2 - canvasRect.top,
        top: rect.top - canvasRect.top,
        bottom: rect.bottom - canvasRect.top,
        left: rect.left - canvasRect.left,
        right: rect.right - canvasRect.left,
      };
    });
  }

  function edgePathD(from, to) {
    const a = nodeAnchors[from];
    const b = nodeAnchors[to];
    if (!a || !b) return "";

    const dx = b.cx - a.cx;
    const dy = b.cy - a.cy;
    const startX = dx > 0 ? a.right : a.left;
    const endX = dx > 0 ? b.left : b.right;
    const startY = a.cy;
    const endY = b.cy;
    const midX = (startX + endX) / 2;

    return `M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`;
  }

  function renderEdges() {
    const svg = $("#arch-edges");
    const canvas = $("#arch-canvas");
    if (!svg || !canvas || !data.edges) return;

    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.innerHTML = "";
    edgeElements = [];

    data.edges.forEach((edge) => {
      const d = edgePathD(edge.from, edge.to);
      if (!d) return;

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const edgeType = edge.type || "data";
      path.setAttribute("d", d);
      path.setAttribute("class", `arch-edge-path edge-${edgeType}`);
      path.dataset.from = edge.from;
      path.dataset.to = edge.to;
      path.dataset.key = `${edge.from}->${edge.to}`;
      svg.appendChild(path);
      edgeElements.push({ path, edge });
    });

    packetEl = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    packetEl.setAttribute("r", "5");
    packetEl.setAttribute("class", "arch-packet");
    svg.appendChild(packetEl);
  }

  function findEdge(from, to) {
    return edgeElements.find((e) => e.edge.from === from && e.edge.to === to);
  }

  function animatePacket(from, to) {
    if (reducedMotion || !packetEl) return;

    const entry = findEdge(from, to);
    if (!entry) {
      packetEl.classList.remove("is-visible");
      return;
    }

    const path = entry.path;
    const edgeType = entry.edge.type || "data";
    const colors = {
      data: "#3b82f6",
      deploy: "#22c55e",
      monitor: "#a855f7",
      auth: "#f97316",
      fail: "#ef4444",
    };
    packetEl.setAttribute("fill", colors[edgeType] || colors.data);

    edgeElements.forEach((e) => {
      e.path.classList.remove("is-active-edge");
    });
    path.classList.add("is-active-edge");
    activeEdgeKey = path.dataset.key;

    const length = path.getTotalLength();
    packetStart = performance.now();
    packetEl.classList.add("is-visible");

    if (packetRaf) cancelAnimationFrame(packetRaf);

    const duration = 900;
    const tick = (now) => {
      const t = Math.min(1, (now - packetStart) / duration);
      const point = path.getPointAtLength(t * length);
      packetEl.setAttribute("cx", point.x);
      packetEl.setAttribute("cy", point.y);
      if (t < 1) {
        packetRaf = requestAnimationFrame(tick);
      }
    };
    packetRaf = requestAnimationFrame(tick);
  }

  function setEdgeFlowState(active) {
    edgeElements.forEach((e) => {
      e.path.classList.toggle("is-flowing", active && !reducedMotion);
    });
  }

  function focusStage(sectionId) {
    activeStageId = sectionId;
    const stage = stageForSection(sectionId);
    const section = data.sections?.find((s) => s.id === sectionId);

    $$(".stage-tab").forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.stage === sectionId);
    });

    $$(".arch-section").forEach((el) => {
      el.classList.toggle("is-dimmed", el.dataset.section !== sectionId);
    });

    const noteEl = $("#arch-stage-note");
    const note = stage?.presenterNote || section?.presenterNote;
    if (noteEl) {
      if (note) {
        noteEl.textContent = note;
        noteEl.hidden = false;
      } else {
        noteEl.hidden = true;
      }
    }

    requestAnimationFrame(() => {
      computeNodeAnchors();
      renderEdges();
    });
  }

  function clearStageFocus() {
    activeStageId = null;
    $$(".stage-tab").forEach((tab) => tab.classList.remove("active"));
    $$(".arch-section").forEach((el) => el.classList.remove("is-dimmed"));
    $("#arch-stage-note").hidden = true;
  }

  function setNodeStates(options) {
    const { currentId, completedIds = [], dimOthers = false } = options;

    $$(".arch-node").forEach((el) => {
      const id = el.dataset.nodeId;
      const isCurrent = id === currentId;
      const isComplete = completedIds.includes(id);

      el.classList.toggle("is-active", isCurrent);
      el.classList.toggle("is-complete", isComplete && !isCurrent);
      el.classList.toggle("is-dimmed", dimOthers && !isCurrent && !isComplete);
      el.setAttribute("aria-current", isCurrent ? "step" : "false");
    });
  }

  function highlightNode(nodeId, options = {}) {
    const { fromFlow = false, skipTimeline = false } = options;
    selectedNodeId = nodeId;
    if (!nodeById(nodeId)) return;

    if (!fromFlow) {
      setNodeStates({ currentId: nodeId, dimOthers: !!activeStageId });
      if (activeStageId) {
        $$(".arch-node").forEach((el) => {
          const id = el.dataset.nodeId;
          const inSection = sectionForNode(id)?.id === activeStageId;
          el.classList.toggle("is-dimmed", id !== nodeId && !inSection);
        });
      }
    }

    if (!skipTimeline && data.timelineFlow) {
      const tIdx = data.timelineFlow.findIndex((s) => s.nodeId === nodeId);
      if (tIdx >= 0) {
        timelineIndex = tIdx;
        updateTimelineUI();
      }
    }
  }

  function resetHighlights() {
    flowIndex = -1;
    timelineIndex = -1;
    liveFlowActive = false;
    selectedNodeId = null;
    activeEdgeKey = null;
    setEdgeFlowState(false);
    if (packetRaf) cancelAnimationFrame(packetRaf);
    packetEl?.classList.remove("is-visible");

    $$(".arch-node").forEach((el) => {
      el.classList.remove("is-active", "is-complete", "is-dimmed");
      el.removeAttribute("aria-current");
    });

    clearStageFocus();
    updateTimelineUI();
    updateProgress();
  }

  function syncTimelineFromFlowNode(nodeId) {
    const tIdx = data.timelineFlow?.findIndex((s) => s.nodeId === nodeId) ?? -1;
    if (tIdx >= 0) {
      timelineIndex = tIdx;
      updateTimelineUI();
    }
  }

  function updateProgress() {
    const liveTotal = data.liveFlow?.length || 0;
    const timelineTotal = data.timelineFlow?.length || 0;

    if (liveFlowActive && flowIndex >= 0) {
      $("#flow-progress").textContent = `Live tour ${flowIndex + 1} / ${liveTotal}`;
    } else if (timelineIndex >= 0) {
      const step = data.timelineFlow[timelineIndex];
      $("#flow-progress").textContent = `Step ${step?.step || timelineIndex + 1} of ${timelineTotal} — ${step?.label || ""}`;
    } else {
      $("#flow-progress").textContent = `${timelineTotal}-step pipeline timeline`;
    }
  }

  function goToFlowStep(index) {
    if (!data.liveFlow || index < 0 || index >= data.liveFlow.length) return;
    flowIndex = index;
    const nodeId = data.liveFlow[index];
    const completed = data.liveFlow.slice(0, index);

    setNodeStates({
      currentId: nodeId,
      completedIds: completed,
      dimOthers: true,
    });

    if (index > 0) {
      animatePacket(data.liveFlow[index - 1], nodeId);
    }

    highlightNode(nodeId, { fromFlow: true, skipTimeline: false });
    syncTimelineFromFlowNode(nodeId);
    updateProgress();

    const section = sectionForNode(nodeId);
    if (section) {
      $$(".arch-section").forEach((el) => {
        el.classList.toggle("is-dimmed", el.dataset.section !== section.id);
      });
    }
  }

  function goToTimelineStep(index) {
    if (!data.timelineFlow || index < 0 || index >= data.timelineFlow.length) return;

    if (liveFlowActive) {
      stopLiveFlow();
      liveFlowActive = false;
    }

    timelineIndex = index;
    const step = data.timelineFlow[index];
    const nodeId = step.nodeId;

    const completed = data.timelineFlow.slice(0, index).map((s) => s.nodeId);
    setNodeStates({
      currentId: nodeId,
      completedIds: completed,
      dimOthers: false,
    });

    if (index > 0) {
      const prevNode = data.timelineFlow[index - 1].nodeId;
      animatePacket(prevNode, nodeId);
    }

    highlightNode(nodeId, { skipTimeline: true });
    updateTimelineUI();
    updateProgress();

    const sectionEl = document.querySelector(`[data-section="${sectionForNode(nodeId)?.id}"]`);
    sectionEl?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "nearest" });
  }

  function startLiveFlow() {
    stopLiveFlow();
    flowPaused = false;
    flowIndex = -1;
    liveFlowActive = true;
    clearStageFocus();
    setEdgeFlowState(true);
    $("#btn-pause").disabled = false;
    $("#btn-pause").textContent = "Pause";

    flowTimer = setInterval(() => {
      if (flowPaused) return;
      const next = flowIndex + 1;
      if (next >= data.liveFlow.length) {
        stopLiveFlow();
        liveFlowActive = false;
        setEdgeFlowState(false);
        return;
      }
      goToFlowStep(next);
    }, FLOW_INTERVAL_MS);

    goToFlowStep(0);
  }

  function stopLiveFlow() {
    if (flowTimer) {
      clearInterval(flowTimer);
      flowTimer = null;
    }
    $("#btn-pause").disabled = true;
  }

  function togglePause() {
    if (!flowTimer && flowIndex < 0) return;
    flowPaused = !flowPaused;
    $("#btn-pause").textContent = flowPaused ? "Resume" : "Pause";
    setEdgeFlowState(!flowPaused && liveFlowActive);
  }

  function initParticles() {
    if (reducedMotion) return;

    const canvas = $("#arch-particles");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let particles = [];
    let w = 0;
    let h = 0;

    function resize() {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    }

    function seed() {
      particles = Array.from({ length: PARTICLE_COUNT }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.15,
        vy: (Math.random() - 0.5) * 0.15,
        r: Math.random() * 1.5 + 0.5,
      }));
    }

    function draw() {
      if (document.hidden) {
        particlesRaf = requestAnimationFrame(draw);
        return;
      }
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "rgba(59, 130, 246, 0.35)";
      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      });
      particlesRaf = requestAnimationFrame(draw);
    }

    resize();
    seed();
    draw();
    window.addEventListener("resize", () => {
      resize();
      seed();
    });
  }

  function bindControls() {
    $("#btn-live-flow")?.addEventListener("click", startLiveFlow);
    $("#btn-pause")?.addEventListener("click", togglePause);
    $("#btn-reset")?.addEventListener("click", () => {
      stopLiveFlow();
      flowPaused = false;
      resetHighlights();
    });

    $("#btn-prev")?.addEventListener("click", () => {
      if (liveFlowActive && flowIndex > 0) {
        goToFlowStep(flowIndex - 1);
        return;
      }
      if (timelineIndex > 0) {
        goToTimelineStep(timelineIndex - 1);
      }
    });

    $("#btn-next")?.addEventListener("click", () => {
      if (liveFlowActive && data.liveFlow && flowIndex < data.liveFlow.length - 1) {
        goToFlowStep(flowIndex + 1);
        return;
      }
      if (data.timelineFlow) {
        if (timelineIndex < data.timelineFlow.length - 1) {
          goToTimelineStep(timelineIndex + 1);
        } else if (timelineIndex < 0) {
          goToTimelineStep(0);
        }
      }
    });

    document.addEventListener("keydown", (ev) => {
      if (ev.target.matches("input, textarea")) return;
      if (ev.key === "ArrowRight") {
        ev.preventDefault();
        $("#btn-next")?.click();
      } else if (ev.key === "ArrowLeft") {
        ev.preventDefault();
        $("#btn-prev")?.click();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

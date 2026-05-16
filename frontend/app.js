/* QML DataFlow Studio v2 — app.js
   Canvas → Execution binding:  deriveSpecFromCanvas() reads node params before every run.
   All API calls use relative /api/ paths (Flask serves both frontend and backend).
*/
"use strict";
(function () {

// ═══════════════════════════════════════════════════════════════════════════
// Utilities
// ═══════════════════════════════════════════════════════════════════════════
const $ = (id) => document.getElementById(id);
const qs = (sel, root) => (root || document).querySelector(sel);

function showEl(id, show = true) {
  const el = $(id); if (el) el.style.display = show ? "" : "none";
}

function setRunBar(id, msg, kind = "info") {
  const el = $(id); if (!el) return;
  el.style.display = "";
  el.className = ""; // reset
  const map = { running: "running", ok: "success", error: "error" };
  if (map[kind]) el.classList.add(map[kind]);
  el.textContent = msg;
}

function fmtPct(v) {
  if (v == null || v === "") return "--";
  const n = parseFloat(v);
  return isNaN(n) ? "--" : (n <= 1 ? (n * 100).toFixed(1) : n.toFixed(1)) + "%";
}

function fmtNum(v, dec = 3) {
  if (v == null || v === "") return "--";
  const n = parseFloat(v);
  return isNaN(n) ? "--" : n.toFixed(dec);
}

function buildTable(rows, maxRows = 20) {
  if (!rows || !rows.length) return "<p class='text-muted'>No data.</p>";
  const cols = Object.keys(rows[0]);
  const subset = rows.slice(0, maxRows);
  let h = "<table class='preview-table'><thead><tr>"
    + cols.map(c => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
  subset.forEach(r => {
    h += "<tr>" + cols.map(c => {
      const v = r[c]; return `<td>${v == null ? "" : v}</td>`;
    }).join("") + "</tr>";
  });
  return h + "</tbody></table>";
}

function downloadText(filename, text, mime = "text/plain") {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

function csvFromRows(rows) {
  if (!rows || !rows.length) return "";
  const cols = Object.keys(rows[0]);
  const lines = [cols.join(",")];
  rows.forEach(r => lines.push(cols.map(c => JSON.stringify(r[c] ?? "")).join(",")));
  return lines.join("\n");
}

// ═══════════════════════════════════════════════════════════════════════════
// Tab switching
// ═══════════════════════════════════════════════════════════════════════════
function showTab(name) {
  document.querySelectorAll(".tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.tab === name);
  });
  document.querySelectorAll(".tab-content").forEach(s => {
    s.classList.toggle("active", s.id === "tab-" + name);
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// Canvas state
// ═══════════════════════════════════════════════════════════════════════════
let canvasModel = { nodes: [], edges: [] };
let selectedNodeId = null;
let pendingSourceId = null;
let nextNodeId = 1;
let nextX = 20, nextY = 20;

// ═══════════════════════════════════════════════════════════════════════════
// App-level state
// ═══════════════════════════════════════════════════════════════════════════
let runHistory = [];        // [{label, spec, result}]
let activeModelId = null;   // set after a successful run
let activeFeatureCols = []; // used by predict tab
let predictionRows = [];    // last prediction result for export
let chartAccuracy = null;
let chartLoss = null;
let chartComparison = null;
let uploadedFileData = null; // from /api/upload, pending dialog mapping
let registryData = {};

// ═══════════════════════════════════════════════════════════════════════════
// Backend health
// ═══════════════════════════════════════════════════════════════════════════
async function checkHealth() {
  try {
    const r = await fetch("/api/health");
    const j = await r.json();
    const dot = $("status-dot"), txt = $("status-text");
    if (j.status === "ok") {
      dot.className = "status-dot ok";
      txt.textContent = `Backend v${j.version || "?"} online`;
    } else {
      dot.className = "status-dot err";
      txt.textContent = "Backend error";
    }
  } catch {
    const dot = $("status-dot"), txt = $("status-text");
    dot.className = "status-dot err";
    txt.textContent = "Backend offline";
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Registry — populates sidebar dropdowns + domain buttons
// ═══════════════════════════════════════════════════════════════════════════
async function initRegistry() {
  try {
    const r = await fetch("/api/registry");
    if (!r.ok) throw new Error("registry fetch failed");
    registryData = await r.json();
    buildDomainButtons(registryData.datasets || {});
    populateDropdowns(registryData);
  } catch (e) {
    console.warn("Registry load failed:", e);
    $("domain-btns").innerHTML = '<span class="text-muted">Could not load datasets.</span>';
  }
}

function buildDomainButtons(datasets) {
  const wrap = $("domain-btns");
  if (!wrap) return;
  if (!Object.keys(datasets).length) {
    wrap.innerHTML = '<span class="text-muted">No datasets configured.</span>';
    return;
  }
  wrap.innerHTML = "";
  Object.entries(datasets).forEach(([key, meta]) => {
    const btn = document.createElement("button");
    btn.className = "btn btn-sm";
    btn.textContent = meta.label || key;
    btn.title = meta.description || "";
    btn.addEventListener("click", () => loadDomainDataset(key, meta));
    wrap.appendChild(btn);
  });
}

function populateDropdowns(reg) {
  const encSel = $("sel-encoding");
  const ansSel = $("sel-ansatz");
  const optSel = $("sel-optimizer");
  if (!encSel || !ansSel || !optSel) return;

  if (reg.encoders && Object.keys(reg.encoders).length) {
    encSel.innerHTML = Object.entries(reg.encoders)
      .map(([k, v]) => `<option value="${k}">${v.label || k}</option>`).join("");
  }
  if (reg.ansatze && Object.keys(reg.ansatze).length) {
    ansSel.innerHTML = Object.entries(reg.ansatze)
      .map(([k, v]) => `<option value="${k}">${v.label || k}</option>`).join("");
  }
  if (reg.optimizers && Object.keys(reg.optimizers).length) {
    optSel.innerHTML = Object.entries(reg.optimizers)
      .map(([k, v]) => `<option value="${k}">${v.label || k}</option>`).join("");
  }
}

async function loadDomainDataset(key, meta) {
  const panel = $("objective-panel");
  if (panel) {
    panel.textContent = `Loading ${meta.label || key}…`;
    panel.style.display = "";
  }
  try {
    const r = await fetch(`/api/dataset/${key}`);
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);

    // Sync controls from recommended settings
    const rec = data.recommended || {};
    if (rec.encoder) setVal("sel-encoding", rec.encoder);
    if (rec.circuit) setVal("sel-ansatz", rec.circuit);
    if (rec.optimizer) setVal("sel-optimizer", rec.optimizer);
    if (rec.shots) $("inp-shots").value = rec.shots;
    if (rec.maxiter) $("inp-maxiter").value = rec.maxiter;

    // Sync / create Dataset node on canvas
    applyDatasetToCanvas(data);

    if (panel) {
      panel.innerHTML = `<strong>${data.domain || key}</strong> — ${data.description || ""} &nbsp;|&nbsp;
        ${data.n_rows} rows, ${data.feature_columns.length} features, label: <code>${data.label_column}</code>`;
    }
  } catch (e) {
    if (panel) panel.textContent = "Error: " + e.message;
    console.error(e);
  }
}

function setVal(id, value) {
  const el = $(id); if (!el) return;
  const opt = el.querySelector(`option[value="${value}"]`);
  if (opt) el.value = value;
}

function applyDatasetToCanvas(data) {
  const nq = Math.max(1, data.feature_columns.length);
  const params = {
    path: data.path,
    label: data.label_column,
    features: data.feature_columns.join(", "),
    n_rows: String(data.n_rows),
    domain: data.domain || ""
  };

  // Update or create Dataset node
  let ds = canvasModel.nodes.find(n => n.type === "dataset");
  if (!ds) {
    ds = makeNode("dataset", "Dataset", params, 20, 20);
    canvasModel.nodes.push(ds);
  } else {
    Object.assign(ds.params, params);
  }

  // Keep Circuit node qubit count in sync with feature count
  const cirNode = canvasModel.nodes.find(n => n.type === "circuit");
  if (cirNode) {
    cirNode.params.num_qubits = String(nq);
  }

  validateFlow();
  renderCanvas();
  if (ds) selectNode(ds.id);
}

// ═══════════════════════════════════════════════════════════════════════════
// Spec derivation — canvas is the source of truth
// ═══════════════════════════════════════════════════════════════════════════
function deriveSpecFromCanvas() {
  const byType = {};
  canvasModel.nodes.forEach(n => { byType[n.type] = n; });

  // Dataset
  const dsNode = byType["dataset"];
  let dataset;
  if (dsNode) {
    const feats = (dsNode.params.features || "")
      .split(",").map(s => s.trim()).filter(Boolean);
    dataset = {
      type: "csv",
      path: dsNode.params.path || null,
      label_column: dsNode.params.label || "",
      feature_columns: feats,
      test_size: parseFloat($("inp-test-size").value || 25) / 100,
      seed: 42
    };
  } else {
    dataset = {
      type: "csv",
      path: null,
      label_column: "",
      feature_columns: [],
      test_size: parseFloat($("inp-test-size").value || 25) / 100,
      seed: 42
    };
  }

  // Encoder — node params override sidebar
  const encNode = byType["encoder"];
  const encoder = {
    type: encNode?.params?.type || $("sel-encoding").value || "angle"
  };

  // Circuit — qubit count must equal feature count; derive from dataset if circuit node is missing/stale
  const cirNode = byType["circuit"];
  const featureCount = dataset.feature_columns.length;
  const nqRaw = parseInt(cirNode?.params?.num_qubits || featureCount, 10);
  const nq = featureCount > 0 ? featureCount : Math.max(1, nqRaw);
  const circuit = {
    type: cirNode?.params?.type || $("sel-ansatz").value || "realamplitudes",
    num_qubits: nq,
    reps: parseInt(cirNode?.params?.reps || $("inp-reps").value || 2, 10)
  };

  // Optimizer
  const optNode = byType["optimizer"];
  const optimizer = {
    type: optNode?.params?.type || $("sel-optimizer").value || "cobyla",
    maxiter: parseInt(optNode?.params?.maxiter || $("inp-maxiter").value || 20, 10)
  };

  const framework = $("sel-framework").value || "qiskit";
  const shots = parseInt($("inp-shots").value || 128, 10);

  return { framework, execution: { shots }, dataset, encoder, circuit, optimizer };
}

function validateSpec(spec) {
  const errs = [];
  if (!spec.dataset.path && spec.dataset.type === "csv") {
    errs.push("No dataset loaded. Load a domain dataset or upload a CSV.");
  }
  if (!spec.dataset.label_column) errs.push("No label column specified.");
  if (!spec.dataset.feature_columns.length) errs.push("No feature columns specified.");
  if (spec.circuit.num_qubits < 1) errs.push("Circuit needs ≥1 qubit.");
  return errs;
}

// ═══════════════════════════════════════════════════════════════════════════
// Flow validation (visual status)
// ═══════════════════════════════════════════════════════════════════════════
function validateFlow() {
  const el = $("flow-status");
  if (!el) return;
  const types = new Set(canvasModel.nodes.map(n => n.type));
  const required = ["dataset", "encoder", "circuit", "optimizer"];
  const missing = required.filter(t => !types.has(t));
  if (missing.length === 0) {
    el.className = "flow-status valid";
    el.textContent = "✓ Pipeline is complete — ready to run";
  } else {
    el.className = "flow-status invalid";
    el.textContent = `Missing: ${missing.join(", ")}`;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Canvas rendering
// ═══════════════════════════════════════════════════════════════════════════
const TYPE_COLORS = {
  dataset:   "#0f766e",
  encoder:   "#3b82f6",
  circuit:   "#8b5cf6",
  optimizer: "#f59e0b",
  output:    "#22c55e"
};

function makeNode(type, name, params, x, y) {
  return {
    id: nextNodeId++,
    type,
    name,
    pos: { x: x ?? nextX, y: y ?? nextY },
    params: { ...params }
  };
}

function createNodeElement(n) {
  const el = document.createElement("div");
  el.className = "node";
  el.style.left = n.pos.x + "px";
  el.style.top = n.pos.y + "px";
  el.dataset.id = String(n.id);
  if (n.id === selectedNodeId) el.classList.add("selected");

  const color = TYPE_COLORS[n.type] || "#64748b";
  el.innerHTML = `
    <div class="node-header">
      <span class="node-title">${n.name || n.type}</span>
      <span class="node-type-badge" style="background:${color}22;color:${color}">${n.type}</span>
    </div>
    ${Object.entries(n.params || {}).map(([k, v]) =>
      `<span class="node-param">${k}: <strong>${v}</strong></span>`
    ).join("")}
    <div class="ports">
      <span class="port in" title="Input port"></span>
      <span class="port out" title="Output port"></span>
    </div>`;

  el.querySelector(".port.in").addEventListener("click", e => {
    e.stopPropagation();
    if (pendingSourceId && pendingSourceId !== n.id) {
      addEdge(pendingSourceId, n.id);
      pendingSourceId = null;
    }
  });
  el.querySelector(".port.out").addEventListener("click", e => {
    e.stopPropagation();
    pendingSourceId = n.id;
    el.querySelector(".port.out").classList.add("active");
  });

  el.addEventListener("click", e => { e.stopPropagation(); selectNode(n.id); });
  enableDrag(el, n);
  return el;
}

function enableDrag(el, n) {
  let startX, startY, origX, origY, dragging = false;
  el.addEventListener("mousedown", e => {
    if (e.target.tagName === "INPUT") return;
    dragging = true; el.style.cursor = "grabbing";
    startX = e.clientX; startY = e.clientY;
    const cv = $("canvas");
    const cr = cv.getBoundingClientRect();
    const er = el.getBoundingClientRect();
    origX = er.left + cv.scrollLeft - cr.left;
    origY = er.top + cv.scrollTop - cr.top;
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
  const onMove = e => {
    if (!dragging) return;
    const nx = Math.max(0, origX + e.clientX - startX);
    const ny = Math.max(0, origY + e.clientY - startY);
    el.style.left = nx + "px"; el.style.top = ny + "px";
    n.pos = { x: nx, y: ny };
    renderWires();
  };
  const onUp = () => {
    dragging = false; el.style.cursor = "grab";
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  };
}

function renderCanvas() {
  const cv = $("canvas");
  if (!cv) return;
  cv.innerHTML = '<svg id="wires" style="position:absolute;inset:0;pointer-events:none;z-index:3;width:100%;height:100%;overflow:visible"></svg>';
  canvasModel.nodes.forEach(n => cv.appendChild(createNodeElement(n)));
  renderWires();
}

function renderWires() {
  const svg = $("wires");
  if (!svg) return;
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  const cv = $("canvas");
  const cr = cv.getBoundingClientRect();

  canvasModel.edges.forEach(e => {
    const srcEl = cv.querySelector(`.node[data-id="${e.source}"] .port.out`);
    const tgtEl = cv.querySelector(`.node[data-id="${e.target}"] .port.in`);
    if (!srcEl || !tgtEl) return;

    const s = srcEl.getBoundingClientRect();
    const t = tgtEl.getBoundingClientRect();
    const x1 = s.left + s.width / 2 - cr.left + cv.scrollLeft;
    const y1 = s.top + s.height / 2 - cr.top + cv.scrollTop;
    const x2 = t.left + t.width / 2 - cr.left + cv.scrollLeft;
    const y2 = t.top + t.height / 2 - cr.top + cv.scrollTop;

    const dx = Math.max(50, Math.abs(x2 - x1) / 2);
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#3b82f6");
    path.setAttribute("stroke-width", "2.5");
    path.setAttribute("stroke-linecap", "round");
    svg.appendChild(path);
  });
}

function addEdge(srcId, tgtId) {
  if (!canvasModel.edges.find(e => e.source === srcId && e.target === tgtId)) {
    canvasModel.edges.push({ source: srcId, target: tgtId });
  }
  renderWires();
}

function selectNode(id) {
  selectedNodeId = id;
  renderCanvas();
  const n = canvasModel.nodes.find(x => x.id === id);
  const info = $("selected-info"), params = $("node-params");
  if (!n) { info.textContent = "No node selected."; params.innerHTML = ""; return; }
  info.innerHTML = `<strong>${n.name || n.type}</strong> (id ${n.id})`;

  params.innerHTML = Object.entries(n.params || {}).map(([k, v]) =>
    `<label class="node-param" style="display:block;margin-bottom:6px">${k}:
      <input data-param="${k}" value="${v ?? ""}" style="width:100%;margin-top:2px;
        padding:4px 6px;border:1px solid var(--border2);border-radius:4px;font-size:12px" />
    </label>`
  ).join("");
}

// ═══════════════════════════════════════════════════════════════════════════
// Demo pipeline
// ═══════════════════════════════════════════════════════════════════════════
function buildDemoPipeline() {
  canvasModel = { nodes: [], edges: [] };
  nextNodeId = 1;

  const ds  = makeNode("dataset",   "Dataset",   { path: "", label: "target", features: "f1, f2, f3, f4" }, 20, 40);
  const enc = makeNode("encoder",   "Encoder",   { type: "angle" }, 230, 40);
  const cir = makeNode("circuit",   "Circuit",   { type: "realamplitudes", num_qubits: "4", reps: "2" }, 430, 40);
  const opt = makeNode("optimizer", "Optimizer", { type: "cobyla", maxiter: "20" }, 630, 40);
  const out = makeNode("output",    "Output",    { predictions: "true" }, 830, 40);

  canvasModel.nodes.push(ds, enc, cir, opt, out);
  canvasModel.edges.push(
    { source: ds.id, target: enc.id },
    { source: enc.id, target: cir.id },
    { source: cir.id, target: opt.id },
    { source: opt.id, target: out.id }
  );
  validateFlow();
  renderCanvas();
}

// ═══════════════════════════════════════════════════════════════════════════
// Upload + CSV mapper dialog
// ═══════════════════════════════════════════════════════════════════════════
async function handleUploadClick() {
  const fileEl = $("csv-file");
  const f = fileEl?.files?.[0];
  if (!f) { alert("Choose a file first."); return; }

  const form = new FormData(); form.append("file", f);
  try {
    const r = await fetch("/api/upload", { method: "POST", body: form });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || r.statusText);
    uploadedFileData = j;
    openMapperDialog(j);
  } catch (e) {
    alert("Upload failed: " + e.message);
  }
}

function openMapperDialog(data) {
  const dlg = $("csv-mapper");
  const labelSel = $("csv-label");
  const featSel = $("csv-features");
  const numOnly = $("csv-numeric-only");
  const health = $("csv-health");

  const allCols = data.columns || [];
  const numCols = data.numeric_columns || [];

  function rebuildOptions(numericOnly) {
    const cols = numericOnly ? numCols : allCols;
    labelSel.innerHTML = cols.map(c => `<option value="${c}">${c}</option>`).join("");
    featSel.innerHTML  = cols.map(c => `<option value="${c}">${c}</option>`).join("");

    // Auto-guess label = last column
    if (cols.length) labelSel.value = cols[cols.length - 1];
    // Auto-select all except label as features
    Array.from(featSel.options).forEach(o => {
      o.selected = o.value !== labelSel.value;
    });
    updateHealth();
  }

  function updateHealth() {
    const label = labelSel.value;
    const feats = Array.from(featSel.selectedOptions).map(o => o.value);
    const nq = Math.max(1, feats.length);
    health.innerHTML = feats.length === 0
      ? "Select at least one feature column."
      : `Label: <strong>${label}</strong> &nbsp;|&nbsp;
         Features: <strong>${feats.length}</strong> &nbsp;|&nbsp;
         Qubits needed: <strong>${nq}</strong> &nbsp;|&nbsp;
         Rows: <strong>${data.n_rows}</strong>`;
  }

  // Preview table
  if (data.preview) {
    $("mapper-preview-wrap").innerHTML = buildTable(data.preview, 8);
  }

  numOnly.addEventListener("change", () => rebuildOptions(numOnly.checked));
  labelSel.addEventListener("change", updateHealth);
  featSel.addEventListener("change", updateHealth);

  rebuildOptions(false);
  dlg.showModal();
}

function applyMapperDialog() {
  const labelSel = $("csv-label");
  const featSel  = $("csv-features");
  const label = labelSel.value;
  const feats = Array.from(featSel.selectedOptions).map(o => o.value);
  if (!feats.length) { alert("Select at least one feature column."); return; }

  $("csv-mapper").close();

  applyDatasetToCanvas({
    path: uploadedFileData.path,
    label_column: label,
    feature_columns: feats,
    n_rows: uploadedFileData.n_rows,
    domain: "custom",
    description: uploadedFileData.filename,
    recommended: {}
  });

  // Sync qubit count
  const nq = Math.max(1, feats.length);
  const cirNode = canvasModel.nodes.find(n => n.type === "circuit");
  if (cirNode) cirNode.params.num_qubits = String(nq);
  renderCanvas();
}

// ═══════════════════════════════════════════════════════════════════════════
// Run pipeline
// ═══════════════════════════════════════════════════════════════════════════
let runInProgress = false;

async function runPipeline() {
  if (runInProgress) return;

  const spec = deriveSpecFromCanvas();
  const errs = validateSpec(spec);
  if (errs.length) { alert("Cannot run:\n• " + errs.join("\n• ")); return; }

  runInProgress = true;
  $("btn-run").disabled = true;

  // Visual feedback
  const rb = $("run-bar");
  rb.style.display = "";
  rb.className = "running";
  rb.innerHTML = '<span class="spinner"></span> Running quantum pipeline…';

  // Mark nodes as running
  canvasModel.nodes.forEach(n => n.status = "running");
  renderCanvas();

  try {
    const r = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(spec)
    });
    const data = await r.json();
    if (!r.ok || data.status === "error") throw new Error(data.error || r.statusText);

    rb.className = "success";
    rb.textContent = `✓ Done in ${data.execution_time_s ?? "?"}s — Accuracy: ${fmtPct(data.accuracy)}`;

    // Persist model
    if (data.model_id) {
      activeModelId = data.model_id;
      activeFeatureCols = spec.dataset.feature_columns;
    }

    // Mark nodes ok
    canvasModel.nodes.forEach(n => n.status = "ok");
    renderCanvas();

    // Store in history
    runHistory.push({
      label: `Run ${runHistory.length + 1} — ${spec.encoder.type} | ${spec.circuit.type} | ${spec.optimizer.type}`,
      spec: { ...spec },
      result: data,
      timestamp: new Date().toLocaleTimeString()
    });

    // Populate results tab
    showResults(data, spec);

    // Update experiments tab
    updateRunHistory();

    // Switch to results
    showTab("results");

  } catch (e) {
    rb.className = "error";
    rb.textContent = "Error: " + e.message;
    canvasModel.nodes.forEach(n => n.status = "error");
    renderCanvas();
    console.error(e);
  } finally {
    runInProgress = false;
    $("btn-run").disabled = false;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Results display
// ═══════════════════════════════════════════════════════════════════════════
function showResults(data, spec) {
  showEl("no-results-msg", false);
  showEl("results-content", true);

  // Metrics
  $("m-acc").textContent       = fmtPct(data.accuracy);
  $("m-train-acc").textContent = fmtPct(data.train_accuracy);
  $("m-prec").textContent      = fmtNum(data.precision);
  $("m-recall").textContent    = fmtNum(data.recall);
  $("m-f1").textContent        = fmtNum(data.f1);
  $("m-auc").textContent       = fmtNum(data.roc_auc);
  $("m-epochs").textContent    = data.epochs ?? "--";
  $("m-time").textContent      = data.execution_time_s != null ? data.execution_time_s + "s" : "--";

  // Confusion matrix
  const cm = data.confusion_matrix;
  if (cm && cm.length === 2) {
    const v00 = cm[0][0], v01 = cm[0][1], v10 = cm[1][0], v11 = cm[1][1];
    $("cm00").innerHTML = `${v00}<br><span class="text-muted" style="font-size:10px">TN</span>`;
    $("cm01").innerHTML = `${v01}<br><span class="text-muted" style="font-size:10px">FP</span>`;
    $("cm10").innerHTML = `${v10}<br><span class="text-muted" style="font-size:10px">FN</span>`;
    $("cm11").innerHTML = `${v11}<br><span class="text-muted" style="font-size:10px">TP</span>`;
  }

  // Baseline
  const bl = data.baseline || {};
  $("base-acc").textContent = fmtPct(bl.test_accuracy);
  $("base-f1").textContent  = fmtNum(bl.f1);
  $("base-auc").textContent = fmtNum(bl.roc_auc);

  // Charts
  const lossCurve = data.loss_history || [];
  const accCurve  = data.accuracy_history || [];

  renderAccuracyChart(accCurve, data.accuracy);
  renderLossChart(lossCurve);

  const lossNote = $("loss-note");
  if (lossNote) {
    lossNote.textContent = (data.loss_history_real_points === 0)
      ? "Note: Loss curve is an estimated interpolation (optimizer did not emit per-step values)."
      : `Actual per-iteration loss values from optimizer callback (${data.loss_history_real_points} points).`;
  }

  // Run summary
  const rs = $("run-summary");
  if (rs) {
    rs.innerHTML = `
      <strong>Encoder:</strong> ${data.encoder || spec.encoder.type} &nbsp;|&nbsp;
      <strong>Circuit:</strong> ${data.circuit || spec.circuit.type} (${spec.circuit.num_qubits} qubits, ${spec.circuit.reps} reps) &nbsp;|&nbsp;
      <strong>Optimizer:</strong> ${data.optimizer || spec.optimizer.type} &nbsp;|&nbsp;
      <strong>Shots:</strong> ${spec.shots} &nbsp;|&nbsp;
      <strong>Dataset:</strong> ${spec.dataset.path ? spec.dataset.path.split("/").pop() : "—"} &nbsp;|&nbsp;
      <strong>Model ID:</strong> <code>${data.model_id || "—"}</code>
    `;
  }

  // Update predict tab
  if (data.model_id) {
    showEl("predict-no-model", false);
    showEl("predict-panel", true);
    $("predict-model-id").textContent = data.model_id;
    $("predict-features").textContent = spec.dataset.feature_columns.join(", ");
  }
}

function renderAccuracyChart(curve, finalAcc) {
  const ctx = $("chart-accuracy");
  if (!ctx) return;
  if (chartAccuracy) chartAccuracy.destroy();

  let pts;
  if (curve && curve.length > 1) {
    pts = curve;
  } else {
    // Synthetic progression toward final accuracy
    const acc = parseFloat(finalAcc) || 0.5;
    const n = 20;
    pts = Array.from({ length: n }, (_, i) => {
      const t = i / (n - 1);
      return parseFloat((acc * (1 - Math.exp(-3 * t)) + 0.5 * Math.exp(-3 * t)).toFixed(3));
    });
  }

  chartAccuracy = new Chart(ctx, {
    type: "line",
    data: {
      labels: pts.map((_, i) => i + 1),
      datasets: [{
        label: "Accuracy",
        data: pts,
        borderColor: "#0f766e",
        backgroundColor: "rgba(15,118,110,0.08)",
        fill: true,
        tension: 0.35,
        pointRadius: pts.length > 30 ? 0 : 3
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y: { min: 0, max: 1 } },
      plugins: { legend: { display: false } }
    }
  });
}

function renderLossChart(curve) {
  const ctx = $("chart-loss");
  if (!ctx) return;
  if (chartLoss) chartLoss.destroy();

  const pts = (curve && curve.length > 1) ? curve
    : Array.from({ length: 20 }, (_, i) => parseFloat((1 / (1 + i * 0.3)).toFixed(3)));

  chartLoss = new Chart(ctx, {
    type: "line",
    data: {
      labels: pts.map((_, i) => i + 1),
      datasets: [{
        label: "Loss",
        data: pts,
        borderColor: "#ef4444",
        backgroundColor: "rgba(239,68,68,0.08)",
        fill: true,
        tension: 0.35,
        pointRadius: pts.length > 30 ? 0 : 3
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y: { min: 0 } },
      plugins: { legend: { display: false } }
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// Run history / experiments
// ═══════════════════════════════════════════════════════════════════════════
function updateRunHistory() {
  const list = $("run-history-list");
  if (!list) return;

  if (!runHistory.length) {
    list.innerHTML = "<p class='text-muted' style='padding:20px 0;text-align:center'>No runs yet.</p>";
    showEl("comparison-card", false);
    return;
  }

  list.innerHTML = runHistory.map((run, i) => {
    const r = run.result;
    return `<div class="run-card">
      <div class="run-header">
        <span class="run-title">${run.label}</span>
        <span class="run-meta">${run.timestamp}</span>
      </div>
      <div class="run-metrics">
        <span class="run-badge q">Acc: ${fmtPct(r.accuracy)}</span>
        <span class="run-badge q">F1: ${fmtNum(r.f1)}</span>
        <span class="run-badge q">AUC: ${fmtNum(r.roc_auc)}</span>
        <span class="run-badge b">${run.spec.encoder.type} | ${run.spec.circuit.type} | ${run.spec.optimizer.type}</span>
        <span class="run-badge b">${r.execution_time_s ?? "?"}s</span>
      </div>
    </div>`;
  }).join("");

  if (runHistory.length >= 2) {
    showEl("comparison-card", true);
    renderComparisonChart();
  }
}

function renderComparisonChart() {
  const ctx = $("chart-comparison");
  if (!ctx) return;
  if (chartComparison) chartComparison.destroy();

  const labels = runHistory.map((r, i) => `Run ${i + 1}`);
  const accs = runHistory.map(r => parseFloat(r.result.accuracy) || 0);
  const f1s  = runHistory.map(r => parseFloat(r.result.f1) || 0);
  const aucs = runHistory.map(r => parseFloat(r.result.roc_auc) || 0);
  const baseAccs = runHistory.map(r => parseFloat(r.result.baseline?.test_accuracy) || 0);

  chartComparison = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "Test Accuracy",   data: accs,     backgroundColor: "rgba(15,118,110,0.7)" },
        { label: "F1 Score",        data: f1s,      backgroundColor: "rgba(59,130,246,0.7)" },
        { label: "ROC-AUC",         data: aucs,     backgroundColor: "rgba(139,92,246,0.7)" },
        { label: "Baseline Acc.",   data: baseAccs, backgroundColor: "rgba(148,163,184,0.5)", borderDash: [4,2] }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y: { min: 0, max: 1 } },
      plugins: { legend: { position: "top" } }
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// Predict tab
// ═══════════════════════════════════════════════════════════════════════════
async function runPredictions() {
  if (!activeModelId) { alert("Run a pipeline first to train a model."); return; }

  const fileEl = $("predict-file");
  const f = fileEl?.files?.[0];
  if (!f) { alert("Choose a file to predict on."); return; }

  const bar = $("predict-run-bar");
  bar.style.display = "";
  bar.textContent = "Uploading data for prediction…";

  try {
    // Upload the file first
    const form = new FormData(); form.append("file", f);
    const upResp = await fetch("/api/upload", { method: "POST", body: form });
    const upData = await upResp.json();
    if (!upResp.ok) throw new Error(upData.error || upResp.statusText);

    bar.textContent = "Running quantum predictions…";

    const r = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model_id: activeModelId,
        path: upData.path,
        feature_columns: activeFeatureCols
      })
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);

    bar.style.display = "none";
    predictionRows = data.results_preview || [];
    showEl("predict-results", true);
    $("predict-result-title").textContent =
      `Predictions — ${data.n_samples} rows, model ${activeModelId}`;
    $("predict-table-wrap").innerHTML = buildTable(predictionRows, 50);

  } catch (e) {
    bar.textContent = "Error: " + e.message;
    console.error(e);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Code generation
// ═══════════════════════════════════════════════════════════════════════════
function genQiskitCode(spec) {
  const enc = spec.encoder.type === "basis" ? "PauliFeatureMap"
            : spec.encoder.type === "iqp"   ? "PauliFeatureMap"
            : "ZZFeatureMap";
  const ansCls = spec.circuit.type === "efficientsu2" ? "EfficientSU2"
               : spec.circuit.type === "twolocal"     ? "TwoLocal"
               : "RealAmplitudes";
  const nq  = spec.circuit.num_qubits || 2;
  const rep = spec.circuit.reps || 2;
  const opt = (spec.optimizer.type || "cobyla").toUpperCase();
  const mi  = spec.optimizer.maxiter || 20;
  const feats = (spec.dataset.feature_columns || []).join('", "');
  const label = spec.dataset.label_column || "target";
  const path  = spec.dataset.path || "your_data.csv";

  return `"""
Qiskit VQC pipeline — generated by QML DataFlow Studio
Encoder : ${spec.encoder.type}  |  Ansatz: ${spec.circuit.type}  |  Optimizer: ${spec.optimizer.type}
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score, classification_report

from qiskit_aer import AerSimulator
from qiskit_aer.primitives import BackendSamplerV2
from qiskit.circuit.library import ${enc}, ${ansCls}
from qiskit_machine_learning.algorithms import VQC
from qiskit_algorithms.optimizers import ${opt}

# ── Data ─────────────────────────────────────────────────────────────────
df = pd.read_csv("${path}")
feature_cols = ["${feats}"]
label_col    = "${label}"

X = df[feature_cols].values.astype(float)
y = df[label_col].values.astype(int)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
scaler = MinMaxScaler(feature_range=(0, np.pi))
X_train = scaler.fit_transform(X_train)
X_test  = scaler.transform(X_test)

# ── Quantum circuit ───────────────────────────────────────────────────────
feature_map = ${enc}(feature_dimension=${nq}, reps=1)
ansatz      = ${ansCls}(num_qubits=${nq}, reps=${rep})

# ── Backend ───────────────────────────────────────────────────────────────
backend = AerSimulator(method="statevector")
sampler = BackendSamplerV2(backend=backend)

# ── VQC ──────────────────────────────────────────────────────────────────
optimizer = ${opt}(maxiter=${mi})
vqc = VQC(
    feature_map=feature_map,
    ansatz=ansatz,
    optimizer=optimizer,
    sampler=sampler,
)

# ── Train ─────────────────────────────────────────────────────────────────
vqc.fit(X_train, y_train)

# ── Evaluate ──────────────────────────────────────────────────────────────
preds = vqc.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, preds):.4f}")
print(classification_report(y_test, preds))
`;
}

function genPennyLaneCode(spec) {
  const nq  = spec.circuit.num_qubits || 2;
  const rep = spec.circuit.reps || 2;
  const mi  = spec.optimizer.maxiter || 20;
  const feats = (spec.dataset.feature_columns || []).join('", "');
  const label = spec.dataset.label_column || "target";
  const path  = spec.dataset.path || "your_data.csv";

  return `"""
PennyLane QML pipeline — generated by QML DataFlow Studio
Encoder: ${spec.encoder.type}  |  Ansatz: ${spec.circuit.type}  |  Optimizer: ${spec.optimizer.type}
"""
import numpy as np
import pandas as pd
import pennylane as qml
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import accuracy_score

# ── Data ─────────────────────────────────────────────────────────────────
df = pd.read_csv("${path}")
feature_cols = ["${feats}"]
label_col    = "${label}"

X = df[feature_cols].values.astype(float)
y = df[label_col].values.astype(int)
y = np.where(y == 0, -1, 1)  # PennyLane classifiers use {-1,+1}

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
scaler = MinMaxScaler(feature_range=(0, np.pi))
X_train = scaler.fit_transform(X_train)
X_test  = scaler.transform(X_test)

# ── Device ────────────────────────────────────────────────────────────────
n_qubits = ${nq}
dev = qml.device("default.qubit", wires=n_qubits)

# ── Ansatz ────────────────────────────────────────────────────────────────
def variational_circuit(params, x):
    # Angle encoding
    for i in range(n_qubits):
        qml.RY(x[i % len(x)], wires=i)
    # Variational layers
    n_layers = ${rep}
    for l in range(n_layers):
        for i in range(n_qubits):
            qml.RY(params[l, i, 0], wires=i)
            qml.RZ(params[l, i, 1], wires=i)
        for i in range(n_qubits - 1):
            qml.CNOT(wires=[i, i + 1])

@qml.qnode(dev)
def circuit(params, x):
    variational_circuit(params, x)
    return qml.expval(qml.PauliZ(0))

# ── Training ─────────────────────────────────────────────────────────────
def cost(params, X_batch, y_batch):
    preds = np.array([circuit(params, x) for x in X_batch])
    return np.mean((preds - y_batch) ** 2)

params = np.random.randn(${rep}, n_qubits, 2, requires_grad=True)
opt    = qml.AdamOptimizer(stepsize=0.05)

for epoch in range(${mi}):
    params, loss = opt.step_and_cost(lambda p: cost(p, X_train, y_train), params)
    if epoch % 5 == 0:
        print(f"Epoch {epoch:3d}  loss={loss:.4f}")

# ── Evaluate ──────────────────────────────────────────────────────────────
raw = np.array([circuit(params, x) for x in X_test])
preds = np.where(raw > 0, 1, 0)
true  = np.where(y_test > 0, 1, 0)
print(f"\\nTest Accuracy: {accuracy_score(true, preds):.4f}")
`;
}

function genFromCanvas() {
  const spec = deriveSpecFromCanvas();
  const framework = $("sel-framework").value || "qiskit";
  const code = framework === "pennylane" ? genPennyLaneCode(spec) : genQiskitCode(spec);
  $("code-preview").textContent = code;
}

// ═══════════════════════════════════════════════════════════════════════════
// Node editor — save node params back to model
// ═══════════════════════════════════════════════════════════════════════════
function saveSelectedNode() {
  if (!selectedNodeId) return;
  const n = canvasModel.nodes.find(x => x.id === selectedNodeId);
  if (!n) return;
  document.querySelectorAll("#node-params [data-param]").forEach(inp => {
    n.params[inp.getAttribute("data-param")] = inp.value;
  });
  validateFlow();
  renderCanvas();
  selectNode(n.id);
}

// ═══════════════════════════════════════════════════════════════════════════
// Import / export canvas model
// ═══════════════════════════════════════════════════════════════════════════
function exportModelJSON() {
  const data = JSON.stringify(canvasModel, null, 2);
  downloadText("pipeline_model.json", data, "application/json");
}

function importModelFromJSON(json) {
  try {
    const m = JSON.parse(json);
    if (!Array.isArray(m.nodes)) throw new Error("Invalid model JSON");
    canvasModel = {
      nodes: m.nodes.map(n => ({ ...n, id: Number(n.id) })),
      edges: Array.isArray(m.edges) ? m.edges : []
    };
    nextNodeId = canvasModel.nodes.reduce((mx, n) => Math.max(mx, n.id), 0) + 1;
    validateFlow();
    renderCanvas();
  } catch (e) {
    alert("Failed to load model: " + e.message);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Bootstrap
// ═══════════════════════════════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {

  // ── Tab switching ──────────────────────────────────────────────────────
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => showTab(btn.dataset.tab));
  });

  // ── Init backend ──────────────────────────────────────────────────────
  checkHealth();
  setInterval(checkHealth, 30000);
  initRegistry();

  // ── Canvas toolbar ────────────────────────────────────────────────────
  function addCanvasNode(type, name, params) {
    const n = makeNode(type, name, params, nextX, nextY);
    nextX += 180; if (nextX > 800) { nextX = 20; nextY += 130; }
    canvasModel.nodes.push(n);
    validateFlow();
    renderCanvas();
    selectNode(n.id);
  }

  document.getElementById("btn-add-dataset")?.addEventListener("click", () =>
    addCanvasNode("dataset", "Dataset", { path: "", label: "target", features: "f1, f2" }));
  document.getElementById("btn-add-encoder")?.addEventListener("click", () =>
    addCanvasNode("encoder", "Encoder", { type: "angle" }));
  document.getElementById("btn-add-circuit")?.addEventListener("click", () =>
    addCanvasNode("circuit", "Circuit", { type: "realamplitudes", num_qubits: "2", reps: "2" }));
  document.getElementById("btn-add-optimizer")?.addEventListener("click", () =>
    addCanvasNode("optimizer", "Optimizer", { type: "cobyla", maxiter: "20" }));
  document.getElementById("btn-add-output")?.addEventListener("click", () =>
    addCanvasNode("output", "Output", { predictions: "true" }));

  document.getElementById("btn-demo-pipeline")?.addEventListener("click", buildDemoPipeline);
  document.getElementById("btn-export-model")?.addEventListener("click", exportModelJSON);
  document.getElementById("btn-load-model")?.addEventListener("click", () =>
    document.getElementById("file-load-model")?.click());

  document.getElementById("file-load-model")?.addEventListener("change", ev => {
    const f = ev.target.files?.[0]; if (!f) return;
    const rdr = new FileReader();
    rdr.onload = () => importModelFromJSON(rdr.result);
    rdr.readAsText(f);
    ev.target.value = "";
  });

  // Click on canvas background deselects
  $("canvas")?.addEventListener("click", () => {
    selectedNodeId = null;
    pendingSourceId = null;
    renderCanvas();
    const info = $("selected-info");
    if (info) info.textContent = "Click a node to edit it.";
    const np = $("node-params");
    if (np) np.innerHTML = "";
  });

  // ── Node editor ───────────────────────────────────────────────────────
  document.getElementById("btn-save-node")?.addEventListener("click", saveSelectedNode);
  document.getElementById("btn-delete-node")?.addEventListener("click", () => {
    if (!selectedNodeId) return;
    canvasModel.nodes = canvasModel.nodes.filter(n => n.id !== selectedNodeId);
    canvasModel.edges = canvasModel.edges.filter(
      e => e.source !== selectedNodeId && e.target !== selectedNodeId
    );
    selectedNodeId = null;
    validateFlow();
    renderCanvas();
    const info = $("selected-info"), np = $("node-params");
    if (info) info.textContent = "Click a node to edit it.";
    if (np) np.innerHTML = "";
  });

  // ── Upload ────────────────────────────────────────────────────────────
  document.getElementById("btn-upload")?.addEventListener("click", handleUploadClick);

  // ── CSV mapper dialog ─────────────────────────────────────────────────
  document.getElementById("csv-apply")?.addEventListener("click", applyMapperDialog);
  document.getElementById("csv-cancel")?.addEventListener("click", () =>
    document.getElementById("csv-mapper")?.close());

  // ── Run pipeline ──────────────────────────────────────────────────────
  document.getElementById("btn-run")?.addEventListener("click", runPipeline);
  document.getElementById("btn-cancel")?.addEventListener("click", () => {
    runInProgress = false;
    $("btn-run").disabled = false;
    const rb = $("run-bar"); if (rb) { rb.textContent = "Cancelled."; rb.className = ""; }
  });

  // ── Predict ───────────────────────────────────────────────────────────
  document.getElementById("btn-predict")?.addEventListener("click", runPredictions);
  document.getElementById("btn-export-predictions")?.addEventListener("click", () => {
    if (!predictionRows.length) return;
    downloadText("predictions.csv", csvFromRows(predictionRows), "text/csv");
  });

  // ── Code tab ──────────────────────────────────────────────────────────
  document.getElementById("btn-gen-qiskit")?.addEventListener("click", () => {
    $("code-preview").textContent = genQiskitCode(deriveSpecFromCanvas());
  });
  document.getElementById("btn-gen-pennylane")?.addEventListener("click", () => {
    $("code-preview").textContent = genPennyLaneCode(deriveSpecFromCanvas());
  });
  document.getElementById("btn-gen-from-model")?.addEventListener("click", genFromCanvas);
  document.getElementById("btn-download-code")?.addEventListener("click", () => {
    const code = $("code-preview").textContent || "";
    if (!code.trim()) return;
    const framework = $("sel-framework").value || "qiskit";
    downloadText(`pipeline_${framework}.py`, code, "text/x-python");
  });
  document.getElementById("btn-export-spec")?.addEventListener("click", () => {
    const spec = deriveSpecFromCanvas();
    downloadText("pipeline_spec.json", JSON.stringify(spec, null, 2), "application/json");
  });

  // ── Initial canvas ────────────────────────────────────────────────────
  buildDemoPipeline();
});

})(); // end IIFE

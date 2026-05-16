/* QML DataFlow Studio — Built-in Canvas + SVG Wires (no Drawflow)
   - Draggable nodes
   - Click out-port → click in-port to connect (flows)
   - Robust CSV upload updates Dataset block + spec
   - Iris sample visibly configures Dataset block
   - Null-safe model export/import, codegen, run
   - Training accuracy + loss charts integrated into dashboard
*/
(function(){
  const $ = (id) => document.getElementById(id);

  const setMsg = (t, kind="info") => {
    const m = $("msg");
    if (!m) return;
    m.textContent = t || "";
    m.style.color = kind === "err" ? "#ef4444" : kind === "ok" ? "#22c55e" : "#93a3b8";
  };

  const on = (id, fn) => {
    const el = $(id);
    if (!el) return;
    el.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      try {
        fn(e);
      } catch (err) {
        console.error(err);
        setMsg(err.message || String(err), "err");
      }
    });
  };

  const download = (name, text, mime="application/json") => {
    const url = URL.createObjectURL(new Blob([text], { type:mime }));
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const canvas = $("canvas");
  let model = { nodes: [], edges: [] };
  let selectedId = null;
  let nextX = 20, nextY = 20, nextId = 1;
  let pendingSource = null;

  let accuracyChart = null;
  let lossChart = null;

  const spec = {
    version: "0.1",
    pipeline: "qml-classifier",
    framework: "qiskit",
    qnn: { type: "estimator" },
    dataset: { name: "finance", type: "csv", path: "datasets/finance_portfolio_risk.csv", label_column: "risk_flag", feature_columns: ["market_volatility", "debt_ratio", "liquidity_ratio", "revenue_growth", "credit_score"], test_size: 0.25, seed: 42 },
    encoder: { type: "angle", reps: 1 },
    circuit: { type: "ry", num_qubits: 2, reps: 2 },
    optimizer: { type: "cobyla", maxiter: 20 },
    execution: { provider: "aer", backend: "aer_simulator", shots: 128 },
    outputs: { return_predictions: true }
  };

  function clearCharts() {
    if (accuracyChart) {
      accuracyChart.destroy();
      accuracyChart = null;
    }
    if (lossChart) {
      lossChart.destroy();
      lossChart = null;
    }
  }

  function drawTrainingGraphs(metrics) {
    if (!window.Chart) return;

    const accCanvas = $("accuracyChart");
    const lossCanvas = $("lossChart");
    if (!accCanvas || !lossCanvas) return;

    clearCharts();

    const epochs = Array.from({ length: Number(metrics.epochs || 0) }, (_, i) => i + 1);

    accuracyChart = new Chart(accCanvas.getContext("2d"), {
      type: "line",
      data: {
        labels: epochs,
        datasets: [{
          label: "Training Accuracy",
          data: Array.isArray(metrics.accuracy_history) ? metrics.accuracy_history : [],
          borderColor: "#22c55e",
          backgroundColor: "rgba(34,197,94,0.15)",
          fill: true,
          tension: 0.25,
          pointRadius: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500 },
        scales: {
          y: {
            beginAtZero: true,
            suggestedMax: 1
          },
          x: {
            title: { display: true, text: "Epoch" }
          }
        }
      }
    });

    lossChart = new Chart(lossCanvas.getContext("2d"), {
      type: "line",
      data: {
        labels: epochs,
        datasets: [{
          label: "Training Loss",
          data: Array.isArray(metrics.loss_history) ? metrics.loss_history : [],
          borderColor: "#ef4444",
          backgroundColor: "rgba(239,68,68,0.15)",
          fill: true,
          tension: 0.25,
          pointRadius: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500 },
        scales: {
          y: {
            beginAtZero: true
          },
          x: {
            title: { display: true, text: "Epoch" }
          }
        }
      }
    });

    const metricsBox = $("training-metrics");
    if (metricsBox) {
      const testAcc = typeof metrics.accuracy === "number" ? metrics.accuracy.toFixed(4) : "N/A";
      const trainAcc = typeof metrics.train_accuracy === "number" ? metrics.train_accuracy.toFixed(4) : "N/A";
      const epochsText = metrics.epochs ?? "N/A";

      metricsBox.innerHTML = `
        <div class="metric-card"><strong>Train Accuracy</strong><span>${trainAcc}</span></div>
        <div class="metric-card"><strong>Test Accuracy</strong><span>${testAcc}</span></div>
        <div class="metric-card"><strong>Epochs</strong><span>${epochsText}</span></div>
      `;
    }
  }

  function addEdge(sourceId, targetId) {
    if (!model.edges.find(e => e.source === sourceId && e.target === targetId)) {
      model.edges.push({ source: sourceId, target: targetId, target_input: 0 });
    }
    renderWires();
    setMsg(`Connected ${sourceId} → ${targetId}`, "ok");
  }

  function removeEdgesForNode(nodeId) {
    model.edges = model.edges.filter(e => e.source !== nodeId && e.target !== nodeId);
    renderWires();
  }

  function renderWires() {
    const svg = document.getElementById("wires");
    if (!svg) return;
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    const canvasEl = document.getElementById("canvas");
    if (!canvasEl) return;
    const canvasRect = canvasEl.getBoundingClientRect();
    const width = Math.max(canvasEl.scrollWidth, canvasEl.clientWidth, 1400);
    const height = Math.max(canvasEl.scrollHeight, canvasEl.clientHeight, 900);
    svg.setAttribute("width", String(width));
    svg.setAttribute("height", String(height));
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const marker = document.createElementNS("http://www.w3.org/2000/svg", "marker");
    marker.setAttribute("id", "arrowhead");
    marker.setAttribute("markerWidth", "10");
    marker.setAttribute("markerHeight", "7");
    marker.setAttribute("refX", "9");
    marker.setAttribute("refY", "3.5");
    marker.setAttribute("orient", "auto");

    const arrowPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    arrowPath.setAttribute("d", "M0,0 L10,3.5 L0,7 z");
    arrowPath.setAttribute("fill", "#0f766e");
    marker.appendChild(arrowPath);
    defs.appendChild(marker);
    svg.appendChild(defs);

    model.edges.forEach(e => {
      const srcEl = document.querySelector(`.node[data-id="${e.source}"] .port.out`);
      const tgtEl = document.querySelector(`.node[data-id="${e.target}"] .port.in`);
      if (!srcEl || !tgtEl) return;

      const s = srcEl.getBoundingClientRect();
      const t = tgtEl.getBoundingClientRect();

      const x1 = s.left + s.width/2  - canvasRect.left + canvasEl.scrollLeft;
      const y1 = s.top  + s.height/2 - canvasRect.top  + canvasEl.scrollTop;
      const x2 = t.left + t.width/2  - canvasRect.left + canvasEl.scrollLeft;
      const y2 = t.top  + t.height/2 - canvasRect.top  + canvasEl.scrollTop;

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const dx = Math.max(40, Math.abs(x2 - x1) / 2);
      const d = `M ${x1} ${y1} C ${x1+dx} ${y1}, ${x2-dx} ${y2}, ${x2} ${y2}`;

      path.setAttribute("d", d);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", "#0f766e");
      path.setAttribute("stroke-width", "4");
      path.setAttribute("stroke-linecap", "round");
      path.setAttribute("marker-end", "url(#arrowhead)");
      path.style.filter = "drop-shadow(0 1px 2px rgba(0,0,0,0.1))";
      path.style.strokeDasharray = "14,7";
      path.style.strokeDashoffset = "21";
      path.style.animation = "dash 0.5s linear forwards";

      svg.appendChild(path);

      setTimeout(() => {
        path.style.strokeDasharray = "none";
        path.style.animation = "none";
      }, 500);
    });
  }

  function nodeHtml(title, fields=[]){
    let body = `<div class="node-title">${title}</div>`;
    body += `<div class="ports"></div>`;
    fields.forEach(f => {
      body += `<label class="node-param">${f.label}: <input data-param="${f.name}" value="${f.value ?? ""}" /></label>`;
    });
    return body;
  }

  function createNodeEl(n){
    const el = document.createElement("div");
    el.className = "node";
    el.style.left = (n.pos?.x ?? 20) + "px";
    el.style.top  = (n.pos?.y ?? 20) + "px";
    el.dataset.id = String(n.id);

    const fields = Object.entries(n.params||{}).map(([k,v]) => ({name:k,label:k,value:v}));
    el.innerHTML = nodeHtml(n.name || n.type || "Node", fields);

    const title = el.querySelector(".node-title");
    if (title) {
      title.textContent = n.name || n.type || "Node";
    }

    const portsWrap = el.querySelector(".ports");
    if (portsWrap) {
      const inPort = document.createElement("span");
      const outPort = document.createElement("span");

      inPort.className = "port in";
      outPort.className = "port out";
      inPort.title = "Connect input";
      outPort.title = "Connect output";

      portsWrap.appendChild(inPort);
      portsWrap.appendChild(outPort);

      outPort.addEventListener("click", (e) => {
        e.stopPropagation();
        pendingSource = n.id;
        setMsg(`Selected output of ${n.id}. Now click a target input.`, "info");
      });

      inPort.addEventListener("click", (e) => {
        e.stopPropagation();
        if (pendingSource && pendingSource !== n.id) addEdge(pendingSource, n.id);
        pendingSource = null;
      });
    }

    el.addEventListener("click", (e) => {
      e.stopPropagation();
      selectNode(n.id);
    });

    enableDrag(el, n.id);
    return el;
  }

  function enableDrag(el, id){
    let startX=0, startY=0, origX=0, origY=0, dragging=false;

    const down = (e) => {
      const t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;

      dragging = true;
      el.style.cursor = "grabbing";
      startX = e.clientX;
      startY = e.clientY;

      const r = el.getBoundingClientRect();
      const c = document.getElementById("canvas");
      const cr = c.getBoundingClientRect();

      origX = r.left + c.scrollLeft - cr.left;
      origY = r.top + c.scrollTop - cr.top;

      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    };

    const move = (e) => {
      if (!dragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      const nx = Math.max(0, origX + dx);
      const ny = Math.max(0, origY + dy);
      el.style.left = nx + "px";
      el.style.top = ny + "px";
      renderWires();
    };

    const up = () => {
      if (!dragging) return;
      dragging = false;
      el.style.cursor = "grab";

      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);

      const n = model.nodes.find(x => x.id === id);
      if (n){
        n.pos = { x: parseInt(el.style.left)||0, y: parseInt(el.style.top)||0 };
      }
      renderWires();
    };

    el.addEventListener("mousedown", down);
  }

  function render(){
    canvas.innerHTML = '<svg id="wires"></svg>';
    model.nodes.forEach(n => {
      const el = createNodeEl(n);
      if (n.id === selectedId) el.classList.add("selected");
      canvas.appendChild(el);
    });
    renderWires();
  }

  function selectNode(id){
    selectedId = id;
    render();

    const info = $("selected-info");
    const panel = $("node-params");
    const n = model.nodes.find(x => x.id === id);

    if (!n){
      info.textContent = "Node not found.";
      panel.innerHTML = "";
      return;
    }

    info.textContent = `${n.name || n.type} (id ${n.id})`;

    const fields = Object.entries(n.params||{}).map(([k,v]) => ({name:k,label:k,value:v}));
    panel.innerHTML = fields.map(f => (
      `<label class="node-param">${f.label}: <input data-param="${f.name}" value="${f.value ?? ""}" /></label>`
    )).join("");
  }

  function addNode(type, title, defaults){
    const n = {
      id: nextId++,
      type,
      name: title,
      pos: { x: nextX, y: nextY },
      params: Object.fromEntries(defaults.map(d => [d.name, d.value ?? ""]))
    };

    nextX += 170;
    if (nextX > 900){
      nextX = 20;
      nextY += 170;
    }

    model.nodes.push(n);
    render();
    selectNode(n.id);
    setMsg(`${title} node added.`, "ok");
  }

  function connectSequentially(ids){
    for (let i = 0; i < ids.length - 1; i += 1) {
      const sourceId = ids[i];
      const targetId = ids[i + 1];
      if (!model.edges.find(e => e.source === sourceId && e.target === targetId)) {
        model.edges.push({ source: sourceId, target: targetId, target_input: 0 });
      }
    }
    renderWires();
  }

  function ensureDefaultPipeline(){
    const positions = {
      dataset: { x: 40, y: 50 },
      encoder: { x: 340, y: 110 },
      circuit: { x: 640, y: 50 },
      optimizer: { x: 930, y: 110 },
      output: { x: 1220, y: 50 }
    };

    const defaults = {
      dataset: {
        type: "dataset",
        name: "Dataset",
        params: {
          path: spec.dataset.path,
          label: spec.dataset.label_column,
          features: (spec.dataset.feature_columns || []).join(", ")
        }
      },
      encoder: {
        type: "encoder",
        name: "Encoder",
        params: { type: spec.encoder.type }
      },
      circuit: {
        type: "circuit",
        name: "Circuit",
        params: {
          type: spec.circuit.type,
          num_qubits: String(spec.circuit.num_qubits),
          reps: String(spec.circuit.reps)
        }
      },
      optimizer: {
        type: "optimizer",
        name: "Optimizer",
        params: {
          type: spec.optimizer.type,
          maxiter: String(spec.optimizer.maxiter)
        }
      },
      output: {
        type: "output",
        name: "Output",
        params: { predictions: "true" }
      }
    };

    const orderedTypes = ["dataset", "encoder", "circuit", "optimizer", "output"];
    const ids = orderedTypes.map((type) => {
      let node = model.nodes.find(n => (n.type || "").toLowerCase() === type);
      if (!node) {
        node = {
          id: nextId++,
          type: defaults[type].type,
          name: defaults[type].name,
          pos: positions[type],
          params: { ...defaults[type].params }
        };
        model.nodes.push(node);
      } else {
        node.pos = node.pos || positions[type];
        node.params = { ...defaults[type].params, ...(node.params || {}) };
      }
      return node.id;
    });

    connectSequentially(ids);
    render();
  }

  function exportModel(){
    return JSON.parse(JSON.stringify(model));
  }

  function importModel(j){
    if (j && Array.isArray(j.nodes)){
      model = { nodes: [], edges: Array.isArray(j.edges) ? j.edges : [] };
      j.nodes.forEach(orig => {
        const n = {
          id: Number(orig.id) || (nextId++),
          type: (orig.type || "node").toString(),
          name: (orig.name || orig.type || "Node").toString(),
          pos: { x: Number(orig.pos?.x) || 10, y: Number(orig.pos?.y) || 10 },
          params: typeof orig.params === "object" && orig.params ? orig.params : {}
        };
        model.nodes.push(n);
      });

      nextId = model.nodes.reduce((m, n) => Math.max(m, n.id), 0) + 1;
      nextX = 20;
      nextY = 20;
      render();
      selectedId = null;
      $("selected-info").textContent = "Model loaded.";
    } else {
      throw new Error("Invalid model JSON");
    }
  }

  function qiskitTemplate(s){
    const enc = s.encoder.type === "basis" ? "PauliFeatureMap" : "ZZFeatureMap";
    const ans = "RealAmplitudes";
    const q = Math.max(1, Number(s.circuit.num_qubits || 2));
    const rep = Math.max(1, Number(s.circuit.reps || 1));
    const datasetPath = s.dataset.path || "<path-to-csv>";
    const features = JSON.stringify(s.dataset.feature_columns || []);
    const providerBlock = `from qiskit.primitives import BackendSamplerV2
from qiskit_aer import AerSimulator

backend = AerSimulator()
sampler = BackendSamplerV2(backend=backend, options={"default_shots": ${Number(s.execution.shots || 128)}})`;

    return `# Auto-generated Qiskit quantum pipeline template
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from qiskit.circuit.library import ${enc}, ${ans}
from qiskit_machine_learning.algorithms.classifiers import VQC
from qiskit_algorithms.optimizers import ${String(s.optimizer.type || "cobyla").toUpperCase()}

${providerBlock}

df = pd.read_csv("${datasetPath}")
feature_columns = ${features}
label_column = "${s.dataset.label_column || "label"}"
X = df[feature_columns].astype(float).to_numpy()
y = df[label_column].astype(int).to_numpy()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=${Number(s.dataset.test_size || 0.25)}, random_state=${Number(s.dataset.seed || 42)}, stratify=y)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

feature_map = ${enc}(feature_dimension=${q}, reps=${Number(s.encoder.reps || 1)})
ansatz = ${ans}(num_qubits=${q}, reps=${rep})
optimizer = ${String(s.optimizer.type || "cobyla").toUpperCase()}(maxiter=${Number(s.optimizer.maxiter || 20)})

classifier = VQC(feature_map=feature_map, ansatz=ansatz, optimizer=optimizer, sampler=sampler)
classifier.fit(X_train, y_train)
predictions = classifier.predict(X_test)

print("Test accuracy:", accuracy_score(y_test, predictions))
print("Predictions:", predictions[:10])
`;
  }

  function pennyLaneTemplate(s){
    const q = Math.max(1, Number(s.circuit.num_qubits || 2));
    const rep = Math.max(1, Number(s.circuit.reps || 1));
    const datasetPath = s.dataset.path || "<path-to-csv>";
    const features = JSON.stringify(s.dataset.feature_columns || []);
    const deviceBlock = `dev = qml.device("default.qubit", wires=${q}, shots=${Number(s.execution.shots || 128)})`;

    return `# Auto-generated PennyLane template
import pennylane as qml
from pennylane import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

df = pd.read_csv("${datasetPath}")
feature_columns = ${features}
label_column = "${s.dataset.label_column || "label"}"
X = df[feature_columns].astype(float).to_numpy()
y = df[label_column].astype(int).to_numpy()

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=${Number(s.dataset.test_size || 0.25)}, random_state=${Number(s.dataset.seed || 42)}, stratify=y)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

${deviceBlock}

@qml.qnode(dev)
def circuit(features, weights):
    qml.AngleEmbedding(features[:${q}], wires=range(${q}), rotation="Y")
    qml.StronglyEntanglingLayers(weights, wires=range(${q}))
    return qml.expval(qml.PauliZ(0))

weights = np.random.random((${rep}, ${q}, 3), requires_grad=True)
print("Template ready. Add your optimizer/training loop here.")
`;
  }

  function codeTemplate(s){
    return (s.framework || "qiskit") === "pennylane" ? pennyLaneTemplate(s) : qiskitTemplate(s);
  }

  document.addEventListener("DOMContentLoaded", () => {
    setMsg("Canvas ready. Add nodes from the toolbar.", "ok");

    on("add-dataset", () => addNode("dataset","Dataset",[
      {name:"path",label:"CSV path",value:""},
      {name:"label",label:"Label",value:""},
      {name:"features",label:"Features (comma)",value:""}
    ]));

    on("add-encoder", () => addNode("encoder","Encoder",[
      {name:"type",label:"Type (angle/basis)",value:"angle"}
    ]));

    on("add-circuit", () => addNode("circuit","Circuit",[
      {name:"type",label:"Type (ry/realamplitudes)",value:"ry"},
      {name:"num_qubits",label:"#qubits",value:"2"},
      {name:"reps",label:"layers",value:"1"}
    ]));

    on("add-optimizer", () => addNode("optimizer","Optimizer",[
      {name:"type",label:"Type",value:"cobyla"},
      {name:"maxiter",label:"Max iter",value:"15"}
    ]));

    on("add-output", () => addNode("output","Output",[
      {name:"predictions",label:"Return predictions (true/false)",value:"true"}
    ]));

    on("btn-save-node", () => {
      if (!selectedId) return setMsg("Select a node first.","err");
      const n = model.nodes.find(x => x.id === selectedId);
      if (!n) return setMsg("Node not found.","err");

      const inputs = document.querySelectorAll("#node-params [data-param]");
      inputs.forEach(inp => {
        n.params[inp.getAttribute("data-param")] = inp.value;
      });

      render();
      selectNode(n.id);
      setMsg("Node saved.","ok");
    });

    on("btn-delete-node", () => {
      if (!selectedId) return setMsg("Select a node first.","err");
      removeEdgesForNode(selectedId);
      model.nodes = model.nodes.filter(x => x.id !== selectedId);
      selectedId = null;
      render();
      $("node-params").innerHTML = "";
      $("selected-info").textContent = "No node selected.";
      setMsg("Node deleted.","ok");
    });

    on("btn-export-model", () => download("pipeline_model.json", JSON.stringify(exportModel(),null,2)));
    on("btn-save-model", () => download("node_canvas.json", JSON.stringify(exportModel(),null,2)));
    on("btn-load-model", () => $("file-load-model").click());
    on("btn-load-model-ui", () => $("file-load-model").click());

    $("file-load-model").addEventListener("change", (ev) => {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;

      const r = new FileReader();
      r.onload = () => {
        try {
          importModel(JSON.parse(r.result));
        } catch(e) {
          setMsg("Failed to load model: " + e.message, "err");
        }
      };
      r.readAsText(f);
    });

    const info = {
      dataset: "Dataset: choose a domain CSV or upload your own, then map label and feature columns into the pipeline.",
      encoder: "Encoder: maps classical features onto the quantum circuit with angle or basis-style feature maps.",
      circuit: "Circuit: defines the trainable variational ansatz and qubit count used for quantum classification.",
      optimizer:"Optimizer: controls quantum training iterations through COBYLA or SPSA.",
      output: "Output: execution metrics, predictions, dashboard charts, and code templates for Qiskit or PennyLane."
    };

    Array.from(document.querySelectorAll("[data-info]")).forEach(b => {
      b.addEventListener("click",(e)=>{
        e.preventDefault();
        $("info-text").textContent = info[b.dataset.info] || "";
      });
    });

    const result = $("result");
    const codeBox = $("codePreview");
    const selectFramework = $("select-framework");
    const selectEncoding = $("select-encoding");
    const selectAnsatz = $("select-ansatz");
    const selectOptimizer = $("select-optimizer");
    const selectProvider = $("select-provider");
    const inputLayers = $("input-layers");
    const inputMaxIter = $("input-maxiter");
    const inputBackend = $("input-backend");
    const inputShots = $("input-shots");
    function syncSpecFromControls() {
      spec.framework = selectFramework.value;
      spec.encoder.type = selectEncoding.value;
      spec.circuit.type = selectAnsatz.value;
      spec.circuit.reps = Number(inputLayers.value || 1);
      spec.optimizer.type = selectOptimizer.value;
      spec.optimizer.maxiter = Number(inputMaxIter.value || 20);
      spec.execution.provider = selectProvider.value;
      spec.execution.backend = inputBackend.value || "aer_simulator";
      spec.execution.shots = Number(inputShots.value || 128);
    }

    async function refreshBackends() {
      try {
        const resp = await fetch("http://localhost:5000/backends");
        const data = await resp.json();
        if (!resp.ok) throw new Error(data?.error || resp.statusText);
        result.textContent = JSON.stringify(data, null, 2);
        setMsg("Backend catalog refreshed. Qiskit Aer is the official simulator for this app.", "ok");
      } catch (e) {
        setMsg(e.message || String(e), "err");
      }
    }

    async function loadDataset(datasetName) {
      try {
        setMsg(`Loading ${datasetName} dataset...`);
        const resp = await fetch(`http://localhost:5000/dataset/${datasetName}`);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data?.error || resp.statusText);

        spec.dataset = {
          name: data.name,
          type: "csv",
          path: data.path,
          label_column: data.label_column,
          feature_columns: data.feature_columns,
          test_size: 0.25,
          seed: 42
        };
        spec.circuit.num_qubits = Math.max(1, data.feature_columns.length);

        let ds = model.nodes.find(n => (n.type||"").toLowerCase()==="dataset");
        if (!ds) {
          ds = {
            id: nextId++,
            type:"dataset",
            name:"Dataset",
            pos:{ x:20, y:20 },
            params:{
              path: data.path,
              label: data.label_column,
              features: data.feature_columns.join(", ")
            }
          };
          model.nodes.push(ds);
        } else {
          ds.params.path = data.path;
          ds.params.label = data.label_column;
          ds.params.features = data.feature_columns.join(", ");
        }

      render();
      selectNode(ds.id);
      ensureDefaultPipeline();
      result.textContent = JSON.stringify({ dataset: data.name, config: data }, null, 2);
      setMsg(`${data.domain} dataset loaded successfully.`, "ok");
      } catch (e) {
        setMsg(e.message || String(e), "err");
      }
    }

    on("btn-finance", () => loadDataset("finance"));
    on("btn-supply-chain", () => loadDataset("supply_chain"));
    on("btn-hr", () => loadDataset("hr"));
    on("btn-refresh-backends", () => refreshBackends());

    on("btn-upload", async () => {
      try {
        const fileEl = $("csvFile");
        const f = fileEl?.files?.[0];
        if (!f) return setMsg("Choose a .csv first.","err");
        if (!f.name.toLowerCase().endsWith(".csv")) return setMsg("Only .csv files allowed.","err");

        setMsg("Uploading CSV...");
        const form = new FormData();
        form.append("file", f);

        const resp = await fetch("http://localhost:5000/upload", { method:"POST", body: form });
        const j = await resp.json();
        if (!resp.ok) throw new Error(j?.error || resp.statusText);

        const { label, features } = inferLabelAndFeatures(j.columns || []);
        spec.dataset = {
          name: "custom-upload",
          type:"csv",
          path:j.path,
          label_column:label,
          feature_columns:features,
          test_size:0.25,
          seed:42
        };
        spec.circuit.num_qubits = Math.max(1, features.length);

        let ds = model.nodes.find(n => (n.type||"").toLowerCase()==="dataset") || null;
        if (!ds) {
          ds = {
            id: nextId++,
            type:"dataset",
            name:"Dataset",
            pos:{ x:20, y:20 },
            params:{ path:j.path || "", label:label || "", features:features.join(", ") }
          };
          model.nodes.push(ds);
        } else {
          ds.params.path = j.path || "";
          ds.params.label = label || "";
          ds.params.features = features.join(", ");
          if (selectedId === ds.id) {
            selectNode(ds.id);
          } else {
            render();
          }
        }

        ensureDefaultPipeline();
        result.textContent = JSON.stringify({ upload:j, chosen:{label, features} }, null, 2);
        setMsg(`Upload OK. Label=${label}; #features=${features.length}.`,"ok");
      } catch (e) {
        setMsg(e.message || String(e), "err");
      }
    });

    function inferLabelAndFeatures(cols){
      if (!Array.isArray(cols) || cols.length===0) return { label:"", features:[] };
      const lower = cols.map(c => String(c||"").toLowerCase());
      const candidates = ["label","class","target","y","outcome","species","risk_flag","disruption_flag","attrition_flag"];
      let li = lower.findIndex(c => candidates.includes(c));
      if (li === -1) li = cols.length - 1;
      return { label: cols[li] || "", features: cols.filter((_,i) => i !== li) };
    }

    on("btn-generate", () => {
      syncSpecFromControls();
      codeBox.textContent = codeTemplate(spec);
      setMsg(`${spec.framework === "pennylane" ? "PennyLane" : "Qiskit"} template generated.`, "ok");
    });

    on("btn-download-code", () => {
      const url = URL.createObjectURL(new Blob([$("codePreview").textContent || ""], {type:"text/x-python"}));
      const a = document.createElement("a");
      a.href = url;
      a.download = "generated_run.py";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });

    on("btn-export", () => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(spec,null,2)],{type:"application/json"}));
      const a = document.createElement("a");
      a.href = url;
      a.download = "pipeline.json";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });

    on("btn-generate-from-model", () => {
      try {
        const map = {};
        model.nodes.forEach(n => {
          const key = (n?.type || n?.name || "node").toString().toLowerCase();
          map[key] = n;
        });

        const ds = map["dataset"];
        if (ds && ds.params){
          const rawFeats = ds.params.features;
          const feats = typeof rawFeats === "string"
            ? rawFeats.split(",").map(s => s.trim()).filter(Boolean)
            : Array.isArray(rawFeats) ? rawFeats : [];

          spec.dataset = {
            name: spec.dataset?.name || "model-dataset",
            type: "csv",
            path: ds.params.path || spec.dataset?.path || "",
            label_column: ds.params.label || spec.dataset?.label_column || "label",
            feature_columns: feats,
            test_size: 0.25,
            seed: 42
          };
        }

        syncSpecFromControls();
        spec.encoder = { type: map["encoder"]?.params?.type || $("select-encoding").value, reps: 1 };
        const cir = map["circuit"]?.params || {};

        spec.circuit = {
          type: cir.type || $("select-ansatz").value,
          num_qubits: Number(cir.num_qubits || 2),
          reps: Number(cir.reps || $("input-layers").value || 1)
        };

        spec.optimizer = {
          type: map["optimizer"]?.params?.type || selectOptimizer.value || "cobyla",
          maxiter: Number(map["optimizer"]?.params?.maxiter || inputMaxIter.value || 20)
        };

        $("codePreview").textContent = codeTemplate(spec);
        setMsg("Spec generated from model.","ok");
      } catch (e) {
        setMsg("Error generating from model: " + e.message, "err");
      }
    });

    on("btn-run", async () => {
      try {
        setMsg("Running pipeline...");
        $("result").textContent = "Running...";

        syncSpecFromControls();
        spec.circuit.num_qubits = Math.max(1, Number(spec.circuit.num_qubits || spec.dataset.feature_columns.length || 2));
        spec.optimizer.maxiter  = Math.max(1, Number(spec.optimizer.maxiter || 20));
        spec.execution.provider = "aer";
        spec.execution.backend = "aer_simulator";

        const resp = await fetch("http://localhost:5000/run", {
          method:"POST",
          headers:{ "Content-Type":"application/json" },
          body: JSON.stringify(spec)
        });

        const data = await resp.json();
        if (!resp.ok) throw new Error(data?.error || resp.statusText);

        $("result").textContent = JSON.stringify(data, null, 2);
        drawTrainingGraphs(data);
        setMsg("Pipeline finished. Dashboard metrics updated successfully.", "ok");
      } catch (e) {
        clearCharts();
        setMsg(e.message || String(e), "err");
        $("result").textContent = "";
      }
    });

    syncSpecFromControls();
    codeBox.textContent = codeTemplate(spec);
    ensureDefaultPipeline();
    loadDataset("finance");
    refreshBackends();
  });
})();

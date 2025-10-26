// ---------- default spec (will switch to CSV after upload) ----------
const spec = {
  version: "0.1",
  pipeline: "qml-classifier",
  qnn: { type: "estimator" },
  dataset: {
    // you can keep synthetic *or* your diabetes CSV; caps below keep it fast anyway
    type: "csv",
    path: "uploads/diabetes.csv",
    label_column: "Outcome",
    feature_columns: [
      "Pregnancies","Glucose","BloodPressure","SkinThickness",
      "Insulin","BMI","DiabetesPedigreeFunction","Age"
    ],
    test_size: 0.2,
    seed: 42
  },
  encoder: { type: "zzfeaturemap" },
  circuit: { type: "realamplitudes", num_qubits: 4, reps: 1 }, // cap default to 4
  optimizer: { type: "cobyla", maxiter: 20 },                  // cap default to 20
  outputs: { return_predictions: true, return_generated_code: true }
};

// ---------- UI refs ----------
const info   = document.getElementById("info");
const result = document.getElementById("result");
const msg    = document.getElementById("msg");
const fileEl = document.getElementById("csvFile");

const btnLoadSample = document.getElementById("btn-load-sample");
const btnGenerate   = document.getElementById("btn-generate");
const btnDownloadCode = document.getElementById("btn-download-code");
const selectEncoding  = document.getElementById("select-encoding");
const selectAnsatz    = document.getElementById("select-ansatz");
const inputLayers     = document.getElementById("input-layers");

const texts = {
  dataset: "Upload a CSV or use the demo synthetic data. CSV should have numeric features and a label/class column.",
  encoder: "Encoder (ZZFeatureMap): turns numbers into qubit rotations so the circuit can 'see' them.",
  circuit: "Circuit (QNNCircuit + RealAmplitudes): trainable pattern; optimizer tunes its angles.",
  optimizer: "Optimizer (COBYLA): knob-turner that reduces mistakes during training.",
  output: "Training & Output: .fit() learns; .score() prints accuracy; predictions returned."
};

// ---------- helpers ----------
function setMsg(text, type = "info") {
  msg.textContent = text || "";
  msg.style.color = type === "err" ? "#ef4444" : type === "ok" ? "#22c55e" : "#93a3b8";
}

function inferLabelAndFeatures(columns) {
  const lower = columns.map(c => String(c).toLowerCase());
  const candidates = ["label", "class", "target", "y", "outcome", "outcomes"];
  let labelIdx = lower.findIndex(c => candidates.includes(c));
  if (labelIdx === -1) labelIdx = columns.length - 1;
  const label = columns[labelIdx];
  const features = columns.filter((_, i) => i !== labelIdx);
  return { label, features };
}

async function uploadCSV(file) {
  const form = new FormData();
  form.append("file", file);
  const resp = await fetch("http://localhost:5000/upload", { method: "POST", body: form });
  const data = await resp.json();
  if (!resp.ok) {
    const detail = data?.detail || data?.error || resp.statusText;
    throw new Error(`Upload failed: ${detail}`);
  }
  return data; // { ok, path, columns, rows, preview }
}

/*
  Fixed startup/initialization for Drawflow + side-panel.
  - Wrap initialization in DOMContentLoaded to ensure elements exist
  - Add setMsg helper and global error handler so JS failures surface in UI
  - Defensive lookups for DOM elements (no-op if missing)
  - Keeps existing logic (node add, export, import, codegen, CSV sample)
*/

(function () {
  'use strict';

  // Helper: show messages to the user
  function setMsg(text, type = 'info') {
    try {
      const el = document.getElementById('msg');
      if (el) {
        el.textContent = text || '';
        el.style.color = type === 'err' ? '#ef4444' : type === 'ok' ? '#22c55e' : '#444';
      } else {
        console.log('[msg]', text);
      }
    } catch (e) { console.error(e); }
  }

  // Log JS errors into UI for easier debugging
  window.addEventListener('error', function (ev) {
    console.error('Unhandled error', ev.error || ev.message);
    setMsg('JavaScript error: ' + (ev.error?.message || ev.message), 'err');
  });

  document.addEventListener('DOMContentLoaded', function () {
    try {
      // Ensure required DOM elements exist before proceeding
      if (!document.getElementById('drawflow')) {
        setMsg('Editor container not found (missing #drawflow).', 'err');
        return;
      }

      // Initialize Drawflow editor safely
      const editor = new Drawflow(document.getElementById('drawflow'));
      editor.reroute = true;
      editor.start();

      // small incremental placement
      let nextNodeX = 10;
      let nextNodeY = 10;
      function nextPos() {
        const p = { x: nextNodeX, y: nextNodeY };
        nextNodeX += 160;
        if (nextNodeX > 900) { nextNodeX = 10; nextNodeY += 160; }
        return p;
      }

      // Create node html with inputs for side-panel / persistence
      function nodeHtml(title, fields = []) {
        let body = `<div class="node-title"><strong>${title}</strong></div>`;
        fields.forEach(f => {
          const val = f.value ?? f.default ?? '';
          body += `<label class="node-param">${f.label}: <input data-param="${f.name}" value="${val}" style="width:140px" /></label>`;
        });
        return `<div class="box">${body}</div>`;
      }

      function addTypedNode(type, title, params = []) {
        const pos = nextPos();
        const html = nodeHtml(title, params);
        const inputs = type === 'dataset' ? 0 : 1;
        const outputs = type === 'output' ? 0 : 1;
        const data = { type, params: params.reduce((acc, p) => { acc[p.name] = p.value ?? p.default ?? ''; return acc; }, {}) };
        const nodeId = editor.addNode(title, inputs, outputs, pos.x, pos.y, null, data, html);
        setMsg(`${title} node added.`, 'ok');
        return nodeId;
      }

      // Attach toolbar actions if buttons exist
      const btn = id => document.getElementById(id);
      if (btn('add-dataset')) btn('add-dataset').addEventListener('click', () => {
        addTypedNode('dataset', 'Dataset', [{ name: 'path', label: 'path', default: '' }, { name: 'label_column', label: 'label_col', default: 'label' }]);
      });
      if (btn('add-encoder')) btn('add-encoder').addEventListener('click', () => {
        addTypedNode('encoder', 'Encoder', [{ name: 'type', label: 'type', default: 'angle' }]);
      });
      if (btn('add-circuit')) btn('add-circuit').addEventListener('click', () => {
        addTypedNode('circuit', 'Circuit', [{ name: 'ansatz', label: 'ansatz', default: 'ry' }, { name: 'layers', label: 'layers', default: '2' }]);
      });
      if (btn('add-optimizer')) btn('add-optimizer').addEventListener('click', () => {
        addTypedNode('optimizer', 'Optimizer', [{ name: 'name', label: 'name', default: 'SPSA' }, { name: 'maxiter', label: 'maxiter', default: '100' }]);
      });
      if (btn('add-output')) btn('add-output').addEventListener('click', () => {
        addTypedNode('output', 'Output', [{ name: 'model', label: 'model', default: 'qnn' }]);
      });

      // Extract params helpers
      function extractNodeParamsFromHtml(html) {
        const params = {};
        try {
          const tmp = document.createElement('div');
          tmp.innerHTML = html || '';
          const inputs = tmp.querySelectorAll('[data-param]');
          inputs.forEach(inp => { params[inp.getAttribute('data-param')] = inp.value; });
        } catch (e) { /* ignore */ }
        return params;
      }
      function extractNodeParams(nodeObj) {
        const params = {};
        if (!nodeObj) return params;
        if (nodeObj.html) Object.assign(params, extractNodeParamsFromHtml(nodeObj.html));
        if (nodeObj.data?.params) Object.assign(params, nodeObj.data.params);
        return params;
      }

      // export model to simple schema
      function exportModelSchema() {
        const exported = editor.export();
        const nodesObj = exported.drawflow?.Home || {};
        const nodes = [];
        const edges = [];
        Object.keys(nodesObj).forEach(id => {
          const n = nodesObj[id];
          const params = extractNodeParams(n);
          nodes.push({
            id: parseInt(id, 10),
            type: n.data?.type || (n.name || '').toLowerCase(),
            name: n.name,
            pos: { x: n.pos_x, y: n.pos_y },
            params
          });
          if (n.outputs) {
            Object.keys(n.outputs).forEach(outputIndex => {
              const connections = n.outputs[outputIndex].connections || [];
              connections.forEach(conn => {
                edges.push({
                  source: parseInt(id, 10),
                  source_output: parseInt(outputIndex, 10),
                  target: conn.node,
                  target_input: conn.input
                });
              });
            });
          }
        });
        return { version: "0.1", nodes, edges, created_at: new Date().toISOString() };
      }

      function downloadFile(filename, text, mime='application/json') {
        const blob = new Blob([text], { type: mime + ';charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }

      if (btn('btn-export-model')) btn('btn-export-model').addEventListener('click', () => {
        const model = exportModelSchema();
        downloadFile('pipeline_model.json', JSON.stringify(model, null, 2));
        setMsg('Model JSON exported.');
      });

      // side-panel selection handling
      let lastSelectedNodeId = null;
      function showNodeInSidepanel(nodeId) {
        const exported = editor.export();
        const home = exported.drawflow?.Home || {};
        const node = home[nodeId];
        const selInfo = document.getElementById('selected-info');
        const paramsDiv = document.getElementById('node-params');
        if (!paramsDiv || !selInfo) return;
        paramsDiv.innerHTML = '';
        if (!node) {
          selInfo.textContent = 'No node selected.';
          lastSelectedNodeId = null;
          return;
        }
        lastSelectedNodeId = parseInt(nodeId, 10);
        selInfo.textContent = `Selected: ${node.name} (id=${nodeId})`;
        const params = extractNodeParams(node);
        Object.keys(params).forEach(k => {
          const v = params[k] ?? '';
          const el = document.createElement('label');
          el.className = 'node-param';
          el.innerHTML = `${k}: <input id="param-${k}" data-param="${k}" value="${v}" style="width:160px" />`;
          paramsDiv.appendChild(el);
        });
        if (Object.keys(params).length === 0) {
          paramsDiv.innerHTML = '<div class="muted">No editable params for this node.</div>';
        }
      }

      // Hook up drawflow selection events (safe)
      try {
        editor.on('nodeSelected', function (id) { showNodeInSidepanel(id); });
        editor.on('nodeUnselected', function () { showNodeInSidepanel(null); });
      } catch (e) {
        // Older/newer Drawflow builds may differ; provide a fallback: poll selection on click
        document.getElementById('drawflow').addEventListener('click', function () {
          const exported = editor.export();
          // pick first selected node if any (Drawflow stores selected under 'editor_selected' in some versions)
          const sel = Object.keys(exported.drawflow?.Home || {})[0];
          showNodeInSidepanel(sel);
        });
      }

      // Save node edits back to editor
      if (btn('btn-save-node')) btn('btn-save-node').addEventListener('click', () => {
        if (!lastSelectedNodeId) { setMsg('Select a node first.', 'err'); return; }
        const exported = editor.export();
        const home = exported.drawflow?.Home || {};
        const node = home[lastSelectedNodeId];
        if (!node) { setMsg('Selected node not found.', 'err'); return; }
        const paramsDiv = document.getElementById('node-params');
        const inputs = paramsDiv.querySelectorAll('[data-param]');
        const newParams = {};
        inputs.forEach(inp => { newParams[inp.getAttribute('data-param')] = inp.value; });
        const fields = Object.keys(newParams).map(k => ({ name: k, label: k, value: newParams[k] }));
        node.html = nodeHtml(node.name, fields);
        node.data = node.data || {};
        node.data.params = Object.assign({}, node.data.params || {}, newParams);
        exported.drawflow = exported.drawflow || {};
        exported.drawflow.Home = exported.drawflow.Home || {};
        exported.drawflow.Home[lastSelectedNodeId] = node;
        editor.import(exported);
        setMsg('Node saved.');
        showNodeInSidepanel(lastSelectedNodeId);
      });

      if (btn('btn-delete-node')) btn('btn-delete-node').addEventListener('click', () => {
        if (!lastSelectedNodeId) { setMsg('Select a node to delete.', 'err'); return; }
        try {
          editor.removeNode(lastSelectedNodeId);
          setMsg('Node deleted.');
          lastSelectedNodeId = null;
          showNodeInSidepanel(null);
        } catch (e) {
          setMsg('Failed to delete node: ' + e.message, 'err');
        }
      });

      // Load model (file input)
      const fileLoadEl = document.getElementById('file-load-model');
      if (btn('btn-load-model-ui')) btn('btn-load-model-ui').addEventListener('click', () => {
        if (fileLoadEl) fileLoadEl.click();
      });
      if (fileLoadEl) {
        fileLoadEl.addEventListener('change', (ev) => {
          const f = ev.target.files[0];
          if (!f) return;
          const reader = new FileReader();
          reader.onload = () => {
            try {
              const json = JSON.parse(reader.result);
              // convert pipeline schema shape into drawflow if needed
              if (json.nodes && json.edges) {
                const draw = { drawflow: { Home: {} }, modules: {} };
                json.nodes.forEach(n => {
                  const fields = Object.keys(n.params || {}).map(k => ({ name: k, label: k, value: n.params[k] }));
                  const html = nodeHtml(n.name || n.type, fields);
                  draw.drawflow.Home[String(n.id)] = {
                    id: n.id,
                    name: n.name || n.type,
                    html,
                    pos_x: n.pos?.x || 10,
                    pos_y: n.pos?.y || 10,
                    data: { type: n.type, params: n.params },
                    inputs: {},
                    outputs: {}
                  };
                });
                json.edges.forEach((e) => {
                  const s = String(e.source);
                  const t = String(e.target);
                  draw.drawflow.Home[s].outputs = draw.drawflow.Home[s].outputs || {};
                  draw.drawflow.Home[s].outputs[0] = draw.drawflow.Home[s].outputs[0] || { connections: [] };
                  draw.drawflow.Home[s].outputs[0].connections.push({ node: parseInt(t, 10), input: e.target_input ?? 0 });
                });
                editor.import(draw);
                setMsg('Model loaded (converted).');
                return;
              }
              if (json.drawflow) {
                editor.import(json);
                setMsg('Drawflow model loaded.');
              } else {
                setMsg('Unrecognized model format.', 'err');
              }
            } catch (e) {
              setMsg('Failed to load model: ' + e.message, 'err');
            }
          };
          reader.readAsText(f);
        });
      }

      // Generate from model -> pipeline spec + code preview
      if (btn('btn-generate-from-model')) btn('btn-generate-from-model').addEventListener('click', () => {
        const model = exportModelSchema();
        const nmap = {};
        model.nodes.forEach(n => { nmap[n.type || n.name.toLowerCase()] = n; });
        const featureCount = 4;
        const pipeline = {
          name: 'qml-pipeline-from-model',
          dataset: nmap['dataset'] ? { type: 'inline', path: nmap['dataset'].params.path || null, label_column: nmap['dataset'].params.label_column || null } : { type: 'inline', n_samples: 6 },
          encoder: { type: nmap['encoder'] ? (nmap['encoder'].params.type || 'angle') : 'angle', params: { features: featureCount } },
          circuit: { ansatz: nmap['circuit'] ? (nmap['circuit'].params.ansatz || 'ry') : 'ry', layers: parseInt(nmap['circuit']?.params.layers || 2, 10) },
          optimizer: { name: nmap['optimizer'] ? (nmap['optimizer'].params.name || 'SPSA') : 'SPSA', maxiter: parseInt(nmap['optimizer']?.params.maxiter || 100, 10) },
          output: { model: nmap['output'] ? (nmap['output'].params.model || 'qnn') : 'qnn', framework: 'qiskit' }
        };
        const resultEl = document.getElementById('result');
        if (resultEl) resultEl.textContent = JSON.stringify(pipeline, null, 2);
        const code = (typeof generateQiskitTemplate === 'function') ? generateQiskitTemplate(pipeline) : '# code generator not available';
        const preview = document.getElementById('codePreview');
        if (preview) preview.textContent = code;
        setMsg('Generated pipeline spec and code from model.', 'ok');
      });

      // Expose editor for debugging (optional)
      window.__drawflow_editor = editor;

      // Indicate ready
      setMsg('Editor ready. Add nodes from the toolbar.', 'ok');

    } catch (err) {
      console.error('Initialization failed', err);
      setMsg('Initialization error: ' + (err?.message || err), 'err');
    }
  }); // DOMContentLoaded end

})(); // IIFE end

/////////////////////// Drawflow visual editor ///////////////////////
const editor = new Drawflow(document.getElementById("drawflow"));
editor.reroute = true;
editor.start();

// small incremental id placement
let nextNodeX = 10;
let nextNodeY = 10;
function nextPos() { const p = { x: nextNodeX, y: nextNodeY }; nextNodeX += 160; if (nextNodeX > 600) { nextNodeX = 10; nextNodeY += 160; } return p; }

// helper to create simple node HTML with editable params
function nodeHtml(title, fields = []) {
  let body = `<div class="node-title"><strong>${title}</strong></div>`;
  fields.forEach(f => {
    const val = f.value ?? f.default ?? '';
    body += `<label class="node-param">${f.label}: <input data-param="${f.name}" value="${val}" style="width:140px" /></label>`;
  });
  return `<div class="box">${body}</div>`;
}

// add typed node
function addTypedNode(type, title, params = []) {
  const pos = nextPos();
  const html = nodeHtml(title, params);
  const inputs = type === 'dataset' ? 0 : 1;
  const outputs = type === 'output' ? 0 : 1;
  const data = { type, params: params.reduce((acc, p) => { acc[p.name] = p.value ?? p.default ?? ''; return acc; }, {}) };
  const nodeId = editor.addNode(title, inputs, outputs, pos.x, pos.y, null, data, html);
  return nodeId;
}

// attach toolbar actions
document.getElementById("add-dataset").addEventListener("click", () => {
  addTypedNode('dataset', 'Dataset', [{ name: 'path', label: 'path', default: '' }, { name: 'label_column', label: 'label_col', default: 'label' }]);
});
document.getElementById("add-encoder").addEventListener("click", () => {
  addTypedNode('encoder', 'Encoder', [{ name: 'type', label: 'type', default: 'angle' }]);
});
document.getElementById("add-circuit").addEventListener("click", () => {
  addTypedNode('circuit', 'Circuit', [{ name: 'ansatz', label: 'ansatz', default: 'ry' }, { name: 'layers', label: 'layers', default: '2' }]);
});
document.getElementById("add-optimizer").addEventListener("click", () => {
  addTypedNode('optimizer', 'Optimizer', [{ name: 'name', label: 'name', default: 'SPSA' }, { name: 'maxiter', label: 'maxiter', default: '100' }]);
});
document.getElementById("add-output").addEventListener("click", () => {
  addTypedNode('output', 'Output', [{ name: 'model', label: 'model', default: 'qnn' }]);
});

// utility: extract param values from node html inputs
function extractNodeParamsFromHtml(html) {
  const params = {};
  try {
    const tmp = document.createElement('div');
    tmp.innerHTML = html || '';
    const inputs = tmp.querySelectorAll('[data-param]');
    inputs.forEach(inp => { params[inp.getAttribute('data-param')] = inp.value; });
  } catch (e) { /* ignore */ }
  return params;
}

function extractNodeParams(nodeObj) {
  const params = {};
  if (nodeObj.html) Object.assign(params, extractNodeParamsFromHtml(nodeObj.html));
  if (nodeObj.data?.params) Object.assign(params, nodeObj.data.params);
  return params;
}

// export drawflow model and convert to pipeline schema
function exportModelSchema() {
  const exported = editor.export();
  const nodesObj = exported.drawflow?.Home || {};
  const nodes = [];
  const edges = [];
  Object.keys(nodesObj).forEach(id => {
    const n = nodesObj[id];
    const params = extractNodeParams(n);
    nodes.push({
      id: parseInt(id, 10),
      type: n.data?.type || (n.name || '').toLowerCase(),
      name: n.name,
      pos: { x: n.pos_x, y: n.pos_y },
      params
    });
    if (n.outputs) {
      Object.keys(n.outputs).forEach(outputIndex => {
        const connections = n.outputs[outputIndex].connections || [];
        connections.forEach(conn => {
          edges.push({
            source: parseInt(id, 10),
            source_output: parseInt(outputIndex, 10),
            target: conn.node,
            target_input: conn.input
          });
        });
      });
    }
  });
  const schema = { version: "0.1", nodes, edges, created_at: new Date().toISOString() };
  return schema;
}

// download helper
function download(filename, text, mime='application/json') {
  const blob = new Blob([text], { type: mime + ';charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// selection & side-panel logic
let lastSelectedNodeId = null;

function showNodeInSidepanel(nodeId) {
  const exported = editor.export();
  const home = exported.drawflow?.Home || {};
  const node = home[nodeId];
  const selInfo = document.getElementById('selected-info');
  const paramsDiv = document.getElementById('node-params');
  paramsDiv.innerHTML = '';
  if (!node) {
    selInfo.textContent = 'No node selected.';
    lastSelectedNodeId = null;
    return;
  }
  lastSelectedNodeId = parseInt(nodeId, 10);
  selInfo.textContent = `Selected: ${node.name} (id=${nodeId})`;
  const params = extractNodeParams(node);
  Object.keys(params).forEach(k => {
    const v = params[k] ?? '';
    const el = document.createElement('label');
    el.className = 'node-param';
    el.innerHTML = `${k}: <input id="param-${k}" data-param="${k}" value="${v}" style="width:160px" />`;
    paramsDiv.appendChild(el);
  });
  if (Object.keys(params).length === 0) {
    paramsDiv.innerHTML = '<div class="muted">No editable params for this node.</div>';
  }
}

// hook: Drawflow provides nodeSelected event; fall back to click on drawflow to capture selection
try {
  editor.on('nodeSelected', function(id) { showNodeInSidepanel(id); });
  editor.on('nodeUnselected', function() { showNodeInSidepanel(null); });
} catch (e) {
  // fallback: clicking toolbar to refresh doesn't select node, user can still use Export/Import
}

// Save node edits back into the drawflow export and re-import
document.getElementById('btn-save-node').addEventListener('click', () => {
  if (!lastSelectedNodeId) { setMsg('Select a node first.', 'err'); return; }
  const exported = editor.export();
  const home = exported.drawflow?.Home || {};
  const node = home[lastSelectedNodeId];
  if (!node) { setMsg('Selected node not found.', 'err'); return; }
  // read inputs from sidepanel
  const paramsDiv = document.getElementById('node-params');
  const inputs = paramsDiv.querySelectorAll('[data-param]');
  const newParams = {};
  inputs.forEach(inp => { newParams[inp.getAttribute('data-param')] = inp.value; });
  // rebuild html for node so visible inputs reflect new values
  const fields = Object.keys(newParams).map(k => ({ name: k, label: k, value: newParams[k] }));
  node.html = nodeHtml(node.name, fields);
  node.data = node.data || {};
  node.data.params = Object.assign({}, node.data.params || {}, newParams);
  // place back into exported structure and re-import to refresh UI
  exported.drawflow = exported.drawflow || {};
  exported.drawflow.Home = exported.drawflow.Home || {};
  exported.drawflow.Home[lastSelectedNodeId] = node;
  editor.import(exported);
  setMsg('Node saved.');
  showNodeInSidepanel(lastSelectedNodeId);
});

document.getElementById('btn-delete-node').addEventListener('click', () => {
  if (!lastSelectedNodeId) { setMsg('Select a node to delete.', 'err'); return; }
  try {
    editor.removeNode(lastSelectedNodeId);
    setMsg('Node deleted.');
    lastSelectedNodeId = null;
    showNodeInSidepanel(null);
  } catch (e) {
    setMsg('Failed to delete node: ' + e.message, 'err');
  }
});

// Save / Load model JSON
document.getElementById('btn-save-model').addEventListener('click', () => {
  const exported = editor.export();
  download('pipeline_model_drawflow.json', JSON.stringify(exported, null, 2));
  setMsg('Model downloaded.');
});

document.getElementById('btn-load-model-ui').addEventListener('click', () => {
  document.getElementById('file-load-model').click();
});
document.getElementById('file-load-model').addEventListener('change', (ev) => {
  const f = ev.target.files[0];
  if (!f) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const json = JSON.parse(reader.result);
      // if the uploaded file is our pipeline schema (nodes/edges), attempt to convert to Drawflow
      if (json.nodes && json.edges) {
        // build a minimal Drawflow export compatible object
        const draw = { drawflow: { Home: {} }, modules: {} };
        json.nodes.forEach(n => {
          // rebuilt node html using params object
          const fields = Object.keys(n.params || {}).map(k => ({ name: k, label: k, value: n.params[k] }));
          const html = nodeHtml(n.name || n.type, fields);
          draw.drawflow.Home[String(n.id)] = {
            id: n.id,
            name: n.name || n.type,
            html,
            pos_x: n.pos?.x || 10,
            pos_y: n.pos?.y || 10,
            data: { type: n.type, params: n.params },
            inputs: {},
            outputs: {}
          };
        });
        // add edges as simple connections
        json.edges.forEach((e, idx) => {
          const s = String(e.source);
          const t = String(e.target);
          draw.drawflow.Home[s].outputs = draw.drawflow.Home[s].outputs || {};
          draw.drawflow.Home[s].outputs[0] = draw.drawflow.Home[s].outputs[0] || { connections: [] };
          draw.drawflow.Home[s].outputs[0].connections.push({ node: parseInt(t,10), input: e.target_input ?? 0 });
        });
        editor.import(draw);
        setMsg('Model loaded (converted).');
        return;
      }
      // Otherwise assume it is a drawflow export
      if (json.drawflow) {
        editor.import(json);
        setMsg('Drawflow model loaded.');
      } else {
        setMsg('Unrecognized model format.', 'err');
      }
    } catch (e) {
      setMsg('Failed to load model: ' + e.message, 'err');
    }
  };
  reader.readAsText(f);
});

// Generate pipeline spec & code from current visual model (existing behavior retained)
document.getElementById("btn-generate-from-model").addEventListener("click", () => {
  const model = exportModelSchema();
  const nmap = {};
  model.nodes.forEach(n => { nmap[n.type || n.name.toLowerCase()] = n; });
  const featureCount = 4;
  const pipeline = {
    name: 'qml-pipeline-from-model',
    dataset: nmap['dataset'] ? { type: 'inline', path: nmap['dataset'].params.path || null, label_column: nmap['dataset'].params.label_column || null } : { type: 'inline', n_samples: 6 },
    encoder: { type: nmap['encoder'] ? (nmap['encoder'].params.type || 'angle') : 'angle', params: { features: featureCount } },
    circuit: { ansatz: nmap['circuit'] ? (nmap['circuit'].params.ansatz || 'ry') : 'ry', layers: parseInt(nmap['circuit']?.params.layers || 2, 10) },
    optimizer: { name: nmap['optimizer'] ? (nmap['optimizer'].params.name || 'SPSA') : 'SPSA', maxiter: parseInt(nmap['optimizer']?.params.maxiter || 100, 10) },
    output: { model: nmap['output'] ? (nmap['output'].params.model || 'qnn') : 'qnn', framework: 'qiskit' }
  };
  document.getElementById('result').textContent = JSON.stringify(pipeline, null, 2);
  const code = generateQiskitTemplate(pipeline);
  document.getElementById('codePreview').textContent = code;
  setMsg('Generated pipeline spec and code from model.');
});

/////////////////////// existing code below (CSV parsing, sample loader, code generation, run/export handlers) ///////////////////////

// --- client-side CSV parsing + iris sample (for quick offline preview)
const irisSample = `sepal_length,sepal_width,petal_length,petal_width,label
5.1,3.5,1.4,0.2,0
4.9,3.0,1.4,0.2,0
6.2,3.4,5.4,2.3,2
5.9,3.0,5.1,1.8,2
5.6,2.9,3.6,1.3,1
5.7,2.8,4.1,1.3,1`;

function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/);
  const header = lines.shift().split(',').map(s => s.trim());
  const rows = lines.map(line => line.split(',').map(v => v.trim()));
  return { header, rows };
}

// preserve the rest of your previous helpers and UI wiring (upload, load sample, generate/export/download code, run)
let currentData = null;
let generatedCode = '';

// buildPipelineSpec is still useful for manual controls; keep it as-is
function buildPipelineSpec() {
  if (document.getElementById('result').textContent) {
    try { return JSON.parse(document.getElementById('result').textContent); } catch (e) { /* ignore */ }
  }
  const featureCount = currentData ? (currentData.header.length - 1) : 4;
  return {
    name: 'qml-pipeline-prototype',
    dataset: { columns: currentData ? currentData.header : [], n_samples: currentData ? currentData.rows.length : 0 },
    encoder: { type: document.getElementById('select-encoding').value, params: { features: featureCount } },
    circuit: { ansatz: document.getElementById('select-ansatz').value, layers: parseInt(document.getElementById('input-layers').value, 10) },
    optimizer: { name: 'SPSA', maxiter: 100 },
    output: { model: 'qnn', framework: 'qiskit' }
  };
}

// generateQiskitTemplate (kept as before)
function generateQiskitTemplate(specObj) {
  const features = (specObj.encoder?.params?.features) || ((specObj.dataset?.columns || []).length - 1) || 4;
  const encoding = specObj.encoder?.type || 'angle';
  const ansatz = specObj.circuit?.ansatz || 'ry';
  const layers = specObj.circuit?.layers || specObj.circuit?.reps || 1;

  const code = `# Auto-generated Qiskit template (prototype)
# Requires: qiskit, qiskit-machine-learning
from qiskit import QuantumCircuit, Aer
from qiskit.utils import algorithm_globals
import numpy as np

# --- Data placeholder ---
# Replace with your data loading (CSV/pandas) to obtain X (n_samples, ${features}) and y
# X = ...
# y = ...

# --- Encoding ---
def build_encoding_circuit(x):
    qc = QuantumCircuit(${features})
${encoding === 'angle' ? "    # Angle encoding: map features to RY rotations\n    for i in range(min(len(x), " + features + ")):\n        qc.ry(x[i], i)" : "    # Basis encoding placeholder: convert features to bitstring and prepare basis state\n    # TODO: implement suitable basis encoding\n    pass"}
    return qc

# --- Variational ansatz ---
def build_variational_circuit(params):
    qc = QuantumCircuit(${features})
    idx = 0
${ansatz === 'ry' ? `    for l in range(${layers}):
        for q in range(${features}):
            qc.ry(params[idx], q); idx += 1
        for q in range(${features}-1):
            qc.cz(q, q+1)` : `    for l in range(${layers}):
        for q in range(${features}):
            qc.rz(params[idx], q); idx += 1
        for q in range(${features}-1):
            qc.cz(q, q+1)`}

    return qc

# --- QNN/Estimator skeleton (integrate with qiskit-machine-learning) ---
def build_qnn():
    backend = Aer.get_backend('aer_simulator')
    # Placeholder: wire encoding+variational circuits into a QNN/Estimator
    pass

if __name__ == "__main__":
    print("Template generated. Replace placeholders (data loading, training) and run with qiskit installed.")
`;
  return code;
}

// reuse existing download helper for code files (text/plain)
function downloadCode(filename, text) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// Wire up existing UI buttons (upload, sample, generate, download, run)
document.getElementById('btn-load-sample').addEventListener('click', () => {
  currentData = parseCSV(irisSample);
  setMsg('Iris sample loaded (' + currentData.rows.length + ' rows).');
  document.getElementById('result').textContent = JSON.stringify({ header: currentData.header, n_samples: currentData.rows.length }, null, 2);
});

document.getElementById('btn-generate').addEventListener('click', () => {
  const spec = buildPipelineSpec();
  generatedCode = generateQiskitTemplate(spec);
  document.getElementById('codePreview').textContent = generatedCode;
  setMsg('Generated code preview ready.');
});

document.getElementById('btn-download-code').addEventListener('click', () => {
  if (!generatedCode) { setMsg('Generate code first.', 'err'); return; }
  downloadCode('qml_pipeline_template.py', generatedCode);
});

// keep other existing upload/run/export handlers if present in your file (they are preserved above)
document.getElementById("btn-dataset").onclick   = () => (info.textContent = texts.dataset);
document.getElementById("btn-encoder").onclick   = () => (info.textContent = texts.encoder);
document.getElementById("btn-circuit").onclick   = () => (info.textContent = texts.circuit);
document.getElementById("btn-optimizer").onclick = () => (info.textContent = texts.optimizer);
document.getElementById("btn-output").onclick    = () => (info.textContent = texts.output);

// export current spec (uses buildPipelineSpec to capture UI state)
document.getElementById("btn-export").onclick = () => {
  const out = buildPipelineSpec();
  const blob = new Blob([JSON.stringify(out, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "pipeline.json"; a.click();
  URL.revokeObjectURL(url);
};

document.getElementById("btn-upload").onclick = async () => {
  try {
    if (!fileEl.files || fileEl.files.length === 0) {
      setMsg("Please choose a .csv file first.", "err");
      return;
    }
    const f = fileEl.files[0];
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setMsg("Only .csv files are allowed.", "err");
      return;
    }

    setMsg("Uploading CSV…");
    const up = await uploadCSV(f);
    const { label, features } = inferLabelAndFeatures(up.columns);

    // switch dataset to use uploaded CSV
    spec.dataset = {
      type: "csv",
      path: up.path,
      label_column: label,
      feature_columns: features,
      test_size: 0.2,
      seed: 42
    };

    // CAP to keep the demo snappy
    spec.circuit.num_qubits = Math.max(1, Math.min(features.length, 4));
    spec.optimizer.maxiter  = Math.min(spec.optimizer.maxiter ?? 20, 20);

    // update client-side preview state too
    currentData = { header: up.columns, rows: up.preview || [] };

    setMsg(`Upload OK. Using "${label}" as label and ${features.length} feature(s). Rows: ${up.rows}.`, "ok");
    result.textContent = JSON.stringify({ upload: up, chosen: spec.dataset, circuit: spec.circuit, optimizer: spec.optimizer }, null, 2);
  } catch (e) {
    setMsg(String(e.message || e), "err");
  }
};

btnLoadSample.onclick = () => {
  currentData = parseCSV(irisSample);
  setMsg('Iris sample loaded (' + currentData.rows.length + ' rows).', 'ok');
  result.textContent = JSON.stringify({ header: currentData.header, n_samples: currentData.rows.length }, null, 2);
};

btnGenerate.onclick = () => {
  const built = buildPipelineSpec();
  generatedCode = generateQiskitTemplate(built);
  document.getElementById("codePreview").textContent = generatedCode;
  setMsg("Generated code preview ready.", "ok");
};

btnDownloadCode.onclick = () => {
  if (!generatedCode) {
    setMsg("Generate code first.", "err");
    return;
  }
  download("qml_pipeline_template.py", generatedCode);
};

document.getElementById("btn-run").onclick = async () => {
  result.textContent = "Running...";
  setMsg("");

  const longRunNotice = setTimeout(() => {
    setMsg("Still running… large circuits can be slow. We cap qubits (≤4) and iterations (≤20) to keep it responsive.");
  }, 4000);

  try {
    // force a lightweight configuration before sending to backend
    spec.circuit = { type: "realamplitudes", num_qubits: 4, reps: 1 };
    spec.optimizer = { type: "cobyla", maxiter: 15 };

    const resp = await fetch("http://localhost:5000/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(spec)
    });

    const data = await resp.json();
    clearTimeout(longRunNotice);

    if (!resp.ok) {
      const detail = data?.detail || data?.error || resp.statusText;
      throw new Error(`Run failed: ${detail}`);
    }
    result.textContent = JSON.stringify(data, null, 2);
    setMsg("Pipeline finished.", "ok");
  } catch (e) {
    clearTimeout(longRunNotice);
    setMsg(String(e.message || e), "err");
    result.textContent = "";
  }
};
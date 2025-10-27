document.addEventListener("DOMContentLoaded", () => {
  const spec = {
    version: "0.1",
    pipeline: "qml-classifier",
    qnn: { type: "estimator" },
    dataset: { type: "synthetic-line", num_samples: 24, num_features: 2, test_size: 0.2, seed: 42 },
    encoder: { type: "angle" },
    circuit: { type: "ry", num_qubits: 2, reps: 2 },
    optimizer: { type: "cobyla", maxiter: 15 },
    outputs: { return_predictions: true }
  };

  const msg = id("msg"), result = id("result"), codeBox = id("codePreview");
  const selectEncoding = id("select-encoding"), selectAnsatz = id("select-ansatz"), inputLayers = id("input-layers");
  const csvInput = id("csvFile");

  function id(s){ return document.getElementById(s); }
  function setMsg(text, type="info"){
    msg.textContent = text || "";
    msg.style.color = type === "err" ? "#ef4444" : type === "ok" ? "#22c55e" : "#93a3b8";
  }
  window.onerror = (m, s, l, c, e) => setMsg("JS error: " + (e?.message || m), "err");

  if (!window.Drawflow) { setMsg("Drawflow not loaded. Check network.", "err"); return; }

  // start Drawflow
  const editor = new Drawflow(id("drawflow"));
  editor.start();

  // --- helpers ---
  let nextX = 20, nextY = 20;
  const nextPos = () => { const p = {x:nextX, y:nextY}; nextX += 170; if (nextX > 900){ nextX=20; nextY+=170; } return p; };
  const nodeHtml = (title, fields=[]) => {
    let body = `<div class="node-title"><strong>${title}</strong></div>`;
    fields.forEach(f => body += `<label class="node-param">${f.label}: <input data-param="${f.name}" value="${f.value ?? ""}" /></label>`);
    return `<div class="box">${body}</div>`;
  };
  const addNode = (type, title, params=[]) => {
    const pos = nextPos(), html = nodeHtml(title, params);
    const ins = type === "dataset" ? 0 : 1, outs = type === "output" ? 0 : 1;
    const data = { type, params: Object.fromEntries(params.map(p => [p.name, p.value ?? ""])) };
    return editor.addNode(title, ins, outs, pos.x, pos.y, null, data, html);
  };

  // --- toolbar actions ---
  id("add-dataset").onclick  = () => { addNode("dataset","Dataset",[{name:"path",label:"CSV path",value:""},{name:"label",label:"Label",value:""},{name:"features",label:"Features (comma)",value:""}]); setMsg("Dataset node added.","ok"); };
  id("add-encoder").onclick  = () => { addNode("encoder","Encoder",[{name:"type",label:"Type (angle/basis)",value:"angle"}]); setMsg("Encoder node added.","ok"); };
  id("add-circuit").onclick  = () => { addNode("circuit","Circuit",[{name:"type",label:"Type (ry/realamplitudes)",value:"ry"},{name:"num_qubits",label:"#qubits",value:"2"},{name:"reps",label:"layers",value:"1"}]); setMsg("Circuit node added.","ok"); };
  id("add-optimizer").onclick= () => { addNode("optimizer","Optimizer",[{name:"type",label:"Type",value:"cobyla"},{name:"maxiter",label:"Max iter",value:"15"}]); setMsg("Optimizer node added.","ok"); };
  id("add-output").onclick   = () => { addNode("output","Output",[{name:"predictions",label:"Return predictions (true/false)",value:"true"}]); setMsg("Output node added.","ok"); };

  // select node → side editor
  let selectedId = null;
  const showNode = (nodeId) => {
    selectedId = nodeId;
    const panel = id("node-params"), selInfo = id("selected-info");
    panel.innerHTML = "";
    if (!nodeId){ selInfo.textContent = "No node selected."; return; }
    const exp = editor.export().drawflow.Home || {};
    const node = exp[nodeId]; if (!node){ selInfo.textContent = "Node not found."; return; }
    selInfo.textContent = `${node.name} (id ${nodeId})`;
    const fields = Object.entries(node.data?.params || {}).map(([k,v]) => ({name:k,label:k,value:v}));
    panel.innerHTML = nodeHtml(node.name, fields);
  };
  editor.on("nodeSelected", idd => showNode(String(idd)));
  editor.on("nodeUnselected", () => showNode(null));

  id("btn-save-node").onclick = () => {
    if (!selectedId){ setMsg("Select a node first.","err"); return; }
    const exp = editor.export(), home = exp.drawflow.Home || {}, node = home[selectedId];
    if (!node){ setMsg("Node not found.","err"); return; }
    const inputs = document.querySelectorAll("#node-params [data-param]");
    const newParams = {}; inputs.forEach(inp => newParams[inp.getAttribute("data-param")] = inp.value);
    node.data = node.data || {}; node.data.params = {...(node.data.params||{}), ...newParams};
    node.html = nodeHtml(node.name, Object.entries(node.data.params).map(([k,v]) => ({name:k,label:k,value:v})));
    editor.import(exp); showNode(selectedId);
    setMsg("Node saved.","ok");
  };
  id("btn-delete-node").onclick = () => {
    if (!selectedId){ setMsg("Select a node first.","err"); return; }
    // Try known Drawflow removal APIs, otherwise fall back to removing from exported structure
    try {
      if (typeof editor.removeNode === 'function') {
        editor.removeNode(selectedId);
      } else if (typeof editor.removeNodeId === 'function') {
        editor.removeNodeId(selectedId);
      } else {
        const exp = editor.export();
        if (exp && exp.drawflow && exp.drawflow.Home && exp.drawflow.Home[selectedId]) {
          delete exp.drawflow.Home[selectedId];
          editor.import(exp);
        } else {
          throw new Error('No removal API available');
        }
      }
      selectedId = null; showNode(null); setMsg('Node deleted.','ok');
    } catch (er) {
      setMsg('Failed to delete node: ' + (er.message || er), 'err');
    }
  };

  // Export/Import model
  const exportModel = () => {
    const exported = (editor.export() && editor.export().drawflow && editor.export().drawflow.Home) ? editor.export().drawflow.Home : {};
    const nodes = [], edges = [];
    Object.keys(exported).forEach(id => {
      const n = exported[id];
      // compute a safe type: prefer declared data.type, otherwise fall back to node.name (lowercased) if present
      let ntype = 'node';
      if (n && n.data && n.data.type) ntype = n.data.type;
      else if (n && typeof n.name === 'string' && n.name.length) ntype = n.name.toLowerCase();
      nodes.push({ id: Number(id), type: ntype, name: n?.name, pos: { x: n?.pos_x, y: n?.pos_y }, params: n?.data?.params || {} });
      if (n && n.outputs) Object.keys(n.outputs).forEach(out =>
        (n.outputs[out].connections || []).forEach(c => edges.push({ source: Number(id), target: c.node, target_input: c.input }))
      );
    });
    return { nodes, edges };
  };
  id("btn-export-model").onclick = () => {
    const blob = new Blob([JSON.stringify(exportModel(), null, 2)], {type:"application/json"});
    const url = URL.createObjectURL(blob); const a=document.createElement("a");
    a.href=url; a.download="pipeline_model.json"; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    setMsg("Model JSON exported.","ok");
  };
  id("btn-save-model").onclick = () => {
    const raw = editor.export(); const blob = new Blob([JSON.stringify(raw,null,2)], {type:"application/json"});
    const url = URL.createObjectURL(blob); const a=document.createElement("a");
    a.href=url; a.download="drawflow.json"; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    setMsg("Drawflow JSON exported.","ok");
  };
  id("btn-load-model").onclick = () => id("file-load-model").click();
  id("btn-load-model-ui").onclick = () => id("file-load-model").click();
  id("file-load-model").addEventListener("change", ev => {
    const f = ev.target.files?.[0]; if (!f) return;
    const r = new FileReader();
    r.onload = () => {
      try {
        const j = JSON.parse(r.result);
        if (j.nodes && j.edges){
          const draw = { drawflow:{ Home:{} }, modules:{} };
          j.nodes.forEach(n => {
            const fields = Object.entries(n.params||{}).map(([k,v])=>({name:k,label:k,value:v}));
            draw.drawflow.Home[String(n.id)] = { id:n.id, name:n.name||n.type, html: nodeHtml(n.name||n.type, fields),
              pos_x:n.pos?.x||10, pos_y:n.pos?.y||10, data:{ type:n.type, params:n.params }, inputs:{}, outputs:{} };
          });
          j.edges.forEach(e => {
            const s=String(e.source), t=String(e.target);
            draw.drawflow.Home[s].outputs = draw.drawflow.Home[s].outputs || {};
            draw.drawflow.Home[s].outputs[0] = draw.drawflow.Home[s].outputs[0] || { connections: [] };
            draw.drawflow.Home[s].outputs[0].connections.push({ node:Number(t), input:e.target_input ?? 0 });
          });
          editor.import(draw);
        }else{
          editor.import(j);
        }
        setMsg("Model loaded.","ok");
      } catch (er){ setMsg("Failed to load model: "+er.message,"err"); }
    };
    r.readAsText(f);
  });

  // Generate From Model → spec + code
  id("btn-generate-from-model").onclick = () => {
    const model = exportModel(); const nmap = {};
    model.nodes.forEach(n => nmap[n.type || (n.name||"").toLowerCase()] = n);
    const ds = nmap["dataset"];
    if (ds && ds.params){
      const feats = ds.params.features ? String(ds.params.features).split(",").map(s=>s.trim()).filter(Boolean) : [];
      if (ds.params.path) spec.dataset = { type:"csv", path: ds.params.path, label_column: ds.params.label || "label", feature_columns: feats, test_size:0.2, seed:42 };
    }
    const encType = nmap["encoder"]?.params?.type || selectEncoding.value;
    const cir = nmap["circuit"]?.params || {};
    spec.encoder = { type: encType };
    spec.circuit = { type: cir.type || selectAnsatz.value, num_qubits: Number(cir.num_qubits || 2), reps: Number(cir.reps || inputLayers.value) };
    spec.optimizer = { type: nmap["optimizer"]?.params?.type || "cobyla", maxiter: Number(nmap["optimizer"]?.params?.maxiter || 15) };
    codeBox.textContent = codeTemplate(spec);
    setMsg("Spec generated from model.","ok");
  };

  // explanations
  const info = {
    dataset: "Dataset: CSV or Iris; choose label & features.",
    encoder: "Encoder: map features to qubit rotations (Angle/Basis).",
    circuit: "Circuit: variational ansatz (RY/RealAmplitudes) + layers.",
    optimizer:"Optimizer: tune parameters (COBYLA).",
    output:  "Output: accuracy and optional predictions."
  };
  document.querySelectorAll("[data-info]").forEach(b => b.addEventListener("click", () => id("info-text").textContent = info[b.dataset.info]));

  // Load Iris sample
  id("btn-load-sample").onclick = () => {
    spec.dataset = { type:"iris", path:null, label_column:"target", feature_columns:["sepal length","sepal width","petal length","petal width"], test_size:0.2, seed:42 };
    spec.circuit.num_qubits = 4; spec.circuit.reps = 1;
    setMsg("Loaded Iris sample.","ok");
  };

  // Upload CSV
  id("btn-upload").onclick = async () => {
    try{
      const f = csvInput.files?.[0]; if (!f) return setMsg("Choose a .csv first.","err");
      if (!f.name.toLowerCase().endsWith(".csv")) return setMsg("Only .csv files allowed.","err");
      setMsg("Uploading CSV…");
      const form = new FormData(); form.append("file", f);
      const resp = await fetch("http://localhost:5000/upload", { method:"POST", body: form });
      const j = await resp.json(); if(!resp.ok) throw new Error(j?.error || resp.statusText);
      const {label,features} = inferLabelAndFeatures(j.columns);
      spec.dataset = { type:"csv", path:j.path, label_column:label, feature_columns:features, test_size:0.2, seed:42 };
      spec.circuit.num_qubits = Math.max(1, Math.min(features.length, 4));
      setMsg(`Upload OK. Label = ${label}; #features = ${features.length}.`,"ok");
      result.textContent = JSON.stringify({upload:j, chosen:{label,features}}, null, 2);
    }catch(e){ setMsg(e.message || String(e), "err"); }
  };
  function inferLabelAndFeatures(cols){
    const lower = cols.map(c => String(c).toLowerCase());
    const candidates = ["label","class","target","y","outcome"];
    let li = lower.findIndex(c => candidates.includes(c));
    if (li === -1) li = cols.length - 1;
    return { label: cols[li], features: cols.filter((_,i)=>i!==li) };
  }

  // Generate code (from bottom controls)
  id("btn-generate").onclick = () => {
    spec.encoder.type = selectEncoding.value;
    spec.circuit.type = selectAnsatz.value;
    spec.circuit.reps = Number(inputLayers.value || 1);
    codeBox.textContent = codeTemplate(spec);
    setMsg("Code template generated.","ok");
  };
  function codeTemplate(s){
    const enc = s.encoder.type === "basis" ? "PauliFeatureMap" : "ZZFeatureMap";
    const ans = s.circuit.type === "realamplitudes" ? "RealAmplitudes" : "RY";
    const q = Math.max(1, Math.min(Number(s.circuit.num_qubits||2), 4));
    const reps = Math.max(1, Number(s.circuit.reps||1));
    return `# Auto-generated Qiskit template
from qiskit import QuantumCircuit
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit.circuit.library import ${enc}, ${ans}

enc = ${enc}(feature_dimension=${q})
var = ${ans}(num_qubits=${q}, reps=${reps})
qc = QuantumCircuit(${q}); qc.compose(enc, inplace=True); qc.compose(var, inplace=True)
qnn = EstimatorQNN(qc)
# Fit on your data (X,y) and report accuracy...
`;
  }
  id("btn-download-code").onclick = () => {
    const blob = new Blob([codeBox.textContent||""], {type:"text/x-python"});
    const url = URL.createObjectURL(blob); const a=document.createElement("a");
    a.href=url; a.download="generated_run.py"; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };

  // Export spec JSON
  id("btn-export").onclick = () => {
    const blob = new Blob([JSON.stringify(spec,null,2)], {type:"application/json"});
    const url = URL.createObjectURL(blob); const a=document.createElement("a");
    a.href=url; a.download="pipeline.json"; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    setMsg("Spec exported.","ok");
  };

  // Run
  id("btn-run").onclick = async () => {
    try{
      setMsg(""); result.textContent = "Running…";
      spec.circuit.num_qubits = Math.max(1, Math.min(Number(spec.circuit.num_qubits||4), 4));
      spec.optimizer.maxiter = Math.max(1, Math.min(Number(spec.optimizer.maxiter||15), 20));
      const resp = await fetch("http://localhost:5000/run", { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify(spec) });
      const data = await resp.json(); if(!resp.ok) throw new Error(data?.error || resp.statusText);
      result.textContent = JSON.stringify(data, null, 2);
      setMsg("Pipeline finished.","ok");
    }catch(e){ setMsg(e.message || String(e), "err"); result.textContent = ""; }
  };

  setMsg("Editor ready. Add nodes from the toolbar.","ok");
});

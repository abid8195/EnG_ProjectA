/* QML DataFlow Studio — Built-in Canvas + SVG Wires (no Drawflow)
   - Draggable nodes
   - Click out-port → click in-port to connect (flows)
   - Robust CSV upload updates Dataset block + spec
   - Iris sample visibly configures Dataset block
   - Null-safe model export/import, codegen, run
*/
(function(){
  // ---------- helpers ----------
  const $ = (id) => document.getElementById(id);
  const setMsg = (t, kind="info") => {
    const m = $("msg"); if (!m) return;
    m.textContent = t || "";
    m.style.color = kind === "err" ? "#ef4444" : kind === "ok" ? "#22c55e" : "#93a3b8";
  };
  const on = (id, fn) => {
    const el = $(id); if (!el) return;
    el.addEventListener("click", (e) => {
      e.preventDefault(); e.stopPropagation();
      try { fn(e); } catch (err) { console.error(err); setMsg(err.message || String(err), "err"); }
    });
  };
  const download = (name, text, mime="application/json") => {
    const url = URL.createObjectURL(new Blob([text], { type:mime }));
    const a=document.createElement("a"); a.href=url; a.download=name; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  };

  // ---------- state ----------
  const canvas = $("canvas");
  let model = { nodes: [], edges: [] };
  let selectedId = null;
  let nextX=20, nextY=20, nextId=1;
  let pendingSource = null; // for click–click wiring
  let lastUpload = null; // { ok, path, columns, preview }

  // SPEC used by backend / codegen
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

  // ---------- wiring ----------
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

    const canvasRect = document.getElementById("canvas").getBoundingClientRect();

    model.edges.forEach(e => {
      const srcEl = document.querySelector(`.node[data-id="${e.source}"] .port.out`);
      const tgtEl = document.querySelector(`.node[data-id="${e.target}"] .port.in`);
      if (!srcEl || !tgtEl) return;

      const s = srcEl.getBoundingClientRect();
      const t = tgtEl.getBoundingClientRect();

      const x1 = s.left + s.width/2  - canvasRect.left + document.getElementById("canvas").scrollLeft;
      const y1 = s.top  + s.height/2 - canvasRect.top  + document.getElementById("canvas").scrollTop;
      const x2 = t.left + t.width/2  - canvasRect.left + document.getElementById("canvas").scrollLeft;
      const y2 = t.top  + t.height/2 - canvasRect.top  + document.getElementById("canvas").scrollTop;

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      const dx = Math.max(40, Math.abs(x2 - x1) / 2);
      const d = `M ${x1} ${y1} C ${x1+dx} ${y1}, ${x2-dx} ${y2}, ${x2} ${y2}`;
      path.setAttribute("d", d);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", "#111");
      path.setAttribute("stroke-width", "2");
      path.setAttribute("stroke-linecap", "round");
      svg.appendChild(path);
    });
  }

  // ---------- node rendering ----------
  function nodeHtml(title, fields=[]){
    let body = `<div class="node-title">${title}</div>`;
    // inline ports row appended by createNodeEl
    body += `<div class="ports"></div>`;
    fields.forEach(f => body += `<label class="node-param">${f.label}: <input data-param="${f.name}" value="${f.value ?? ""}" /></label>`);
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

    // insert ports and header text
    const title = el.querySelector(".node-title");
    if (title) {
      title.textContent = n.name || n.type || "Node";
    }
    const portsWrap = el.querySelector(".ports");
    if (portsWrap) {
      const inPort  = document.createElement("span");
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

    el.addEventListener("click", (e) => { e.stopPropagation(); selectNode(n.id); });
    enableDrag(el, n.id);
    return el;
  }
  function enableDrag(el, id){
    let startX=0, startY=0, origX=0, origY=0, dragging=false;
    const down = (e) => {
      const t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      dragging = true; el.style.cursor="grabbing";
      startX = e.clientX; startY = e.clientY;
      const r = el.getBoundingClientRect();
      const c = document.getElementById("canvas");
      const cr = c.getBoundingClientRect();
      origX = r.left + c.scrollLeft - cr.left;
      origY = r.top  + c.scrollTop  - cr.top;
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    };
    const move = (e) => {
      if (!dragging) return;
      const dx = e.clientX - startX, dy = e.clientY - startY;
      const nx = Math.max(0, origX + dx), ny = Math.max(0, origY + dy);
      el.style.left = nx + "px"; el.style.top = ny + "px";
      renderWires(); // live-update wires
    };
    const up = () => {
      if (!dragging) return;
      dragging=false; el.style.cursor="grab";
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

  // ---------- selection + side panel ----------
  function selectNode(id){
    selectedId = id;
    render(); // updates selection outline
    const info = $("selected-info"), panel = $("node-params");
    const n = model.nodes.find(x => x.id === id);
    if (!n){ info.textContent = "Node not found."; panel.innerHTML=""; return; }
    info.textContent = `${n.name || n.type} (id ${n.id})`;

    const fields = Object.entries(n.params||{}).map(([k,v]) => ({name:k,label:k,value:v}));
    panel.innerHTML = fields.map(f => (
      `<label class="node-param">${f.label}: <input data-param="${f.name}" value="${f.value ?? ""}" /></label>`
    )).join("");
  }

  // ---------- add nodes ----------
  function addNode(type, title, defaults){
    const n = {
      id: nextId++,
      type,
      name: title,
      pos: { x: nextX, y: nextY },
      params: Object.fromEntries(defaults.map(d => [d.name, d.value ?? ""]))
    };
    nextX += 170; if (nextX > 900){ nextX = 20; nextY += 170; }
    model.nodes.push(n);
    render(); selectNode(n.id);
    setMsg(`${title} node added.`, "ok");
  }

  // ---------- export/import ----------
  function exportModel(){
    return JSON.parse(JSON.stringify(model)); // includes nodes + edges
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
      nextX = 20; nextY = 20;
      render(); selectedId = null; $("selected-info").textContent = "Model loaded.";
    } else {
      throw new Error("Invalid model JSON");
    }
  }

  // ---------- code template ----------
  function codeTemplate(s){
    const enc = s.encoder.type === "basis" ? "PauliFeatureMap" : "ZZFeatureMap";
    const ans = s.circuit.type === "realamplitudes" ? "RealAmplitudes" : "RY";
    const q   = Math.max(1, Math.min(Number(s.circuit.num_qubits||2), 4));
    const rep = Math.max(1, Number(s.circuit.reps||1));
    return `# Auto-generated Qiskit template
from qiskit import QuantumCircuit
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit.circuit.library import ${enc}, ${ans}

enc = ${enc}(feature_dimension=${q})
var = ${ans}(num_qubits=${q}, reps=${rep})
qc = QuantumCircuit(${q}); qc.compose(enc, inplace=True); qc.compose(var, inplace=True)
qnn = EstimatorQNN(qc)
# Fit on your data (X,y) and report accuracy...
`;
  }

  // ---------- toolbar bindings ----------
  document.addEventListener("DOMContentLoaded", () => {
    setMsg("Canvas ready. Add nodes from the toolbar.", "ok");

    // add buttons
    on("add-dataset", () => addNode("dataset","Dataset",[
      {name:"path",label:"CSV path",value:""},
      {name:"label",label:"Label",value:""},
      {name:"features",label:"Features (comma)",value:""}
    ]));
    on("add-encoder", () => addNode("encoder","Encoder",[ {name:"type",label:"Type (angle/basis)",value:"angle"} ]));
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

    // save / delete
    on("btn-save-node", () => {
      if (!selectedId) return setMsg("Select a node first.","err");
      const n = model.nodes.find(x => x.id === selectedId);
      if (!n) return setMsg("Node not found.","err");
      const inputs = document.querySelectorAll("#node-params [data-param]");
      inputs.forEach(inp => { n.params[inp.getAttribute("data-param")] = inp.value; });
      // re-render updated params on the node element
      render(); selectNode(n.id);
      setMsg("Node saved.","ok");
    });

    on("btn-delete-node", () => {
      if (!selectedId) return setMsg("Select a node first.","err");
      removeEdgesForNode(selectedId);
      model.nodes = model.nodes.filter(x => x.id !== selectedId);
      selectedId = null;
      render(); $("node-params").innerHTML = ""; $("selected-info").textContent = "No node selected.";
      setMsg("Node deleted.","ok");
    });

    // export / import
    on("btn-export-model", () => download("pipeline_model.json", JSON.stringify(exportModel(),null,2)));
    on("btn-save-model",   () => download("node_canvas.json", JSON.stringify(exportModel(),null,2)));
    on("btn-load-model",   () => $("file-load-model").click());
    on("btn-load-model-ui",() => $("file-load-model").click());
    $("file-load-model").addEventListener("change", (ev) => {
      const f = ev.target.files && ev.target.files[0]; if (!f) return;
      const r = new FileReader();
      r.onload = () => { try { importModel(JSON.parse(r.result)); } catch(e){ setMsg("Failed to load model: "+e.message,"err"); } };
      r.readAsText(f);
    });

    // info
    const info = {
      dataset: "Dataset: CSV or Iris; choose label & features.",
      encoder: "Encoder: map features to qubit rotations (Angle/Basis).",
      circuit: "Circuit: variational ansatz (RY/RealAmplitudes) + layers.",
      optimizer:"Optimizer: tune parameters (COBYLA).",
      output:  "Output: accuracy and optional predictions."
    };
    Array.from(document.querySelectorAll("[data-info]")).forEach(b => {
      b.addEventListener("click",(e)=>{ e.preventDefault(); $("info-text").textContent = info[b.dataset.info] || ""; });
    });

    // bottom actions
    const result = $("result");
    const codeBox = $("codePreview");
    const selectEncoding = $("select-encoding");
    const selectAnsatz   = $("select-ansatz");
    const inputLayers    = $("input-layers");

    on("btn-load-sample", () => {
      // Update SPEC
      spec.dataset = { type:"iris", path:null, label_column:"target",
        feature_columns:["sepal length","sepal width","petal length","petal width"], test_size:0.2, seed:42 };
      spec.circuit.num_qubits = 4; spec.circuit.reps = 1;

      // Create/update Dataset node so it’s visible
      let ds = model.nodes.find(n => (n.type||"").toLowerCase()==="dataset");
      if (!ds) {
        ds = {
          id: nextId++, type:"dataset", name:"Dataset",
          pos:{ x:20, y:20 },
          params:{ path:"(Iris built-in)", label:"target", features:"sepal length, sepal width, petal length, petal width" }
        };
        model.nodes.push(ds);
      } else {
        ds.params.path = "(Iris built-in)";
        ds.params.label = "target";
        ds.params.features = "sepal length, sepal width, petal length, petal width";
      }
      render(); selectNode(ds.id);
      setMsg("Loaded Iris sample.", "ok");
    });

    async function doUpload(file){
      const result = $("result");
      try {
        if (!file) throw new Error("Choose a .csv first.");
        if (!file.name.toLowerCase().endsWith(".csv")) throw new Error("Only .csv files allowed.");
        setMsg("Uploading CSV…");
        const form = new FormData(); form.append("file", file);
        const resp = await fetch("http://localhost:5000/upload", { method:"POST", body: form });
        const j = await resp.json(); if (!resp.ok) throw new Error(j?.error || resp.statusText);

        lastUpload = j; // store
        populateSelectorsFromUpload(j);

        const { label, features } = inferLabelAndFeatures(j.columns || []);
        // Update SPEC for legacy run path as well
        spec.dataset = { type:"csv", path:j.path, label_column:label, feature_columns:features, test_size:0.2, seed:42 };
        spec.circuit.num_qubits = Math.max(1, Math.min(features.length, 4));

        // Update Dataset node if present
        const ds = model.nodes.find(n => (n.type||"").toLowerCase()==="dataset") || null;
        if (ds) {
          ds.params.path = j.path || "";
          ds.params.label = label || "";
          ds.params.features = features.join(", ");
          if (selectedId === ds.id) selectNode(ds.id); else render();
        }

        result && (result.textContent = JSON.stringify({ upload:j, chosen:{label, features} }, null, 2));
        setMsg(`Upload OK. Label=${label}; #features=${features.length}.`,"ok");
      } catch (e) {
        setMsg(e.message || String(e), "err");
        result && (result.textContent = "");
      }
    }

    on("btn-upload", async () => {
      try {
        const fileEl = $("csvFile");
        const f = fileEl?.files?.[0]; if (!f) return setMsg("Choose a .csv first.","err");
        await doUpload(f);
        // Keep fileEl.value intact; clearing it is optional.
      } catch (e) { setMsg(e.message || String(e), "err"); }
    });
    function inferLabelAndFeatures(cols){
      if (!Array.isArray(cols) || cols.length===0) return { label:"", features:[] };
      const lower = cols.map(c => String(c||"").toLowerCase());
      const candidates = ["label","class","target","y","outcome","outcome"];
      let li = lower.findIndex(c => candidates.includes(c));
      if (li === -1) li = cols.length - 1;
      return { label: cols[li] || "", features: cols.filter((_,i) => i !== li) };
    }

    function populateSelectorsFromUpload(upload){
      if (!upload || !Array.isArray(upload.columns)) return;
      const labelSel = $("labelCol");
      const featsDiv = $("featureCols");
      if (!labelSel && !featsDiv) return; // UI not present
      const cols = upload.columns.slice();
      // label select
      if (labelSel){
        labelSel.innerHTML = "";
        cols.forEach((c, idx) => {
          const opt = document.createElement("option");
          opt.value = c; opt.textContent = c;
          if (idx === cols.length - 1) opt.selected = true;
          labelSel.appendChild(opt);
        });
      }
      // features checkboxes (default all except label)
      if (featsDiv){
        featsDiv.innerHTML = "";
        const defaultLabel = cols[cols.length - 1];
        cols.forEach((c) => {
          const id = `feat_${c.replace(/[^a-zA-Z0-9_\-]/g,'_')}`;
          const wrap = document.createElement("label");
          wrap.style.marginRight = "6px";
          const cb = document.createElement("input");
          cb.type = "checkbox"; cb.value = c; cb.id = id; cb.checked = (c !== defaultLabel);
          const txt = document.createTextNode(" " + c);
          wrap.appendChild(cb); wrap.appendChild(txt);
          featsDiv.appendChild(wrap);
        });
      }
    }

    function getSelectedFeatures(){
      const featsDiv = $("featureCols");
      if (!featsDiv) return [];
      const cbs = featsDiv.querySelectorAll('input[type="checkbox"]');
      return Array.from(cbs).filter(x => x.checked).map(x => x.value);
    }

    // New quick-run upload input
    const quickUpload = $("upload");
    if (quickUpload){
      quickUpload.addEventListener("change", async (ev) => {
        const f = ev.target.files && ev.target.files[0];
        if (f) await doUpload(f);
      });
    }

    on("btn-generate", () => {
      spec.encoder.type = selectEncoding.value;
      spec.circuit.type = selectAnsatz.value;
      spec.circuit.reps = Number(inputLayers.value || 1);
      codeBox.textContent = codeTemplate(spec);
      setMsg("Code template generated.","ok");
    });

    on("btn-download-code", () => {
      const url = URL.createObjectURL(new Blob([$("codePreview").textContent || ""], {type:"text/x-python"}));
      const a=document.createElement("a"); a.href=url; a.download="generated_run.py"; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    });

    on("btn-export", () => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(spec,null,2)],{type:"application/json"}));
      const a=document.createElement("a"); a.href=url; a.download="pipeline.json"; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
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
          const feats = typeof rawFeats === "string" ? rawFeats.split(",").map(s=>s.trim()).filter(Boolean)
                       : Array.isArray(rawFeats) ? rawFeats : [];
          spec.dataset = {
            type: ds.params.path && ds.params.path !== "(Iris built-in)" ? "csv" : (spec.dataset?.type || "synthetic-line"),
            path: ds.params.path && ds.params.path !== "(Iris built-in)" ? ds.params.path : null,
            label_column: ds.params.label || spec.dataset?.label_column || "label",
            feature_columns: feats,
            test_size: 0.2,
            seed: 42
          };
        }
        spec.encoder = { type: map["encoder"]?.params?.type || $("select-encoding").value };
        const cir = map["circuit"]?.params || {};
        spec.circuit = {
          type: cir.type || $("select-ansatz").value,
          num_qubits: Number(cir.num_qubits || 2),
          reps: Number(cir.reps || $("input-layers").value || 1)
        };
        spec.optimizer = {
          type: map["optimizer"]?.params?.type || "cobyla",
          maxiter: Number(map["optimizer"]?.params?.maxiter || 15)
        };
        $("codePreview").textContent = codeTemplate(spec);
        setMsg("Spec generated from model.","ok");
      } catch (e) { setMsg("Error generating from model: " + e.message, "err"); }
    });

    on("btn-run", async () => {
      try {
        setMsg(""); $("result").textContent = "Running…";
        spec.circuit.num_qubits = Math.max(1, Math.min(Number(spec.circuit.num_qubits||4), 4));
        spec.optimizer.maxiter  = Math.max(1, Math.min(Number(spec.optimizer.maxiter||15), 20));
        const resp = await fetch("http://localhost:5000/run", {
          method:"POST", headers:{ "Content-Type":"application/json" },
          body: JSON.stringify(spec)
        });
        const data = await resp.json(); if (!resp.ok) throw new Error(data?.error || resp.statusText);
        $("result").textContent = JSON.stringify(data, null, 2);
        setMsg("Pipeline finished.","ok");
      } catch (e) { setMsg(e.message || String(e), "err"); $("result").textContent = ""; }
    });

    // New quick Run Pipeline button
    const quickRunBtn = $("run");
    if (quickRunBtn){
      quickRunBtn.addEventListener("click", async (e) => {
        e.preventDefault(); e.stopPropagation();
        try {
          const resultBox = $("result");
          resultBox && (resultBox.textContent = "Running…");
          if (!lastUpload || !lastUpload.path) throw new Error("Upload a CSV first.");
          const labelSel = $("labelCol");
          const label = labelSel ? labelSel.value : null;
          const features = getSelectedFeatures();
          const testSizeEl = $("testSize");
          const numQEl = $("numQubits");
          const testSize = testSizeEl ? Number(testSizeEl.value || 0.2) : 0.2;
          const numQ = numQEl ? Number(numQEl.value || 4) : 4;

          const runSpec = {
            pipeline: "qml-classifier",
            qnn: { type: "estimator" },
            dataset: { type: "csv", path: lastUpload.path, label_column: label, feature_columns: features, test_size: testSize, shuffle: true },
            circuit: { type: "realamplitudes", num_qubits: numQ, reps: 1 },
            optimizer: { type: "cobyla", maxiter: 50 },
            outputs: { return_predictions: true }
          };

          const resp = await fetch("http://localhost:5000/run", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify(runSpec)
          });
          const data = await resp.json();
          if (!resp.ok) throw new Error(data?.error || resp.statusText);
          resultBox && (resultBox.textContent = JSON.stringify(data, null, 2));
          setMsg("Pipeline finished.", "ok");
        } catch (err) {
          setMsg(err.message || String(err), "err");
          const resultBox = $("result"); resultBox && (resultBox.textContent = "");
        }
      });
    }

    // See Instructions handler: download text from backend
    const seeBtn = $("seeInstructions");
    if (seeBtn){
      seeBtn.addEventListener("click", async (e) => {
        // If wrapped in a form, default submit will handle download; also provide fetch fallback
        try {
          const resp = await fetch("http://localhost:5000/instructions");
          const blob = await resp.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url; a.download = "QML_Pipeline_Instructions.txt";
          document.body.appendChild(a); a.click(); a.remove();
          URL.revokeObjectURL(url);
        } catch (_) { /* ignore */ }
      });
    }
  });
})();

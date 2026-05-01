(function () {
  const $ = (id) => document.getElementById(id);

  const setMsg = (text, kind = "info") => {
    const msg = $("msg");
    if (!msg) return;

    msg.textContent = text || "";
    msg.style.color =
      kind === "err" ? "#ef4444" :
      kind === "ok" ? "#22c55e" :
      "#93a3b8";
  };

  const on = (id, fn) => {
    const el = $(id);
    if (!el) return;

    el.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();

      try {
        fn(event);
      } catch (error) {
        console.error(error);
        setMsg(error.message || String(error), "err");
      }
    });
  };

  const download = (filename, text, mime = "application/json") => {
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;

    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  };

  const canvas = $("canvas");

  let model = {
    nodes: [],
    edges: []
  };

  let selectedId = null;
  let nextX = 20;
  let nextY = 20;
  let nextId = 1;
  let pendingSource = null;

  let accuracyChart = null;
  let lossChart = null;
  let lastMetrics = null;

  const spec = {
    version: "0.1",
    pipeline: "qml-classifier",
    qnn: {
      type: "estimator"
    },
    dataset: {
      type: "synthetic-line",
      num_samples: 24,
      num_features: 2,
      test_size: 0.2,
      seed: 42
    },
    encoder: {
      type: "angle"
    },
    circuit: {
      type: "ry",
      num_qubits: 2,
      reps: 2
    },
    optimizer: {
      type: "cobyla",
      maxiter: 15
    },
    outputs: {
      return_predictions: true
    }
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

  function validateExecutionResponse(data) {
    const required = [
      "accuracy_history",
      "loss_history",
      "epochs",
      "train_accuracy",
      "accuracy"
    ];

    const missing = required.filter((key) => !(key in data));

    if (missing.length > 0) {
      throw new Error(
        "Backend response missing metric fields: " + missing.join(", ")
      );
    }

    if (!Array.isArray(data.accuracy_history)) {
      throw new Error("accuracy_history must be an array");
    }

    if (!Array.isArray(data.loss_history)) {
      throw new Error("loss_history must be an array");
    }

    if (data.accuracy_history.length === 0 || data.loss_history.length === 0) {
      throw new Error("Backend returned empty metric history");
    }

    return true;
  }

  function formatNumber(value) {
    return typeof value === "number" ? value.toFixed(4) : "N/A";
  }

  function updateDatasetSummary(summary) {
    const box = $("dataset-summary");
    if (!box) return;

    if (!summary) {
      box.innerHTML = `
        <h3>Dataset Summary Preview</h3>
        <p>Select a dataset or run the pipeline to view dataset information.</p>
      `;
      return;
    }

    const features = summary.feature_columns || [];
    const dropped = summary.dropped_features || [];

    box.innerHTML = `
      <h3>Dataset Summary Preview</h3>
      <p><strong>Dataset type:</strong> ${summary.dataset_type || "N/A"}</p>
      <p><strong>Rows used:</strong> ${summary.rows_used ?? summary.rows ?? "N/A"}</p>
      <p><strong>Label column:</strong> ${summary.label_column || "N/A"}</p>
      <p><strong>Number of features:</strong> ${summary.num_features ?? features.length}</p>
      <p><strong>Selected features:</strong> ${features.length ? features.join(", ") : "N/A"}</p>
      ${
        dropped.length
          ? `<p><strong>Dropped non-numeric features:</strong> ${dropped.join(", ")}</p>`
          : ""
      }
    `;
  }

  function updateTrainingSummary(metrics) {
    const box = $("training-summary");
    if (!box) return;

    const summary = metrics.training_summary || {};

    box.innerHTML = `
      <div class="summary-card">
        <strong>Status</strong>
        <span>${summary.execution_status || "Completed"}</span>
      </div>
      <div class="summary-card">
        <strong>Best Accuracy</strong>
        <span>${formatNumber(summary.best_train_accuracy ?? metrics.best_train_accuracy)}</span>
      </div>
      <div class="summary-card">
        <strong>Final Loss</strong>
        <span>${formatNumber(summary.final_loss ?? metrics.final_loss)}</span>
      </div>
      <div class="summary-card">
        <strong>Convergence</strong>
        <span>${summary.convergence_status || metrics.convergence_status || "N/A"}</span>
      </div>
    `;
  }

  function drawTrainingGraphs(metrics) {
    if (!window.Chart) {
      throw new Error("Chart.js is not loaded");
    }

    validateExecutionResponse(metrics);

    const accuracyCanvas = $("accuracyChart");
    const lossCanvas = $("lossChart");

    if (!accuracyCanvas || !lossCanvas) return;

    clearCharts();

    const epochs = Array.from(
      { length: Number(metrics.epochs || 0) },
      (_, i) => i + 1
    );

    accuracyChart = new Chart(accuracyCanvas.getContext("2d"), {
      type: "line",
      data: {
        labels: epochs,
        datasets: [
          {
            label: "Training Accuracy",
            data: metrics.accuracy_history,
            borderColor: "#22c55e",
            backgroundColor: "rgba(34,197,94,0.15)",
            fill: true,
            tension: 0.25,
            pointRadius: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 500
        },
        scales: {
          y: {
            beginAtZero: true,
            suggestedMax: 1
          },
          x: {
            title: {
              display: true,
              text: "Epoch"
            }
          }
        }
      }
    });

    lossChart = new Chart(lossCanvas.getContext("2d"), {
      type: "line",
      data: {
        labels: epochs,
        datasets: [
          {
            label: "Training Loss",
            data: metrics.loss_history,
            borderColor: "#ef4444",
            backgroundColor: "rgba(239,68,68,0.15)",
            fill: true,
            tension: 0.25,
            pointRadius: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
          duration: 500
        },
        scales: {
          y: {
            beginAtZero: true
          },
          x: {
            title: {
              display: true,
              text: "Epoch"
            }
          }
        }
      }
    });

    const metricsBox = $("training-metrics");

    if (metricsBox) {
      metricsBox.innerHTML = `
        <div class="metric-card">
          <strong>Train Accuracy</strong>
          <span>${formatNumber(metrics.train_accuracy)}</span>
        </div>
        <div class="metric-card">
          <strong>Test Accuracy</strong>
          <span>${formatNumber(metrics.accuracy)}</span>
        </div>
        <div class="metric-card">
          <strong>Epochs</strong>
          <span>${metrics.epochs ?? "N/A"}</span>
        </div>
      `;
    }

    updateTrainingSummary(metrics);
    updateDatasetSummary(metrics.dataset_summary);
  }

  function addEdge(sourceId, targetId) {
    if (!model.edges.find((e) => e.source === sourceId && e.target === targetId)) {
      model.edges.push({
        source: sourceId,
        target: targetId,
        target_input: 0
      });
    }

    renderWires();
    setMsg(`Connected ${sourceId} → ${targetId}`, "ok");
  }

  function removeEdgesForNode(nodeId) {
    model.edges = model.edges.filter(
      (e) => e.source !== nodeId && e.target !== nodeId
    );

    renderWires();
  }

  function renderWires() {
    const svg = $("wires");
    if (!svg) return;

    while (svg.firstChild) {
      svg.removeChild(svg.firstChild);
    }

    const canvasEl = $("canvas");
    if (!canvasEl) return;

    const canvasRect = canvasEl.getBoundingClientRect();

    model.edges.forEach((edge) => {
      const srcEl = document.querySelector(
        `.node[data-id="${edge.source}"] .port.out`
      );
      const tgtEl = document.querySelector(
        `.node[data-id="${edge.target}"] .port.in`
      );

      if (!srcEl || !tgtEl) return;

      const s = srcEl.getBoundingClientRect();
      const t = tgtEl.getBoundingClientRect();

      const x1 = s.left + s.width / 2 - canvasRect.left + canvasEl.scrollLeft;
      const y1 = s.top + s.height / 2 - canvasRect.top + canvasEl.scrollTop;
      const x2 = t.left + t.width / 2 - canvasRect.left + canvasEl.scrollLeft;
      const y2 = t.top + t.height / 2 - canvasRect.top + canvasEl.scrollTop;

      const path = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path"
      );

      const dx = Math.max(40, Math.abs(x2 - x1) / 2);

      const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;

      path.setAttribute("d", d);
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", "#2563eb");
      path.setAttribute("stroke-width", "3");
      path.setAttribute("stroke-linecap", "round");

      svg.appendChild(path);
    });
  }

  function nodeHtml(title, fields = []) {
    let html = `<div class="node-title">${title}</div>`;
    html += `<div class="ports"></div>`;

    fields.forEach((field) => {
      html += `
        <label class="node-param">
          ${field.label}:
          <input data-param="${field.name}" value="${field.value ?? ""}" />
        </label>
      `;
    });

    return html;
  }

  function createNodeEl(node) {
    const el = document.createElement("div");

    el.className = "node";
    el.style.left = (node.pos?.x ?? 20) + "px";
    el.style.top = (node.pos?.y ?? 20) + "px";
    el.dataset.id = String(node.id);

    const fields = Object.entries(node.params || {}).map(([key, value]) => ({
      name: key,
      label: key,
      value
    }));

    el.innerHTML = nodeHtml(node.name || node.type || "Node", fields);

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

      outPort.addEventListener("click", (event) => {
        event.stopPropagation();
        pendingSource = node.id;
        setMsg(`Selected output of ${node.id}. Now click a target input.`);
      });

      inPort.addEventListener("click", (event) => {
        event.stopPropagation();

        if (pendingSource && pendingSource !== node.id) {
          addEdge(pendingSource, node.id);
        }

        pendingSource = null;
      });
    }

    el.addEventListener("click", (event) => {
      event.stopPropagation();
      selectNode(node.id);
    });

    enableDrag(el, node.id);

    return el;
  }

  function enableDrag(el, id) {
    let startX = 0;
    let startY = 0;
    let origX = 0;
    let origY = 0;
    let dragging = false;

    const down = (event) => {
      const target = event.target;

      if (
        target &&
        (
          target.tagName === "INPUT" ||
          target.tagName === "TEXTAREA" ||
          target.isContentEditable
        )
      ) {
        return;
      }

      dragging = true;
      startX = event.clientX;
      startY = event.clientY;

      const rect = el.getBoundingClientRect();
      const canvasEl = $("canvas");
      const canvasRect = canvasEl.getBoundingClientRect();

      origX = rect.left + canvasEl.scrollLeft - canvasRect.left;
      origY = rect.top + canvasEl.scrollTop - canvasRect.top;

      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    };

    const move = (event) => {
      if (!dragging) return;

      const dx = event.clientX - startX;
      const dy = event.clientY - startY;

      const newX = Math.max(0, origX + dx);
      const newY = Math.max(0, origY + dy);

      el.style.left = newX + "px";
      el.style.top = newY + "px";

      renderWires();
    };

    const up = () => {
      if (!dragging) return;

      dragging = false;

      document.removeEventListener("mousemove", move);
      document.removeEventListener("mouseup", up);

      const node = model.nodes.find((n) => n.id === id);

      if (node) {
        node.pos = {
          x: parseInt(el.style.left) || 0,
          y: parseInt(el.style.top) || 0
        };
      }

      renderWires();
    };

    el.addEventListener("mousedown", down);
  }

  function render() {
    if (!canvas) return;

    canvas.innerHTML = `<svg id="wires"></svg>`;

    model.nodes.forEach((node) => {
      const el = createNodeEl(node);

      if (node.id === selectedId) {
        el.classList.add("selected");
      }

      canvas.appendChild(el);
    });

    renderWires();
  }

  function selectNode(id) {
    selectedId = id;
    render();

    const info = $("selected-info");
    const panel = $("node-params");
    const node = model.nodes.find((n) => n.id === id);

    if (!node) {
      info.textContent = "Node not found.";
      panel.innerHTML = "";
      return;
    }

    info.textContent = `${node.name || node.type} (id ${node.id})`;

    const fields = Object.entries(node.params || {}).map(([key, value]) => ({
      name: key,
      label: key,
      value
    }));

    panel.innerHTML = fields.map((field) => `
      <label class="node-param">
        ${field.label}:
        <input data-param="${field.name}" value="${field.value ?? ""}" />
      </label>
    `).join("");
  }

  function addNode(type, title, defaults) {
    const node = {
      id: nextId++,
      type,
      name: title,
      pos: {
        x: nextX,
        y: nextY
      },
      params: Object.fromEntries(
        defaults.map((item) => [item.name, item.value ?? ""])
      )
    };

    nextX += 170;

    if (nextX > 900) {
      nextX = 20;
      nextY += 170;
    }

    model.nodes.push(node);
    render();
    selectNode(node.id);
    setMsg(`${title} node added.`, "ok");
  }

  function exportModel() {
    return JSON.parse(JSON.stringify(model));
  }

  function importModel(json) {
    if (!json || !Array.isArray(json.nodes)) {
      throw new Error("Invalid model JSON");
    }

    model = {
      nodes: [],
      edges: Array.isArray(json.edges) ? json.edges : []
    };

    json.nodes.forEach((original) => {
      model.nodes.push({
        id: Number(original.id) || nextId++,
        type: (original.type || "node").toString(),
        name: (original.name || original.type || "Node").toString(),
        pos: {
          x: Number(original.pos?.x) || 10,
          y: Number(original.pos?.y) || 10
        },
        params: typeof original.params === "object" && original.params
          ? original.params
          : {}
      });
    });

    nextId = model.nodes.reduce(
      (max, node) => Math.max(max, node.id),
      0
    ) + 1;

    nextX = 20;
    nextY = 20;
    selectedId = null;

    render();

    $("selected-info").textContent = "Model loaded.";
  }

  function codeTemplate(currentSpec) {
    const encoder =
      currentSpec.encoder.type === "basis"
        ? "PauliFeatureMap"
        : "ZZFeatureMap";

    const ansatz =
      currentSpec.circuit.type === "realamplitudes"
        ? "RealAmplitudes"
        : "RY";

    const qubits = Math.max(
      1,
      Math.min(Number(currentSpec.circuit.num_qubits || 2), 4)
    );

    const reps = Math.max(
      1,
      Number(currentSpec.circuit.reps || 1)
    );

    return `# Auto-generated Qiskit template
from qiskit import QuantumCircuit
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit.circuit.library import ${encoder}, ${ansatz}

enc = ${encoder}(feature_dimension=${qubits})
var = ${ansatz}(num_qubits=${qubits}, reps=${reps})

qc = QuantumCircuit(${qubits})
qc.compose(enc, inplace=True)
qc.compose(var, inplace=True)

qnn = EstimatorQNN(qc)
# Fit on your data and report accuracy.
`;
  }

  function updateDatasetNode(data) {
    let datasetNode = model.nodes.find(
      (node) => (node.type || "").toLowerCase() === "dataset"
    );

    if (!datasetNode) {
      datasetNode = {
        id: nextId++,
        type: "dataset",
        name: "Dataset",
        pos: {
          x: 20,
          y: 20
        },
        params: {
          path: data.path || "",
          label: data.label_column || "",
          features: (data.feature_columns || []).join(", ")
        }
      };

      model.nodes.push(datasetNode);
    } else {
      datasetNode.params.path = data.path || "";
      datasetNode.params.label = data.label_column || "";
      datasetNode.params.features = (data.feature_columns || []).join(", ");
    }

    render();
    selectNode(datasetNode.id);
  }

  document.addEventListener("DOMContentLoaded", () => {
    setMsg("Canvas ready. Add nodes from the toolbar.", "ok");

    on("add-dataset", () => addNode("dataset", "Dataset", [
      { name: "path", label: "CSV path", value: "" },
      { name: "label", label: "Label", value: "" },
      { name: "features", label: "Features comma", value: "" }
    ]));

    on("add-encoder", () => addNode("encoder", "Encoder", [
      { name: "type", label: "Type angle/basis", value: "angle" }
    ]));

    on("add-circuit", () => addNode("circuit", "Circuit", [
      { name: "type", label: "Type ry/realamplitudes", value: "ry" },
      { name: "num_qubits", label: "qubits", value: "2" },
      { name: "reps", label: "layers", value: "1" }
    ]));

    on("add-optimizer", () => addNode("optimizer", "Optimizer", [
      { name: "type", label: "Type", value: "cobyla" },
      { name: "maxiter", label: "Max iter", value: "15" }
    ]));

    on("add-output", () => addNode("output", "Output", [
      { name: "predictions", label: "Return predictions", value: "true" }
    ]));

    on("btn-save-node", () => {
      if (!selectedId) {
        return setMsg("Select a node first.", "err");
      }

      const node = model.nodes.find((n) => n.id === selectedId);

      if (!node) {
        return setMsg("Node not found.", "err");
      }

      const inputs = document.querySelectorAll("#node-params [data-param]");

      inputs.forEach((input) => {
        node.params[input.getAttribute("data-param")] = input.value;
      });

      render();
      selectNode(node.id);
      setMsg("Node saved.", "ok");
    });

    on("btn-delete-node", () => {
      if (!selectedId) {
        return setMsg("Select a node first.", "err");
      }

      removeEdgesForNode(selectedId);

      model.nodes = model.nodes.filter(
        (node) => node.id !== selectedId
      );

      selectedId = null;

      render();

      $("node-params").innerHTML = "";
      $("selected-info").textContent = "No node selected.";

      setMsg("Node deleted.", "ok");
    });

    on("btn-export-model", () => {
      download(
        "pipeline_model.json",
        JSON.stringify(exportModel(), null, 2)
      );
    });

    on("btn-save-model", () => {
      download(
        "node_canvas.json",
        JSON.stringify(exportModel(), null, 2)
      );
    });

    on("btn-load-model", () => $("file-load-model").click());
    on("btn-load-model-ui", () => $("file-load-model").click());

    $("file-load-model").addEventListener("change", (event) => {
      const file = event.target.files && event.target.files[0];

      if (!file) return;

      const reader = new FileReader();

      reader.onload = () => {
        try {
          importModel(JSON.parse(reader.result));
        } catch (error) {
          setMsg("Failed to load model: " + error.message, "err");
        }
      };

      reader.readAsText(file);
    });

    const info = {
      dataset: "Dataset block selects CSV or built-in data and validates label/features before execution.",
      encoder: "Encoder maps features to quantum-style rotations.",
      circuit: "Circuit defines the model ansatz and number of layers.",
      optimizer: "Optimizer controls training iterations.",
      output: "Output displays accuracy, loss, predictions, dataset summary, and exportable metrics."
    };

    Array.from(document.querySelectorAll("[data-info]")).forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        $("info-text").textContent = info[button.dataset.info] || "";
      });
    });

    const result = $("result");
    const codeBox = $("codePreview");
    const selectEncoding = $("select-encoding");
    const selectAnsatz = $("select-ansatz");
    const inputLayers = $("input-layers");

    async function loadDataset(datasetName) {
      try {
        setMsg(`Loading ${datasetName} dataset...`);

        const response = await fetch(
          `http://localhost:5000/dataset/${datasetName}`
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data?.error || response.statusText);
        }

        spec.dataset = {
          type: "csv",
          path: data.path,
          label_column: data.label_column,
          feature_columns: data.feature_columns,
          test_size: 0.2,
          seed: 42
        };

        spec.circuit.num_qubits = Math.max(
          1,
          Math.min(data.feature_columns.length, 4)
        );

        updateDatasetNode(data);
        updateDatasetSummary(data.dataset_summary);

        result.textContent = JSON.stringify(
          {
            dataset: data.name,
            config: data
          },
          null,
          2
        );

        setMsg(
          `${datasetName} dataset loaded successfully. Dataset summary updated.`,
          "ok"
        );
      } catch (error) {
        setMsg(error.message || String(error), "err");
      }
    }

    on("btn-diabetes", () => loadDataset("diabetes"));
    on("btn-iris", () => loadDataset("iris"));
    on("btn-realestate", () => loadDataset("realestate"));

    on("btn-upload", async () => {
      try {
        const fileInput = $("csvFile");
        const file = fileInput?.files?.[0];

        if (!file) {
          return setMsg("Choose a .csv first.", "err");
        }

        if (!file.name.toLowerCase().endsWith(".csv")) {
          return setMsg("Only .csv files allowed.", "err");
        }

        setMsg("Uploading CSV...");

        const form = new FormData();
        form.append("file", file);

        const response = await fetch("http://localhost:5000/upload", {
          method: "POST",
          body: form
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data?.error || response.statusText);
        }

        spec.dataset = {
          type: "csv",
          path: data.path,
          label_column: data.label_column,
          feature_columns: data.feature_columns,
          test_size: 0.2,
          seed: 42
        };

        spec.circuit.num_qubits = Math.max(
          1,
          Math.min(data.feature_columns.length, 4)
        );

        updateDatasetNode(data);
        updateDatasetSummary(data.dataset_summary);

        result.textContent = JSON.stringify(
          {
            upload: data
          },
          null,
          2
        );

        setMsg(
          `Upload OK. Label=${data.label_column}; #features=${data.feature_columns.length}.`,
          "ok"
        );
      } catch (error) {
        setMsg(error.message || String(error), "err");
      }
    });

    on("btn-generate", () => {
      spec.encoder.type = selectEncoding.value;
      spec.circuit.type = selectAnsatz.value;
      spec.circuit.reps = Number(inputLayers.value || 1);

      codeBox.textContent = codeTemplate(spec);

      setMsg("Code template generated.", "ok");
    });

    on("btn-download-code", () => {
      download(
        "generated_run.py",
        $("codePreview").textContent || "",
        "text/x-python"
      );
    });

    on("btn-export", () => {
      download(
        "pipeline.json",
        JSON.stringify(spec, null, 2),
        "application/json"
      );
    });

    on("btn-download-metrics", () => {
      if (!lastMetrics) {
        return setMsg(
          "Run the pipeline first before downloading metrics.",
          "err"
        );
      }

      const exportPayload = {
        exported_at: new Date().toISOString(),
        dataset_summary: lastMetrics.dataset_summary,
        training_summary: lastMetrics.training_summary,
        accuracy_history: lastMetrics.accuracy_history,
        loss_history: lastMetrics.loss_history,
        epochs: lastMetrics.epochs,
        spec_echo: lastMetrics.spec_echo
      };

      download(
        "training_metrics.json",
        JSON.stringify(exportPayload, null, 2),
        "application/json"
      );

      setMsg("Training metrics exported successfully.", "ok");
    });

    on("btn-generate-from-model", () => {
      try {
        const map = {};

        model.nodes.forEach((node) => {
          const key = (node?.type || node?.name || "node")
            .toString()
            .toLowerCase();

          map[key] = node;
        });

        const datasetNode = map["dataset"];

        if (datasetNode && datasetNode.params) {
          const rawFeatures = datasetNode.params.features;

          const features =
            typeof rawFeatures === "string"
              ? rawFeatures.split(",").map((s) => s.trim()).filter(Boolean)
              : Array.isArray(rawFeatures)
                ? rawFeatures
                : [];

          spec.dataset = {
            type:
              datasetNode.params.path &&
              datasetNode.params.path !== "(Iris built-in)"
                ? "csv"
                : spec.dataset?.type || "synthetic-line",
            path:
              datasetNode.params.path &&
              datasetNode.params.path !== "(Iris built-in)"
                ? datasetNode.params.path
                : null,
            label_column:
              datasetNode.params.label ||
              spec.dataset?.label_column ||
              "label",
            feature_columns: features,
            test_size: 0.2,
            seed: 42
          };
        }

        spec.encoder = {
          type: map["encoder"]?.params?.type || $("select-encoding").value
        };

        const circuitParams = map["circuit"]?.params || {};

        spec.circuit = {
          type: circuitParams.type || $("select-ansatz").value,
          num_qubits: Number(circuitParams.num_qubits || 2),
          reps: Number(circuitParams.reps || $("input-layers").value || 1)
        };

        spec.optimizer = {
          type: map["optimizer"]?.params?.type || "cobyla",
          maxiter: Number(map["optimizer"]?.params?.maxiter || 15)
        };

        $("codePreview").textContent = codeTemplate(spec);

        setMsg("Spec generated from model.", "ok");
      } catch (error) {
        setMsg(
          "Error generating from model: " + error.message,
          "err"
        );
      }
    });

    on("btn-run", async () => {
      try {
        setMsg("Validating and running pipeline...");
        result.textContent = "Running...";

        spec.circuit.num_qubits = Math.max(
          1,
          Math.min(Number(spec.circuit.num_qubits || 4), 4)
        );

        spec.optimizer.maxiter = Math.max(
          1,
          Math.min(Number(spec.optimizer.maxiter || 15), 20)
        );

        const response = await fetch("http://localhost:5000/run", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(spec)
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data?.error || response.statusText);
        }

        validateExecutionResponse(data);

        lastMetrics = data;

        result.textContent = JSON.stringify(data, null, 2);

        drawTrainingGraphs(data);

        setMsg(
          "Pipeline finished. Dataset summary, training summary, and charts updated successfully.",
          "ok"
        );
      } catch (error) {
        clearCharts();
        setMsg(error.message || String(error), "err");
        result.textContent = "";
      }
    });
  });
})();
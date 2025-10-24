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

let currentData = null;
let generatedCode = '';

// build a pipeline spec from current UI and dataset
function buildPipelineSpec() {
  const working = JSON.parse(JSON.stringify(spec)); // shallow copy
  // dataset from currentData if available
  if (currentData) {
    const { header } = currentData;
    const { label, features } = inferLabelAndFeatures(header);
    working.dataset = {
      type: "inline",
      path: null,
      label_column: label,
      feature_columns: features,
      n_samples: currentData.rows.length,
      preview: currentData.rows.slice(0,6)
    };
    working.circuit.num_qubits = Math.max(1, Math.min(features.length, 4));
  }
  // encoder/circuit from UI controls
  working.encoder = { type: selectEncoding.value };
  working.circuit = { type: selectAnsatz.value === 'ry' ? 'ry-layer' : 'cz-entangler', num_qubits: working.circuit.num_qubits ?? 4, reps: parseInt(inputLayers.value, 10) || 1 };
  return working;
}

function generateQiskitTemplate(specObj) {
  const features = (specObj.dataset.feature_columns || []).length || 4;
  const encoding = specObj.encoder.type || 'angle';
  const ansatz = specObj.circuit.type || 'ry-layer';
  const layers = specObj.circuit.reps || 1;

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
${ansatz === 'ry-layer' ? `    for l in range(${layers}):
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

function download(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// ---------- button handlers ----------
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
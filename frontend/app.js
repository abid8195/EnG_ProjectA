const spec = {
  version: "0.1",
  pipeline: "qml-classifier",
  qnn: { type: "estimator" },
  dataset: {
    type: "synthetic-line",
    num_samples: 20,
    num_features: 2,
    rule: "x_plus_y_ge_0",
    test_size: 0.2,
    seed: 42
  },
  encoder: { type: "zzfeaturemap" },
  circuit: { type: "realamplitudes", num_qubits: 2, reps: 1 },
  optimizer: { type: "cobyla", maxiter: 60 },
  outputs: { return_predictions: true, return_generated_code: true }
};

const info = document.getElementById("info");
const result = document.getElementById("result");

const texts = {
  dataset: "Dataset: tiny synthetic 2D points (X) with labels (y). Blue if x+y≥0 else green.",
  encoder: "Encoder (ZZFeatureMap): turns numbers into qubit rotations so the circuit can 'see' them.",
  circuit: "Circuit (QNNCircuit + RealAmplitudes): trainable pattern; optimizer tunes its angles.",
  optimizer: "Optimizer (COBYLA): knob-turner that reduces mistakes during training.",
  output: "Training & Output: .fit() learns; .score() prints accuracy; predictions returned."
};

document.getElementById("btn-dataset").onclick  = () => info.textContent = texts.dataset;
document.getElementById("btn-encoder").onclick  = () => info.textContent = texts.encoder;
document.getElementById("btn-circuit").onclick  = () => info.textContent = texts.circuit;
document.getElementById("btn-optimizer").onclick= () => info.textContent = texts.optimizer;
document.getElementById("btn-output").onclick   = () => info.textContent = texts.output;

document.getElementById("btn-export").onclick = () => {
  const blob = new Blob([JSON.stringify(spec, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "pipeline.json"; a.click();
  URL.revokeObjectURL(url);
};

document.getElementById("btn-run").onclick = async () => {
  result.textContent = "Running...";
  try {
    const resp = await fetch("http://localhost:5000/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(spec)
    });
    const data = await resp.json();
    result.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    result.textContent = "Error: " + e.message;
  }
};

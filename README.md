# QML DataFlow Studio

**A SysML and model-based design inspired visual studio for building, training, and deploying Quantum Machine Learning classification pipelines — without requiring access to real quantum hardware.**

QML DataFlow Studio lets organisations visually compose a full QML pipeline as connected blocks (dataset → encoder → circuit → optimiser → execution), train a Variational Quantum Classifier (VQC) on their own domain data, and generate actionable risk predictions — all running locally on a free quantum circuit simulator.

---

## Table of Contents

1. [What This Application Does](#what-this-application-does)
2. [Market Value and Organisational Use Case](#market-value-and-organisational-use-case)
3. [Application Workflow](#application-workflow)
4. [Getting Started](#getting-started)
5. [Settings Tuning Guide](#settings-tuning-guide)
6. [CSV File Guidelines](#csv-file-guidelines)
7. [Domain Datasets and Sample Files](#domain-datasets-and-sample-files)
8. [Interpreting Outputs](#interpreting-outputs)
9. [Technology Stack](#technology-stack)
10. [Project Structure](#project-structure)
11. [Academic References](#academic-references)

---

## What This Application Does

QML DataFlow Studio provides a five-tab interface covering the complete machine learning lifecycle:

| Tab | Purpose |
|-----|---------|
| **Pipeline Canvas** | Drag-and-drop visual builder — compose Dataset, Encoder, Circuit, Optimiser, and Execution nodes as a connected flow diagram |
| **Train** | Upload a labelled CSV, map columns to features and a target label, then train a Variational Quantum Classifier |
| **Predict** | Upload an unlabelled CSV and get per-row risk/outcome predictions using the trained model |
| **Compare** | Side-by-side accuracy and F1 comparison across multiple trained runs |
| **Code Export** | Auto-generated Qiskit or PennyLane starter code derived directly from the visual canvas |

Every setting on the canvas (encoder type, circuit depth, optimiser, shot count, iterations) is wired directly to the training and prediction execution — the canvas is the single source of truth.

---

## Market Value and Organisational Use Case

### The Problem

Real quantum hardware (IBM Quantum, IonQ, Quantinuum) costs thousands of dollars per hour of access and requires specialist infrastructure. Most organisations — banks, logistics providers, HR analytics teams — cannot justify that cost for exploratory or operational ML work.

### The Solution

This application runs on **Qiskit Aer**, IBM's official open-source quantum circuit simulator. Aer simulates quantum circuits on classical hardware with high fidelity using a statevector backend — meaning:

- No quantum hardware is needed
- No cloud credentials or API keys are required
- No usage fees — fully free and local
- Results are deterministic and reproducible

The simulation accuracy for small circuits (4–8 qubits, 1–3 reps) is mathematically equivalent to ideal noise-free quantum hardware. For practical binary classification tasks this produces results competitive with, and often comparable to, classical ML baselines.

### Why Quantum for Classification?

Variational Quantum Classifiers exploit quantum phenomena — superposition and entanglement — to encode and process feature relationships in ways that classical models cannot natively represent. For structured tabular data:

- **ZZFeatureMap** encodes feature interactions through two-qubit entangling gates, capturing second-order correlations in a single encoding layer
- **Parameterised ansatz circuits** (RealAmplitudes, EfficientSU2) create a trainable hypothesis space in the Hilbert space of the quantum system
- **Hybrid training loop** uses a classical optimiser (COBYLA, SPSA, ADAM) to minimise a cross-entropy loss measured from circuit output probabilities

For organisations without access to real quantum systems, a simulated VQC provides:
- A production-ready quantum ML workflow today
- A direct migration path to real quantum hardware in the future — the same code runs on IBM Quantum Cloud with one backend swap
- Competitive classification accuracy for low-to-medium dimensional datasets (3–8 features)
- Demonstrable quantum readiness to clients and stakeholders

### Who Can Use This

| Sector | Use Case | Target Label |
|--------|---------|-------------|
| **Banking / Finance** | Credit risk, loan default prediction, fraud screening | risk_flag (0/1) |
| **Supply Chain / Logistics** | Supplier disruption forecasting, inventory risk | disruption_flag (0/1) |
| **Human Resources** | Employee attrition prediction, retention planning | attrition_flag (0/1) |
| **Healthcare** | Patient risk stratification | diagnosis or outcome flag |
| **Insurance** | Claim likelihood, underwriting risk | claim_flag (0/1) |
| **Retail** | Customer churn prediction | churn_flag (0/1) |

Any binary classification problem with 3–8 numeric feature columns and 80–500 training rows can be plugged directly into this application.

---

## Application Workflow

### Phase 1 — Design the Pipeline (Canvas Tab)

1. Open the **Pipeline Canvas** tab
2. The default canvas shows five connected nodes: Dataset → Encoder → Circuit → Optimiser → Execution
3. Click any node to open its settings panel on the right
4. Configure:
   - **Dataset node**: select a built-in domain dataset or use "Custom Upload" for your own CSV
   - **Encoder node**: choose ZZFeatureMap (recommended for structured tabular data) or PauliFeatureMap
   - **Circuit node**: choose ansatz (RealAmplitudes recommended), set repetitions (1–3)
   - **Optimiser node**: choose COBYLA (recommended for < 50 parameters) or SPSA (recommended for large circuits)
   - **Execution node**: set framework (Qiskit Aer), shots (default 1024)
5. The canvas auto-derives the qubit count from the number of feature columns in the loaded dataset

### Phase 2 — Train the Model (Train Tab)

1. Click the **Train** tab
2. Click **Upload Training CSV** and select your labelled dataset
3. The column mapper dialog opens — assign each column to either a Feature or the Target Label
4. Review the canvas: the circuit node automatically updates its qubit count to match your feature count
5. Adjust **Iterations (training)** in the side panel settings (start with 30–50)
6. Click **Run Pipeline** (or press `Ctrl+Enter`)
7. Watch the live training curve — loss should decrease, accuracy should increase
8. When training completes, review:
   - **Test accuracy** and **F1 score** (main metrics)
   - **Baseline accuracy** (majority-class baseline to beat)
   - Training curve chart
9. The model is automatically saved to `models/` for use in prediction

### Phase 3 — Evaluate and Tune

The model is ready for prediction when:
- Test accuracy is meaningfully above the baseline (e.g., baseline 60%, model 72%+)
- F1 score is above 0.65 (balanced precision and recall)
- The training loss curve shows a downward trend (not flat from iteration 1)

If accuracy is poor, follow the [Settings Tuning Guide](#settings-tuning-guide) below.

### Phase 4 — Predict on New Data (Predict Tab)

1. Click the **Predict** tab
2. Click **Upload Prediction CSV** — this file has the same feature columns as training but **no target label column**
3. Click **Run Prediction**
4. The output table shows each row with its predicted label:
   - `HIGH RISK` / `low risk` (Finance, Supply Chain, HR)
   - Or `1` / `0` for custom datasets
5. Export results to CSV using the download button

### Phase 5 — Compare Runs (Compare Tab)

- View side-by-side bar charts of accuracy and F1 across multiple training runs
- Use this to compare the effect of different encoder, circuit, or optimiser settings

### Phase 6 — Export Code (Code Export Tab)

- Click **Generate Code** to produce a Qiskit or PennyLane script that replicates your canvas configuration
- This starter code can be extended, version-controlled, and run independently of the GUI

---

## Getting Started

### Prerequisites

- Python 3.11 or 3.12
- Windows, macOS, or Linux
- 4 GB RAM minimum (8 GB recommended for circuits with 6+ qubits)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/abid8195/EnG_ProjectA.git
cd EnG_ProjectA

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start the application
python app.py
```

### Open the Application

Navigate to `http://localhost:5000` in your browser. The Flask server serves both the frontend and all `/api/` routes from a single process — no separate frontend server is needed.

### Verify Everything Works

1. The Pipeline Canvas tab should load with 5 connected nodes
2. Select **Finance** from the Dataset node
3. Switch to the Train tab, click **Run Pipeline**
4. Training should complete in 30–120 seconds and display a loss curve

---

## Settings Tuning Guide

### Goal: Maximise test accuracy above baseline

**Step 1 — Start with defaults**

| Setting | Recommended Default |
|---------|-------------------|
| Encoder | ZZFeatureMap |
| Ansatz | RealAmplitudes |
| Reps | 1 |
| Optimiser | COBYLA |
| Iterations | 30 |
| Shots | 1024 |

Run once and note the test accuracy and F1.

**Step 2 — If accuracy is poor (< 60% or below baseline)**

- Increase **Iterations** to 80–150 (most common fix — the optimiser needs more steps)
- Increase **Reps** to 2 (adds circuit depth, more expressive hypothesis space)
- Switch encoder to **PauliFeatureMap** (captures different feature interaction patterns)
- Try **SPSA** optimiser (better for noisy loss landscapes with more parameters)

**Step 3 — If training loss is flat from the start**

- The circuit may be too shallow — increase Reps to 2 or 3
- Try **EfficientSU2** ansatz (more entanglement layers)
- Ensure feature columns are numeric and normalised — see CSV guidelines

**Step 4 — If training is very slow (> 5 min)**

- Reduce Reps to 1
- Reduce Shots to 512
- Use COBYLA instead of ADAM (fewer function evaluations)
- Reduce feature count to 4–5 columns (fewer qubits = exponentially faster simulation)

**Step 5 — Accuracy target thresholds**

| Accuracy Range | Interpretation | Action |
|---------------|---------------|--------|
| Below baseline | Model not learning | Increase iterations, change encoder |
| Baseline to +5% | Marginal improvement | Tune reps and optimiser |
| +5% to +15% above baseline | Good — ready for cautious deployment | Proceed to predict |
| +15% above baseline | Strong — confident predictions | Proceed to predict |

**Rule of thumb**: for a balanced 50/50 dataset, an accuracy of 70%+ with F1 > 0.68 is deployment-ready for organisational screening use cases (not safety-critical decisions).

---

## CSV File Guidelines

### Training CSV Requirements

| Property | Requirement |
|----------|------------|
| Format | UTF-8 encoded `.csv` with header row |
| Rows | 80–500 rows (120–200 is the sweet spot for VQC training) |
| Feature columns | 3–8 numeric columns |
| Target column | 1 binary integer column (values: 0 and 1 only) |
| Missing values | None — remove or impute all NaN rows before upload |
| Data types | All feature columns must be numeric (int or float) |
| Class balance | Aim for 40/60 to 60/40 split between 0 and 1 labels |

### Feature Column Guidelines

- Use **continuous numeric features** wherever possible (e.g., scores, ratios, counts, percentages)
- **Do not include** categorical text columns, date columns, or ID columns
- **Do not include** the target label in the feature columns
- Scale awareness: the application applies StandardScaler automatically — raw feature magnitudes do not need pre-normalisation
- Avoid highly correlated features (e.g., revenue and revenue_growth together) — quantum encoders amplify correlations

### Target Label Column

- Must be named clearly (e.g., `risk_flag`, `attrition_flag`, `disruption_flag`)
- Values must be exactly `0` (negative / safe / no-event) and `1` (positive / at-risk / event)
- No other values (NaN, 2, -1, strings) are accepted

### Prediction CSV Requirements

| Property | Requirement |
|----------|------------|
| Columns | Exactly the same feature column names as the training CSV |
| Target column | Omit the target label column |
| Rows | 1–500 rows |
| Values | Same numeric format as training data |

### Finance Domain Example

**Training columns**: `market_volatility`, `debt_ratio`, `liquidity_ratio`, `revenue_growth`, `credit_score`, `risk_flag`

**Prediction columns**: `market_volatility`, `debt_ratio`, `liquidity_ratio`, `revenue_growth`, `credit_score`

### Supply Chain Domain Example

**Training columns**: `supplier_delay_days`, `inventory_turnover`, `defect_rate`, `shipping_cost_index`, `demand_variance`, `disruption_flag`

**Prediction columns**: `supplier_delay_days`, `inventory_turnover`, `defect_rate`, `shipping_cost_index`, `demand_variance`

### HR Attrition Domain Example

**Training columns**: `overtime_hours`, `engagement_score`, `years_at_company`, `training_hours`, `performance_score`, `attrition_flag`

**Prediction columns**: `overtime_hours`, `engagement_score`, `years_at_company`, `training_hours`, `performance_score`

---

## Domain Datasets and Sample Files

### Built-in Training Datasets

Pre-loaded domain datasets are available from the Dataset node on the canvas. These require no upload:

| Dataset | Domain | Features | Rows | Target |
|---------|--------|---------|------|--------|
| Finance | Banking / Credit Risk | 5 numeric | 120 | risk_flag |
| Supply Chain | Logistics / Operations | 5 numeric | 120 | disruption_flag |
| HR Attrition | Human Resources | 5 numeric | 120 | attrition_flag |

### Sample Files for Testing

Sample CSV files are provided in `sample_data/` for end-to-end testing:

| File | Purpose |
|------|---------|
| `finance_training_120rows.csv` | Finance training dataset (120 rows, labelled) |
| `supply_chain_training_120rows.csv` | Supply chain training dataset (120 rows, labelled) |
| `hr_training_120rows.csv` | HR attrition training dataset (120 rows, labelled) |
| `finance_predict_25rows.csv` | Finance prediction test (25 rows, no label) |
| `supply_chain_predict_25rows.csv` | Supply chain prediction test (25 rows, no label) |
| `hr_predict_25rows.csv` | HR prediction test (25 rows, no label) |

**Recommended test workflow:**
1. Upload `finance_training_120rows.csv` in the Train tab
2. Map all 5 feature columns; set `risk_flag` as the target label
3. Run training with Iterations = 50
4. When training completes (accuracy > 65%), switch to the Predict tab
5. Upload `finance_predict_25rows.csv`
6. Run prediction — output column `risk_label` shows `HIGH RISK` or `low risk` per row

---

## Interpreting Outputs

### Training Output Metrics

| Metric | Description | Target |
|--------|------------|--------|
| **Test Accuracy** | Percentage of correctly classified test rows | > baseline + 5% |
| **F1 Score** | Harmonic mean of precision and recall (0–1) | > 0.65 |
| **Baseline Accuracy** | Majority-class classifier (predict all-zero) | Reference only |
| **Training Loss** | Cross-entropy loss per iteration | Should decrease |
| **Epochs** | Number of optimiser iterations completed | — |

### Prediction Output

The prediction output table contains all original feature columns plus:

| Added Column | Values | Meaning |
|-------------|--------|---------|
| `prediction` | `0` or `1` | Raw binary class output |
| `risk_label` | `HIGH RISK` / `low risk` | Human-readable label |

A prediction of `1` / `HIGH RISK` means the model places that row in the positive class — e.g., a borrower likely to default, a supplier likely to cause a disruption, or an employee likely to resign.

**Important**: These predictions are a quantitative screening tool, not a definitive verdict. Organisations should use them as a ranked list for prioritising human review, not as automated decision systems for consequential outcomes.

---

## Technology Stack

### Frontend

| Technology | Role |
|-----------|------|
| Vanilla JavaScript (ES2020) | Full application logic, canvas rendering, API calls |
| HTML5 Canvas API | Pipeline node graph — drag, connect, and configure blocks |
| SVG wires | Directional flow arrows between connected nodes |
| Chart.js v4 | Training loss curve, accuracy curve, comparison bar charts |
| Native HTML `<dialog>` | CSV column mapper modal |
| CSS Grid / Flexbox | Responsive five-tab layout |

The frontend makes all API calls using relative `/api/` paths — no hardcoded host or port. This means the same frontend works whether served from Flask's development server, a production WSGI server (Waitress), or any reverse proxy.

### Backend

| Technology | Role |
|-----------|------|
| Flask 3.x | REST API server — serves frontend static files and all `/api/` routes |
| Waitress | Production-grade WSGI server (used instead of Flask dev server) |
| joblib | Model persistence — saves/loads trained weights and pipeline spec |
| pandas | CSV parsing, feature extraction, result formatting |
| scikit-learn | StandardScaler normalisation, train/test split, accuracy/F1 metrics |
| openpyxl | Excel file support for dataset uploads |

### Quantum Machine Learning

| Technology | Role |
|-----------|------|
| Qiskit 1.x | Core quantum circuit construction and transpilation |
| Qiskit Aer | Statevector quantum circuit simulator — runs circuits locally without hardware |
| qiskit-machine-learning 0.9.x | `VQC` (Variational Quantum Classifier), feature maps, ansatze |
| qiskit-algorithms | COBYLA, SPSA, ADAM, SLSQP classical optimisers |
| BackendSamplerV2 | Connects VQC measurement to the Aer simulator backend |

### Quantum Architecture Details

The VQC pipeline follows this structure for each training run:

```
Raw CSV Features
      ↓
StandardScaler (zero mean, unit variance)
      ↓
Feature Map (ZZFeatureMap or PauliFeatureMap)
  — encodes normalised features as qubit rotation angles
  — ZZFeatureMap: second-order Pauli Z interactions, captures feature correlations
      ↓
Ansatz Circuit (RealAmplitudes / EfficientSU2 / TwoLocal)
  — parameterised Ry and CNOT gates
  — parameters θ are the trainable weights
      ↓
Measurement (BackendSamplerV2 → Aer statevector)
  — samples bitstring probability distribution over all 2^n states
      ↓
Parity Interpretation
  — XOR of all measured bits → class 0 or class 1
      ↓
Cross-Entropy Loss (computed classically)
      ↓
Classical Optimiser (COBYLA / SPSA / ADAM)
  — updates θ to minimise loss
  — iterates until convergence or max iterations reached
```

### Canvas-to-Execution Binding (SysML-Inspired Design)

The canvas is the **single source of truth** for the entire pipeline specification. Before every training or prediction run, `deriveSpecFromCanvas()` reads the current state of all canvas nodes and constructs the full pipeline specification JSON. This means:

- Changing the encoder type on the canvas changes the encoder used in training
- Changing the circuit reps changes the circuit depth
- No manual JSON editing is required — the visual model drives execution

This design mirrors **SysML Block Definition Diagrams** where system components and their interconnections are modelled graphically, and execution is derived from the model rather than hand-coded configuration.

### Model Persistence

VQC objects cannot be serialised with pickle because Qiskit internally defines a `parity` closure function that Python's pickle module cannot locate. The application solves this by:

1. **Saving**: extracting `classifier.weights` (a plain numpy array) plus the pipeline spec dict
2. **Loading**: reconstructing a fresh VQC object from the spec, then injecting the saved weights via `vqc._fit_result` (an `OptimizerResult` object) — bypassing the read-only `weights` property setter

This means the full trained state is recoverable from just the weight vector and the spec, with no dependency on pickle-incompatible closures.

---

## Project Structure

```
EnG_ProjectA/
├── app.py                          # Flask application — serves frontend + all /api/ routes
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── .gitignore
│
├── backend/
│   ├── quantum_runner.py           # VQC training engine, rebuild_classifier, model save/load
│   ├── dataset_catalog.py          # Built-in dataset registry (Finance, Supply Chain, HR)
│   ├── pipeline_registry.py        # Encoder, ansatz, optimiser configuration lookup
│   └── datasets/
│       ├── finance.csv
│       ├── supply_chain.csv
│       └── hr_attrition.csv
│
├── frontend/
│   ├── index.html                  # Main application shell — five-tab layout
│   ├── app.js                      # Full application logic — canvas, API calls, charts
│   └── style.css                   # Styling — canvas, panels, charts, responsive layout
│
├── sample_data/
│   ├── finance_training_120rows.csv
│   ├── supply_chain_training_120rows.csv
│   ├── hr_training_120rows.csv
│   ├── finance_predict_25rows.csv
│   ├── supply_chain_predict_25rows.csv
│   └── hr_predict_25rows.csv
│
├── models/                         # Trained model weights saved here (gitignored)
├── uploads/                        # Uploaded CSVs stored here temporarily (gitignored)
└── logs/                           # Training logs (gitignored)
```

---

## Academic References

The following sources informed the design, implementation, and theoretical foundations of QML DataFlow Studio:

### Quantum Machine Learning Foundations

1. Biamonte, J., Wittek, P., Pancotti, N., Rebentrost, P., Wiebe, N., & Lloyd, S. (2017). *Quantum machine learning*. Nature, 549(7671), 195–202. https://doi.org/10.1038/nature23474

2. Schuld, M., Sinayskiy, I., & Petruccione, F. (2015). *An introduction to quantum machine learning*. Contemporary Physics, 56(2), 172–185. https://doi.org/10.1080/00107514.2014.964942

3. Cerezo, M., Arrasmith, A., Babbush, R., Benjamin, S. C., Endo, S., Fujii, K., ... & Coles, P. J. (2021). *Variational quantum algorithms*. Nature Reviews Physics, 3(9), 625–644. https://doi.org/10.1038/s42254-021-00348-9

### Variational Quantum Classifiers

4. Havlíček, V., Córcoles, A. D., Temme, K., Harrow, A. W., Kandala, A., Chow, J. M., & Gambetta, J. M. (2019). *Supervised learning with quantum-enhanced feature spaces*. Nature, 567(7747), 209–212. https://doi.org/10.1038/s41586-019-0980-2

5. Schuld, M., & Killoran, N. (2019). *Quantum machine learning in feature Hilbert spaces*. Physical Review Letters, 122(4), 040504. https://doi.org/10.1103/PhysRevLett.122.040504

### Quantum Simulation and Qiskit

6. Aleksandrowicz, G., Alexander, T., Barkoutsos, P., Bello, L., Ben-Haim, Y., Bucher, D., ... & Zoufal, C. (2019). *Qiskit: An open-source framework for quantum computing*. Zenodo. https://doi.org/10.5281/zenodo.2562110

7. IBM Quantum (2023). *Qiskit Aer documentation*. https://qiskit.github.io/qiskit-aer/

8. Qiskit Machine Learning Team (2023). *Qiskit Machine Learning documentation — VQC*. https://qiskit-community.github.io/qiskit-machine-learning/

### Optimisation Methods

9. Powell, M. J. D. (1994). *A direct search optimization method that models the objective and constraint functions by linear interpolation*. In Advances in Optimization and Numerical Analysis (pp. 51–67). Springer. (COBYLA)

10. Spall, J. C. (1998). *An overview of the simultaneous perturbation method for efficient optimization*. Johns Hopkins APL Technical Digest, 19(4), 482–492. (SPSA)

### Model-Based and SysML Design

11. Friedenthal, S., Moore, A., & Steiner, R. (2014). *A Practical Guide to SysML: The Systems Modeling Language* (3rd ed.). Morgan Kaufmann.

12. Object Management Group (2019). *OMG Systems Modeling Language (SysML) v1.6 Specification*. https://www.omg.org/spec/SysML/1.6/

### Quantum Computing Market and Industry Value

13. McKinsey & Company (2021). *Quantum technology sees record investments, progress on talent gap*. McKinsey Global Institute Report.

14. Boston Consulting Group (2022). *The coming quantum leap in computing*. BCG Technology Report. https://www.bcg.com/publications/2021/building-quantum-advantage

15. Preskill, J. (2018). *Quantum computing in the NISQ era and beyond*. Quantum, 2, 79. https://doi.org/10.22331/q-2018-08-06-79

---

## Limitations and Responsible Use

- **Simulation fidelity**: Qiskit Aer statevector simulation is noise-free. Real quantum hardware introduces gate errors, decoherence, and readout noise that will affect accuracy. Results from this application represent an idealised upper bound.
- **Dataset size**: VQC training is computationally expensive on classical hardware. Datasets larger than 500 rows or circuits with more than 6 qubits will be significantly slower (minutes, not seconds).
- **Binary classification only**: The current implementation supports two-class (0/1) prediction targets. Multi-class support would require one-vs-rest encoding or a different readout strategy.
- **Not safety-critical**: Predictions should be used as a ranked screening tool to prioritise human review — not as automated decision systems for consequential outcomes (loan denials, hiring decisions, medical diagnoses).

---

## Licence

This project was developed as part of an engineering research project. See individual file headers for attribution.

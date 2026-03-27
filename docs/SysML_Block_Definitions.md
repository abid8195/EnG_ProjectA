# SysML Block Definitions for QML Pipeline

## Overview
This document defines the SysML block structure for the QML DataFlow Studio, following Model-Based Design (MBD) principles as outlined in the project requirements.

## SysML Block Hierarchy

### 1. **QMLPipeline** (System Block)
**Purpose**: Top-level system block representing the complete QML workflow
**Interfaces**: 
- Input: Raw dataset (CSV, numpy array)
- Output: Predictions, accuracy metrics, trained model

**Internal Blocks**:
- DataBlock
- EncoderBlock  
- CircuitBlock
- OptimizerBlock
- OutputBlock

### 2. **DataBlock** (Component Block)
**Purpose**: Data ingestion and preprocessing
**Stereotype**: «block»
**Properties**:
- dataset_type: {iris, diabetes, realestate, synthetic, mnist_subset}
- num_samples: Integer
- num_features: Integer
- test_size: Float [0.1, 0.5]
- seed: Integer

**Operations**:
- load_data(): Dataset
- preprocess(): NormalizedData
- split_data(): (TrainData, TestData)

**Flows Out**: ProcessedData → EncoderBlock

### 3. **EncoderBlock** (Component Block)  
**Purpose**: Quantum feature encoding
**Stereotype**: «block»
**Properties**:
- encoding_type: {angle, basis, amplitude}
- n_qubits: Integer [1, 8]
- feature_map: String

**Operations**:
- encode_classical(data): QuantumState
- create_feature_map(): QuantumCircuit

**Templates**:
- **Angle Encoding**: RY gates with classical data as rotation angles
- **Basis Encoding**: Direct binary encoding in computational basis  
- **Amplitude Encoding**: Normalized amplitudes in quantum state

**Flows**: 
- In: ProcessedData ← DataBlock
- Out: EncodedData → CircuitBlock

### 4. **CircuitBlock** (Component Block)
**Purpose**: Variational quantum neural network
**Stereotype**: «block»  
**Properties**:
- ansatz_type: {ry, ry_linear, efficient_su2, hardware_efficient}
- num_layers: Integer [1, 10] 
- num_qubits: Integer [1, 8]
- entanglement: {linear, circular, full}

**Operations**:
- build_ansatz(): VariationalCircuit
- parameterize(): ParameterizedCircuit

**Templates**:
- **RY Ansatz**: Single-qubit RY rotations + entangling gates
- **Hardware Efficient**: Native gate set for quantum hardware
- **Efficient SU2**: Universal 2-design circuits

**Flows**:
- In: EncodedData ← EncoderBlock  
- Out: QuantumFeatures → OptimizerBlock

### 5. **OptimizerBlock** (Component Block)
**Purpose**: Classical optimization of quantum parameters
**Stereotype**: «block»
**Properties**:
- optimizer_type: {cobyla, spsa, adam, l_bfgs_b}
- max_iterations: Integer [10, 1000]
- tolerance: Float
- learning_rate: Float (for gradient-based)

**Operations**:
- optimize_parameters(): OptimalParameters
- cost_function(): Float

**Flows**:
- In: QuantumFeatures ← CircuitBlock
- Out: TrainedModel → OutputBlock

### 6. **OutputBlock** (Component Block)
**Purpose**: Results aggregation and metrics
**Stereotype**: «block»
**Properties**:
- return_predictions: Boolean
- metrics: {accuracy, precision, recall, f1}

**Operations**:
- evaluate_model(): Metrics
- generate_predictions(): Predictions

**Flows**:
- In: TrainedModel ← OptimizerBlock
- Out: Results → System Boundary

## Block Relationships (SysML Internal Block Diagram)

```
[QMLPipeline]
├── DataBlock
│   ├── load_iris() | load_diabetes() | load_mnist_subset()
│   └── flow: ProcessedData
├── EncoderBlock  
│   ├── angle_encoding() | basis_encoding()
│   └── flow: EncodedData
├── CircuitBlock
│   ├── ry_ansatz() | hardware_efficient_ansatz()
│   └── flow: QuantumFeatures  
├── OptimizerBlock
│   ├── cobyla() | spsa()
│   └── flow: TrainedModel
└── OutputBlock
    └── flow: Results
```

## Flow Specifications

### Data Flow (SysML Activity Diagram)
1. **RawData** → [DataBlock.preprocess()] → **ProcessedData**
2. **ProcessedData** → [EncoderBlock.encode()] → **EncodedData** 
3. **EncodedData** → [CircuitBlock.parameterize()] → **QuantumFeatures**
4. **QuantumFeatures** → [OptimizerBlock.optimize()] → **TrainedModel**
5. **TrainedModel** → [OutputBlock.evaluate()] → **Results**

### Control Flow
- Sequential execution: DataBlock → EncoderBlock → CircuitBlock → OptimizerBlock → OutputBlock
- Error handling: Each block validates inputs and propagates errors
- State persistence: Model parameters saved at each optimization step

## Validation Requirements
- **Iris Dataset**: Binary classification (setosa vs versicolor)
- **MNIST Subset**: Digit classification (0 vs 1) with 1000 samples max
- **Accuracy Target**: >80% on test set for valid pipeline
- **Performance**: <60 seconds execution time

This SysML structure ensures the QML DataFlow Studio follows formal MBD principles while remaining practical for quantum machine learning workflows.
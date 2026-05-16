"""
Pipeline component registry.

Defines the supported encoders, ansatze, and optimizers.
Flask serves this via /api/registry so the frontend builds dropdowns dynamically —
adding a new component here automatically makes it available in the UI.
"""
from __future__ import annotations

ENCODER_REGISTRY: dict = {
    "angle": {
        "label": "Angle Encoding (ZZFeatureMap)",
        "description": "Maps each feature to a rotation angle. Good general-purpose choice.",
        "qiskit_class": "ZZFeatureMap",
    },
    "basis": {
        "label": "Basis Encoding (PauliFeatureMap)",
        "description": "Pauli Z + ZZ terms. Captures pairwise feature interactions.",
        "qiskit_class": "PauliFeatureMap",
    },
    "iqp": {
        "label": "IQP Encoding (PauliFeatureMap X+ZZ)",
        "description": "Instantaneous Quantum Polynomial encoding. Adds X-basis correlations.",
        "qiskit_class": "PauliFeatureMap",
    },
}

ANSATZ_REGISTRY: dict = {
    "realamplitudes": {
        "label": "RealAmplitudes",
        "description": "RY rotations + CNOT entanglement. Efficient and widely used.",
        "qiskit_class": "RealAmplitudes",
    },
    "efficientsu2": {
        "label": "EfficientSU2",
        "description": "SU(2) rotations (RY+RZ) + CX entanglement. Higher expressibility.",
        "qiskit_class": "EfficientSU2",
    },
    "twolocal": {
        "label": "TwoLocal (RY+RZ / CX)",
        "description": "Customisable two-local circuit. Broad parameter space.",
        "qiskit_class": "TwoLocal",
    },
    "ry": {
        "label": "RY Layers",
        "description": "Simple RY-only layers. Fast to evaluate, lower expressibility.",
        "qiskit_class": "RealAmplitudes",
    },
}

OPTIMIZER_REGISTRY: dict = {
    "cobyla": {
        "label": "COBYLA (gradient-free)",
        "description": "Constrained Optimisation BY Linear Approximation. Reliable for small circuits.",
        "qiskit_class": "COBYLA",
    },
    "spsa": {
        "label": "SPSA (stochastic gradient)",
        "description": "Simultaneous Perturbation Stochastic Approximation. Robust to noise.",
        "qiskit_class": "SPSA",
    },
    "adam": {
        "label": "ADAM (adaptive gradient)",
        "description": "Adaptive moment estimation. Fast convergence for smooth landscapes.",
        "qiskit_class": "ADAM",
    },
    "slsqp": {
        "label": "SLSQP (gradient-based)",
        "description": "Sequential Least Squares Programming. Best for noiseless simulators.",
        "qiskit_class": "SLSQP",
    },
}

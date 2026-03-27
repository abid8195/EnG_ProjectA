from qiskit_machine_learning.algorithms.classifiers import NeuralNetworkClassifier
from qiskit_machine_learning.neural_networks import EstimatorQNN
from qiskit_machine_learning.circuit.library import QNNCircuit
from qiskit.primitives import Estimator
import numpy as np

# Test if we can use a simple function as optimizer
def simple_optimizer(objective_function, initial_point, **kwargs):
    """Simple test optimizer"""
    from scipy.optimize import minimize
    result = minimize(objective_function, initial_point, method='COBYLA', 
                     options={'maxiter': kwargs.get('maxiter', 100)})
    return result.x

# Let's see what the interface expects
try:
    # Create a simple test circuit
    qc = QNNCircuit(num_qubits=2)
    qnn = EstimatorQNN(circuit=qc, estimator=Estimator())
    
    # Try with simple function
    clf = NeuralNetworkClassifier(qnn, optimizer=simple_optimizer)
    print("✓ Custom optimizer function accepted")
    
except Exception as e:
    print("✗ Custom optimizer failed:", e)
    import traceback
    traceback.print_exc()
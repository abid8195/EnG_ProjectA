import qiskit
print("Qiskit version:", qiskit.__version__)

try:
    from qiskit.utils import algorithm_globals
    print("✓ qiskit.utils.algorithm_globals found")
except ImportError as e:
    print("✗ qiskit.utils.algorithm_globals not found:", e)
    try:
        from qiskit_algorithms.utils import algorithm_globals
        print("✓ qiskit_algorithms.utils.algorithm_globals found")
    except ImportError as e2:
        print("✗ qiskit_algorithms.utils.algorithm_globals not found:", e2)

try:
    from qiskit.algorithms.optimizers import COBYLA
    print("✓ qiskit.algorithms.optimizers.COBYLA found")
except ImportError as e:
    print("✗ qiskit.algorithms.optimizers.COBYLA not found:", e)
    try:
        from qiskit_algorithms.optimizers import COBYLA
        print("✓ qiskit_algorithms.optimizers.COBYLA found")
    except ImportError as e2:
        print("✗ qiskit_algorithms.optimizers.COBYLA not found:", e2)

try:
    from qiskit_machine_learning.neural_networks import EstimatorQNN
    print("✓ EstimatorQNN found")
except ImportError as e:
    print("✗ EstimatorQNN not found:", e)

try:
    from qiskit.primitives import Estimator
    print("✓ Estimator found")
except ImportError as e:
    print("✗ Estimator not found:", e)
import qiskit.utils
print("Available in qiskit.utils:", dir(qiskit.utils))

try:
    import numpy as np
    np.random.seed(42)
    print("✓ Using numpy.random as fallback")
except Exception as e:
    print("✗ numpy fallback failed:", e)
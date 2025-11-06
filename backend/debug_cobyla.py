try:
    from qiskit.algorithms.optimizers import COBYLA
    print("✓ qiskit.algorithms.optimizers.COBYLA works")
except Exception as e:
    print("✗ qiskit.algorithms.optimizers failed:", str(e))
    print("Exception type:", type(e))
    try:
        from qiskit_algorithms.optimizers import COBYLA
        print("✓ qiskit_algorithms.optimizers.COBYLA works")
    except Exception as e2:
        print("✗ qiskit_algorithms.optimizers failed:", str(e2))
        print("Exception type:", type(e2))
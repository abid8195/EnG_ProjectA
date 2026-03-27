try:
    from scipy.optimize import minimize
    print("✓ scipy.optimize.minimize available")
    
    # Test if we can create a simple COBYLA-like optimizer
    def cobyla_optimizer(fun, x0, maxiter=100):
        """Simple wrapper around scipy.optimize.minimize with COBYLA method"""
        result = minimize(fun, x0, method='COBYLA', options={'maxiter': maxiter})
        return result.x, result.fun, result.nfev
    
    print("✓ COBYLA wrapper function created")
    
except Exception as e:
    print("✗ scipy optimizer failed:", e)

# Also check if we can import other optimizers
try:
    from qiskit.algorithms.optimizers import SPSA  # This might be available
    print("✓ SPSA optimizer available")
except Exception as e:
    print("✗ SPSA not available:", e)
#!/usr/bin/env python3
"""Test imports for QML pipeline."""
try:
    from runner import run_pipeline
    print("✓ runner.py imports successful!")
    
    from codegen import write_generated_run
    print("✓ codegen.py imports successful!")
    
    print("✓ All imports working correctly!")
    
except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
"""
quantum_runner.py — DEPRECATED shim
-------------------------------------
All execution logic has been migrated to the ``runners/`` package as part of
the Strategy Pattern refactor.  This file is kept only for backwards
compatibility with any external code that imports directly from it.

    DEPRECATED: from quantum_runner import run_pipeline
    USE INSTEAD: from runners import get_runner
                 get_runner(spec).run(spec)

    DEPRECATED: from quantum_runner import list_execution_backends
    USE INSTEAD: from runners import list_all_backends

This shim will be removed in a future release.
"""

import warnings

from runners.aer_simulator import AerSimulatorRunner as _AerRunner
from runners import list_all_backends as list_execution_backends  # noqa: F401

__all__ = ["run_pipeline", "list_execution_backends"]


def run_pipeline(spec: dict) -> dict:
    """
    DEPRECATED. Use ``runners.get_runner(spec).run(spec)`` instead.

    Kept for backwards compatibility — delegates to AerSimulatorRunner.
    """
    warnings.warn(
        "quantum_runner.run_pipeline() is deprecated. "
        "Use `from runners import get_runner; get_runner(spec).run(spec)` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _AerRunner().run(spec)

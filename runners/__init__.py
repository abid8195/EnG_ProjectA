"""
runners/__init__.py
-------------------
Public API for the runners package.

Exports
-------
get_runner(spec)      → PipelineRunner
    Factory: selects the correct runner from the pipeline spec.

list_all_backends()   → dict
    Aggregates describe() from every registered runner for the /backends
    endpoint.

PipelineRunner
    Re-exported so callers can type-hint without touching runners.base.

Selection logic in get_runner()
--------------------------------
1. ``spec["pipeline_type"] == "classical"``  → ClassicalRunner
2. ``spec["execution"]["provider"] == "kipu"`` → KipuHubRunner
3. Default → AerSimulatorRunner
"""

from __future__ import annotations

from typing import Any, Dict

from runners.base import PipelineRunner
from runners.classical import ClassicalRunner
from runners.aer_simulator import AerSimulatorRunner
from runners.kipu_hub import KipuHubRunner

# Registry of all available runners (order determines /backends list order)
_REGISTRY: list[PipelineRunner] = [
    AerSimulatorRunner(),
    ClassicalRunner(),
    KipuHubRunner(),
]


def get_runner(spec: Dict[str, Any]) -> PipelineRunner:
    """
    Select and return the appropriate PipelineRunner for the given spec.

    Parameters
    ----------
    spec : dict
        Full pipeline specification from the /run request body.

    Returns
    -------
    PipelineRunner
        The concrete runner instance to call ``.run(spec)`` on.
    """
    pipeline_type = (spec.get("pipeline_type") or "").lower()
    provider = (spec.get("execution", {}).get("provider") or "").lower()

    if pipeline_type == "classical":
        return ClassicalRunner()

    if provider == "kipu":
        return KipuHubRunner()

    # Default: Qiskit Aer quantum simulation
    return AerSimulatorRunner()


def list_all_backends() -> Dict[str, Any]:
    """
    Return a dict describing every registered backend, suitable for the
    /backends Flask route.

    Returns
    -------
    dict with keys:
        ``backends``          list of backend description dicts
        ``official_simulator``  str — the recommended default backend name
    """
    return {
        "backends": [runner.describe() for runner in _REGISTRY],
        "official_simulator": "qiskit-aer",
    }


__all__ = [
    "PipelineRunner",
    "get_runner",
    "list_all_backends",
]

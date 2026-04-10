"""
runners/kipu_hub.py
-------------------
KipuHubRunner — stub for future Kipu real-hardware execution.

This runner is registered as a valid backend so it appears in the /backends
response and the UI can show it as "coming soon."  Any attempt to actually
call ``run()`` raises a descriptive NotImplementedError until the Kipu Hub
SDK and credentials are wired in.

To implement this runner in the future:
1. Install the Kipu Hub SDK / client library.
2. Replace the ``run()`` body with real API calls.
3. Flip ``available`` to ``True`` in ``describe()``.
4. Add KipuHub credential handling (env vars / config file).
"""

from __future__ import annotations

from typing import Any, Dict

from runners.base import PipelineRunner


class KipuHubRunner(PipelineRunner):
    """
    Forward-compatible stub for Kipu Hub real-hardware quantum execution.

    Raises ``NotImplementedError`` if called until the API is wired up.
    """

    # ------------------------------------------------------------------
    # PipelineRunner interface
    # ------------------------------------------------------------------

    def describe(self) -> Dict[str, Any]:
        return {
            "provider": "kipu",
            "backend": "kipu-hub",
            "label": "Kipu Hub (coming soon)",
            "available": False,
        }

    def run(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError(
            "KipuHub real-hardware execution is not yet implemented. "
            "Set execution.provider to 'aer' to use the local Qiskit Aer "
            "simulator, or set pipeline_type to 'classical' for a "
            "Logistic Regression baseline."
        )

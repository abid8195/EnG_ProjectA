"""
runner.py — backwards-compatible shim
--------------------------------------
DO NOT add new logic here.  This file exists purely so that any legacy code
(tests, notebooks, scripts) that did ``from runner import run_pipeline``
continues to work without modification.

All execution logic has moved to the ``runners/`` package.
"""

from runners import get_runner


def run_pipeline(spec: dict) -> dict:
    """Shim: delegate to the appropriate PipelineRunner via the factory."""
    return get_runner(spec).run(spec)

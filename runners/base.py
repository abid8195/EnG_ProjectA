"""
runners/base.py
---------------
Abstract base class that defines the shared contract every PipelineRunner
implementation must satisfy.

Design notes
------------
- ``run()`` accepts the full pipeline spec dict and returns a
  dashboard-compatible result dict. Both the classical and quantum runners
  return the same top-level keys so the frontend never needs to branch on
  runner type.
- ``describe()`` returns a machine-readable summary of the backend for the
  /backends endpoint.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class PipelineRunner(ABC):
    """
    Strategy interface for all execution backends.

    Subclasses must implement :py:meth:`run` and :py:meth:`describe`.
    They should not override ``__init__`` unless they need to accept
    runner-specific configuration that cannot come from the spec dict.
    """

    @abstractmethod
    def run(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the full ML pipeline described by *spec* and return metrics.

        Parameters
        ----------
        spec : dict
            Pipeline specification. Recognised top-level keys:

            ``dataset``
                Source data (name, path, label_column, feature_columns, …)
            ``circuit``
                Quantum circuit config (num_qubits, reps, …)  — ignored by
                ClassicalRunner.
            ``encoder``
                Feature-map config (type, reps) — ignored by ClassicalRunner.
            ``optimizer``
                Optimiser config (type, maxiter).
            ``execution``
                Backend config (provider, shots).
            ``pipeline_type``
                Optional. ``"classical"`` forces ClassicalRunner regardless of
                the execution provider.

        Returns
        -------
        dict
            Must contain at minimum:
            ``status``, ``accuracy``, ``train_accuracy``,
            ``loss_history``, ``accuracy_history``, ``epochs``,
            ``n_train``, ``n_test``.
        """
        ...

    @abstractmethod
    def describe(self) -> Dict[str, Any]:
        """
        Return a machine-readable description of this backend.

        Returns
        -------
        dict
            Must contain at minimum:
            ``provider`` (str), ``label`` (str), ``available`` (bool).
        """
        ...

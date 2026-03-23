"""
Small helper for integrating Kipu Quantum Hub (Kipu Quantum Hub + Qiskit provider).

Keep this file intentionally minimal so the rest of the app can dispatch between:
- classical execution (existing)
- kipu_simulator execution (Sprint 1 demo)
"""

from __future__ import annotations

import os
from typing import Any


def _require_access_token() -> str:
    token = os.getenv("KIPU_ACCESS_TOKEN")
    token = token.strip() if isinstance(token, str) else ""
    if not token:
        raise ValueError(
            "Missing KIPU_ACCESS_TOKEN environment variable. "
            "Set it before using execution_mode='kipu_simulator'."
        )
    return token


def get_kipu_provider() -> Any:
    """
    Return a HubQiskitProvider authenticated using KIPU_ACCESS_TOKEN.
    """
    try:
        from qhub.quantum.sdk import HubQiskitProvider
    except ImportError as e:
        raise ImportError(
            "Kipu integration requires 'qhub-quantum' package. "
            "Install it with `pip install qhub-quantum` (or update requirements)."
        ) from e

    try:
        return HubQiskitProvider(access_token=_require_access_token())
    except Exception as e:
        raise ValueError(f"Kipu provider initialization failed: {e}")


def get_kipu_backend(backend_name: str | None = None) -> Any:
    """
    Return a Qiskit backend from Kipu Quantum Hub.
    """
    provider = get_kipu_provider()
    name = backend_name or os.getenv("KIPU_BACKEND_NAME", "azure.ionq.simulator")
    return provider.get_backend(name)


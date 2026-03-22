# backend/kipu_executor.py
"""
Kipu Quantum Hub execution module.
Uses the qhub-quantum SDK (pip install qhub-quantum).
Docs: https://kipu-quantum.com/platform/
"""

from __future__ import annotations
import time
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_kipu_backends(token: str) -> List[Dict[str, Any]]:
    """
    Return a list of available Kipu backends (simulators + real hardware).

    Each entry:
        {
          "name":        str,        # backend identifier
          "type":        str,        # "simulator" | "hardware"
          "num_qubits":  int | None,
          "operational": bool,
          "description": str
        }

    Raises:
        ImportError  – qhub-quantum is not installed
        RuntimeError – authentication failed or API error
    """
    provider = _get_provider(token)
    backends = []

    try:
        raw_backends = provider.backends()
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch Kipu backends: {exc}") from exc

    for b in raw_backends:
        try:
            cfg = b.configuration()
            n_qubits = getattr(cfg, "n_qubits", None)
            simulator = getattr(cfg, "simulator", False)
            backend_name = getattr(cfg, "backend_name", str(b))
            description = getattr(cfg, "description", "")
            operational = getattr(b.status(), "operational", True)
        except Exception:
            backend_name = str(b)
            n_qubits = None
            simulator = False
            operational = True
            description = ""

        backends.append({
            "name":        backend_name,
            "type":        "simulator" if simulator else "hardware",
            "num_qubits":  n_qubits,
            "operational": operational,
            "description": description,
        })

    return backends


def run_kipu_circuit(
    token:        str,
    backend_name: str,
    circuit_spec: Dict[str, Any],
    shots:        int = 1024,
    timeout_s:    int = 120,
) -> Dict[str, Any]:
    """
    Build a Qiskit circuit from *circuit_spec*, submit it to the specified
    Kipu backend, wait for results and return them.

    circuit_spec keys (all optional):
        num_qubits  (int, default 2)
        gates       list of {"gate": "h"|"cx"|"rx"|"ry"|"rz", "qubits": [...], "params":[...]}
        measure_all (bool, default True)

    Returns:
        {
          "status":     "ok",
          "job_id":     str,
          "backend":    str,
          "shots":      int,
          "counts":     {str: int},
          "time_taken": float   # seconds
        }

    Raises:
        ImportError  – qhub-quantum or qiskit not installed
        RuntimeError – execution error / timeout
    """
    from qiskit import QuantumCircuit  # raises ImportError if qiskit missing

    provider     = _get_provider(token)
    num_qubits   = max(1, min(int(circuit_spec.get("num_qubits", 2)), 20))
    measure_all  = bool(circuit_spec.get("measure_all", True))
    gates        = circuit_spec.get("gates", [])

    # ------------------------------------------------------------------
    # Build circuit
    # ------------------------------------------------------------------
    qc = QuantumCircuit(num_qubits, num_qubits if measure_all else 0)

    # Apply any explicit gates first
    for g in gates:
        gate   = str(g.get("gate", "")).lower()
        qubits = [int(q) for q in g.get("qubits", [])]
        params = [float(p) for p in g.get("params", [])]

        # Guard: skip qubits out of range
        if any(q >= num_qubits for q in qubits):
            continue

        if gate == "h" and len(qubits) == 1:
            qc.h(qubits[0])
        elif gate == "cx" and len(qubits) == 2:
            qc.cx(qubits[0], qubits[1])
        elif gate == "rx" and len(qubits) == 1 and params:
            qc.rx(params[0], qubits[0])
        elif gate == "ry" and len(qubits) == 1 and params:
            qc.ry(params[0], qubits[0])
        elif gate == "rz" and len(qubits) == 1 and params:
            qc.rz(params[0], qubits[0])
        elif gate == "x" and len(qubits) == 1:
            qc.x(qubits[0])
        elif gate == "z" and len(qubits) == 1:
            qc.z(qubits[0])
        elif gate == "s" and len(qubits) == 1:
            qc.s(qubits[0])
        elif gate == "t" and len(qubits) == 1:
            qc.t(qubits[0])

    # Default: Bell-state-like circuit when no gates supplied
    if not gates:
        qc.h(0)
        if num_qubits > 1:
            qc.cx(0, 1)

    if measure_all:
        qc.measure(list(range(num_qubits)), list(range(num_qubits)))

    # ------------------------------------------------------------------
    # Submit to Kipu
    # ------------------------------------------------------------------
    try:
        backend = provider.get_backend(backend_name)
    except Exception as exc:
        raise RuntimeError(
            f"Backend '{backend_name}' not found on Kipu Hub: {exc}"
        ) from exc

    t0 = time.time()
    try:
        job = backend.run(qc, shots=shots)
        job_id = str(job.job_id())
    except Exception as exc:
        raise RuntimeError(f"Failed to submit job to Kipu: {exc}") from exc

    # ------------------------------------------------------------------
    # Poll for result
    # ------------------------------------------------------------------
    counts = _wait_for_result(job, timeout_s=timeout_s)
    elapsed = round(time.time() - t0, 2)

    return {
        "status":     "ok",
        "job_id":     job_id,
        "backend":    backend_name,
        "shots":      shots,
        "counts":     counts,
        "time_taken": elapsed,
        "circuit":    qc.draw(output="text").__str__(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_provider(token: str):
    """Instantiate HubQiskitProvider with the user token."""
    try:
        from qhub_quantum.providers.qiskit import HubQiskitProvider  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "qhub-quantum is not installed. Run: pip install qhub-quantum"
        ) from exc

    if not token or not token.strip():
        raise ValueError("A Kipu personal access token is required.")

    try:
        provider = HubQiskitProvider(token=token.strip())
    except Exception as exc:
        raise RuntimeError(
            f"Failed to authenticate with Kipu Hub: {exc}"
        ) from exc

    return provider


def _wait_for_result(job, timeout_s: int = 120) -> Dict[str, int]:
    """Poll a Kipu job until it completes, then return measurement counts."""
    deadline = time.time() + timeout_s
    poll_interval = 2  # seconds

    while time.time() < deadline:
        try:
            status = job.status()
            status_name = status.name if hasattr(status, "name") else str(status)

            if status_name in ("DONE", "COMPLETED", "JobStatus.DONE"):
                result = job.result()
                counts = result.get_counts()
                # counts may be a list (one experiment) — flatten
                if isinstance(counts, list):
                    counts = counts[0] if counts else {}
                return {str(k): int(v) for k, v in counts.items()}

            elif status_name in ("ERROR", "CANCELLED", "FAILED",
                                  "JobStatus.ERROR", "JobStatus.CANCELLED"):
                raise RuntimeError(f"Kipu job ended with status: {status_name}")

        except RuntimeError:
            raise
        except Exception:
            pass  # transient poll failure — keep trying

        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.5, 10)  # exponential back-off

    raise RuntimeError(
        f"Kipu job timed out after {timeout_s}s. "
        "The job may still be running on the Kipu Hub."
    )

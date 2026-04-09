# EnG_ProjectB

SysML and model-based design inspired visual studio for building Quantum Machine Learning pipelines as connected blocks, exporting a structured JSON specification, generating Qiskit or PennyLane starter code, and running a Qiskit-backed quantum classifier on domain datasets for Finance, Supply Chain, and Human Resources with Qiskit Aer as the official simulator.

## Canonical app

- Frontend: [index.html](C:\Users\abidu\OneDrive\Documents\eng_proj_B\Eng_Proj_B\EnG_ProjectB\index.html)
- Backend API: [app.py](C:\Users\abidu\OneDrive\Documents\eng_proj_B\Eng_Proj_B\EnG_ProjectB\app.py)
- Quantum execution engine: [quantum_runner.py](C:\Users\abidu\OneDrive\Documents\eng_proj_B\Eng_Proj_B\EnG_ProjectB\quantum_runner.py)

The `backend/` folder now acts as a compatibility shim that points to the canonical root application.

## Client-goal coverage

- Visual block and flow modeling of a QML pipeline
- JSON pipeline export from the modeled graph
- Auto-generated Qiskit and PennyLane code templates
- Quantum training and inference driven by the modeled encoder, circuit, optimizer, and execution settings
- Official local simulator execution through Qiskit Aer
- Domain datasets for Finance, Supply Chain, and Human Resources

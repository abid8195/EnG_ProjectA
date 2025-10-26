import io
import json
from app import app  # import from this folder

def test_upload_and_run():
    client = app.test_client()

    # small CSV content
    data = {'file': (io.BytesIO(b'feature1,feature2,label\n1,2,0\n3,4,1'), 'test.csv')}
    resp = client.post('/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200, f"Upload failed: {resp.data}"
    j = resp.get_json()
    assert j.get('ok') is True
    assert 'path' in j and 'columns' in j and 'rows' in j

    # Minimal spec with CSV dataset pointing to the uploaded path
    spec = {
        'pipeline': 'test',
        'qnn': {'type': 'estimator'},
        'dataset': {'type': 'csv', 'path': j['path'], 'label_column': 'label', 'feature_columns': ['feature1','feature2']},
        'circuit': {'type': 'realamplitudes', 'num_qubits': 2, 'reps': 1},
        'optimizer': {'type': 'cobyla', 'maxiter': 1},
        'outputs': {'return_predictions': False}
    }
    resp2 = client.post('/run', data=json.dumps(spec), content_type='application/json')
    assert resp2.status_code == 200, f"Run failed: {resp2.data}"
    j2 = resp2.get_json()
    # If qiskit not installed, we still get a graceful payload with status ok
    assert j2.get('status') in ('success', 'ok')

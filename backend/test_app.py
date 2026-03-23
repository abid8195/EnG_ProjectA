import io, json
from app import app

def test_upload_and_run():
    client = app.test_client()

    # Upload CSV
    data = {'file': (io.BytesIO(b'feature1,feature2,label\n1,2,0\n3,4,1'), 'test.csv')}
    resp = client.post('/upload', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200, f"Upload failed: {resp.data}"
    j = resp.get_json()
    assert j.get('ok') is True
    assert 'path' in j and 'columns' in j and 'preview' in j

    # Minimal spec that points to uploaded CSV
    spec = {
        'pipeline': 'test',
        'qnn': {'type': 'estimator'},
        'dataset': {'type': 'csv', 'path': j['path'], 'label_column': 'label', 'feature_columns': ['feature1','feature2']},
        'circuit': {'type': 'realamplitudes', 'num_qubits': 2, 'reps': 1},
        'optimizer': {'type': 'cobyla', 'maxiter': 1},
        'outputs': {'return_predictions': False}
    }
    resp2 = client.post('/run', data=json.dumps(spec), content_type='application/json')

    if resp2.status_code == 200:
        j2 = resp2.get_json()
        assert j2.get('status') == 'ok'
    else:
        assert resp2.status_code == 500
        j2 = resp2.get_json()
        assert j2.get('error') == 'Qiskit packages missing'

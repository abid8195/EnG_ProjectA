import io, json
from app import app

def test_upload_and_run():
    client = app.test_client()

    # Upload CSV — needs enough rows with BOTH labels for LogisticRegression
    csv_data = (
        b"feature1,feature2,label\n"
        b"1,2,0\n3,4,1\n5,6,0\n7,8,1\n9,1,0\n"
        b"2,3,1\n4,5,0\n6,7,1\n8,9,0\n1,9,1\n"
    )
    data = {'file': (io.BytesIO(csv_data), 'test.csv')}
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


# ---------------------------------------------------------------------------
# Kipu endpoint tests (no real Kipu account required)
# ---------------------------------------------------------------------------

def test_kipu_backends_no_token():
    """GET /kipu/backends without a token must return 400."""
    client = app.test_client()
    resp = client.get('/kipu/backends')
    assert resp.status_code == 400
    j = resp.get_json()
    assert 'error' in j
    assert 'token' in j['error'].lower()


def test_kipu_backends_empty_token():
    """GET /kipu/backends with an empty token must return 400."""
    client = app.test_client()
    resp = client.get('/kipu/backends?token=')
    assert resp.status_code == 400
    j = resp.get_json()
    assert 'error' in j


def test_kipu_run_no_token():
    """POST /kipu/run without token must return 400."""
    client = app.test_client()
    resp = client.post(
        '/kipu/run',
        data=json.dumps({'backend_name': 'aer_simulator', 'shots': 100}),
        content_type='application/json'
    )
    assert resp.status_code == 400
    j = resp.get_json()
    assert 'error' in j
    assert 'token' in j['error'].lower()


def test_kipu_run_no_backend():
    """POST /kipu/run with token but no backend_name must return 400."""
    client = app.test_client()
    resp = client.post(
        '/kipu/run',
        data=json.dumps({'token': 'dummy-token', 'shots': 100}),
        content_type='application/json'
    )
    assert resp.status_code == 400
    j = resp.get_json()
    assert 'error' in j
    assert 'backend' in j['error'].lower()


def test_kipu_run_invalid_shots():
    """POST /kipu/run with shots=0 must return 400."""
    client = app.test_client()
    resp = client.post(
        '/kipu/run',
        data=json.dumps({'token': 'dummy', 'backend_name': 'aer_simulator', 'shots': 0}),
        content_type='application/json'
    )
    assert resp.status_code == 400
    j = resp.get_json()
    assert 'shots' in j['error'].lower()


def test_kipu_run_sdk_missing_or_bad_token():
    """
    POST /kipu/run with a dummy token — either the SDK isn't installed (500)
    or the token is invalid (4xx). Both are acceptable; we just verify the
    response has an 'error' key.
    """
    client = app.test_client()
    resp = client.post(
        '/kipu/run',
        data=json.dumps({
            'token': 'definitely-not-a-real-token',
            'backend_name': 'aer_simulator',
            'shots': 10,
            'circuit_spec': {'num_qubits': 2}
        }),
        content_type='application/json'
    )
    assert resp.status_code in (400, 401, 500)
    j = resp.get_json()
    assert 'error' in j

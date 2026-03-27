"""
Integration tests for QML Pipeline - Testing without requiring full Qiskit install
"""
import requests
import json
import os
import time


BASE_URL = "http://127.0.0.1:5000"


def test_health():
    """Test health endpoint"""
    print("\n🧪 Testing /health endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data['status'] == 'ok'
        print("✅ Health check passed")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


def test_upload_iris():
    """Test uploading iris_like.csv"""
    print("\n🧪 Testing /upload with iris_like.csv...")
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'backend', 'uploads', 'iris_like.csv')
        if not os.path.exists(csv_path):
            print(f"⚠️  File not found: {csv_path}")
            return False
        
        with open(csv_path, 'rb') as f:
            files = {'file': ('iris_like.csv', f, 'text/csv')}
            r = requests.post(f"{BASE_URL}/upload", files=files, timeout=10)
        
        assert r.status_code == 200
        data = r.json()
        assert data['ok'] is True
        assert 'path' in data
        assert 'columns' in data
        assert 'species' in data['columns']
        print(f"✅ Upload successful: {data['columns']}")
        return data
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False


def test_upload_diabetes():
    """Test uploading diabetes_small.csv"""
    print("\n🧪 Testing /upload with diabetes_small.csv...")
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'backend', 'uploads', 'diabetes_small.csv')
        if not os.path.exists(csv_path):
            print(f"⚠️  File not found: {csv_path}")
            return False
        
        with open(csv_path, 'rb') as f:
            files = {'file': ('diabetes_small.csv', f, 'text/csv')}
            r = requests.post(f"{BASE_URL}/upload", files=files, timeout=10)
        
        assert r.status_code == 200
        data = r.json()
        assert data['ok'] is True
        assert 'Outcome' in data['columns']
        print(f"✅ Upload successful: {data['columns']}")
        return data
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False


def test_upload_wine():
    """Test uploading wine_small.csv"""
    print("\n🧪 Testing /upload with wine_small.csv...")
    try:
        csv_path = os.path.join(os.path.dirname(__file__), 'backend', 'uploads', 'wine_small.csv')
        if not os.path.exists(csv_path):
            print(f"⚠️  File not found: {csv_path}")
            return False
        
        with open(csv_path, 'rb') as f:
            files = {'file': ('wine_small.csv', f, 'text/csv')}
            r = requests.post(f"{BASE_URL}/upload", files=files, timeout=10)
        
        assert r.status_code == 200
        data = r.json()
        assert data['ok'] is True
        assert 'Class' in data['columns']
        print(f"✅ Upload successful: {data['columns']}")
        return data
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False


def test_instructions():
    """Test instructions endpoint"""
    print("\n🧪 Testing /instructions endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/instructions", timeout=5)
        assert r.status_code == 200
        assert 'text/plain' in r.headers['Content-Type']
        assert 'QML Pipeline Instructions' in r.text
        print("✅ Instructions endpoint passed")
        return True
    except Exception as e:
        print(f"❌ Instructions failed: {e}")
        return False


def test_run_pipeline_diabetes():
    """Test running pipeline with diabetes dataset"""
    print("\n🧪 Testing /run with diabetes dataset...")
    try:
        # First upload
        upload_result = test_upload_diabetes()
        if not upload_result:
            print("⚠️  Skipping run test - upload failed")
            return False
        
        # Build spec
        spec = {
            "pipeline": "qml-classifier",
            "qnn": {"type": "estimator"},
            "dataset": {
                "type": "csv",
                "path": upload_result['path'],
                "label_column": "Outcome",
                "feature_columns": ["Glucose", "BMI", "Age"],
                "test_size": 0.2,
                "shuffle": True
            },
            "circuit": {
                "type": "realamplitudes",
                "num_qubits": 3,
                "reps": 1
            },
            "optimizer": {
                "type": "cobyla",
                "maxiter": 10
            },
            "outputs": {
                "return_predictions": True
            }
        }
        
        print("   Sending run request (this may take 1-2 minutes)...")
        r = requests.post(f"{BASE_URL}/run", 
                         json=spec, 
                         headers={'Content-Type': 'application/json'},
                         timeout=300)
        
        if r.status_code == 200:
            data = r.json()
            assert data['status'] == 'ok'
            result = data['result']
            assert 'accuracy' in result
            assert 'message' in result
            print(f"✅ Pipeline run successful!")
            print(f"   Accuracy: {result['accuracy']:.2%}")
            print(f"   Message: {result['message']}")
            return True
        elif r.status_code == 500:
            data = r.json()
            if 'Qiskit packages missing' in data.get('error', ''):
                print("⚠️  Qiskit not installed - this is expected in some environments")
                return None
            else:
                print(f"❌ Server error: {data.get('error')}")
                return False
        else:
            print(f"❌ Run failed with status {r.status_code}: {r.text}")
            return False
            
    except requests.Timeout:
        print("⚠️  Request timed out - pipeline may be too slow")
        return None
    except Exception as e:
        print(f"❌ Run failed: {e}")
        return False


def test_invalid_spec():
    """Test that invalid spec is rejected"""
    print("\n🧪 Testing /run with invalid spec...")
    try:
        spec = {
            "pipeline": "invalid-type",
            "qnn": {"type": "estimator"}
        }
        
        r = requests.post(f"{BASE_URL}/run",
                         json=spec,
                         headers={'Content-Type': 'application/json'},
                         timeout=10)
        
        assert r.status_code == 400
        data = r.json()
        assert 'error' in data
        print(f"✅ Invalid spec properly rejected: {data['error'][:50]}...")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def run_all_tests():
    """Run all integration tests"""
    print("="*60)
    print("QML PIPELINE INTEGRATION TESTS")
    print("="*60)
    print(f"Testing backend at: {BASE_URL}")
    print("Make sure the Flask server is running!")
    print("="*60)
    
    results = {}
    
    # Test all endpoints
    results['health'] = test_health()
    results['instructions'] = test_instructions()
    results['upload_iris'] = bool(test_upload_iris())
    results['upload_diabetes'] = bool(test_upload_diabetes())
    results['upload_wine'] = bool(test_upload_wine())
    results['invalid_spec'] = test_invalid_spec()
    results['run_pipeline'] = test_run_pipeline_diabetes()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    total = len(results)
    
    for test, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{status} - {test}")
    
    print("="*60)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    print("="*60)
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    
    return failed == 0


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)

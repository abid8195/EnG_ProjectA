import os
import json
import tempfile
import unittest
import numpy as np

from qml_pipeline.pipeline  import Pipeline, preprocess_data, postprocess_results
from qml_pipeline.model_io  import load_model, save_model, model_exists


BASE_CONFIG = {
    'n_qubits':      2,
    'layers':        1,
    'ansatz':        'ry',
    'entanglement':  'linear',
    'encoding_type': 'angle',
}


class TestPipelineInit(unittest.TestCase):
    def _make(self, **overrides):
        cfg = {**BASE_CONFIG, **overrides}
        return Pipeline(cfg)

    def test_default_config(self):
        p = self._make()
        self.assertIsNotNone(p)
        self.assertEqual(p.n_qubits, 2)
        self.assertEqual(p.layers,   1)

    def test_ansatz_variants(self):
        for ansatz in ('ry', 'rz', 'rx', 'rxyz'):
            with self.subTest(ansatz=ansatz):
                p = self._make(ansatz=ansatz)
                self.assertEqual(p.ansatz, ansatz)

    def test_entanglement_variants(self):
        for ent in ('linear', 'circular', 'full'):
            with self.subTest(entanglement=ent):
                p = self._make(entanglement=ent)
                self.assertEqual(p.entanglement, ent)

    def test_encoding_variants(self):
        for enc in ('angle', 'basis', 'zz'):
            with self.subTest(encoding=enc):
                p = self._make(encoding_type=enc)
                self.assertEqual(p.encoding_type, enc)

    def test_invalid_ansatz_raises(self):
        with self.assertRaises(ValueError):
            self._make(ansatz='bad_ansatz')

    def test_invalid_entanglement_raises(self):
        with self.assertRaises(ValueError):
            self._make(entanglement='star')

    def test_invalid_encoding_raises(self):
        with self.assertRaises(ValueError):
            self._make(encoding_type='fourier')

    def test_rxyz_param_count(self):
        p = self._make(ansatz='rxyz', n_qubits=2, layers=1)
        self.assertEqual(p.var_circuit.param_count(), 2 * 1 * 3)

    def test_ry_param_count(self):
        p = self._make(ansatz='ry', n_qubits=3, layers=2)
        self.assertEqual(p.var_circuit.param_count(), 3 * 2 * 1)


class TestPipelineParams(unittest.TestCase):
    def setUp(self):
        self.pipeline = Pipeline(BASE_CONFIG)

    def test_params_shape(self):
        expected = self.pipeline.var_circuit.param_count()
        self.assertEqual(self.pipeline.params.shape, (expected,))

    def test_params_setter_valid(self):
        n = self.pipeline.var_circuit.param_count()
        new_params = np.zeros(n)
        self.pipeline.params = new_params
        np.testing.assert_array_equal(self.pipeline.params, new_params)

    def test_params_setter_wrong_size(self):
        with self.assertRaises(ValueError):
            self.pipeline.params = np.zeros(999)


class TestPreprocessData(unittest.TestCase):

    def test_output_range(self):
        data = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        out  = preprocess_data(data)
        self.assertAlmostEqual(out.min(), 0.0, places=6)
        self.assertAlmostEqual(out.max(), 1.0, places=6)

    def test_nan_filled(self):
        data = np.array([[1.0, np.nan], [3.0, 4.0]])
        out  = preprocess_data(data)
        self.assertFalse(np.isnan(out).any())

    def test_single_row(self):
        data = np.array([[1.0, 2.0, 3.0]])
        out  = preprocess_data(data)
        self.assertEqual(out.shape, (1, 3))


class TestPostprocessResults(unittest.TestCase):

    def test_argmax_per_row(self):
        results = np.array([[0.1, 0.9], [0.8, 0.2]])
        preds   = postprocess_results(results)
        np.testing.assert_array_equal(preds, [1, 0])


class TestModelIO(unittest.TestCase):

    def test_save_and_load(self):
        model = {'key': 'value', 'number': 42}
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
            tmp_path = f.name
        try:
            save_model(tmp_path, model)
            loaded = load_model(tmp_path)
            self.assertEqual(model, loaded)
        finally:
            os.remove(tmp_path)

    def test_model_exists_true(self):
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            tmp_path = f.name
        try:
            self.assertTrue(model_exists(tmp_path))
        finally:
            os.remove(tmp_path)

    def test_model_exists_false(self):
        self.assertFalse(model_exists('/nonexistent/path/model.json'))


if __name__ == '__main__':
    unittest.main()

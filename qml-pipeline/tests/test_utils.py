import unittest
import numpy as np

from qml_pipeline.utils import (
    compute_accuracy,
    confusion_matrix_simple,
    flatten_counts,
    validate_pipeline_config,
)


class TestComputeAccuracy(unittest.TestCase):

    def test_perfect_score(self):
        preds  = np.array([0, 1, 2, 1])
        labels = np.array([0, 1, 2, 1])
        self.assertAlmostEqual(compute_accuracy(preds, labels), 1.0)

    def test_zero_score(self):
        preds  = np.array([1, 2, 0])
        labels = np.array([0, 1, 2])
        self.assertAlmostEqual(compute_accuracy(preds, labels), 0.0)

    def test_partial_score(self):
        preds  = np.array([0, 1, 0, 1])
        labels = np.array([0, 1, 1, 0])
        self.assertAlmostEqual(compute_accuracy(preds, labels), 0.5)

    def test_empty(self):
        self.assertEqual(compute_accuracy(np.array([]), np.array([])), 0.0)

    def test_returns_float(self):
        result = compute_accuracy(np.array([1]), np.array([1]))
        self.assertIsInstance(result, float)


class TestConfusionMatrix(unittest.TestCase):

    def test_shape(self):
        preds  = np.array([0, 1, 2, 1])
        labels = np.array([0, 1, 2, 0])
        cm     = confusion_matrix_simple(preds, labels, n_classes=3)
        self.assertEqual(cm.shape, (3, 3))

    def test_perfect_diagonal(self):
        preds  = np.array([0, 1, 2])
        labels = np.array([0, 1, 2])
        cm     = confusion_matrix_simple(preds, labels, n_classes=3)
        np.testing.assert_array_equal(cm, np.eye(3, dtype=int))

    def test_all_wrong(self):
        preds  = np.array([1, 0])
        labels = np.array([0, 1])
        cm     = confusion_matrix_simple(preds, labels, n_classes=2)
        self.assertEqual(cm[0, 0], 0)
        self.assertEqual(cm[1, 1], 0)
        self.assertEqual(cm[0, 1], 1)
        self.assertEqual(cm[1, 0], 1)

    def test_row_sum_equals_class_count(self):
        labels = np.array([0, 0, 1, 1, 2])
        preds  = np.array([0, 1, 1, 0, 2])
        cm     = confusion_matrix_simple(preds, labels, n_classes=3)
        np.testing.assert_array_equal(cm.sum(axis=1), [2, 2, 1])


class TestFlattenCounts(unittest.TestCase):

    def test_sums_to_one(self):
        counts = {'00': 256, '01': 256, '10': 256, '11': 256}
        probs  = flatten_counts(counts, n_qubits=2)
        self.assertAlmostEqual(probs.sum(), 1.0, places=5)

    def test_length(self):
        counts = {'0': 1024}
        probs  = flatten_counts(counts, n_qubits=3)
        self.assertEqual(len(probs), 8)

    def test_uniform(self):
        n       = 2
        n_shots = 1024
        counts  = {f'{i:0{n}b}': n_shots // (2**n) for i in range(2**n)}
        probs   = flatten_counts(counts, n_qubits=n)
        for p in probs:
            self.assertAlmostEqual(p, 0.25, places=5)


class TestValidatePipelineConfig(unittest.TestCase):

    def _valid(self, **overrides):
        cfg = {
            'n_qubits': 4, 'layers': 2,
            'ansatz': 'ry', 'entanglement': 'linear', 'encoding_type': 'angle',
            **overrides
        }
        validate_pipeline_config(cfg)

    def test_valid_defaults(self):
        self._valid()

    def test_valid_rx(self):
        self._valid(ansatz='rx')

    def test_valid_rxyz(self):
        self._valid(ansatz='rxyz')

    def test_valid_circular(self):
        self._valid(entanglement='circular')

    def test_valid_full(self):
        self._valid(entanglement='full')

    def test_valid_zz_encoding(self):
        self._valid(encoding_type='zz')

    def test_invalid_ansatz(self):
        with self.assertRaises(ValueError):
            self._valid(ansatz='unknown')

    def test_invalid_entanglement(self):
        with self.assertRaises(ValueError):
            self._valid(entanglement='star')

    def test_invalid_encoding(self):
        with self.assertRaises(ValueError):
            self._valid(encoding_type='fourier')

    def test_bad_n_qubits(self):
        with self.assertRaises(ValueError):
            self._valid(n_qubits=-1)

    def test_bad_layers(self):
        with self.assertRaises(ValueError):
            self._valid(layers=0)


if __name__ == '__main__':
    unittest.main()

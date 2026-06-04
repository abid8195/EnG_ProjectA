"""
Unit tests for backend/dataset_catalog.py

Verifies that every entry in DATASET_CONFIGS is structurally correct,
references existing files, and contains coherent column metadata.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.dataset_catalog import DATASET_CONFIGS  # noqa: E402

REQUIRED_KEYS = {"path", "label_column", "feature_columns", "description", "domain"}
EXPECTED_DATASETS = {"finance", "supply_chain", "hr"}


class TestDatasetCatalogPresence:
    def test_catalog_is_dict(self):
        assert isinstance(DATASET_CONFIGS, dict)

    def test_catalog_not_empty(self):
        assert len(DATASET_CONFIGS) > 0

    def test_finance_present(self):
        assert "finance" in DATASET_CONFIGS

    def test_supply_chain_present(self):
        assert "supply_chain" in DATASET_CONFIGS

    def test_hr_present(self):
        assert "hr" in DATASET_CONFIGS

    def test_all_expected_datasets_present(self):
        missing = EXPECTED_DATASETS - set(DATASET_CONFIGS.keys())
        assert not missing, f"Missing datasets: {missing}"


class TestDatasetCatalogStructure:
    @pytest.fixture(params=list(DATASET_CONFIGS.keys()))
    def dataset_name(self, request):
        return request.param

    def test_required_keys_present(self, dataset_name):
        entry = DATASET_CONFIGS[dataset_name]
        missing = REQUIRED_KEYS - set(entry.keys())
        assert not missing, f"Dataset '{dataset_name}' missing keys: {missing}"

    def test_label_column_is_string(self, dataset_name):
        label = DATASET_CONFIGS[dataset_name]["label_column"]
        assert isinstance(label, str) and label.strip() != ""

    def test_feature_columns_is_list(self, dataset_name):
        cols = DATASET_CONFIGS[dataset_name]["feature_columns"]
        assert isinstance(cols, list)

    def test_feature_columns_not_empty(self, dataset_name):
        cols = DATASET_CONFIGS[dataset_name]["feature_columns"]
        assert len(cols) >= 1

    def test_each_feature_column_is_string(self, dataset_name):
        for col in DATASET_CONFIGS[dataset_name]["feature_columns"]:
            assert isinstance(col, str) and col.strip() != ""

    def test_description_is_non_empty_string(self, dataset_name):
        desc = DATASET_CONFIGS[dataset_name]["description"]
        assert isinstance(desc, str) and desc.strip() != ""

    def test_domain_is_non_empty_string(self, dataset_name):
        domain = DATASET_CONFIGS[dataset_name]["domain"]
        assert isinstance(domain, str) and domain.strip() != ""

    def test_path_is_absolute(self, dataset_name):
        path = DATASET_CONFIGS[dataset_name]["path"]
        assert Path(path).is_absolute(), f"Dataset '{dataset_name}' path is not absolute: {path}"

    def test_csv_file_exists(self, dataset_name):
        path = DATASET_CONFIGS[dataset_name]["path"]
        assert Path(path).exists(), f"Dataset '{dataset_name}' file missing: {path}"

    def test_csv_file_is_readable(self, dataset_name):
        import pandas as pd
        path = DATASET_CONFIGS[dataset_name]["path"]
        df = pd.read_csv(path)
        assert len(df) > 0

    def test_label_column_in_csv(self, dataset_name):
        import pandas as pd
        cfg = DATASET_CONFIGS[dataset_name]
        df = pd.read_csv(cfg["path"])
        assert cfg["label_column"] in df.columns, (
            f"Label column '{cfg['label_column']}' not found in {dataset_name} CSV. "
            f"Available: {df.columns.tolist()}"
        )

    def test_feature_columns_in_csv(self, dataset_name):
        import pandas as pd
        cfg = DATASET_CONFIGS[dataset_name]
        df = pd.read_csv(cfg["path"])
        missing = [c for c in cfg["feature_columns"] if c not in df.columns]
        assert not missing, (
            f"Feature columns missing from {dataset_name} CSV: {missing}. "
            f"Available: {df.columns.tolist()}"
        )

    def test_label_not_in_feature_columns(self, dataset_name):
        cfg = DATASET_CONFIGS[dataset_name]
        assert cfg["label_column"] not in cfg["feature_columns"], (
            f"Dataset '{dataset_name}': label_column '{cfg['label_column']}' "
            "appears in feature_columns — this would leak the target."
        )


class TestDatasetCatalogFinanceSpecifics:
    def test_finance_label_is_risk_flag(self):
        assert DATASET_CONFIGS["finance"]["label_column"] == "risk_flag"

    def test_finance_has_5_features(self):
        assert len(DATASET_CONFIGS["finance"]["feature_columns"]) == 5

    def test_finance_features_include_market_volatility(self):
        assert "market_volatility" in DATASET_CONFIGS["finance"]["feature_columns"]

    def test_finance_features_include_credit_score(self):
        assert "credit_score" in DATASET_CONFIGS["finance"]["feature_columns"]

    def test_finance_domain_is_finance(self):
        assert "finance" in DATASET_CONFIGS["finance"]["domain"].lower()

    def test_finance_recommended_settings_present(self):
        assert "recommended" in DATASET_CONFIGS["finance"]

    def test_finance_recommended_has_encoder(self):
        rec = DATASET_CONFIGS["finance"]["recommended"]
        assert "encoder" in rec

    def test_finance_recommended_encoder_is_angle(self):
        assert DATASET_CONFIGS["finance"]["recommended"]["encoder"] == "angle"


class TestDatasetCatalogSupplyChainSpecifics:
    def test_supply_chain_label_is_disruption_flag(self):
        assert DATASET_CONFIGS["supply_chain"]["label_column"] == "disruption_flag"

    def test_supply_chain_has_5_features(self):
        assert len(DATASET_CONFIGS["supply_chain"]["feature_columns"]) == 5

    def test_supply_chain_features_include_supplier_delay(self):
        assert "supplier_delay_days" in DATASET_CONFIGS["supply_chain"]["feature_columns"]

    def test_supply_chain_recommended_optimizer_is_spsa(self):
        assert DATASET_CONFIGS["supply_chain"]["recommended"]["optimizer"] == "spsa"


class TestDatasetCatalogHRSpecifics:
    def test_hr_label_is_attrition_flag(self):
        assert DATASET_CONFIGS["hr"]["label_column"] == "attrition_flag"

    def test_hr_has_5_features(self):
        assert len(DATASET_CONFIGS["hr"]["feature_columns"]) == 5

    def test_hr_features_include_engagement_score(self):
        assert "engagement_score" in DATASET_CONFIGS["hr"]["feature_columns"]

    def test_hr_domain_mentions_human(self):
        assert "human" in DATASET_CONFIGS["hr"]["domain"].lower()

from __future__ import annotations

from pathlib import Path

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


DATASET_CONFIGS = {
    "finance": {
        "path": DATASETS_DIR / "finance_portfolio_risk.csv",
        "label_column": "risk_flag",
        "feature_columns": [
            "market_volatility",
            "debt_ratio",
            "liquidity_ratio",
            "revenue_growth",
            "credit_score",
        ],
        "description": "Finance portfolio risk classification for screening high-risk applications.",
        "domain": "Finance",
    },
    "supply_chain": {
        "path": DATASETS_DIR / "supply_chain_disruption.csv",
        "label_column": "disruption_flag",
        "feature_columns": [
            "supplier_delay_days",
            "inventory_turnover",
            "defect_rate",
            "shipping_cost_index",
            "demand_variance",
        ],
        "description": "Supply chain disruption classification for delivery and sourcing planning.",
        "domain": "Supply Chain",
    },
    "hr": {
        "path": DATASETS_DIR / "hr_attrition.csv",
        "label_column": "attrition_flag",
        "feature_columns": [
            "overtime_hours",
            "engagement_score",
            "years_at_company",
            "training_hours",
            "performance_score",
        ],
        "description": "Human resources attrition-risk classification for retention planning.",
        "domain": "Human Resources",
    },
}


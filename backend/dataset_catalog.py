"""Domain dataset catalogue — maps short names to CSV paths and column configs."""
from __future__ import annotations
from pathlib import Path

# Datasets live at <project_root>/datasets/
DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"

DATASET_CONFIGS: dict = {
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
        "description": (
            "Finance portfolio risk classification. "
            "Predict high-risk loan/investment applications for analyst triage."
        ),
        "domain": "Finance",
        "recommended": {
            "encoder": "angle",
            "circuit": "realamplitudes",
            "optimizer": "cobyla",
            "shots": 128,
            "maxiter": 20,
            "reps": 2,
        },
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
        "description": (
            "Supply chain disruption classification. "
            "Identify at-risk suppliers and shipments for proactive intervention."
        ),
        "domain": "Supply Chain",
        "recommended": {
            "encoder": "basis",
            "circuit": "efficientsu2",
            "optimizer": "spsa",
            "shots": 128,
            "maxiter": 20,
            "reps": 2,
        },
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
        "description": (
            "HR attrition-risk classification. "
            "Predict employee attrition for targeted retention planning."
        ),
        "domain": "Human Resources",
        "recommended": {
            "encoder": "angle",
            "circuit": "realamplitudes",
            "optimizer": "cobyla",
            "shots": 128,
            "maxiter": 20,
            "reps": 2,
        },
    },
}

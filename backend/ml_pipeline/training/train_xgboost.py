"""
XGBoost Resilience Scorer Training Script.
Predicts district-level composite resilience score (0–1).
"""
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
import shap
import joblib
import json
import os
from datetime import datetime


# ─── Resilience Score Formula ─────────────────────────────────────────────────

def compute_resilience_score(
    failed_ratio: float,
    hours_to_50pct: float,
    final_operational_pct: float,
    max_expected_hours: float = 72.0,
    w1: float = 0.25,
    w2: float = 0.35,
    w3: float = 0.40,
) -> float:
    """
    Composite resilience score formula.
    
    R = w1 * Absorption + w2 * Adaptation + w3 * Restoration
    
    Absorption  = 1 - failed_ratio          (ability to absorb initial shock)
    Adaptation  = 1 - hours_to_50pct / max  (speed of adaptation)
    Restoration = final_operational_pct/100 (completeness of restoration)
    
    All components in [0, 1], weighted sum in [0, 1].
    """
    absorption = max(0.0, 1.0 - failed_ratio)
    adaptation = max(0.0, 1.0 - hours_to_50pct / max_expected_hours)
    restoration = max(0.0, min(1.0, final_operational_pct / 100.0))
    return w1 * absorption + w2 * adaptation + w3 * restoration


# ─── Feature Engineering ──────────────────────────────────────────────────────

FEATURE_COLUMNS = [
    # District static
    "population_log",
    "area_sqkm",
    "urban_density_log",
    "income_level_encoded",
    "critical_infra_count",
    "backup_node_ratio",
    "historical_avg_recovery_hours",
    "historical_resilience_mean",
    # Incident
    "disaster_type_encoded",
    "severity_score",
    "affected_node_ratio",
    "n_critical_nodes_affected",
    # Recovery state
    "power_recovery_pct",
    "transport_recovery_pct",
    "telecom_recovery_pct",
    "emergency_recovery_pct",
    "mobility_recovery_pct",
    "service_recovery_pct",
    "hours_elapsed",
    "repair_crews_deployed",
    "resource_budget_used_pct",
    # Graph features
    "betweenness_centrality",
    "clustering_coefficient",
    "n_isolated_nodes",
    "in_degree_mean",
]


def generate_synthetic_resilience_data(n_samples: int = 5000) -> pd.DataFrame:
    """Generate synthetic resilience training data."""
    np.random.seed(42)
    records = []

    income_encoder = {"low": 0, "medium": 1, "high": 2}
    disaster_encoder = {"blackout": 0, "flood": 1, "infrastructure_failure": 2, "compound": 3}

    for _ in range(n_samples):
        income = np.random.choice(["low", "medium", "high"], p=[0.3, 0.5, 0.2])
        disaster = np.random.choice(list(disaster_encoder.keys()))
        severity = np.random.uniform(1, 10)
        population = np.random.lognormal(11.5, 0.4)
        area = np.random.uniform(10, 40)

        # Recovery percentages (correlated with income and severity)
        base_recovery = max(0, 1 - severity / 15 + income_encoder[income] * 0.1)
        power_rec = np.clip(base_recovery + np.random.normal(0, 0.15), 0, 1) * 100
        transport_rec = np.clip(base_recovery + np.random.normal(0.1, 0.1), 0, 1) * 100
        telecom_rec = np.clip(base_recovery - 0.05 + np.random.normal(0, 0.15), 0, 1) * 100
        emergency_rec = np.clip(base_recovery + 0.15 + np.random.normal(0, 0.1), 0, 1) * 100
        mobility_rec = np.clip(base_recovery - 0.1 + np.random.normal(0, 0.15), 0, 1) * 100
        service_rec = np.clip(base_recovery + np.random.normal(0, 0.12), 0, 1) * 100

        failed_ratio = np.clip(severity / 10 * np.random.uniform(0.3, 0.8), 0, 1)
        hours_to_50pct = np.clip(severity * 3 * np.random.lognormal(0, 0.3), 0.5, 72)
        final_operational = np.mean([power_rec, transport_rec, telecom_rec, emergency_rec, mobility_rec, service_rec])

        # Compute ground truth resilience score
        resilience = compute_resilience_score(
            failed_ratio=failed_ratio,
            hours_to_50pct=hours_to_50pct,
            final_operational_pct=final_operational,
        )

        records.append({
            "population_log": np.log1p(population),
            "area_sqkm": area,
            "urban_density_log": np.log1p(population / area),
            "income_level_encoded": income_encoder[income],
            "critical_infra_count": np.random.randint(5, 45),
            "backup_node_ratio": np.random.uniform(0.1, 0.4),
            "historical_avg_recovery_hours": np.random.uniform(8, 48),
            "historical_resilience_mean": np.random.uniform(0.4, 0.9),
            "disaster_type_encoded": disaster_encoder[disaster],
            "severity_score": severity,
            "affected_node_ratio": failed_ratio,
            "n_critical_nodes_affected": np.random.randint(0, 15),
            "power_recovery_pct": power_rec,
            "transport_recovery_pct": transport_rec,
            "telecom_recovery_pct": telecom_rec,
            "emergency_recovery_pct": emergency_rec,
            "mobility_recovery_pct": mobility_rec,
            "service_recovery_pct": service_rec,
            "hours_elapsed": np.random.uniform(6, 72),
            "repair_crews_deployed": np.random.randint(1, 20),
            "resource_budget_used_pct": np.random.uniform(20, 100),
            "betweenness_centrality": np.random.uniform(0, 1),
            "clustering_coefficient": np.random.uniform(0, 1),
            "n_isolated_nodes": np.random.randint(0, 20),
            "in_degree_mean": np.random.uniform(1, 5),
            "resilience_score": resilience,
        })

    return pd.DataFrame(records)


# ─── Training ─────────────────────────────────────────────────────────────────

def train_resilience_model(
    data_path: str = None,
    output_dir: str = "ml_pipeline/artifacts",
):
    """Train the XGBoost resilience scorer."""
    if data_path and os.path.exists(data_path):
        df = pd.read_csv(data_path)
    else:
        print("Generating synthetic resilience training data...")
        df = generate_synthetic_resilience_data(n_samples=5000)

    print(f"Training on {len(df)} samples")

    X = df[FEATURE_COLUMNS].values
    y = df["resilience_score"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBRegressor(
        n_estimators=500,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="reg:squarederror",
        eval_metric="mae",
        early_stopping_rounds=20,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    pearson_r = np.corrcoef(y_test, y_pred)[0, 1]

    print(f"\n=== Test Set Evaluation ===")
    print(f"MAE:       {mae:.4f}")
    print(f"R²:        {r2:.4f}")
    print(f"Pearson r: {pearson_r:.4f}")

    # SHAP feature importance
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test[:200])
    feature_importance = dict(zip(FEATURE_COLUMNS, np.abs(shap_values).mean(axis=0).tolist()))
    top_features = sorted(feature_importance.items(), key=lambda x: -x[1])[:10]
    print("\nTop 10 features by SHAP importance:")
    for feat, imp in top_features:
        print(f"  {feat}: {imp:.4f}")

    # Save
    os.makedirs(output_dir, exist_ok=True)
    joblib.dump(model, os.path.join(output_dir, "xgb_resilience.pkl"))

    config = {
        "model_type": "XGBRegressor",
        "version": "xgb-v1.0",
        "features": FEATURE_COLUMNS,
        "trained_at": datetime.now().isoformat(),
        "test_mae": float(mae),
        "test_r2": float(r2),
        "test_pearson_r": float(pearson_r),
        "top_features": [{"feature": f, "shap_importance": v} for f, v in top_features],
    }
    with open(os.path.join(output_dir, "xgb_config.json"), "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ XGBoost model saved to {output_dir}/xgb_resilience.pkl")
    return model, config


if __name__ == "__main__":
    train_resilience_model(output_dir="ml_pipeline/artifacts")

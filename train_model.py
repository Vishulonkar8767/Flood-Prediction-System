"""
train_model.py
---------------
Trains three ML models (Random Forest, Decision Tree, Logistic Regression)
on flood_dataset.csv, compares them on Accuracy / Precision / Recall / F1 /
Confusion Matrix, picks the best model, and saves:

    flood_model.pkl   -> the best trained model
    scaler.pkl        -> the StandardScaler used for preprocessing
    model_info.json   -> metrics for all models + feature importance
                          (consumed by the Flask app / Analytics page)

Run:
    python train_model.py
"""

import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                              precision_score, recall_score, roc_auc_score,
                              roc_curve)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

DATASET_PATH = "flood_dataset.csv"
FEATURE_COLUMNS = [
    "Rainfall", "Temperature", "Humidity", "River_Water_Level",
    "River_Flow", "Soil_Moisture", "Wind_Speed", "Atmospheric_Pressure",
    "Previous_Rainfall", "Drainage_Capacity", "Elevation"
]
TARGET_COLUMN = "Flood"


def main():
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"{DATASET_PATH} not found. Run 'python generate_dataset.py' first."
        )

    df = pd.read_csv(DATASET_PATH)

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=10, random_state=42
        ),
        "Decision Tree": DecisionTreeClassifier(max_depth=8, random_state=42),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
    }

    results = {}
    trained_models = {}

    for name, model in models.items():
        model.fit(X_train_scaled, y_train)
        preds = model.predict(X_test_scaled)
        proba = model.predict_proba(X_test_scaled)[:, list(model.classes_).index(1)]

        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        f1 = f1_score(y_test, preds, zero_division=0)
        cm = confusion_matrix(y_test, preds).tolist()
        auc = roc_auc_score(y_test, proba)
        fpr, tpr, _ = roc_curve(y_test, proba)

        # Downsample ROC points for compact JSON (thresholds can number in
        # the hundreds; ~40 points is plenty for a smooth chart)
        step = max(1, len(fpr) // 40)
        roc_points = [
            {"fpr": round(float(f), 4), "tpr": round(float(t), 4)}
            for f, t in list(zip(fpr, tpr))[::step]
        ]
        if roc_points[-1]["fpr"] != 1.0:
            roc_points.append({"fpr": 1.0, "tpr": 1.0})

        results[name] = {
            "accuracy": round(acc * 100, 2),
            "precision": round(prec * 100, 2),
            "recall": round(rec * 100, 2),
            "f1_score": round(f1 * 100, 2),
            "auc": round(float(auc), 4),
            "confusion_matrix": cm,
            "roc_curve": roc_points,
        }
        trained_models[name] = model

        print(f"\n=== {name} ===")
        print(f"Accuracy : {acc:.4f}")
        print(f"Precision: {prec:.4f}")
        print(f"Recall   : {rec:.4f}")
        print(f"F1-score : {f1:.4f}")
        print(f"AUC      : {auc:.4f}")
        print(f"Confusion Matrix:\n{np.array(cm)}")

    # ---- Pick the best model by F1-score (balances precision & recall) ----
    best_name = max(results, key=lambda n: results[n]["f1_score"])
    best_model = trained_models[best_name]

    print(f"\n>>> Best model selected: {best_name} <<<")

    joblib.dump(best_model, "flood_model.pkl")
    joblib.dump(scaler, "scaler.pkl")

    # ---- Feature importance (Random Forest is used for explainability
    #      regardless of which model wins, since RF naturally exposes it) ----
    rf_for_importance = trained_models["Random Forest"]
    importances = rf_for_importance.feature_importances_
    feature_importance = sorted(
        [
            {"feature": f, "importance": round(float(imp) * 100, 2)}
            for f, imp in zip(FEATURE_COLUMNS, importances)
        ],
        key=lambda d: d["importance"],
        reverse=True,
    )

    model_info = {
        "best_model": best_name,
        "models": results,
        "feature_importance": feature_importance,
        "feature_columns": FEATURE_COLUMNS,
        "total_records": int(len(df)),
        "flood_cases": int(df[TARGET_COLUMN].sum()),
        "no_flood_cases": int((df[TARGET_COLUMN] == 0).sum()),
        "num_parameters": len(FEATURE_COLUMNS),
    }

    with open("model_info.json", "w") as f:
        json.dump(model_info, f, indent=2)

    print("\nSaved flood_model.pkl, scaler.pkl and model_info.json")


if __name__ == "__main__":
    main()
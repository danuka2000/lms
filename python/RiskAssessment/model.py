"""Train and apply the academic risk model to manually entered module data."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
import lightgbm as lgb


BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = Path(os.getenv("RISK_TRAINING_DATA", BASE_DIR / "data" / "student_academic_risk.csv"))
INPUT_PATH = Path(os.getenv("RISK_INPUT_DATA", BASE_DIR / "data" / "manual_risk_inputs.csv"))
MODEL_DIR = Path(__file__).resolve().parent / "ModelOutput"
MODEL_PATH = MODEL_DIR / "risk_model.joblib"

# Core performance features available in student_academic_risk.csv.
FEATURES = [
    "previous_gpa",
    "attendance",
    "assignment_score",
    "quiz_score",
    "study_hours",
    "engagement_score",
    "late_assignments",
    "completed_assignments",
    "learning_progress",
]
RISK_LEVELS = {"low": "Low", "medium": "Medium", "high": "High"}


def _add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features that improve class separation."""
    df = df.copy()
    df["score_avg"] = (df["assignment_score"] + df["quiz_score"]) / 2
    df["gpa_x_attendance"] = df["previous_gpa"] * df["attendance"] / 100
    df["progress_gap"] = df["learning_progress"] - df["score_avg"]
    df["late_ratio"] = df["late_assignments"] / df["completed_assignments"].clip(lower=1)
    df["performance_index"] = df["score_avg"] * df["attendance"] / 100 * df["learning_progress"] / 100
    return df


# All features used by the model (base + engineered)
MODEL_FEATURES = FEATURES + [
    "score_avg",
    "gpa_x_attendance",
    "progress_gap",
    "late_ratio",
    "performance_index",
]


def _make_pipeline(class_weight: dict | None = None) -> Pipeline:
    from collections import Counter
    estimator = lgb.LGBMClassifier(
        n_estimators=600,
        learning_rate=0.03,
        max_depth=10,
        num_leaves=127,
        min_child_samples=5,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight=class_weight,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("classifier", estimator),
        ]
    )


def train_model() -> tuple[Pipeline, dict[str, float | int]]:
    """Train from the labeled CSV and save the estimator in ModelOutput."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found at {DATASET_PATH}. Add student_academic_risk.csv to python/data/ "
            "or set RISK_TRAINING_DATA in python/.env."
        )

    training = pd.read_csv(DATASET_PATH)
    missing = [column for column in FEATURES + ["academic_risk_level"] if column not in training.columns]
    if missing:
        raise ValueError(f"Training CSV is missing required columns: {', '.join(missing)}")

    training["risk_level"] = (
        training["academic_risk_level"].astype(str).str.strip().str.lower().map(RISK_LEVELS)
    )
    training = training.dropna(subset=["risk_level"])
    if training["risk_level"].nunique() != 3:
        raise ValueError("Training CSV must contain Low, Medium, and High academic_risk_level labels.")

    # Add engineered features
    training = _add_engineered_features(training)

    # Compute balanced class weights
    from collections import Counter
    counts = Counter(training["risk_level"])
    total = len(training["risk_level"])
    class_weight = {cls: total / (3 * cnt) for cls, cnt in counts.items()}

    X = training[MODEL_FEATURES]
    y = training["risk_level"]

    model = _make_pipeline(class_weight=class_weight)
    model.fit(X, y)

    # Compute training accuracy for informational logging
    from sklearn.metrics import accuracy_score
    train_acc = accuracy_score(y, model.predict(X))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump(model, MODEL_PATH)

    return model, {
        "training_rows": len(training),
        "classes": int(training["risk_level"].nunique()),
        "accuracy": train_acc,
    }


def assess_manual_records(user_id: str) -> list[dict]:
    model, _ = train_model()
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Manual input CSV not found at {INPUT_PATH}. Create it using the template in python/data/."
        )
    records = pd.read_csv(INPUT_PATH)
    required = ["user_id", "student_id", "student_name", "module_id", "module_name"] + FEATURES
    missing = [column for column in required if column not in records.columns]
    if missing:
        raise ValueError(f"Manual input CSV is missing required columns: {', '.join(missing)}")
    if records.empty:
        return []

    # Manual rows represent a student's enrolled modules. Never return rows
    # belonging to another signed-in account.
    records["user_id"] = records["user_id"].astype("string").str.strip()
    records = records[records["user_id"] == str(user_id)].copy()
    if records.empty:
        return []

    # Add engineered features for prediction
    records = _add_engineered_features(records)

    records["risk_level"] = model.predict(records[MODEL_FEATURES])
    records["confidence"] = model.predict_proba(records[MODEL_FEATURES]).max(axis=1)
    risks = records[records["risk_level"].isin(["High", "Medium"])]
    return [
        {
            "user_id": str(row["user_id"]),
            "student_id": str(row["student_id"]),
            "student_name": str(row["student_name"]),
            "module_id": str(row["module_id"]),
            "module_name": str(row["module_name"]),
            "risk_level": str(row["risk_level"]),
            "confidence": round(float(row["confidence"]), 3),
            "previous_gpa": _number(row["previous_gpa"]),
            "attendance": _number(row["attendance"]),
            "assignment_score": _number(row["assignment_score"]),
            "quiz_score": _number(row["quiz_score"]),
            "study_hours": _number(row["study_hours"]),
            "engagement_score": _number(row["engagement_score"]),
            "late_assignments": _number(row["late_assignments"]),
            "completed_assignments": _number(row["completed_assignments"]),
            "learning_progress": _number(row["learning_progress"]),
        }
        for _, row in risks.iterrows()
    ]


def _number(value):
    return None if pd.isna(value) else float(value)

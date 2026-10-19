"""Train and apply the academic risk model to manually entered module data."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = Path(os.getenv("RISK_TRAINING_DATA", BASE_DIR / "data" / "student_academic_risk.csv"))
INPUT_PATH = Path(os.getenv("RISK_INPUT_DATA", BASE_DIR / "data" / "manual_risk_inputs.csv"))
MODEL_DIR = Path(__file__).resolve().parent / "ModelOutput"
MODEL_PATH = MODEL_DIR / "risk_model.joblib"

# These are the performance features available in student_academic_risk.csv.
# Enter a separate set of values for every student/module in the manual CSV.
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


def _make_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=12,
                    min_samples_leaf=2,
                    class_weight="balanced_subsample",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
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

    model = _make_pipeline()
    model.fit(training[FEATURES], training["risk_level"])
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    import joblib

    joblib.dump(model, MODEL_PATH)
    return model, {
        "training_rows": len(training),
        "classes": int(training["risk_level"].nunique()),
    }


def assess_manual_records() -> list[dict]:
    model, _ = train_model()
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Manual input CSV not found at {INPUT_PATH}. Create it using the template in python/data/."
        )
    records = pd.read_csv(INPUT_PATH)
    required = ["student_id", "student_name", "module_id", "module_name"] + FEATURES
    missing = [column for column in required if column not in records.columns]
    if missing:
        raise ValueError(f"Manual input CSV is missing required columns: {', '.join(missing)}")
    if records.empty:
        return []

    records["risk_level"] = model.predict(records[FEATURES])
    records["confidence"] = model.predict_proba(records[FEATURES]).max(axis=1)
    risks = records[records["risk_level"].isin(["High", "Medium"])]
    return [
        {
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

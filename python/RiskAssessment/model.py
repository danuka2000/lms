"""Train and apply the Sprint 1 academic risk classifier."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = Path(os.getenv("RISK_TRAINING_DATA", BASE_DIR / "data" / "AI_Personalized_Learning.csv"))
INPUT_PATH = Path(os.getenv("RISK_INPUT_DATA", BASE_DIR / "data" / "manual_risk_inputs.csv"))
MODEL_DIR = Path(__file__).resolve().parent / "ModelOutput"
MODEL_PATH = MODEL_DIR / "risk_model.joblib"

# The supplied dataset has no module field. These signals are available per
# student in that dataset and can also be entered for each module manually.
NUMERIC_FEATURES = [
    "age",
    "previous_gpa",
    "completed_modules",
    "avg_time_per_module",
    "engagement_score",
    "distraction_events",
    "quiz_accuracy",
    "feedback_score",
    "path_efficiency_score",
]
CATEGORICAL_FEATURES = ["education_level", "learning_style", "contextual_difficulty_level"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
OUTCOME_TO_RISK = {
    "fail": "High",
    "poor": "High",
    "at risk": "High",
    "average": "Medium",
    "satisfactory": "Medium",
    "fair": "Medium",
    "good": "Low",
    "excellent": "Low",
}


def _make_pipeline() -> Pipeline:
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocess = ColumnTransformer(
        [("numeric", numeric, NUMERIC_FEATURES), ("categorical", categorical, CATEGORICAL_FEATURES)]
    )
    return Pipeline(
        [
            ("preprocess", preprocess),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    max_depth=10,
                    min_samples_split=4,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )


def train_model() -> tuple[Pipeline, dict[str, float | int]]:
    """Train from the supplied outcomes and persist the fitted model."""
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found at {DATASET_PATH}. Place AI_Personalized_Learning.csv in python/data/ "
            "or set RISK_TRAINING_DATA in python/.env."
        )

    training = pd.read_csv(DATASET_PATH)
    missing = [column for column in FEATURES + ["learning_outcome"] if column not in training.columns]
    if missing:
        raise ValueError(f"Training CSV is missing required columns: {', '.join(missing)}")

    training["risk_level"] = training["learning_outcome"].astype(str).str.strip().str.lower().map(OUTCOME_TO_RISK)
    training = training.dropna(subset=["risk_level"])
    if training["risk_level"].nunique() < 2:
        raise ValueError("Training data must contain at least two recognized outcome levels (Fail, Average, Good, or Excellent).")

    model = _make_pipeline()
    from sklearn.model_selection import cross_val_score

    cv_scores = cross_val_score(model, training[FEATURES], training["risk_level"], cv=5)
    mean_accuracy = round(float(cv_scores.mean()), 3)

    model.fit(training[FEATURES], training["risk_level"])
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    # Model is retrained from the CSV at service start; joblib file is a local
    # convenience for VS Code and is not needed to serve requests.
    import joblib

    joblib.dump(model, MODEL_PATH)
    return model, {
        "training_rows": len(training),
        "classes": int(training["risk_level"].nunique()),
        "accuracy": mean_accuracy,
    }


def assess_manual_records() -> list[dict]:
    model, _ = train_model()
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Manual input CSV not found at {INPUT_PATH}. Create python/data/manual_risk_inputs.csv using the provided template."
        )
    records = pd.read_csv(INPUT_PATH)
    required = ["student_id", "student_name", "module_id", "module_name"] + FEATURES
    missing = [column for column in required if column not in records.columns]
    if missing:
        raise ValueError(f"Manual input CSV is missing required columns: {', '.join(missing)}")
    if records.empty:
        return []

    records["risk_level"] = model.predict(records[FEATURES])
    probabilities = model.predict_proba(records[FEATURES])
    records["confidence"] = probabilities.max(axis=1)
    risks = records[records["risk_level"].isin(["High", "Medium"])]
    assessments = []
    for _, row in risks.iterrows():
        assessments.append(
            {
                "student_id": str(row["student_id"]),
                "student_name": str(row["student_name"]),
                "module_id": str(row["module_id"]),
                "module_name": str(row["module_name"]),
                "risk_level": str(row["risk_level"]),
                "confidence": round(float(row["confidence"]), 3),
                "quiz_accuracy": _number(row["quiz_accuracy"]),
                "engagement_score": _number(row["engagement_score"]),
                "previous_gpa": _number(row["previous_gpa"]),
                "completed_modules": _number(row["completed_modules"]),
                "contextual_difficulty_level": str(row["contextual_difficulty_level"]),
            }
        )
    return assessments


def _number(value):
    return None if pd.isna(value) else float(value)

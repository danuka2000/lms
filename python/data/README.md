# Sprint 1 risk assessment data

- `student_academic_risk.csv` is the training dataset. It contains student performance features and the target label `academic_risk_level` (`Low`, `Medium`, or `High`).
- `manual_risk_inputs.csv` is the manually entered live input. Each row represents one student in one module. Add a separate row for each module; the same student can appear more than once.

The manual CSV includes student and module identifiers plus the feature columns from the training dataset: `previous_gpa`, `attendance`, `assignment_score`, `quiz_score`, `study_hours`, `engagement_score`, `late_assignments`, `completed_assignments`, and `learning_progress`. Use the same measurement scales as the training file. The model learns the risk classes directly from `academic_risk_level`; the client lists High and Medium risk modules.

The older `AI_Personalized_Learning.csv` is no longer used by this risk model. To use a dataset at a different location, set `RISK_TRAINING_DATA` or `RISK_INPUT_DATA` in `python/.env` to an absolute CSV path.

# Sprint 1 risk assessment data

- `student_academic_risk.csv` is the training dataset. It contains performance features and the `academic_risk_level` target (`Low`, `Medium`, or `High`).
- `manual_risk_inputs.csv` is the manually entered module list. Each row is one user and one enrolled module.

Set `user_id` to the MongoDB ID in the current user's login token. The Risk Assessment page shows that ID when no assigned risk rows are found. Add one row per enrolled module and use the same user ID on each row. The API verifies the login token and only evaluates rows whose `user_id` matches the signed-in account.

The remaining manual input columns are student/module identifiers plus the model features from the training CSV: `previous_gpa`, `attendance`, `assignment_score`, `quiz_score`, `study_hours`, `engagement_score`, `late_assignments`, `completed_assignments`, and `learning_progress`. Keep their measurement scales consistent with the training dataset.

The older `AI_Personalized_Learning.csv` is not used by this risk model. To choose a different dataset path, set `RISK_TRAINING_DATA` or `RISK_INPUT_DATA` in `python/.env`.

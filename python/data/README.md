# Sprint 1 risk assessment data

- `AI_Personalized_Learning.csv` is the historical training dataset. Copy the supplied CSV here.
- `manual_risk_inputs.csv` is the manually entered live input. Each row is one student in one module. Add or edit rows here; a student with risk in several modules appears several times in the client report.

The manual CSV must include the columns shown in the template. Feature meanings and scales should match the training dataset: quiz accuracy, engagement, and path efficiency are 0–100; feedback score uses the dataset's scale; GPA uses the dataset's GPA scale. The model predicts each module's risk using these inputs. The client displays High and Medium rows. The model learns from `learning_outcome`: Fail/Poor maps to High, Fair/Average/Satisfactory to Medium, Good/Excellent to Low.

For a different location, set `RISK_TRAINING_DATA` or `RISK_INPUT_DATA` in `python/.env` to an absolute CSV path.

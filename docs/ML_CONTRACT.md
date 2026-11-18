# ML Contract

FastAPI imports the inference function directly:

`from ml.inference import predict_default`

Input feature keys in this starter:
- `annual_revenue`: float
- `requested_loan_amount`: float
- `existing_loan_amount`: float
- `years_in_business`: integer
- `credit_score`: integer

Required output:
- `default_probability`: float in [0, 1]
- `risk_category`: agreed category label
- `model_version`: string
- `is_mock`: boolean

The ML team must confirm feature definitions, units, missing-value handling, preprocessing, target class mapping, probability calibration, thresholds, model versioning and evaluation before replacing the mock. Do not assume LOW/MEDIUM/HIGH thresholds in this starter are approved business policy.

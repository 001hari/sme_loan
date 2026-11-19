# API Contract — first vertical slice

Base URL: `http://127.0.0.1:8000/api/v1`

## Submit application
`POST /applications`

Request:
```json
{
  "applicant_name": "Asha Patel",
  "business_name": "Patel Foods",
  "annual_revenue": 1000000,
  "requested_loan_amount": 300000,
  "existing_loan_amount": 50000,
  "years_in_business": 5,
  "credit_score": 700
}
```

Response: application object containing `id`, submitted fields, `status`, and `created_at`.

## List applications
`GET /applications`

Response: array of application objects.

## Get one application
`GET /applications/{application_id}`

## Run prediction
`POST /applications/{application_id}/predict`

Response:
```json
{
  "id": "prediction UUID",
  "application_id": "application UUID",
  "default_probability": 0.23,
  "risk_category": "LOW",
  "model_version": "mock-v0",
  "is_mock": true,
  "created_at": "timestamp"
}
```

The numerical value above is illustrative. Actual mock output depends on the submitted features. `is_mock: true` explicitly marks it as non-production.

# Workflow — first vertical slice

1. Applicant enters business and financial details in Streamlit.
2. Streamlit sends JSON to FastAPI.
3. FastAPI validates the request using Pydantic.
4. Backend service writes the application through SQLAlchemy.
5. A user triggers prediction.
6. FastAPI calls the root-level ML inference function.
7. Backend saves prediction and updates application status to `RISK_ASSESSED`.
8. Streamlit displays the result and clearly marks mock output.

This starter does not yet implement RM/LO roles, review transitions, approval/rejection decisions, authentication, or audit history. Those should be added only against the team's approved workflow.

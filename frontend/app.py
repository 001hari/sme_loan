import streamlit as st

from frontend.services.api_client import (
    APIError,
    fetch_applications,
    predict_application,
    submit_application,
)

st.set_page_config(page_title="SME Loan Risk System", page_icon="🏦", layout="wide")
st.title("SME Loan Default Risk Prediction")
st.caption("Development prototype — predictions are currently MOCK outputs.")

tab_submit, tab_view = st.tabs(["Submit application", "View applications"])

with tab_submit:
    st.subheader("Applicant and business information")
    with st.form("application_form"):
        applicant_name = st.text_input("Applicant name")
        business_name = st.text_input("Business name")
        col1, col2 = st.columns(2)
        with col1:
            annual_revenue = st.number_input("Annual revenue (₹)", min_value=1.0, value=1000000.0, step=50000.0)
            requested_loan_amount = st.number_input("Requested loan amount (₹)", min_value=1.0, value=300000.0, step=10000.0)
            existing_loan_amount = st.number_input("Existing loan amount (₹)", min_value=0.0, value=50000.0, step=5000.0)
        with col2:
            years_in_business = st.number_input("Years in business", min_value=0, max_value=150, value=5)
            credit_score = st.number_input("Credit score", min_value=300, max_value=900, value=700)
        submitted = st.form_submit_button("Submit application", type="primary")

    if submitted:
        payload = {
            "applicant_name": applicant_name,
            "business_name": business_name,
            "annual_revenue": annual_revenue,
            "requested_loan_amount": requested_loan_amount,
            "existing_loan_amount": existing_loan_amount,
            "years_in_business": int(years_in_business),
            "credit_score": int(credit_score),
        }
        try:
            result = submit_application(payload)
            st.success("Application saved successfully.")
            st.json(result)
        except APIError as exc:
            st.error(str(exc))

with tab_view:
    st.subheader("Submitted applications")
    if st.button("Refresh applications"):
        st.rerun()
    try:
        applications = fetch_applications()
        if not applications:
            st.info("No applications found yet.")
        for application in applications:
            with st.expander(
                f'{application["business_name"]} — {application["applicant_name"]} ({application["status"]})'
            ):
                st.json(application)
                if st.button("Run mock risk prediction", key=f'predict-{application["id"]}'):
                    try:
                        prediction = predict_application(application["id"])
                        st.warning("MOCK prediction only — not a real credit-risk assessment.")
                        st.json(prediction)
                    except APIError as exc:
                        st.error(str(exc))
    except APIError as exc:
        st.error(str(exc))
        st.caption("Make sure the FastAPI backend is running.")

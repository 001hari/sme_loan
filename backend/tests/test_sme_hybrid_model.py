import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

from ml.data_generation.generate_synthetic_sme_data import (
    FEATURES, TARGET, generate_dataset, validate_dataset,
)
from ml.training.train_sme_hybrid_model import (
    NUMERICAL_FEATURES, build_models, load_splits,
)
from backend.app.services import sme_hybrid_prediction_service as inference
from backend.app.services.sme_hybrid_prediction_service import RiskPrediction
from backend.app.services.workflow_service import Principal, WorkflowService


@pytest.fixture(scope="module")
def fitted_models():
    frame = generate_dataset(1_000, seed=13)
    train, test = train_test_split(frame, test_size=.2, random_state=13, stratify=frame[TARGET])
    models = build_models(seed=13)
    for model in models.values():
        model.fit(train[FEATURES], train[TARGET])
    return frame, train, test, models


def test_synthetic_dataset_schema_target_and_financial_consistency():
    frame = generate_dataset(1_500, seed=23)
    summary = validate_dataset(frame)
    assert list(frame.columns) == FEATURES + [TARGET]
    assert summary["features"] == 23
    assert summary["missing_values"] == summary["duplicate_rows"] == 0
    assert set(frame[TARGET].unique()) == {0, 1}
    assert .10 <= frame[TARGET].mean() <= .30
    assert np.allclose(frame.debt_to_revenue_ratio, frame.total_liabilities / frame.annual_revenue, atol=5e-5)
    assert np.allclose(frame.loan_to_revenue_ratio, frame.loan_amount / frame.annual_revenue, atol=5e-5)
    assert np.allclose(frame.profit_margin, frame.annual_profit / frame.annual_revenue, atol=5e-5)
    assert frame.late_payment_history.dtype == bool


def test_split_loader_keeps_raw_values_and_rejects_overlap(tmp_path):
    frame = generate_dataset(800, seed=29)
    train, test = train_test_split(frame, test_size=.2, random_state=29, stratify=frame[TARGET])
    train_path, test_path = tmp_path / "train.csv", tmp_path / "test.csv"
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)
    loaded_train, loaded_test = load_splits(train_path, test_path)
    assert loaded_train.shape == (640, 24)
    assert loaded_test.shape == (160, 24)
    assert isinstance(loaded_train.loc[0, "sector"], str)
    assert len(set(pd.util.hash_pandas_object(loaded_train, index=False)) &
               set(pd.util.hash_pandas_object(loaded_test, index=False))) == 0
    with pytest.raises(ValueError, match="across the boundary"):
        load_splits(train_path, train_path)


def test_preprocessor_scaling_is_fitted_only_on_training_rows():
    frame = generate_dataset(500, seed=31)
    train, test = train_test_split(frame, test_size=.2, random_state=31, stratify=frame[TARGET])
    test = test.copy()
    test.loc[:, "annual_revenue"] = 9_000_000_000_000
    model = build_models(seed=31)["Logistic Regression"]
    model.fit(train[FEATURES], train[TARGET])
    numeric_pipeline = model.named_steps["preprocessor"].named_transformers_["numeric"]
    scaler_mean = numeric_pipeline.named_steps["scaler"].mean_
    training_means = train[NUMERICAL_FEATURES].astype(float).mean().to_numpy()
    assert np.allclose(scaler_mean, training_means)
    assert not np.isclose(scaler_mean[NUMERICAL_FEATURES.index("annual_revenue")],
                          test.annual_revenue.mean())


def test_all_models_predict_raw_rows_and_return_valid_probabilities(fitted_models):
    _frame, _train, test, models = fitted_models
    raw = test[FEATURES].iloc[:12].copy()
    raw.loc[:, "state"] = "Unknown State"
    for name, model in models.items():
        prediction = model.predict(raw)
        probability = model.predict_proba(raw)
        assert len(prediction) == len(raw), name
        assert probability.shape == (len(raw), 2), name
        assert np.isfinite(probability).all() and ((probability >= 0) & (probability <= 1)).all()
        assert np.allclose(probability.sum(axis=1), 1)


def test_saved_hybrid_pipeline_loads_and_predicts_raw_features(fitted_models, tmp_path):
    _frame, _train, test, models = fitted_models
    model = models["SME Hybrid Model"]
    sample = test[FEATURES].iloc[:5].copy()
    path = tmp_path / "model.joblib"
    joblib.dump(model, path)
    loaded = joblib.load(path)
    assert loaded.predict(sample).tolist() == model.predict(sample).tolist()
    assert np.allclose(loaded.predict_proba(sample), model.predict_proba(sample))


def test_application_mapping_rejects_missing_required_fields():
    with pytest.raises(ValueError, match="annual_revenue"):
        inference.application_features({"state": "Kerala"}, ["state", "annual_revenue"])


def test_default_probability_uses_metadata_class_even_if_class_order_is_reversed(monkeypatch):
    class Model:
        classes_ = np.array([1, 0])
        def predict(self, _frame):
            return np.array([1])
        def predict_proba(self, _frame):
            return np.array([[.73, .27]])

    monkeypatch.setattr(inference, "_load_model_and_metadata", lambda: (
        Model(), {"feature_names": ["annual_revenue"], "default_class": 1,
                  "class_mapping": {"0": "Non-default", "1": "Default / High Risk"},
                  "model_version": "test"},
    ))
    prediction = inference.predict_sme_hybrid({"annual_revenue": 1_000_000})
    assert prediction.predicted_class_label == "Default / High Risk"
    assert prediction.default_probability == pytest.approx(.73)
    assert prediction.risk_score == pytest.approx(73.0)


def test_loan_officer_workflow_calls_hybrid_prediction_and_persists_it(monkeypatch):
    application = {"application_id": 81, "annual_revenue": 1_000_000}
    prediction = RiskPrediction(1, "Default / High Risk", .73, .73)

    class Repository:
        def __init__(self):
            self.saved = None
        def get_officer_application(self, _application_id):
            return application
        def save_prediction(self, officer_id, application_id, saved_prediction):
            self.saved = (officer_id, application_id, saved_prediction)
            return 93

    calls = []
    monkeypatch.setattr("backend.app.services.workflow_service.predict_sme_hybrid",
                        lambda row: (calls.append(row), prediction)[1])
    repository = Repository()
    service = WorkflowService(repository)
    result = service.assess_risk(Principal(5, "Officer", "officer@example.com", "LOAN_OFFICER"), 81)
    assert result is prediction
    assert calls == [application]
    assert repository.saved == (5, 81, prediction)

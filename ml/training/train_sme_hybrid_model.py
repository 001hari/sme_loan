"""Fit, evaluate, and save the raw-input SME Hybrid Model."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score,
    precision_recall_curve, precision_score, recall_score, roc_auc_score, roc_curve,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.data_generation.generate_synthetic_sme_data import (
    CATEGORICAL_FEATURES, FEATURES, NUMERICAL_FEATURES, TARGET,
)


ROOT = Path(__file__).resolve().parents[2]
TRAIN_PATH = ROOT / "dataset" / "sme_train.csv"
TEST_PATH = ROOT / "dataset" / "sme_test.csv"
ARTIFACTS = ROOT / "ml" / "artifacts"
RESULTS = ROOT / "ml" / "results"
SEED = 42
MODEL_VERSION = "1.0.0"
CLASS_MAPPING = {0: "Non-default", 1: "Default / High Risk"}


def build_preprocessor(*, scale_numeric: bool) -> ColumnTransformer:
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("numeric", numeric, NUMERICAL_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ])


def build_models(seed: int = SEED) -> dict[str, object]:
    logistic = Pipeline([
        ("preprocessor", build_preprocessor(scale_numeric=True)),
        ("classifier", LogisticRegression(
            C=1.0, max_iter=2000, solver="lbfgs", class_weight="balanced", random_state=seed,
        )),
    ])
    forest = Pipeline([
        ("preprocessor", build_preprocessor(scale_numeric=False)),
        ("classifier", RandomForestClassifier(
            n_estimators=180, max_depth=14, min_samples_leaf=4,
            max_features="sqrt", class_weight="balanced_subsample",
            random_state=seed, n_jobs=-1,
        )),
    ])
    hybrid = VotingClassifier(
        estimators=[("logistic_regression", logistic), ("random_forest", forest)],
        voting="soft", weights=[1, 1], n_jobs=1,
    )
    return {
        "Logistic Regression": logistic,
        "Random Forest": forest,
        "SME Hybrid Model": hybrid,
    }


def load_splits(train_path: Path = TRAIN_PATH, test_path: Path = TEST_PATH):
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    expected = FEATURES + [TARGET]
    if list(train.columns) != expected or list(test.columns) != expected:
        raise ValueError("Train and test files must contain the exact raw feature schema and target order.")
    if train.isna().any().any() or test.isna().any().any():
        raise ValueError("Synthetic train/test datasets must be complete before training.")
    train_hashes = set(pd.util.hash_pandas_object(train, index=False).tolist())
    test_hashes = set(pd.util.hash_pandas_object(test, index=False).tolist())
    if train_hashes.intersection(test_hashes):
        raise ValueError("Train/test split contains duplicate rows across the boundary.")
    if set(train[TARGET].unique()) != {0, 1} or set(test[TARGET].unique()) != {0, 1}:
        raise ValueError("Both splits must contain target classes 0 and 1.")
    return train, test


def _metrics(y_true, prediction, probabilities) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, prediction)),
        "precision_default": float(precision_score(y_true, prediction, pos_label=1, zero_division=0)),
        "recall_default": float(recall_score(y_true, prediction, pos_label=1, zero_division=0)),
        "f1_default": float(f1_score(y_true, prediction, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
    }


def evaluate_and_save(
    train: pd.DataFrame,
    test: pd.DataFrame,
    *,
    artifact_dir: Path = ARTIFACTS,
    results_dir: Path = RESULTS,
    run_cross_validation: bool = True,
) -> dict:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    X_train, y_train = train[FEATURES], train[TARGET]
    X_test, y_test = test[FEATURES], test[TARGET]
    models = build_models()
    comparison, reports, matrices, cv_results = {}, {}, {}, {}
    curves = {}

    for name, model in models.items():
        if run_cross_validation:
            cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
            scores = cross_validate(
                model, X_train, y_train, cv=cv, n_jobs=1, error_score="raise",
                scoring={"accuracy": "accuracy", "precision": "precision",
                         "recall": "recall", "f1": "f1", "roc_auc": "roc_auc"},
            )
            cv_results[name] = {
                metric: {"mean": float(np.mean(scores[f"test_{metric}"])),
                         "std": float(np.std(scores[f"test_{metric}"], ddof=1))}
                for metric in ("accuracy", "precision", "recall", "f1", "roc_auc")
            }
        model.fit(X_train, y_train)
        prediction = model.predict(X_test)
        classes = list(model.classes_)
        probability = model.predict_proba(X_test)[:, classes.index(1)]
        comparison[name] = _metrics(y_test, prediction, probability)
        reports[name] = classification_report(
            y_test, prediction, labels=[0, 1], target_names=[CLASS_MAPPING[0], CLASS_MAPPING[1]],
            output_dict=True, zero_division=0,
        )
        matrices[name] = confusion_matrix(y_test, prediction, labels=[0, 1]).tolist()
        curves[name] = (probability, prediction)

    hybrid = models["SME Hybrid Model"]
    joblib.dump(hybrid, artifact_dir / "sme_hybrid_model.joblib")
    metrics_frame = pd.DataFrame(comparison).rename_axis("Metric")
    metrics_frame.to_csv(results_dir / "sme_hybrid_test_comparison.csv")
    (results_dir / "sme_hybrid_classification_reports.json").write_text(
        json.dumps(reports, indent=2), encoding="utf-8",
    )
    confusion_rows = []
    for name, matrix in matrices.items():
        tn, fp, fn, tp = matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1]
        confusion_rows.append({"model": name, "true_non_default_pred_non_default": tn,
                               "true_non_default_pred_default": fp,
                               "true_default_pred_non_default": fn, "true_default_pred_default": tp})
    pd.DataFrame(confusion_rows).to_csv(results_dir / "sme_hybrid_confusion_matrices.csv", index=False)
    pd.DataFrame([
        {"model": name, "metric": metric, **summary}
        for name, values in cv_results.items() for metric, summary in values.items()
    ]).to_csv(results_dir / "sme_hybrid_cross_validation.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for name, (probability, _prediction) in curves.items():
        fpr, tpr, _ = roc_curve(y_test, probability)
        axes[0].plot(fpr, tpr, label=f"{name} (AUC {roc_auc_score(y_test, probability):.3f})")
        precision, recall, _ = precision_recall_curve(y_test, probability)
        axes[1].plot(recall, precision, label=name)
    axes[0].plot([0, 1], [0, 1], linestyle="--", color="grey", linewidth=1)
    axes[0].set(title="ROC curves (synthetic test split)", xlabel="False positive rate", ylabel="True positive rate")
    axes[1].set(title="Precision-recall curves (synthetic test split)", xlabel="Recall", ylabel="Precision")
    for axis in axes:
        axis.legend(loc="best", fontsize=8)
        axis.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(results_dir / "sme_hybrid_roc_pr_curves.png", dpi=150)
    plt.close(fig)

    metadata = {
        "model_name": "SME Hybrid Model", "model_version": MODEL_VERSION,
        "dataset_source": "Synthetic, generated from live PostgreSQL business and loan application schema.",
        "dataset_file": "dataset/synthetic_sme_loan_data.csv",
        "training_file": "dataset/sme_train.csv", "testing_file": "dataset/sme_test.csv",
        "target_column": TARGET,
        "class_mapping": {str(k): v for k, v in CLASS_MAPPING.items()},
        "default_class": 1, "decision_threshold": 0.5,
        "feature_names": FEATURES, "numerical_features": NUMERICAL_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "preprocessing": {
            "numerical": "median imputation; StandardScaler in Logistic Regression only",
            "categorical": "most-frequent imputation; OneHotEncoder(handle_unknown='ignore')",
            "fit_scope": "training split only; preprocessing is embedded in each estimator pipeline",
        },
        "generation_seed": SEED,
        "training_rows": int(len(train)), "testing_rows": int(len(test)),
        "training_class_counts": {str(k): int(v) for k, v in y_train.value_counts().sort_index().items()},
        "testing_class_counts": {str(k): int(v) for k, v in y_test.value_counts().sort_index().items()},
        "synthetic_default_label_generation": (
            "Bernoulli sampling from a logistic probability based on credit score, debt/revenue, "
            "loan/revenue, DSCR, weak profit margin, late/missed payments, cash-flow stability, "
            "and declining/weak revenue growth. The intercept is calibrated for 20% expected "
            "prevalence; sampled outcomes are not forced to an exact class count."
        ),
        "model_parameters": {
            "logistic_regression": "C=1.0, lbfgs, max_iter=2000, class_weight=balanced",
            "random_forest": "180 trees, max_depth=14, min_samples_leaf=4, max_features=sqrt, class_weight=balanced_subsample",
            "voting": "sklearn VotingClassifier, voting=soft, equal weights [1, 1]",
        },
        "test_metrics": comparison, "training_only_cross_validation": cv_results,
        "confusion_matrices_label_order": [CLASS_MAPPING[0], CLASS_MAPPING[1]],
        "confusion_matrices": matrices,
        "evaluation_caveat": "All metrics measure agreement with this generator's simulated labels, not observed repayment outcomes or real-world bank performance.",
        "created_date": date.today().isoformat(),
    }
    (artifact_dir / "sme_hybrid_model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"metrics": comparison, "reports": reports, "confusion_matrices": matrices,
            "cv": cv_results, "metadata": metadata, "model": hybrid}


def main() -> None:
    train, test = load_splits()
    result = evaluate_and_save(train, test)
    report = [
        "# SME Hybrid Model evaluation (synthetic labels)", "",
        "This measures fit to simulated labels generated by this project, not real bank outcomes.", "",
        "| Metric | Logistic Regression | Random Forest | SME Hybrid Model |",
        "|---|---:|---:|---:|",
    ]
    for metric, label in (("accuracy", "Accuracy"), ("precision_default", "Precision (default)"),
                          ("recall_default", "Recall (default)"), ("f1_default", "F1 (default)"),
                          ("roc_auc", "ROC-AUC")):
        vals = [result["metrics"][name][metric] for name in ("Logistic Regression", "Random Forest", "SME Hybrid Model")]
        report.append(f"| {label} | " + " | ".join(f"{value:.4f}" for value in vals) + " |")
    report.extend(["", "Positive class: `1` = Default / High Risk. Threshold: 0.5.",
                   "Test rows were held out from preprocessing fitting, cross-validation, and model selection."])
    (RESULTS / "sme_hybrid_model_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": result["metrics"], "cv": result["cv"],
                      "artifact": str(ARTIFACTS / "sme_hybrid_model.joblib")}, indent=2))


if __name__ == "__main__":
    main()

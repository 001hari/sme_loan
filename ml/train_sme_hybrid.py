# Updated training script: use official test set
import pandas as pd
import json
import os
from pathlib import Path
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    roc_curve,
    precision_recall_curve,
)
import matplotlib.pyplot as plt
import joblib

# Paths
TRAIN_PATH = Path('C:/Users/nucle/PycharmProjects/SME_PRE_PREDICTION/dataset/sme_train.csv')
TEST_PATH = Path('C:/Users/nucle/PycharmProjects/SME_PRE_PREDICTION/dataset/sme_test.csv')
ARTIFACT_DIR = Path('C:/Users/nucle/PycharmProjects/SME_PRE_PREDICTION/ml/artifacts')
RESULTS_DIR = Path('C:/Users/nucle/PycharmProjects/SME_PRE_PREDICTION/ml/results')
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Load datasets
train_df = pd.read_csv(TRAIN_PATH)
test_df = pd.read_csv(TEST_PATH)

TARGET_COL = 'default'
X_train = train_df.drop(columns=[TARGET_COL])
y_train = train_df[TARGET_COL]
X_test = test_df.drop(columns=[TARGET_COL])
y_test = test_df[TARGET_COL]

# Feature type detection
numeric_features = X_train.select_dtypes(include=['int64', 'float64']).columns.tolist()
categorical_features = X_train.select_dtypes(include=['object', 'bool']).columns.tolist()

numeric_transformer = Pipeline(steps=[('imputer', SimpleImputer(strategy='median')), ('scaler', StandardScaler())])
categorical_transformer = Pipeline(steps=[('imputer', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(handle_unknown='ignore'))])

preprocess = ColumnTransformer(transformers=[('num', numeric_transformer, numeric_features), ('cat', categorical_transformer, categorical_features)])

logreg = LogisticRegression(max_iter=2000, class_weight='balanced', random_state=42)
rf = RandomForestClassifier(n_estimators=180, max_depth=14, min_samples_leaf=4, class_weight='balanced_subsample', random_state=42, n_jobs=-1)

logreg_pipe = Pipeline(steps=[('preprocess', preprocess), ('clf', logreg)])
rf_pipe = Pipeline(steps=[('preprocess', preprocess), ('clf', rf)])

voting_clf = VotingClassifier(estimators=[('logreg', logreg_pipe), ('rf', rf_pipe)], voting='soft')

# Fit on full training data
logreg_pipe.fit(X_train, y_train)
rf_pipe.fit(X_train, y_train)
voting_clf.fit(X_train, y_train)

# Evaluation helper
def evaluate_model(name, model, X_test, y_test):
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'precision': precision_score(y_test, y_pred, zero_division=0),
        'recall': recall_score(y_test, y_pred, zero_division=0),
        'f1': f1_score(y_test, y_pred, zero_division=0),
        'roc_auc': roc_auc_score(y_test, y_proba)
    }
    # Confusion matrix plot
    cm = confusion_matrix(y_test, y_pred)
    plt.figure()
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title(f'Confusion Matrix - {name}')
    plt.colorbar()
    tick_marks = range(len(cm))
    plt.xticks(tick_marks, tick_marks)
    plt.yticks(tick_marks, tick_marks)
    plt.ylabel('True')
    plt.xlabel('Pred')
    plt.savefig(RESULTS_DIR / f'confusion_{name}.png')
    plt.close()
    # ROC curve
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    plt.figure()
    plt.plot(fpr, tpr, label=f'AUC={metrics["roc_auc"]:.3f}')
    plt.plot([0,1],[0,1],'k--')
    plt.xlabel('FPR')
    plt.ylabel('TPR')
    plt.title(f'ROC Curve - {name}')
    plt.legend(loc='lower right')
    plt.savefig(RESULTS_DIR / f'roc_{name}.png')
    plt.close()
    # PR curve
    precision, recall, _ = precision_recall_curve(y_test, y_proba)
    plt.figure()
    plt.plot(recall, precision)
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title(f'PR Curve - {name}')
    plt.savefig(RESULTS_DIR / f'pr_{name}.png')
    plt.close()
    report = classification_report(y_test, y_pred, output_dict=True)
    return metrics, report

results = {}
for name, model in [('LogisticRegression', logreg_pipe), ('RandomForest', rf_pipe), ('SMEHybrid', voting_clf)]:
    metrics, report = evaluate_model(name, model, X_test, y_test)
    results[name] = {'metrics': metrics, 'report': report}

# Cross‑validation on training data (5‑fold stratified)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_results = {}
for name, model in [('LogisticRegression', logreg_pipe), ('RandomForest', rf_pipe), ('SMEHybrid', voting_clf)]:
    scores = cross_val_score(model, X_train, y_train, cv=cv, scoring='roc_auc')
    cv_results[name] = scores.tolist()

# Backup existing artifact before overwriting
backup_dir = ARTIFACT_DIR / ('backup_' + pd.Timestamp.now().strftime('%Y%m%d_%H%M%S'))
backup_dir.mkdir(parents=True, exist_ok=True)
if (ARTIFACT_DIR / 'sme_hybrid_model.joblib').exists():
    (ARTIFACT_DIR / 'sme_hybrid_model.joblib').rename(backup_dir / 'sme_hybrid_model.joblib')
if (ARTIFACT_DIR / 'sme_hybrid_model_metadata.json').exists():
    (ARTIFACT_DIR / 'sme_hybrid_model_metadata.json').rename(backup_dir / 'sme_hybrid_model_metadata.json')

# Save model artifact
model_path = ARTIFACT_DIR / 'sme_hybrid_model.joblib'
joblib.dump(voting_clf, model_path)

# Save metadata with updated evaluation
metadata = {
    'model_name': 'SME Hybrid Model',
    'model_version': '1.0.0',
    'training_file': str(TRAIN_PATH),
    'testing_file': str(TEST_PATH),
    'target_column': TARGET_COL,
    'default_class': 1,
    'class_mapping': {'0':'Non-default','1':'Default / High Risk'},
    'feature_names': X_train.columns.tolist(),
    'numeric_features': numeric_features,
    'categorical_features': categorical_features,
    'train_shape': X_train.shape,
    'test_shape': X_test.shape,
    'evaluation': results,
    'cross_validation_auc': cv_results,
    'preprocessing': {'numeric':'median+StandardScaler','categorical':'most_frequent+OneHotEncoder'}
}
metadata_path = ARTIFACT_DIR / 'sme_hybrid_model_metadata.json'
with open(metadata_path, 'w') as f:
    json.dump(metadata, f, indent=2)

print('Training complete. Model saved to', model_path)
print('Metadata saved to', metadata_path)

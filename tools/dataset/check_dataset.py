import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "dataset"

train = pd.read_csv(DATASET_DIR / "sme_train.csv")
test = pd.read_csv(DATASET_DIR / "sme_test.csv")

print("TRAIN DATASET")
print(train["default"].value_counts())
print(train["default"].value_counts(normalize=True) * 100)

print("\nTEST DATASET")
print(test["default"].value_counts())
print(test["default"].value_counts(normalize=True) * 100)

import pandas as pd, json, sys
path = r'C:/Users/nucle/PycharmProjects/SME_PRE_PREDICTION/dataset/sme_train.csv'
df = pd.read_csv(path)
summary = {
    'rows': df.shape[0],
    'cols': df.shape[1],
    'columns': list(df.columns),
    'dtypes': {c: str(df[c].dtype) for c in df.columns},
    'target': 'default',
    'target_counts': df['default'].value_counts().to_dict(),
    'missing_perc': (df.isnull().mean() * 100).round(2).to_dict(),
    'duplicate_rows': int(df.duplicated().sum())
}
print(json.dumps(summary))

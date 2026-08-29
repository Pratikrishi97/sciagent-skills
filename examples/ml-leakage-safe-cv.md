# Example: leakage-safe cross-validation for a biomarker model

**Skills activated:** `ml-for-science`, `biostatistics`

## The prompt

> I have 800 patients with clinical features + a binary outcome (responder/non-responder). The patients come from 12 hospitals. Build an L2-regularized logistic regression biomarker model, tune the regularization with nested group-aware cross-validation (group = hospital), report a held-out AUROC with bootstrap 95% CI, and show SHAP feature importance. Make sure no hospital leaks from train into test.

## What the agent does

`ml-for-science` activates on `scikit-learn`, `cross-validation`, `group CV`, `SHAP`; `biostatistics` for the bootstrap CI.

### 1. Group-aware splitting

```python
# pip install scikit-learn shap statsmodels
import numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold, cross_val_score, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score

df = pd.read_csv("patients.csv")          # cols: hospital, feature_1..N, responder
X = df.drop(columns=["hospital","responder"]).values
y = df["responder"].values
groups = df["hospital"].values
```

### 2. Nested CV with group-aware folds

```python
inner_cv = GroupKFold(n_splits=3)
outer_cv = GroupKFold(n_splits=5)
pipe = Pipeline([("sc", StandardScaler()),
                 ("clf", LogisticRegression(penalty="l2", solver="liblinear", max_iter=2000))])
grid = GridSearchCV(pipe, {"clf__C": np.logspace(-3, 1, 12)},
                    cv=inner_cv, scoring="roc_auc", n_jobs=-1)
scores = cross_val_score(grid, X, y, groups=groups, cv=outer_cv, scoring="roc_auc")
print(f"nested CV AUROC: {scores.mean():.3f} ± {scores.std():.3f}")
```

### 3. Held-out test + bootstrap CI

```python
from sklearn.model_selection import GroupShuffleSplit
split = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=1)
tr, te = next(split.split(X, y, groups))
grid.fit(X[tr], y[tr])
proba = grid.predict_proba(X[te])[:, 1]
auc = roc_auc_score(y[te], proba)

# bootstrap CI on the held-out set
rng = np.random.default_rng(1)
boot = [roc_auc_score(y[te][idx], proba[idx])
        for idx in (rng.choice(len(te), len(te), replace=True) for _ in range(2000))]
ci = np.percentile(boot, [2.5, 97.5])
print(f"held-out AUROC: {auc:.3f} (95% CI {ci[0]:.3f}-{ci[1]:.3f})")
```

### 4. SHAP on the final model

```python
import shap
explainer = shap.LinearExplainer(grid.best_estimator_.named_steps["clf],
                                 grid.best_estimator_.named_steps["sc].transform(X[tr]))
sv = explainer.shap_values(grid.best_estimator_.named_steps["sc].transform(X[te]))
shap.summary_plot(sv, X[te], feature_names=df.columns[:-2], show=False)
```

## Pitfalls the skill surfaces

- Plain `KFold` / `train_test_split` silently leaks patients from the same hospital into both train and test, inflating AUROC by 0.05–0.15. Always pass `groups=` and use `GroupKFold`.
- Scale **inside** the pipeline (after the split), not before — fitting a scaler on the whole dataset is a leakage.
- Tuning on the same CV folds you evaluate on is "selection bias"; nested CV (outer for eval, inner for tuning) is the fix.
- Report a bootstrap CI, not the CV standard deviation — the latter conflates fold variance with estimator variance.

## Reproducibility

`np.random.seed(1)` + `random_state=1` everywhere. Pin scikit-learn + shap in `environment.yml`. Save the fitted pipeline with `joblib.dump(grid, "model.joblib")`.

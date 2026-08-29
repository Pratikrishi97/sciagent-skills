---
name: ml-for-science
description: Supervised and unsupervised machine learning for scientific data using scikit-learn. Use when building classification or regression models, doing feature engineering, model selection, cross-validation, hyperparameter tuning, calibrating probabilities, interpreting models with SHAP, handling imbalanced classes, or diagnosing train/test leakage and generalization gaps in scientific workflows.
license: MIT
compatibility: Requires Python 3.10+ with scikit-learn, pandas, numpy, matplotlib. Optional extras include imbalanced-learn, shap, sktime, darts, mlxtend, category_encoders.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Machine Learning & Statistics
---

# Machine Learning for Science

## Overview

Machine learning (ML) is now standard practice across the natural and social sciences, from genotype-to-phenotype prediction in genomics to materials property regression, ecology species distribution modeling, and clinical risk scoring. The scientific use case differs from a pure software-engineering use case in two ways: (1) **generalization is the headline metric** — a model that overfits a single cohort is scientifically useless, even if it scores well; and (2) **data leakage is a correctness bug, not just a perf bug** — a model that sees test information during training invalidates a result.

This skill covers the canonical scikit-learn workflow — `Pipeline`, `ColumnTransformer`, `cross_val_score`, `GridSearchCV`, nested CV, `CalibratedClassifierCV`, SHAP interpretability, imbalanced data with `imbalanced-learn`, time-series with `sktime`/`darts`, unsupervised exploratory analysis, and the documentation disciplines (model cards, datasheets) that separate scientific ML from ad-hoc ML.

## When to use this skill

- You are fitting a classifier or regressor on tabular scientific data and need honest, leak-free generalization estimates.
- You need to combine numeric, categorical, and text features into a single model.
- You must select between models or tune hyperparameters **without** leaking the test set.
- A reviewer asks "why does your model predict what it predicts?" and you need SHAP / permutation importance.
- Classes are imbalanced (rare disease, rare events, anomaly detection).
- You need calibrated probabilities for downstream decision-making or cost-sensitive thresholds.
- You are building a time-series forecasting pipeline where shuffle-CV would leak the future.
- You want to do unsupervised clustering or dimensionality reduction on high-dimensional omics or sensor data.
- You are writing a model card or datasheet for a paper supplementary material.

## Prerequisites

- Python 3.10+
- scikit-learn >= 1.3, pandas >= 2.0, numpy >= 1.24, matplotlib >= 3.7

```bash
pip install scikit-learn pandas numpy matplotlib
# Optional but recommended for science-grade workflows
pip install imbalanced-learn shap sktime darts mlxtend category_encoders
```

Set a fixed seed for reproducibility: `import numpy as np; np.random.seed(42)` and pass `random_state=42` to every estimator and splitter. Record library versions (`pip freeze > requirements.txt`) in the methods section of any paper using these models.

## Core workflows

### Pipeline + ColumnTransformer with cross-validation

Build a single estimator that bundles preprocessing + model so CV cannot leak scaling statistics from validation folds into training folds.

```python
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, GroupKFold

numeric = ["age", "bmi", "glucose"]
categorical = ["sex", "site"]
X = df[numeric + categorical]
y = df["diabetes"]
groups = df["subject_id"]  # multiple rows per subject -> group-aware CV

pre = ColumnTransformer([
    ("num", StandardScaler(), numeric),
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
])
pipe = Pipeline([("pre", pre),
                ("clf", RandomForestClassifier(n_estimators=400, random_state=42))])

cv = GroupKFold(n_splits=5)  # never split a subject across folds
scores = cross_val_score(pipe, X, y, groups=groups, cv=cv, scoring="roc_auc")
print(f"AUC = {scores.mean():.3f} +/- {scores.std():.3f}")
```

### Hyperparameter tuning with nested cross-validation

Nested CV gives an unbiased estimate of generalization after model selection. Inner loop tunes; outer loop scores.

```python
from sklearn.model_selection import GridSearchCV, cross_val_score

param_grid = {"clf__C": [0.1, 1, 10], "clf__gamma": ["scale", "auto"]}
inner = GridSearchCV(pipe, param_grid, cv=5, scoring="roc_auc", n_jobs=-1)
outer_scores = cross_val_score(inner, X, y, groups=groups,
                                cv=GroupKFold(5), scoring="roc_auc")
print(f"nested AUC = {outer_scores.mean():.3f} +/- {outer_scores.std():.3f}")
```

For larger search spaces, swap `GridSearchCV` for `RandomizedSearchCV` or `skopt.BayesSearchCV` to scale.

### Calibrated probabilities and imbalanced classes

```python
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE

imb_pipe = ImbPipeline([
    ("pre", pre),
    ("smote", SMOTE(random_state=42)),
    ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
])
calibrated = CalibratedClassifierCV(imb_pipe, cv=5, method="isotonic")
calibrated.fit(X, y)  # produces calibrated P(y|x) for downstream thresholds
```

Pick `method="sigmoid"` (Platt) for small datasets and `method="isotonic"` for >= 1000 samples.

### SHAP interpretability

```python
import shap
pipe.fit(X, y)
model = pipe.named_steps["clf"]
X_transformed = pipe.named_steps["pre"].transform(X)
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_transformed)
shap.summary_plot(shap_values, X_transformed,
                 feature_names=numeric + ["sex_F", "sex_M", "site_A", "site_B"])
```

For non-tree models, use `shap.KernelExplainer` (slow) or `shap.LinearExplainer` (fast, exact for linear models).

### Time-series forecasting (no future leakage)

```python
from sktime.forecasting.model_selection import ExpandingWindowSplitter
from sktime.forecasting.compose import ForecastingPipeline
from sktime.forecasting.naive import NaiveForecaster
from sktime.forecasting.trend import PolynomialTrendForecaster

cv = ExpandingWindowSplitter(fh=[1, 2, 3], initial_window=60, step_length=1)
pipe = ForecastingPipeline([
    ("trend", PolynomialTrendForecaster(degree=2)),
    ("naive", NaiveForecaster(strategy="drift")),
])
```

Never use `KFold(shuffle=True)` on temporal data; the test fold must always be later than the training fold.

### Unsupervised exploration (PCA, HDBSCAN clustering)

```python
from sklearn.decomposition import PCA
from sklearn.cluster import HDBSCAN  # scikit-learn >= 1.3
from sklearn.metrics import silhouette_score

Z = StandardScaler().fit_transform(X_num)  # X_num = numeric subset of X
coords = PCA(n_components=2, random_state=42).fit_transform(Z)
labels = HDBSCAN(min_cluster_size=15).fit_predict(Z)
print(f"silhouette = {silhouette_score(Z, labels):.3f}, n_clusters = {len(set(labels))}")
```

HDBSCAN returns `-1` for noise; this is a feature, not a bug, for scientific data where most cells may not belong to any cluster.

### Feature selection with leak-free pipelines

Use `SelectFromModel` or recursive feature elimination (RFE) inside a `Pipeline` so selection happens inside each CV fold.

```python
from sklearn.feature_selection import SelectFromModel, RFECV
from sklearn.linear_model import LogisticRegression

select = SelectFromModel(LogisticRegression(penalty="l1", solver="liblinear",
                                            random_state=42), threshold="median")
pipe_fs = Pipeline([("pre", pre),
                   ("select", select),
                   ("clf", LogisticRegression(max_iter=2000, random_state=42))])
scores = cross_val_score(pipe_fs, X, y, groups=groups,
                         cv=GroupKFold(5), scoring="roc_auc")
```

For exhaustive small-feature subset search, use `mlxtend.feature_selection.SequentialFeatureSelector` with `floating=True`.

## Best practices

- Always wrap preprocessing inside a `Pipeline` so CV folds cannot leak scaler/encoder statistics into training.
- Use group-aware splitters (`GroupKFold`, `GroupShuffleSplit`) whenever multiple rows correspond to one experimental unit (subject, plate, field site, time series).
- For spatial data, use spatial CV (blocked or k-folds over spatial tiles) so adjacent pixels/sites do not cross train/test.
- For temporal data, use `TimeSeriesSplit` or `ExpandingWindowSplitter` — never shuffle.
- Report mean +/- std across folds, plus the full fold vector. A single accuracy number is not a result.
- Fix `random_state` on every stochastic component and record library versions in the methods section.
- Prefer calibrated probabilities to hard labels when downstream decisions are cost-sensitive.
- Use nested CV when reporting a final score after hyperparameter search; otherwise the reported score is optimistically biased.
- Always compare against a trivial baseline (majority class, mean, linear regression on raw features) before claiming a model works.
- Write a one-paragraph model card (intended use, training data, limitations, ethical risks) for any model that ships in a paper or product.

## Common pitfalls

- **Scaling before split.** Fitting `StandardScaler` on the whole dataset leaks mean/std into the test set — wrap in a `Pipeline` or use `sklearn.set_config(transform_output="pandas")`.
- **Shuffled CV on grouped or temporal data.** Random `KFold` on data with repeated subjects or time ordering produces wildly optimistic scores. Always specify a CV that respects the structure.
- **Leaky feature engineering.** Aggregations like "subject mean" or "site z-score" that use the target row, or target encoding without CV, leak `y` into `X`.
- **Reporting accuracy on imbalanced data.** 99% accuracy on a 1% positive class is meaningless. Use ROC AUC, PR AUC, F1, or balanced accuracy, and inspect the confusion matrix.
- **Hyperparameter tuning on the test set.** Choosing `C` or `n_estimators` by peeking at the held-out test invalidates the test estimate. Use nested CV or a dedicated validation set.
- **Uncalibrated probabilities.** RandomForest and SVM output scores, not probabilities. Use `CalibratedClassifierCV` before threshold tuning.
- **Missing `class_weight` or resampling on imbalanced data.** Models will predict the majority class and still score high on accuracy.
- **No baseline.** A 0.85 AUC is meaningless if the baseline (logistic regression on 2 features) already gets 0.83.

## Worked example

End-to-end: predict diabetes from a clinical-style tabular dataset, with honest nested CV, calibrated probabilities, and SHAP.

```python
import numpy as np
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.model_selection import (GroupKFold, GridSearchCV,
                                      cross_val_score, train_test_split)
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score
import shap

# Synthetic but realistic shape: 800 patients, 3 sites, 2:1 imbalance
X, y = make_classification(n_samples=800, n_features=10, n_informative=5,
                            n_redundant=2, weights=[0.67, 0.33], random_state=42)
groups = np.random.default_rng(42).integers(0, 3, size=800)  # 3 clinical sites
feature_names = [f"feat_{i}" for i in range(10)]
X = pd.DataFrame(X, columns=feature_names)

pre = ColumnTransformer([("num", StandardScaler(), feature_names)])
base = Pipeline([("pre", pre),
                ("clf", GradientBoostingClassifier(random_state=42))])

param_grid = {"clf__n_estimators": [100, 200], "clf__max_depth": [2, 3]}
inner = GridSearchCV(base, param_grid, cv=GroupKFold(3),
                     scoring="roc_auc", n_jobs=-1)
outer = GroupKFold(3)
nested = cross_val_score(inner, X, y, groups=groups, cv=outer, scoring="roc_auc")
print(f"nested ROC-AUC = {nested.mean():.3f} +/- {nested.std():.3f}")

# Fit final model + calibrate on a held-out split
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2,
                                           stratify=y, random_state=42)
calibrated = CalibratedClassifierCV(base, method="isotonic", cv=5)
calibrated.fit(X_tr, y_tr)
proba = calibrated.predict_proba(X_te)[:, 1]
print(f"held-out AUC = {roc_auc_score(y_te, proba):.3f}")

# SHAP global explanation on the underlying tree model
base.fit(X_tr, y_tr)
explainer = shap.TreeExplainer(base.named_steps["clf"])
shap_vals = explainer.shap_values(base.named_steps["pre"].transform(X_te))
shap.summary_plot(shap_vals, X_te, feature_names=feature_names, show=False)
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| scikit-learn | Canonical estimators, pipelines, CV, calibration | `pip install scikit-learn` |
| pandas | Tabular data handling | `pip install pandas` |
| numpy | Numerical backbone | `pip install numpy` |
| matplotlib | Residual and ROC plots | `pip install matplotlib` |
| imbalanced-learn | SMOTE, class-weighting, resampling pipelines | `pip install imbalanced-learn` |
| shap | Tree and kernel SHAP interpretability | `pip install shap` |
| sktime | Time-series classification and forecasting | `pip install sktime` |
| darts | High-level time-series forecasting | `pip install darts` |
| mlxtend | Stacking, sequential feature selection | `pip install mlxtend` |
| category_encoders | Target / GLMM encoders with CV built in | `pip install category_encoders` |
| scikit-optimize | Bayesian hyperparameter search | `pip install scikit-optimize` |
| yellowbrick | Visual CV and validation diagnostics | `pip install yellowbrick` |

## References

- [scikit-learn user guide](https://scikit-learn.org/stable/user_guide.html)
- [scikit-learn: Combining estimators (Pipeline, ColumnTransformer)](https://scikit-learn.org/stable/modules/compose.html)
- [Varma & Simon: Bias in error estimation when using cross-validation for model selection](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-7-91)
- [Cawley & Talbot: On Over-fitting in Model Selection vs. Subsequent Selection Error](https://www.jmlr.org/papers/volume11/cawley10a/cawley10a.pdf)
- [SHAP documentation](https://shap.readthedocs.io/en/latest/)
- [imbalanced-learn documentation](https://imbalanced-learn.org/stable/)
- [sktime documentation](https://www.sktime.net/en/stable/)
- [Model Cards for Model Reporting (Mitchell et al., 2019)](https://arxiv.org/abs/1810.03777)
- [Datasheets for Datasets (Gebru et al., 2021)](https://arxiv.org/abs/1803.09010)

## Ethics & safety

- **Leakage invalidates results.** A leaked model is not a buggy model, it is a false scientific claim. Treat every CV split as a hypothesis test on generalization.
- **Bias audit.** Measure performance per subgroup (sex, age, site, ancestry). Report subgroup ROC AUC and PR AUC alongside the headline. A model that scores well overall but fails on one subgroup is not deployable.
- **Reproducibility.** Pin versions, set seeds, log the full CV split indices, and publish the model card with the dataset datasheet.
- **Dual-use.** Predictive models for health, criminal justice, employment, or credit carry real-world harm risk. Prefer calibration + decision-threshold audits over accuracy alone, and surface the model card before any deployment.
- **De-identification.** Clinical and genomic training data must be de-identified; never echo real subject IDs in logs, plots, or SHAP summaries. Honor IRB constraints on data reuse across secondary analyses.

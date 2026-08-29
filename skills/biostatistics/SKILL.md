---
name: biostatistics
description: Statistical analysis for biomedical and clinical research using statsmodels, lifelines, PyMC, and ArviZ. Use when computing power and sample size for study design, running t-tests, Mann-Whitney, chi-square, ANOVA, multiple-comparison correction (Bonferroni, FDR Benjamini-Hochberg), survival analysis with Kaplan-Meier and Cox proportional hazards, mixed-effects models with MixedLM, Bayesian inference, bootstrap confidence intervals, or effect sizes like Cohen d and odds ratios.
license: MIT
compatibility: Requires Python 3.10+ with statsmodels, lifelines, scipy, numpy, pandas, matplotlib. Optional extras include pymc, arviz, pingouin, seaborn, biostat-design.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Machine Learning & Statistics
---

# Biostatistics

## Overview

Biostatistics underpins every clinical trial, epidemiological cohort, omics-wide association, and meta-analysis. The discipline is rigid on three things the broader ML community often skips: (1) **study design before data** — power and sample-size calculations are done before recruitment, not after; (2) **honest multiplicity** — testing 10,000 SNPs at p=0.05 yields ~500 false positives by definition, so multiple-comparison correction is non-negotiable; and (3) **time-to-event and hierarchical structure** — survival data is censored, cohorts are clustered by site / subject / family, and naive regression on these designs is invalid.

This skill covers the canonical biostatistics workflow: study design and power with `statsmodels`, hypothesis testing (t-test, Mann-Whitney, chi-square, ANOVA) with `scipy.stats` and `statsmodels`, multiple-comparison correction (Bonferroni, Holm, Benjamini-Hochberg FDR), survival analysis (Kaplan-Meier, log-rank, Cox PH) with `lifelines`, mixed-effects models with `statsmodels.MixedLM`, Bayesian inference with `PyMC` + `ArviZ`, bootstrap confidence intervals, effect sizes (Cohen's d, odds ratio, hazard ratio), and PRISMA-style meta-analysis.

## When to use this skill

- You are designing a trial or cohort study and need power / sample-size calculations before recruitment.
- You are comparing two or more groups with t-test, Mann-Whitney, ANOVA, or chi-square.
- You ran many tests (e.g., GWAS, DE genes, brain voxels) and need multiple-comparison correction.
- You have censored time-to-event data (recurrence, death, progression) and need Kaplan-Meier curves, log-rank tests, or Cox proportional hazards models.
- Your data is hierarchical (repeated measures, multi-site, family) and you need mixed-effects models.
- You want Bayesian credible intervals instead of frequentist p-values.
- You need bootstrap CIs for a non-standard estimator (e.g., AUC of a custom score).
- You need to report effect sizes (Cohen's d, odds ratio, hazard ratio) alongside p-values.
- You are conducting a meta-analysis and following PRISMA reporting guidelines.

## Prerequisites

- Python 3.10+
- statsmodels >= 0.14, lifelines >= 0.28, scipy >= 1.11, numpy, pandas, matplotlib

```bash
pip install statsmodels lifelines scipy numpy pandas matplotlib
# Optional
pip install pymc arviz pingouin seaborn biostat-design
```

## Core workflows

### Power and sample size for study design

```python
from statsmodels.stats.power import TTestIndPower, GofChisquarePower
import numpy as np

# Two-sample t-test: detect d=0.5 at alpha=0.05, power=0.80
analysis = TTestIndPower()
n_per_group = analysis.solve_power(effect_size=0.5, alpha=0.05, power=0.80)
print(f"need {np.ceil(n_per_group)} subjects per arm")   # ~64

# Power curve for a range of effect sizes
es = np.linspace(0.1, 1.0, 20)
for d in [0.2, 0.5, 0.8]:
    pwr = [analysis.power(d, nobs=64, alpha=0.05) for _ in es]
```

### Hypothesis tests and effect sizes

```python
import numpy as np
from scipy import stats
from statsmodels.stats.weightstats import ttest_ind

# Two-sample t-test with effect size (Cohen's d)
x = np.array([...]); y = np.array([...])
t, p = stats.ttest_ind(x, y, equal_var=False)
d = (x.mean() - y.mean()) / np.sqrt((x.std(ddof=1) ** 2 + y.std(ddof=1) ** 2) / 2)

# Non-parametric alternative
u, p_mw = stats.mannwhitneyu(x, y, alternative="two-sided")

# Chi-square for a 2x2 contingency table
table = np.array([[30, 10], [20, 40]])
chi2, p_chi, dof, exp = stats.chi2_contingency(table)
odds_ratio = (table[0, 0] * table[1, 1]) / (table[0, 1] * table[1, 0])
```

### Multiple-comparison correction (Bonferroni, FDR)

```python
from statsmodels.stats.multitest import multipletests
import numpy as np

pvals = np.array([0.001, 0.04, 0.03, 0.20, 0.012, 0.005, 0.45, 0.025])
# Bonferroni: alpha / m
_, p_bonf, _, _ = multipletests(pvals, alpha=0.05, method="bonferroni")
# Benjamini-Hochberg FDR
_, p_fdr, _, _ = multipletests(pvals, alpha=0.05, method="fdr_bh")
print(f"BH-rejected at FDR<0.05: {(p_fdr < 0.05).sum()} tests")
```

Prefer FDR (Benjamini-Hochberg) over Bonferroni in omics (genomics, proteomics, neuroimaging) — Bonferroni is too conservative when tests are correlated and hypotheses are exploratory.

### Survival analysis with lifelines

```python
import pandas as pd
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test

df = pd.read_csv("survival.csv")  # columns: time, event, arm
kmf = KaplanMeierFitter()
for arm, sub in df.groupby("arm"):
    kmf.fit(sub["time"], sub["event"], label=str(arm))
    kmf.plot_survival_function()

# Log-rank test between two arms
g0 = df[df.arm == 0]; g1 = df[df.arm == 1]
result = logrank_test(g0["time"], g1["time"], g0["event"], g1["event"])
print(f"log-rank p = {result.p_value:.4f}")

# Cox proportional hazards
cph = CoxPHFitter()
cph.fit(df[["time", "event", "age", "treatment"]], "time", "event")
cph.print_summary()
```

Check the proportional hazards assumption with `cph.check_assumptions(df, show_plots=True)` before reporting the hazard ratio.

### Mixed-effects models with statsmodels

```python
import statsmodels.api as sm
import statsmodels.formula.api as smf

# Random intercept for repeated measures per subject
md = smf.mixedlm("response ~ treatment + age", df,
                 groups=df["subject_id"], re_formula="1")
mdf = md.fit()
print(mdf.summary())
```

For nested random effects (e.g., measurement within subject within site) use `vc_formula` for variance components.

### Bootstrap confidence intervals

For non-standard estimators (AUC, ratio of means, custom score), bootstrap CIs are often easier and more honest than asymptotic formulas.

```python
import numpy as np

def auc(y_true, y_score):
    order = np.argsort(-y_score); yt = y_true[order]
    tps = np.cumsum(yt); fps = np.cumsum(1 - yt)
    tpr = tps / tps[-1]; fpr = fps / fps[-1]
    return np.trapz(tpr, fpr)

rng = np.random.default_rng(42)
B = 2000
y_true = np.r_[np.zeros(50), np.ones(50)].astype(int)
y_score = np.r_[rng.normal(0.3, 1, 50), rng.normal(0.8, 1, 50)]
boots = [auc(y_true[rng.integers(0, 100, 100)],
             y_score[rng.integers(0, 100, 100)]) for _ in range(B)]
ci = (np.percentile(boots, 2.5), np.percentile(boots, 97.5))
print(f"AUC = {auc(y_true, y_score):.3f}, 95% bootstrap CI = {ci}")
```

### Bayesian inference with PyMC and ArviZ

```python
import pymc as pm
import arviz as az
import numpy as np

# Beta-Binomial model: estimate a single proportion
rng = np.random.default_rng(0)
n = 80; x = rng.binomial(n, 0.3)  # observed
with pm.Model() as m:
    p = pm.Beta("p", alpha=1, beta=1)        # uniform prior
    obs = pm.Binomial("obs", n=n, p=p, observed=x)
    trace = pm.sample(2000, tune=1000, chains=4, target_accept=0.95, random_seed=42)
az.summary(trace)
az.plot_posterior(trace, var_names=["p"], hdi_prob=0.95)
```

Always check `R-hat < 1.01`, `ESS > 400`, and no divergences before reporting posterior summaries.

## Best practices

- Pre-register your primary outcome and sample size before data collection. A power analysis after seeing the data is not a power analysis.
- Report effect sizes (Cohen's d, odds ratio, hazard ratio) with 95% CIs, not just p-values.
- Use FDR (Benjamini-Hochberg) over Bonferroni for omics — Bonferroni is too conservative when tests are correlated.
- Check Cox PH assumptions before reporting hazard ratios; for non-proportional hazards, switch to time-varying coefficients or stratified Cox.
- For non-normal data, prefer Mann-Whitney / Kruskal-Wallis / permutation tests; for small samples, prefer bootstrap CIs over asymptotic ones.
- Always report the test, the statistic, the degrees of freedom, the p-value, and the effect size: e.g., `t(62)=2.31, p=0.024, d=0.58`.
- Use mixed-effects models (not averaging within subject) for repeated measures — averaging discards within-subject signal and inflates Type I error.
- For meta-analysis, follow PRISMA: flow diagram, risk-of-bias assessment (RoB 2 for RCTs, ROBINS-I for non-randomized), funnel plot asymmetry, and heterogeneity (I-squared, Q-test).

## Common pitfalls

- **No power analysis before recruitment.** Underpowered studies cannot detect real effects and inflate false negatives; overpowered studies waste resources.
- **Multiple testing without correction.** Testing 10,000 SNPs at alpha=0.05 yields ~500 false positives by chance alone.
- **Parametric test on non-normal data.** t-tests assume approximate normality; on heavily skewed or ordinal data, use Mann-Whitney / Wilcoxon / Kruskal-Wallis.
- **Ignoring censoring.** Computing "median survival" by averaging observed times ignores censored subjects; use Kaplan-Meier.
- **Averaging repeated measures.** Collapsing multiple observations per subject loses the within-subject signal and breaks independence.
- **Treating HR > 1 as "large effect."** Hazard ratios are multiplicative; a HR of 1.5 means a 50% increase in hazard, but the absolute risk reduction depends on the baseline rate.
- **Unadjusted funnel plot asymmetry** as evidence of publication bias — it can also reflect real heterogeneity; use Egger's test and trim-and-fill sensitivity.
- **P-hacking.** Running many tests and reporting only the significant one is research misconduct; pre-registration solves this.

## Worked example

End-to-end analysis of a two-arm survival trial: power calculation, log-rank test, Cox model, and forest plot of the hazard ratio.

```python
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from statsmodels.stats.power import TTestIndPower
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test

rng = np.random.default_rng(42)
N = 120
arm = rng.integers(0, 2, N)
# Exponential baseline hazard, treatment effect ~ HR=0.65
true_beta = -0.43
hazard = 0.05 * np.exp(true_beta * arm + 0.02 * rng.normal(60, 10, N) / 10)
time = rng.exponential(1 / hazard)
event = rng.random(N) < 0.9   # 90% event rate
df = pd.DataFrame({"time": time, "event": event.astype(int),
                   "arm": arm, "age": rng.normal(60, 10, N)})

kmf = KaplanMeierFitter()
fig, ax = plt.subplots()
for a, sub in df.groupby("arm"):
    kmf.fit(sub["time"], sub["event"], label=f"arm {a}")
    kmf.plot_survival_function(ax=ax)
ax.set_title("Kaplan-Meier survival by arm")

g0 = df[df.arm == 0]; g1 = df[df.arm == 1]
res = logrank_test(g0["time"], g1["time"], g0["event"], g1["event"])
print(f"log-rank p = {res.p_value:.4f}")

cph = CoxPHFitter()
cph.fit(df[["time", "event", "arm", "age"]], "time", "event")
cph.print_summary()
hr = np.exp(cph.params_["arm"])
ci = np.exp(cph.confidence_intervals_.loc["arm"])
print(f"treatment HR = {hr:.2f} (95% CI {ci.iloc[0]:.2f}-{ci.iloc[1]:.2f})")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| statsmodels | Power analysis, GLM, MixedLM, multiple comparisons | `pip install statsmodels` |
| lifelines | Kaplan-Meier, Cox PH, log-rank, AFT models | `pip install lifelines` |
| scipy.stats | t-test, Mann-Whitney, chi-square, distributions | `pip install scipy` |
| PyMC | Bayesian hierarchical modeling, MCMC | `pip install pymc` |
| ArviZ | Bayesian diagnostics (R-hat, ESS, posterior plots) | `pip install arviz` |
| pingouin | Effect sizes, ANOVA, partial correlations, bayes factors | `pip install pingouin` |
| seaborn | Survival and distribution plots | `pip install seaborn` |
| numpy | Numerical backbone | `pip install numpy` |
| pandas | Cohort data wrangling | `pip install pandas` |
| matplotlib | Kaplan-Meier and forest plots | `pip install matplotlib` |
| biostat-design | Specialized trial design utilities | `pip install biostat-design` |
| scikit-posthocs | Post-hoc tests (Dunn, Nemenyi, Conover) | `pip install scikit-posthocs` |

## References

- [statsmodels documentation](https://www.statsmodels.org/stable/index.html)
- [lifelines documentation](https://lifelines.readthedocs.io/en/latest/)
- [PyMC documentation](https://www.pymc.io/welcome.html)
- [ArviZ documentation](https://python.arviz.org/en/latest/)
- [Benjamini & Hochberg (1995) — Controlling the FDR](https://www.jstor.org/stable/2346101)
- [PRISMA 2020 statement](https://www.prisma-statement.org/)
- [Cohen, J. (1988) — Statistical Power Analysis for the Behavioral Sciences](https://www.routledge.com/9780805802823)
- [Hernan & Robins — Causal Inference: What If](https://www.hsph.harvard.edu/miguel-hernan/causal-inference-book/)
- [ROBINS-I tool for non-randomized studies](https://www.riskofbias.info/welcome/robins-i-tool)

## Ethics & safety

- **Pre-registration.** Pre-register primary outcomes and sample size on ClinicalTrials.gov or OSF before enrollment. Post-hoc re-analysis must be clearly labeled as exploratory.
- **De-identification.** Never include real patient identifiers, birth dates, or geocoded addresses in published summary tables or supplementary data.
- **Multiplicity.** Report the full set of tests you ran, not just significant ones. Selective reporting is research misconduct.
- **Causal claims.** Observational cohort data does not support causal language ("X causes Y"); use "X is associated with Y" and discuss confounders.
- **Equipoise in trials.** Clinical equipoise must hold before randomizing patients; do not assist with trials where one arm is known-inferior.
- **Risk-of-bias reporting.** For meta-analyses, report RoB 2 (RCTs) or ROBINS-I (non-randomized) for every included study. Do not silently aggregate biased evidence.
- **Equity.** Report subgroup analyses by sex, age, and ancestry where possible; flag under-powered subgroup tests as exploratory.

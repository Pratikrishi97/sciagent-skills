---
name: epidemiology
description: Infectious-disease epidemiology toolkit covering compartmental SIR/SEIR models with scipy, real-time effective reproduction number (Rt) estimation with EpiNow2, outbreak detection, case surveillance analysis, vaccine efficacy, survival methods in epidemiology, meta-analysis with pymeta, and geospatial epidemiology. Use this skill whenever the user asks about SIR, SEIR, R0, Rt, EpiNow2, outbreak detection, case surveillance, vaccine efficacy, meta-analysis, or geospatial mapping of disease. Trigger keywords include SIR, SEIR, R0, Rt, EpiNow2, COVID-19, GISAID, surveillance, vaccine efficacy, Kaplan-Meier, PyMeta, geospatial epi, CDC PLACES, Our World in Data.
license: MIT
compatibility: Requires Python 3.10+ with scipy, numpy, pandas, pymare, geopandas. Optional: rpy2 for EpiNow2/epinow2 (R package); pymeta for meta-analysis; epiweeks for MMWR week handling.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Clinical & Medical Research
---

# Epidemiology

## Overview

Epidemiology quantifies how diseases spread through populations and how
interventions (vaccines, NPIs, treatments) reduce burden. The computational
toolbox spans (1) **compartmental models** (SIR, SEIR, SEIR+V) formulated as
ODEs and integrated with scipy; (2) **real-time Rt estimation** using
EpiNow2 (R) or its Python ports, which combines reported case counts with
the generation time distribution to estimate the effective reproduction
number; (3) **outbreak detection** on case surveillance series
(CUSUM, Farrington, Bayesian aberration detection); (4) **vaccine efficacy**
estimation with Kaplan-Meier and Cox PH on phase III trial data; (5)
**meta-analysis** with pymeta; and (6) **geospatial epidemiology** with
geopandas, areal smoothing, and cluster detection.

This skill wires scipy, pymare/pymeta, geopandas, and (optionally) EpiNow2
via rpy2 to produce report-ready epi analysis.

## When to use this skill

- User asks about **SIR/SEIR**, **R0**, **Rt**, **flattening the curve**.
- User mentions **EpiNow2**, **epinow2**, **EpiEstim**, **generation time**.
- User asks for **outbreak detection** or **aberration detection** in case
  surveillance time series.
- User asks for **vaccine efficacy** or **incidence rate ratio**.
- User wants a **meta-analysis** of effect sizes across studies.
- User asks for **geospatial mapping** of disease incidence or prevalence.
- User mentions **CDC PLACES**, **Our World in Data**, **WHO**, **GISAID**.
- Skip for: clinical trial design and CDISC submissions (use
  `clinical-research`), medical-image analysis (use `medical-imaging`),
  de-identification of clinical text (use `clinical-nlp`).

## Prerequisites

- Python 3.10+ (3.11 recommended).
- System tools: `R` (3.6+) with the `EpiNow2`, `EpiEstim`, and `metafor`
  packages for the gold-standard Rt and meta-analysis workflows.
- Python packages:

```bash
pip install scipy numpy pandas pymare geopandas matplotlib seaborn
pip install epiweeks statsmodels lifelines
# Optional: rpy2 for R interop; pymeta as an alternative meta-analysis lib
```

- Data sources: Our World in Data (open, CSV), CDC PLACES (open), WHO
  case counts (open), GISAID (registered access for genomic epi).

## Core workflows

### SIR/SEIR with scipy

Integrate a deterministic SEIR model.

```python
import numpy as np
from scipy.integrate import odeint

def seir(y, t, beta, sigma, gamma, n):
    s, e, i, r = y
    ds = -beta * s * i / n
    de = beta * s * i / n - sigma * e
    di = sigma * e - gamma * i
    dr = gamma * i
    return ds, de, di, dr

n = 1_000_000
beta, sigma, gamma = 0.4, 1/4.0, 1/5.0   # contact rate, incubation, infectious
i0 = 100
t = np.arange(0, 120)
sol = odeint(seir, (n - i0, 0, i0, 0), t, args=(beta, sigma, gamma, n))
s, e, i, r = sol.T
print(f"peak day {np.argmax(i)}, peak cases {int(i.max())}")
print(f"final recovered {int(r[-1])} / {n}")
```

### Real-time Rt with EpiNow2 (via rpy2)

Estimate the time-varying reproduction number from daily reported cases.

```python
import rpy2.robjects as ro
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri
import pandas as pd

epinow2 = importr("EpiNow2")
pandas2ri.activate()

cases = pd.DataFrame({
    "date": pd.date_range("2024-01-01", periods=60, freq="D"),
    "confirm": [int(max(0, np.random.poisson(50 * (1 + 0.1 * np.sin(d / 7))))
                    ) for d in range(60)],
})
r_cases = pandas2ri.py2rpy(cases)
# Generation time (log-normal mean 5.2, sd 4.0) + reporting delay
gt = epinow2.gamma_dist_args(5.2, 4.0)
out = epinow2.epinow(
    r_cases, generation_time=epinow2.generation_time_opts(
        epinow2.gamma_dist(gt[0], gt[1], gt[2], gt[3], gt[4])),
    rt_opts=epinow2.rt_opts(), horizon=14)
print(out)  # Rt median, 90% CI per day
```

### Outbreak detection on case surveillance

Run the Farrington algorithm (or its improved variant) on weekly counts.

```python
import numpy as np, pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

# Farrington-style aberration: compare current week to baseline
def farrington(history: np.ndarray, current: int, alpha=0.05):
    """Use a quasi-Poisson GLM on past 5 years."""
    import statsmodels.api as sm
    past = history[-52 * 5:]  # last 5 years of weeks
    X = sm.add_constant(np.arange(len(past)))
    model = sm.GLM(past, X, family=sm.families.Poisson()).fit()
    mu, phi = model.predict([1, len(past)])[0], model.pearson_chi2 / model.df_resid
    threshold = mu * (1 + 2 / 3 * 1.96 * np.sqrt(phi / mu))
    return {"expected": round(mu, 1), "threshold": round(threshold, 1),
            "alert": current > threshold}

weekly = np.random.poisson(20, 52 * 5 + 1)
weekly[-1] = 50  # spike
print(farrington(weekly[:-1], weekly[-1]))
```

### Vaccine efficacy with Kaplan-Meier and Cox PH

Estimate VE from a phase III trial endpoint (time to symptomatic infection).

```python
import pandas as pd, lifelines
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test

df = pd.read_csv("vaccine_trial.csv")  # time, event, arm (vaccine/placebo)

# VE = 1 - hazard ratio (vaccine vs placebo)
cph = CoxPHFitter()
cph.fit(df, "time", "event")
hr = cph.summary.loc["arm", "exp(coef)"]
ve = (1 - hr) * 100
print(f"VE = {ve:.1f}%  (95% CI "
      f"{(1 - cph.confidence_intervals_.loc['arm','95% upper-bound']) * 100:.1f}-"
      f"{(1 - cph.confidence_intervals_.loc['arm','95% lower-bound']) * 100:.1f}%)")
```

### Meta-analysis with pymeta

Aggregate effect sizes across published studies (random-effects model).

```python
import numpy as np, pymare
from pymare import datasets
from pymare.estimators import DerSimonianLaird

# Example: 5 studies, effect (log OR) + SE
effect = np.array([[0.30], [0.45], [0.20], [0.55], [0.38]])
se = np.array([[0.12], [0.10], [0.15], [0.13], [0.11]])
var = se ** 2
data = pymare.Dataset(y=effect, v=var)
dsl = DerSimonianLaird()
dsl.fit(data)
print(f"pooled effect = {dsl.params_['mean']:.3f} +/- {dsl.params_['sd']:.3f}")
```

### Geospatial epidemiology

Map disease incidence by county and compute smoothed rates.

```python
import geopandas as gpd, pandas as pd, matplotlib.pyplot as plt

shape = gpd.read_file("us_counties.shp")
cases = pd.read_csv("county_cases.csv")  # FIPS, cases, population
gdf = shape.merge(cases, on="FIPS")
gdf["rate_per_100k"] = gdf.cases / gdf.population * 100_000

# Smoothed (empirical Bayes) rates
import numpy as np
mu = gdf.cases.sum() / gdf.population.sum() * 1e5
gdf["smoothed"] = (
    (gdf.cases / (gdf.cases + 100)) * gdf.rate_per_100k +
    (100 / (gdf.cases + 100)) * mu)

fig, ax = plt.subplots(figsize=(10, 6))
gdf.plot(column="smoothed", cmap="YlOrRd", legend=True, ax=ax)
ax.set_axis_off(); plt.savefig("incidence_map.png", dpi=160, bbox_inches="tight")
```

## Best practices

- **Calibrate** SIR/SEIR parameters against observed early-growth data; do
  not assume R0=3 for all pathogens (flu 1.3, measles 12-18, SARS-CoV-2
  original 2.5-3, Omicron 5-7).
- Report Rt with **credible intervals**; EpiNow2 outputs the 90% and 50%
  CrI by default - both are useful.
- For outbreak detection, use **5 years of historical baseline** and a
  7-week exclusion window around holidays; shorter baselines over-alert.
- For vaccine efficacy, use the **per-protocol primary analysis** (early
  after dose 2) and the **intention-to-treat secondary** (entire follow-up);
  report both, with VE waning curves.
- In meta-analysis, always do **heterogeneity** (Cochran's Q, I-squared)
  and **leave-one-out** sensitivity; report if I^2 > 50%.
- For geospatial rates, smooth with **empirical Bayes** or **spatial
  smoothing** to avoid noisy rare-event rates in low-pop counties.
- Use **MMWR weeks** (Sunday-Saturday, week 1 is first week with 4+ days
  in January) consistently across the analysis; ISO weeks differ by +/-1.
- Sequence data in **GISAID** must cite the originating lab and the
  submitting lab in any derivative publication; failure to do so is a
  GISAID access-policy violation.
- Pre-register **epidemiological analyses** with the WHO ICTRP and the
  PROSPERO systematic-review registry.

## Common pitfalls

- Estimating Rt with a **fixed generation time** when the pathogen has
  evolving variants (Omicron BA.1 vs BA.5 differ); update generation time
  with each wave.
- Using **moving-average** smoothing on case counts as if it removes
  reporting delay - it doesn't; EpiNow2 / EpiEstim accounts for the
  delay distribution.
- Treating the per-protocol VE as the headline when the trial has
  substantial non-compliance; pre-specified primary analysis is ITT.
- **Simpson's paradox**: aggregated VE across strata can flip sign vs
  stratum-specific estimates; always report stratified (age, comorbidity).
- Meta-analysis with **publication bias**: generate a funnel plot and
  Egger test before trusting pooled effects.
- Geospatial mapping without **population denominators**; raw case counts
  are dominated by city size, not risk.
- Forgetting **right-censoring**: recent weeks' case counts are
  incomplete; use nowcasting or trim the last 7-14 days.
- Reporting **excess deaths** without a baseline of expected mortality;
  regression on 2015-2019 is standard.

## Worked example

Goal: estimate Rt for a city's case time series, run Farrington aberration
detection, and produce a simple vaccine-efficacy point estimate.

```python
import numpy as np, pandas as pd
from scipy.integrate import odeint
from lifelines import CoxPHFitter

# 1) Simulate SEIR-like case series
np.random.seed(7); n_days = 120
true_rt = np.where(np.arange(n_days) < 30, 2.5, 1.2)
gen_time = 5.0
cases = np.zeros(n_days); cases[0] = 10
for t in range(1, n_days):
    infections = sum(cases[s] * (true_rt[t] ** (1 / gen_time))
                    * np.exp(-(t - s) / 10) for s in range(max(0, t - 21), t))
    cases[t] = max(0, np.random.poisson(infections * 0.1))
df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=n_days),
                   "cases": cases})
print("total cases:", int(cases.sum()))

# 2) Farrington on last week vs last 5 years-equivalent baseline
from statsmodels.tsa.holtwinters import ExponentialSmoothing
fit = ExponentialSmoothing(cases[:-1], trend=None,
                            seasonal=None).fit()
fc = fit.forecast(1)
alert = cases[-1] > fc.values[0] * 1.5
print(f"last week: {cases[-1]}, expected {fc.values[0]:.0f}, alert={alert}")

# 3) Vaccine efficacy
trial = pd.read_csv("vaccine_trial.csv")
cph = CoxPHFitter()
cph.fit(trial, "time", "event")
hr = cph.summary.loc["arm", "exp(coef)"]
print(f"VE = {(1 - hr) * 100:.1f}%")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| scipy | ODE integration for SIR/SEIR | `pip install scipy` |
| numpy / pandas | Series manipulation | `pip install numpy pandas` |
| EpiNow2 (R) | Real-time Rt + nowcasting | via `rpy2` + `install.packages("EpiNow2")` |
| EpiEstim (R) | Rt estimation (Cori method) | via rpy2 |
| pymare / pymeta | Meta-analysis (random effects) | `pip install pymare` |
| lifelines | Survival analysis (VE, KM) | `pip install lifelines` |
| geopandas | Areal/geospatial epi | `pip install geopandas` |
| epiweeks | MMWR week handling | `pip install epiweeks` |
| Our World in Data | Open case/vaccine data | https://github.com/owid |
| CDC PLACES | Local prevalence (US) | https://www.cdc.gov/places |
| GISAID | Genomic surveillance (registered) | https://www.gisaid.org |

## References

- EpiNow2 paper: https://doi.org/10.12688/wellcomeopenres.16055.2
- EpiEstim (Cori) paper: https://doi.org/10.1093/aje/kwt133
- Farrington aberration: https://doi.org/10.1093/ije/25.2.490
- pymare docs: https://neurostuff.github.io/pymare/
- Our World in Data: https://ourworldindata.org/coronavirus
- WHO global surveillance: https://www.who.int/data
- CDC PLACES: https://www.cdc.gov/places/
- GISAID hCov19 acknowledgments: https://www.gisaid.org/

## Ethics & safety

- Epidemiological analyses influence **public health decisions**; report
  with explicit uncertainty and never claim certainty in Rt or R0 estimates.
- For outbreak **response data**, honor the originating institution's
  data-sharing agreement; do not redistribute case counts outside the
  agreed scope (e.g. CDC redistricted line lists).
- **GISAID** sequences are not open data - they are governed by the GISAID
  Data Access Agreement; cite originating and submitting labs in any
  downstream publication. Failure to do so is a serious scientific
  misconduct issue.
- Vaccine-efficacy analysis must reflect the **pre-specified SAP**; do not
  cherry-pick subgroups; pre-registration protects both subjects and readers.
- Avoid **stigmatizing geographic labels** ("country X virus"); use
  pathogen naming conventions (B.1.1.529, BA.5, JN.1) per WHO best
  practices.
- For contact-tracing data, adhere to the local public-health privacy
  regime; never log identifiable contacts in shared analyses.
- Geospatial analyses of small-area disease can **re-identify individuals**
  in low-population areas; suppress cells with denominator < 5.

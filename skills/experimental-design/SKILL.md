---
name: experimental-design
description: Plan and analyze experiments with design of experiments (DOE) using pyDOE2/dexpy, response surface methodology, power analysis and sample-size calculations with statsmodels, and Bayesian optimization with BoTorch. Use when sizing an A/B test, building a fractional factorial, fitting a response surface, or running a sequential design.
license: MIT
compatibility: Requires Python 3.10+ with numpy, pandas, statsmodels, pyDOE2. Optional: dexpy, botorch, gpytorch for Bayesian optimization.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Lab & Automation
---

# Experimental Design

## Overview

Good experimental design (DOE) lets you ask the right question of the data
before you collect it. This skill covers full/fractional factorial designs,
Box-Behnken and central composite designs for response surface methodology
(RSM), sample-size and power calculations, randomization with blocking and
confounding, and sequential designs via Bayesian optimization with BoTorch.
The unifying statistical framing is: pre-register the design, collect data
per the randomization, then analyze with an OLS / mixed-effects model that
matches the design structure. Anything else is observational data dressed up
as an experiment.

## When to use this skill

- You are sizing an A/B test, clinical trial, or lab study.
- You are fitting a response surface to find an optimum.
- You need a fractional factorial to screen many factors with few runs.
- You are building a sequential design (Bayesian optimization) for an
  expensive black-box function.
- You are pre-registering a design and writing the analysis plan.

## Prerequisites

- Python 3.10+
- Core: `numpy`, `pandas`, `scipy`, `statsmodels`, `pyDOE2`
- Optional: `dexpy`, `botorch`, `gpytorch`, `matplotlib` (for diagnostics)
- System: none
- pip install:
  ```bash
  pip install numpy pandas scipy statsmodels pyDOE2
  pip install dexpy botorch gpytorch matplotlib
  ```

## Core workflows

### 1. Full factorial design with pyDOE2

```python
from pyDOE2 import fullfact
import pandas as pd

# 3 factors: A (2 levels), B (2 levels), C (3 levels)
design = fullfact([2, 2, 3])
df = pd.DataFrame(design, columns=["A", "B", "C"])
df = df.astype(int)
# Randomize run order
df = df.sample(frac=1, random_state=42).reset_index(drop=True)
df["run_order"] = df.index + 1
```

### 2. Central composite design (response surface)

```python
from pyDOE2 import ccdesign
import numpy as np

# 3 factors, face-centered (alpha=1) for a bounded region
coded = ccdesign(3, face="ccf")
# Decode to natural units: x in [-1, 1] -> [low, high]
bounds = {"T": (60, 100), "pH": (5, 7), "conc": (10, 50)}
natural = np.zeros_like(coded)
for j, (lo, hi) in enumerate(bounds.values()):
    natural[:, j] = lo + (coded[:, j] + 1) * 0.5 * (hi - lo)
```

### 3. Power analysis with statsmodels

```python
from statsmodels.stats.power import TTestIndPower, FTestAnovaPower

# Sample size for two-sample t-test, d=0.5, alpha=0.05, power=0.8
analysis = TTestIndPower()
n = analysis.solve_power(effect_size=0.5, alpha=0.05, power=0.80)
print(f"n per group: {n:.1f}")  # ~64

# Power of a one-way ANOVA with k=4 groups, n=20/group, f=0.25
p = FTestAnovaPower().solve_power(effect_size=0.25, nobs=20, alpha=0.05,
                                  k_groups=4)
print(f"ANOVA power: {p:.2f}")
```

### 4. Analyze a factorial with OLS

```python
import pandas as pd
import statsmodels.formula.api as smf
import statsmodels.api as sm

# df has columns: A, B, y (numeric, A/B coded -1/+1)
df = pd.DataFrame({
    "A": [-1, -1, 1, 1] * 4,
    "B": [-1, 1, -1, 1] * 4,
    "y": [10, 14, 18, 22, 9, 13, 19, 23, 11, 15, 17, 21, 10, 14, 18, 22],
})
model = smf.ols("y ~ A * B", data=df).fit()
print(model.summary())
```

### 5. Bayesian optimization with BoTorch

```python
import torch
from botorch.models import SingleTaskGP
from botorch.fit import fit_gpytorch_model
from botorch.acquisition import ExpectedImprovement
from botorch.optim import optimize_acqf
from gpytorch.mlls import ExactMarginalLogLikelihood
from botorch.utils.transforms import normalize, unnormalize

bounds = torch.tensor([[0.0], [10.0]], dtype=torch.double)
# Pretend we have 5 evaluations
train_X = torch.linspace(0, 10, 5, dtype=torch.double).unsqueeze(-1)
train_Y = -((train_X - 4) ** 2)  # maximize the negative (i.e. minimize x-4)^2

gp = SingleTaskGP(normalize(train_X, bounds), train_Y)
mll = ExactMarginalLogLikelihood(gp.likelihood, gp)
fit_gpytorch_model(mll)

EI = ExpectedImprovement(gp, best_f=train_Y.max(), maximize=True)
candidate, _ = optimize_acqf(EI, bounds=bounds, q=1, num_restarts=5, raw_samples=20)
next_x = unnormalize(candidate, bounds)
print(f"Next trial at x = {next_x.item():.2f}")
```

## Best practices

- Pre-register the design and analysis plan before collecting any data.
- Always randomize run order; never run in standard order (leaves time
  drift confounded with factor effects).
- Block on known nuisance variables (operator, day, plate).
- Use coded units (-1, +1) for analysis; decode to natural units only for
  the final report.
- Size for the smallest effect you care about, not the effect you hope for.
- Match the analysis model to the design (e.g. random effects for blocks).
- Prefer center points over 3-level factors to test curvature cheaply.
- For sequential designs, decay exploration over time (EI -> PI).
- Report effects with 95% CIs, never only p-values.
- Use power simulations (Monte Carlo) when closed-form power is unavailable.

## Common pitfalls

- Using `fullfact` in standard order without `sample(frac=1)` leaves time
  drift confounded with factors; reviewers will reject.
- Sample-size calculations with effect_size picked post-hoc ("the effect
  we saw") inflates false positives.
- Forgetting to center and scale continuous factors makes main effects
  uninterpretable and breaks interaction terms.
- Treating a Box-Behnken design as a factorial; it has no corner points and
  cannot detect pure quadratic effects well.
- Bayesian optimization with too few initial points and high noise gives
  the GP pathological uncertainty; use 2-3 per dimension minimum.
- Confounding in fractional designs (e.g. resolution III for two-factor
  interactions) is silently set by the alias structure; check the design
  generators before analyzing.
- Pooling center points into the model breaks the curvature estimate; keep
  them separate.
- Power analysis in Python defaults differ across libraries (effect_size
  convention f vs d); double-check definitions.

## Worked example

Design a 2^3 full factorial with 3 center points per condition, run in
randomized order, analyze with OLS, and detect curvature.

```python
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from pyDOE2 import fullfact

rng = np.random.default_rng(20240601)

# 2^3 factorial in coded units
coded = fullfact([2, 2, 2]).astype(int)
coded = pd.DataFrame(coded, columns=["A", "B", "C"]) * 2 - 1  # -> {-1, +1}

# Add 3 center points
center = pd.DataFrame(np.zeros((3, 3)), columns=coded.columns)

df = pd.concat([coded, center], ignore_index=True)
df["y"] = (10 + 2 * df["A"] + 3 * df["B"] + 1.5 * df["A"] * df["B"]
           + 1.5 * (df["A"] ** 2)  # curvature
           + rng.normal(0, 0.5, size=len(df)))
df = df.sample(frac=1, random_state=20240601).reset_index(drop=True)
df["run_order"] = df.index + 1

# Quadratic model captures curvature
df["A2"] = df["A"] ** 2
df["B2"] = df["B"] ** 2
model = smf.ols("y ~ A + B + C + A:B + A2 + B2", data=df).fit()
print(model.summary())
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| numpy | Numeric core | `pip install numpy` |
| pandas | Design tables | `pip install pandas` |
| scipy | Distributions and tests | `pip install scipy` |
| statsmodels | Power, OLS, mixed models | `pip install statsmodels` |
| pyDOE2 | Factorial, CCD, Box-Behnken | `pip install pyDOE2` |
| dexpy | Living-stat DOE library | `pip install dexpy` |
| botorch | Bayesian optimization | `pip install botorch` |
| gpytorch | Gaussian processes | `pip install gpytorch` |
| matplotlib | Diagnostic plots | `pip install matplotlib` |
| pyDOE (legacy) | Original pyDOE | `pip install pyDOE` |
| Formulaic | alt formula API | `pip install formulaic` |

## References

- statsmodels power module: https://www.statsmodels.org/stable/stats.html#power
- pyDOE2 docs: https://github.com/clicumu/pyDOE2
- dexpy: https://github.com/statease/dexpy
- BoTorch tutorial: https://botorch.org/tutorials/
- NIST Engineering Statistics Handbook (DOE): https://itl.nist.gov/div898/handbook/pri/section2/pri2.htm
- Box-Hunter-Hunter (classical DOE): https://onlinelibrary.wiley.com/doi/book/10.1002/9781118628361
- Myrvold Bayesian opt: https://botorch.org/docs/
- Pre-registration template (OSF): https://www.cos.io/initiatives/registered-reports

## Ethics & safety

- **Pre-registration:** commit to the design and analysis before data
  collection; this prevents garden-of-forking-paths inflation.
- **Multiplicity:** report all tests run, correct for multiple comparisons,
  and avoid "as-if-randomized" language unless the design was randomized.
- **Equity:** power for subgroups, not just the average, when treatment
  effects are expected to differ.
- **Animal / human subjects:** obtain IRB/IACUC approval; only test
  within approved factor ranges.
- **Reproducibility:** publish the design matrix, model, and seed alongside
  the results; reviewers must be able to rerun the analysis.

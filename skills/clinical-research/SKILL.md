---
name: clinical-research
description: Design, analyze, and report clinical trials and observational studies with standards-compliant tooling. Covers trial design (phases I-IV, blinding, randomization, sample size), CDISC SDTM/ADaM dataset construction, OMOP CDM and FHIR EHR extraction, survival analysis with lifelines (Kaplan-Meier, Cox PH), propensity-score methods with causalinference, CONSORT reporting, and statsmodels power calculations. Use this skill whenever the user asks about clinical trial design, randomization, blinding, IRB protocols, survival analysis, Cox regression, propensity scores, CONSORT diagrams, CDISC/SDTM/ADaM, OMOP CDM, or sample size for trials. Trigger keywords include clinical trial, phase II/III, CONSORT, Kaplan-Meier, Cox proportional hazards, propensity score, CDISC, SDTM, ADaM, OMOP CDM, FHIR, lifelines, MIMIC-IV, ClinicalTrials.gov, dbGaP, PCORnet.
license: MIT
compatibility: Requires Python 3.10+ with lifelines, statsmodels, pandas, numpy, causalinference, pyarrow. Optional: cdsic-submit-utils, omop-cli, fhir.resources for standards work; duckdb for large EHR extracts.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Clinical & Medical Research
---

# Clinical Research

## Overview

Clinical research spans trial design (sample size, randomization, blinding,
endpoints), execution (CDISC SDTM and ADaM datasets submitted to the FDA),
observational analysis of EHR data harmonized to the OMOP Common Data Model
or FHIR, and statistical analysis (survival, propensity scores, mixed
models). Outputs are CONSORT-compliant reports, CDISC submission-ready
datasets, and statistical-analysis plans.

This skill wires `lifelines` for survival analysis, `statsmodels` for power
and sample size, `causalinference` and `pysyncon` for propensity-score and
synthetic-control inference, plus the CDISC SDTM/ADaM and OMOP CDM
constructs needed for FDA submission and multi-site EHR research.

## When to use this skill

- User asks for **trial design** (phase, blinding, randomization, endpoint).
- User asks for **sample size / power** calculation for a trial.
- User asks for **CONSORT** diagram or reporting checklist.
- User mentions **Kaplan-Meier**, **Cox PH**, **log-rank**, **survival**.
- User asks for **propensity score** matching, IPTW, or synthetic controls.
- User needs **CDISC SDTM/ADaM** dataset construction.
- User wants to query an **OMOP CDM** or **FHIR** EHR database (MIMIC-IV,
  PCORnet, dbGaP).
- Skip for: medical-image analysis (use `medical-imaging`), de-identification
  and NLP on clinical text (use `clinical-nlp`), or epidemiology of infectious
  disease (use `epidemiology`).

## Prerequisites

- Python 3.10+ (3.11 recommended).
- System tools: `R` (optional, for some CDISC submission tooling and
  `survival` package cross-check), `duckdb` CLI for OMOP extracts.
- Python packages:

```bash
pip install lifelines statsmodels pandas numpy pyarrow scipy
pip install causalinference pysyncon   # propensity / synthetic control
pip install fhir.resources duckdb      # FHIR + OMOP
# Optional: pip install aind-data-schema ehrapy for EHR pipelines
```

- Data access: MIMIC-IV requires a PhysioNet credentialed user agreement;
  dbGaP requires an authorized-access application; PCORnet is institution-gated.

## Core workflows

### Sample size and power calculation

Compute the required sample size for a two-arm superiority trial with
binary endpoint using `statsmodels`.

```python
import math
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

# Two-arm trial: 30% control response rate, expect 45% in treatment arm
# alpha=0.05 (two-sided), power=0.80
effect = proportion_effectsize(0.45, 0.30)
analysis = NormalIndPower()
n_per_arm = analysis.solve_power(effect_size=effect, alpha=0.05,
                                 power=0.80, ratio=1.0)
# Inflate 15% for dropout
n_adjusted = math.ceil(n_per_arm / 0.85)
print(f"n per arm (raw): {math.ceil(n_per_arm)}, "
      f"adjusted: {n_adjusted}")
```

### CONSORT diagram and randomization

Build a CONSORT participant flow with randomization blocks.

```python
import pandas as pd
from itertools import cycle

N = 200
block_size = 4
ratio = [2, 2]  # 1:1 allocation
import random; random.seed(42)
arms = []
for _ in range(N // block_size + 1):
    block = ["treatment"] * ratio[0] + ["control"] * ratio[1]
    random.shuffle(block)
    arms.extend(block)
arms = arms[:N]

df = pd.DataFrame({"subject_id": range(1, N + 1), "arm": arms})
print(df.arm.value_counts())

# CONSORT-style flow (Python structure)
consort = {
    "assessed": 280, "excluded": 80, "randomized": 200,
    "allocated_treatment": 100, "allocated_control": 100,
    "lost_to_followup": 8, "analysed_treatment": 96,
    "analysed_control": 95}
print(consort)
```

### Survival analysis with lifelines

Kaplan-Meier estimator + log-rank + Cox proportional hazards model.

```python
import pandas as pd, lifelines
from lifelines import KaplanMeierFitter, CoxPHFitter
from lifelines.statistics import logrank_test

df = pd.read_csv("survival.csv")  # columns: time, event, arm, age, sex
kmf = KaplanMeierFitter()
for arm in df.arm.unique():
    sub = df[df.arm == arm]
    kmf.fit(sub.time, sub.event, label=arm)
    kmf.plot_survival_function()  # matplotlib

# Log-rank test
g1 = df[df.arm == "treatment"]
g0 = df[df.arm == "control"]
lr = logrank_test(g1.time, g0.time, g1.event, g0.event)
print(f"log-rank p={lr.p_value:.4f}")

# Cox PH
cph = CoxPHFitter()
cph.fit(df[["time", "event", "arm", "age", "sex"]], "time", "event")
cph.print_summary()
```

### Propensity score matching and IPTW

Estimate the causal effect of treatment on a binary outcome using
`causalinference`.

```python
import pandas as pd, numpy as np
from causalinference import CausalModel

df = pd.read_csv("obs.csv")  # columns: t (0/1), y, age, sex, charlson
X = df[["age", "sex", "charlson"]].values
t = df["t"].values
y = df["y"].values
cm = CausalModel(y, t, X)
cm.est_propensity_s()
cm.match(n_matches=1, bias_mode="llm")    # 1:1 nearest-neighbor
cm.est_via_matching()
print("ATE:", cm.estimates["matching"]["ate"])
print("95% CI:", cm.estimates["matching"]["ate_lb"],
      cm.estimates["matching"]["ate_ub"])

# IPTW alternative
from sklearn.linear_model import LogisticRegression
ps = LogisticRegression(max_iter=1000).fit(X, t).predict_proba(X)[:, 1]
iptw = np.where(t == 1, 1.0 / ps, 1.0 / (1.0 - ps))
effect = (iptw * t * y).sum() / (iptw * t).sum() - \
         (iptw * (1 - t) * y).sum() / (iptw * (1 - t)).sum()
print(f"IPTW risk difference: {effect:.4f}")
```

### CDISC SDTM/ADaM dataset construction

Build a minimal SDTM `AE` (adverse events) domain and an ADaM `ADSL`
subject-level dataset.

```python
import pandas as pd

# SDTM AE domain: columns follow CDISC SDTM IG (STUDYID, DOMAIN, USUBJID, ...)
ae = pd.DataFrame({
    "STUDYID": ["XYZ-001"] * 4,
    "DOMAIN": ["AE"] * 4,
    "USUBJID": ["001-001", "001-001", "001-002", "001-003"],
    "AESEQ": [1, 2, 1, 1],
    "AETERM": ["Headache", "Nausea", "Fatigue", "Rash"],
    "AEBODSYS": ["Nervous", "Gastrointestinal", "General", "Skin"],
    "AESEV": ["Mild", "Moderate", "Mild", "Severe"],
    "AESER": ["N", "N", "N", "Y"],
})
ae.to_csv("ae.csv", index=False)

# ADaM ADSL: subject-level
adsl = pd.DataFrame({
    "STUDYID": ["XYZ-001"] * 3,
    "USUBJID": ["001-001", "001-002", "001-003"],
    "TRT01P": ["Treatment", "Control", "Treatment"],
    "AGE": [54, 61, 47], "SEX": ["M", "F", "M"],
    "ITTFL": ["Y"] * 3, "SAFFL": ["Y"] * 3,
})
adsl.to_csv("adsl.csv", index=False)
```

### OMOP CDM and FHIR EHR extraction

Query the OMOP `condition_occurrence` table and convert to FHIR Condition.

```python
import duckdb, pandas as pd
con = duckdb.connect("omop.duckdb")  # OMOP CDM v5.4 schema
df = con.execute("""
    SELECT person_id, condition_concept_id,
           condition_start_datetime, condition_source_value
    FROM condition_occurrence
    WHERE condition_start_datetime >= '2020-01-01'
      AND condition_concept_id = 4112382  -- Type 2 DM
""").fetchdf()

# Convert OMOP row -> FHIR Condition
from fhir.resources.condition import Condition
from datetime import datetime
cond = Condition(
    **{
        "subject": {"reference": f"Patient/{int(df.person_id[0])}"},
        "code": {
            "coding": [{"system": "http://snomed.info/sct",
                        "code": "44054006", "display": "Type 2 diabetes mellitus"}]},
        "onsetDateTime": df.condition_start_datetime[0].isoformat(),
        "clinicalStatus": {"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
            "code": "active"}]},
    }
)
print(cond.json())
```

## Best practices

- Pre-register the **statistical analysis plan** (SAP) before database lock;
  deviations go through a formal amendment process.
- Use **intention-to-treat (ITT)** as the primary analysis; per-protocol is
  secondary. Both should be reported.
- For survival: censor at last known alive, verify the **proportional hazards
  assumption** with Schoenfeld residuals (`cph.check_assumptions()`).
- In observational studies, report the **Table 1** baseline characteristics by
  treatment group before and after propensity matching (love plot).
- Use a **caliper** of 0.1-0.2 on the logit of the propensity score for
  matching; tighter calipers improve balance, looser ones improve power.
- Submit CDISC datasets in `XPT` format (`pandas.to_sas`) with define.xml;
  validate with the open-source `Pinnacle21 Community` validator before
  submission.
- For FHIR exports, follow the **Bulk Data Access** (`$export`) flow and
  group-level exports for cohort extraction; respect SMART-on-FHIR scopes.
- Report **CONSORT 2010** for trials and **STROBE** for observational
  studies; missing items are flagged by reviewers.
- Set a single **primary endpoint** and a single **primary analysis**;
  multiplicity is handled via hierarchical testing or Hochberg correction.
- Pre-specify the **non-inferiority margin** if applicable, with rationale.

## Common pitfalls

- Forgetting to censor at last known alive - Kaplan-Meier curves drop to
  zero instead of plateauing.
- Applying **Cox PH** without checking the proportional hazards assumption
  for each covariate; time-varying effects require stratification or
  time-interaction terms.
- **Immortal time bias**: defining treatment exposure after baseline (e.g.
  "filled a prescription within 30 days") makes the treated group immortal
  during that window. Use time-varying covariates or landmark analysis.
- Propensity-score matching on **post-treatment** covariates (e.g. lab
  results taken after the intervention) - matching on a collider introduces
  bias.
- Using **last-observation-carried-forward** for missing data; prefer mixed
  models for repeated measures (MMRM) or multiple imputation.
- Reporting unadjusted **per-protocol** results without reporting ITT as
  primary; this exaggerates effect sizes by 30-50% in many cases.
- Categorizing continuous covariates (e.g. age < 65 vs >= 65) loses
  information and inflates type I error; keep continuous unless nonlinear.
- Submitting CDISC datasets with mismatched `USUBJID` keys between domains -
  `define.xml` will fail validation.

## Worked example

Goal: analyze a Phase III oncology trial with a binary primary endpoint and
time-to-event secondary endpoint; report hazard ratio + CONSORT flow.

```python
import math
import pandas as pd, lifelines
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import logrank_test

adsl = pd.read_csv("adsl.csv")           # subject level
adae = pd.read_csv("adaette.csv")        # time-to-event

# CONSORT counts (basic)
n_assessed = 600; n_excluded = 100; n_rand = 500
n_treat = adsl[adsl.TRT01P == "Treatment"].shape[0]
n_ctrl = adsl[adsl.TRT01P == "Control"].shape[0]
print(f"assessed={n_assessed} excluded={n_excluded} randomized={n_rand} "
      f"treatment={n_treat} control={n_ctrl}")

# Survival analysis
kmf = KaplanMeierFitter()
for arm in adsl.TRT01P.unique():
    sub_ids = adsl[adsl.TRT01P == arm].USUBJID
    sub = adae[adae.USUBJID.isin(sub_ids)]
    kmf.fit(sub.time, sub.event, label=arm)
    kmf.plot_survival_function()
g1 = adae[adae.USUBJID.isin(adsl[adsl.TRT01P == "Treatment"].USUBJID)]
g0 = adae[adae.USUBJID.isin(adsl[adsl.TRT01P == "Control"].USUBJID)]
lr = logrank_test(g1.time, g0.time, g1.event, g0.event)
print(f"log-rank p={lr.p_value:.4f}")

cph = CoxPHFitter()
df_cox = adsl.merge(adae, on="USUBJID")[
    ["time", "event", "TRT01P", "AGE", "SEX"]]
df_cox["TRT01P"] = (df_cox.TRT01P == "Treatment").astype(int)
df_cox["SEX"] = (df_cox.SEX == "M").astype(int)
cph.fit(df_cox, "time", "event")
print(f"HR (treatment vs control) = "
      f"{math.exp(cph.params_['TRT01P']):.2f} "
      f"(95% CI {math.exp(cph.confidence_intervals_.loc['TRT01P','95% lower-bound']):.2f}-"
      f"{math.exp(cph.confidence_intervals_.loc['TRT01P','95% upper-bound']):.2f})")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| lifelines | Kaplan-Meier, Cox PH, log-rank | `pip install lifelines` |
| statsmodels | Power, sample size, GLM | `pip install statsmodels` |
| causalinference | Propensity-score matching/IPTW | `pip install causalinference` |
| pysyncon | Augmented synthetic controls | `pip install pysyncon` |
| pyarrow / pandas | SDTM/ADaM dataset manipulation | `pip install pyarrow` |
| fhir.resources | FHIR STU3/R4 model construction | `pip install fhir.resources` |
| duckdb | OMOP CDM SQL queries | `pip install duckdb` |
| Pinnacle21 Community | CDISC dataset validation (Java) | https://pinnacle21.com |
| ClinicalTrials.gov API | Trial registration and search | https://clinicaltrials.gov/api |
| MIMIC-IV | Critical-care EHR database | PhysioNet credential |
| OMOP CDM vocab | SNOMED/ RxNorm/ ICD10 mappings | https://www.ohdsi.org |

## References

- CONSORT 2010 statement: https://doi.org/10.1136/bmj.c332
- CDISC SDTM/ADaM standards: https://www.cdisc.org/standards
- OMOP CDM v5.4: https://www.ohdsi.org/data-standardization/
- FHIR R4 specification: https://hl7.org/fhir/R4/
- lifelines documentation: https://lifelines.readthedocs.io/
- MIMIC-IV database: https://physionet.org/content/mimiciv/
- ClinicalTrials.gov API: https://clinicaltrials.gov/api/v2/studies
- PCORnet Common Data Model: https://pcornet.org/pcornet-common-data-model/

## Ethics & safety

- Clinical research on human subjects requires **IRB/ethics approval** and
  **informed consent**; never deploy analysis pipelines on identifiable
  patient data without a covered IRB protocol.
- Use only **de-identified** or **limited datasets** under a Data Use
  Agreement; HIPAA Safe Harbor (18 identifiers removed) or Expert
  Determination. Re-identification of de-identified data is a federal offense.
- Statistical analyses are **research findings**, not medical advice; do not
  communicate trial results to patients or clinicians outside the study team.
- Database access (MIMIC-IV, dbGaP, PCORnet) requires credentialed access;
  do not redistribute raw extracts and follow the data use agreement.
- For clinical decision-support applications, all models must undergo
  FDA SaMD review and local clinical validation before patient-facing use.
- Pre-registration of trials and SAPs is required for publication in ICMJE
  journals; do not back-date or alter registered analyses after data lock.

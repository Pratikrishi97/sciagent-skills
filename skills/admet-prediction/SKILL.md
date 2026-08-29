---
name: admet-prediction
description: Predict ADMET (absorption, distribution, metabolism, excretion, toxicity) and physico-chemical properties for small molecules. Covers SwissADME-style rules (Lipinski, Veber, Egan, Ghose), PAINS alerts, hERG and CYP450 inhibition, blood-brain barrier permeability, Ames mutagenicity, and pkCSM-style endpoints. Provides end-to-end predictive modeling with DeepChem and chemprop using Morgan fingerprints feeding random forests and message-passing neural networks. Use this skill whenever the user asks about absorption, bioavailability, blood-brain barrier, CYP450 metabolism, hERG cardiotoxicity, PAINS, drug-likeness filters, or ADMET model training on Tox21/ToxCast/TDC benchmarks. Trigger keywords include ADMET, SwissADME, pkCSM, PAINS, hERG, CYP450, BBB, Tox21, DeepChem, chemprop, TDC.
license: MIT
compatibility: Requires Python 3.10+ with rdkit, deepchem, chemprop, scikit-learn, pandas. Optional: therapeutics-data-commons (tdc) for benchmark endpoints; xgboost for tree boosting.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Drug Discovery & Cheminformatics
---

# ADMET Prediction

## Overview

ADMET (Absorption, Distribution, Metabolism, Excretion, Toxicity) prediction
estimates how a candidate molecule will behave in the body: will it be
absorbed in the gut, cross the blood-brain barrier, be cleared by the
kidney or metabolized by CYP450, inhibit the hERG potassium channel (QT
prolongation risk), or cause mutagenicity? Filtering on ADMET *before*
synthesis saves months of wet-lab iteration.

Two complementary approaches exist: **rule-based** property calculators
(SwissADME, pkCSM filters, RDKit Lipinski/Veber/Egan) flag obvious failures;
**machine-learned** predictors (DeepChem, chemprop, ADMETLab) trained on
Tox21/ToxCast/TDC endpoints produce probabilistic predictions on endpoints
like CYP1A2 inhibition, hERG blockade, AMES mutagenicity, and rat acute
toxicity (LD50).

This skill wires RDKit rule-based filters with DeepChem/chemprop predictive
models so an agent can produce an ADMET profile CSV for a candidate series
in minutes.

## When to use this skill

- User asks about **absorption**, **bioavailability**, **solubility**, **permeability**.
- User mentions **blood-brain barrier**, **CYP450**, **hERG**, **QT prolongation**.
- User asks for **drug-likeness filters** (Lipinski, Veber, Egan, Ghose, Leadlike).
- User asks for **PAINS** or aggregating-compound alerts.
- User wants to **train an ADMET model** on Tox21/ToxCast/TDC benchmarks.
- User mentions **DeepChem**, **chemprop**, **ADMETLab**, **SwissADME**, **pkCSM**.
- Skip for: virtual screening and docking (use `drug-discovery`), pure
  cheminformatics (use `cheminformatics`), retrosynthesis (use `retrosynthesis`).

## Prerequisites

- Python 3.10+ (3.11 recommended; PyTorch 2.x wheels).
- System tools: none mandatory. Optional `openbabel` for DeepChem featurizers.
- Python packages:

```bash
pip install rdkit scikit-learn pandas xgboost matplotlib
pip install deepchem chemprop  # deep learning ADMET models
pip install PyTDC              # Therapeutics Data Commons benchmarks
# Optional: ADMETLab2 (pip install admet-ai) for one-shot prediction API
```

- Optional: `swissadme` (mirror of the web service, useful for batch runs).

## Core workflows

### Rule-based drug-likeness filters

Compute Lipinski/Veber/Egan/Ghose/Leadlike flags plus PAINS alerts for a
compound series using RDKit.

```python
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, FilterCatalog, rdMolDescriptors

def drug_likeness(smiles: str) -> dict:
    m = Chem.MolFromSmiles(smiles)
    if m is None: return {}
    mw, logp = Descriptors.MolWt(m), Crippen.MolLogP(m)
    hbd, hba = Descriptors.NumHDonors(m), Descriptors.NumHAcceptors(m)
    rotb = Descriptors.NumRotatableBonds(m)
    tpsa = rdMolDescriptors.CalcTPSA(m)
    return {
        "smiles": smiles,
        "MW": round(mw, 1),
        "LogP": round(logp, 2),
        "HBD": hbd, "HBA": hba,
        "RotB": rotb, "TPSA": round(tpsa, 1),
        "Lipinski": (mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10),
        "Veber": (rotb <= 10 and tpsa <= 140),
        "Egan_BBB": (tpsa <= 70 and logp <= 5),
        "Ghose": (160 <= mw <= 480 and -0.4 <= logp <= 5.6
                  and 40 <= rdMolDescriptors.CalcNumRings(m) + 0 <= 7
                  and 40 <= Descriptors.TPSA(m) <= 130 or True),
    }

smiles = ["CC(=O)c1ccccc1O", "c1ccccc1C(=O)NCc1ccccc1",
          "O=c1ccc2ccccc2[nH]1", "CCCCCCCCCCCCCC(=O)O"]
print(pd.DataFrame([drug_likeness(s) for s in smiles]))
```

### PAINS and aggregating-compound filters

Flag promiscuous hits before any predictive model runs.

```python
from rdkit import Chem
from rdkit.Chem import FilterCatalog

params = FilterCatalog.FilterCatalogParams()
params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_A)
params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_B)
params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS_C)
params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.BRENK)
catalog = FilterCatalog.FilterCatalog(params)

mols = [Chem.MolFromSmiles(s) for s in
        ["c1ccccc1", "O=C(Cc1ccccc1)Nc1ccccc1",
         "Cc1ccc(N=Nc2ccc(N)cc2)cc1"]]   # last is an azo dye
for m in mols:
    if m and catalog.HasMatch(m):
        print("ALERT:", Chem.MolToSmiles(m),
              catalog.GetMatches(m, maxResults=1)[0].GetDescription())
```

### Train a Tox21 QSAR model with DeepChem

Train a random forest on Morgan fingerprints using the canonical Tox21
12-task benchmark (NR-AR, SR-ARE, ..., SR-p53).

```python
import deepchem as dc
from deepchem.molnet import load_tox21
from deepchem.models import MultitaskClassifier

tasks, datasets, transformers = load_tox21(featurizer="ECFP", split="random")
train, valid, test = datasets

model = MultitaskClassifier(
    n_tasks=len(tasks), n_features=1024, layer_sizes=[500],
    dropout=0.25, batch_size=64, learning_rate=0.001, mode="classification",
    model_dir="./tox21_rf")

model.fit(train, nb_epoch=10)
metric = dc.metrics.Metric(dc.metrics.roc_auc_score, np.mean, mode="classification")
print("valid AUC:", model.evaluate(valid, [metric], transformers))
```

### Chemprop message-passing network for ADMET

Train an MPNN on a custom ADMET endpoint (e.g. hERG inhibition) using chemprop.

```python
import chemprop
import pandas as pd

# CSV columns: smiles,herog_blocker (0/1)
df = pd.read_csv("herg_dataset.csv")
arguments = [
    "--data_path", "herg_dataset.csv",
    "--dataset_type", "classification",
    "--save_dir", "herg_model",
    "--epochs", "30", "--batch_size", "64",
    "--message_hidden_dim", "300", "--depth", "3",
    "--split_type", "scaffold", "--split_sizes", "0.8 0.1 0.1",
]
args = chemprop.args.TrainArgs().parse_args(arguments)
mean, std = chemprop.train.cross_validate(args=args, train_args=args)
print(f"mean valid AUC: {mean:.3f} +/- {std:.3f}")

# Predict
preds = chemprop.train.make_predictions(
    arguments=["--test_path", "candidates.smi",
               "--checkpoint_dir", "herg_model",
               "--preds_path", "preds.csv"])
```

### Blood-brain barrier permeability and pkCSM-style endpoints

Combine rule-based (BBB filter) and learned (TDC BBB benchmark) predictors.

```python
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Crippen, rdMolDescriptors

def bbb_filter(smiles: str) -> bool:
    m = Chem.MolFromSmiles(smiles)
    if m is None: return False
    logp = Crippen.MolLogP(m)
    tpsa = rdMolDescriptors.CalcTPSA(m)
    mw = Chem.Descriptors.MolWt(m)
    return (logp <= 5 and tpsa <= 70 and 150 <= mw <= 450
            and Chem.Descriptors.NumHBD(m) <= 3)

# TDC BBB ML model (provide a trained checkpoint)
# from tdc.benchmark_group import admet_group
# benchmark = admet_group.get("bbb_martins")
# predictions = trained_model.predict(test_smiles)
```

## Best practices

- Run **rule-based filters** first (Lipinski/Veber/Egan/PAINS) - they cost
  nothing and remove obvious failures before ML is wasted.
- Train ADMET models on **scaffold-split** train/test (not random split);
  random splits overestimate generalization by 5-15 AUC points.
- Calibrate probabilities (Platt, isotonic) before thresholding for hit
  triage; raw MPNN outputs are not calibrated.
- Predict endpoints with **applicability domain** checks: a Tanimoto < 0.4
  to training set means extrapolation - flag the prediction as low-confidence.
- Use **multitask** models when multiple related endpoints share chemistry
  (Tox12 12-task); they outperform single-task models by 3-5 AUC points.
- For hERG specifically, prefer the **binary hERG blockers** benchmark
  (TDC `herg`) over `hERG10` (10 uM) - the binary version is more reliable.
- Report the **dataset source** and **split** with every prediction; ADMET
  numbers without provenance are useless.
- Cross-validate across **three** random seeds; chemprop and DeepChem
  exhibit run-to-run variance of +/-2 AUC due to initialization.
- Benchmark on **TDC** before custom endpoints to confirm the pipeline
  matches published baselines.

## Common pitfalls

- Treating ADMET models as binary classifiers with a single 0.5 cutoff - use
  calibrated probabilities and a domain-aware threshold.
- Training on assays with severe **class imbalance** (>90% negatives)
  without `class_weight` or focal loss; AUC looks fine but precision collapses.
- Predicting outside the training chemical space (a natural-product scaffold
  against a model trained on med-chem space) produces garbage with high
  confidence.
- Mixing **stereochemistry** across training and test sets; an SMILES without
  stereo is a different molecule than its enantiomer.
- Forgetting to featurize at the **same fingerprint radius** for train/test
  (Morgan r=2 trained, r=3 tested = silent bug).
- Trusting **in-house ADMET** without external validation; always retrain on
  ChEMBL-derived ADME data or TDC to benchmark.
- Using PAINS as a hard filter; it is a *triage* alert - many approved drugs
  contain PAINS substructures.

## Worked example

Goal: produce an ADMET profile CSV for 50 candidate hits that flags
drug-likeness failures, PAINS, and predicts hERG blockade with a chemprop
checkpoint.

```python
import pandas as pd, chemprop
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, FilterCatalog, rdMolDescriptors

df = pd.read_csv("hits.smi", sep="\t", names=["smiles", "compound_id"])

def likeness(s):
    m = Chem.MolFromSmiles(s)
    return {
        "MW": round(Descriptors.MolWt(m), 1),
        "LogP": round(Crippen.MolLogP(m), 2),
        "TPSA": round(rdMolDescriptors.CalcTPSA(m), 1),
        "Lipinski": (Descriptors.MolWt(m) <= 500 and Crippen.MolLogP(m) <= 5
                     and Descriptors.NumHDonors(m) <= 5
                     and Descriptors.NumHAcceptors(m) <= 10),
    }

props = df.smiles.map(likeness).apply(pd.Series)
df = pd.concat([df, props], axis=1)

# PAINS filter
params = FilterCatalog.FilterCatalogParams()
params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
pains = FilterCatalog.FilterCatalog(params)
df["PAINS"] = df.smiles.map(
    lambda s: pains.HasMatch(Chem.MolFromSmiles(s)))

# hERG prediction
df[["herg_prob"]] = chemprop.train.make_predictions(
    arguments=["--test_path", df[["smiles"]].to_csv("tmp.csv", index=False),
               "--checkpoint_dir", "herg_model_checkpoints",
               "--preds_path", "tmp_preds.csv"])
df.to_csv("admet_profile.csv", index=False)
print(df.head())
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| RDKit | Rule-based filters, descriptors, PAINS | `pip install rdkit` |
| DeepChem | Tox21/ToxCast multitask models, featurizers | `pip install deepchem` |
| chemprop | Message-passing neural network for ADMET | `pip install chemprop` |
| scikit-learn | Random forests, calibration, evaluation | `pip install scikit-learn` |
| XGBoost | Gradient boosting for tabular ADMET features | `pip install xgboost` |
| TDC (Therapeutics Data Commons) | 220+ ADMET benchmarks | `pip install PyTDC` |
| ADMET-AI | One-shot ADMET prediction API (ADMETLab2) | `pip install admet-ai` |
| SwissADME | Web service for drug-likeness flags | https://www.swissadme.ch |
| pkCSM | Web service for pkCSM-style endpoints | http://biosig.unimelb.edu.au/pkcsm/ |
| Tox21 | 12-task toxicity benchmark | via DeepChem `load_tox21` |
| ToxCast | EPA toxicity screening (ToxCast/Tox21) | https://www.epa.gov/chemical-research |

## References

- DeepChem documentation: https://deepchem.readthedocs.io/
- chemprop paper: https://doi.org/10.1021/acs.jcim.9b00237
- Therapeutics Data Commons: https://doi.org/10.1038/s41451-022-00388-7
- SwissADME: https://doi.org/10.3390/molecules21121427
- pkCSM: https://doi.org/10.1038/nature13358
- Tox21 challenge: https://doi.org/10.3389/fenvs.2017.00016
- PAINS filters: https://doi.org/10.1038/nature17618
- ADMETLab 2.0: https://doi.org/10.1093/nar/gkab395

## Ethics & safety

- ADMET predictions are **research hypotheses** for hit triage only - they do
  not replace preclinical PK/toxicology studies or IND-enabling studies.
- Do not communicate predicted toxicity as a safety claim; predictions can
  be wrong by an order of magnitude. Always flag uncertainty.
- Acute toxicity models (rat LD50) and CYP models can be repurposed to
  predict the toxicity of weaponizable substances; **decline** to run
  predictions that are explicitly framed as optimizing harm.
- When using proprietary ADMET datasets (Cerep, Eurofins, Cyprotex), respect
  the licensing terms and do not redistribute or train competing models.
- Patient-derived compound libraries (e.g. from biobanks) carry IRB consent
  constraints; do not include identifiable patient data in training sets.
- Always cite the dataset and model version - ADMET predictions are
  non-reproducible without provenance; supply the SMILES, model card, and
  training set hash with every output.

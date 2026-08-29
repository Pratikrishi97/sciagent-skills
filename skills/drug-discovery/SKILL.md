---
name: drug-discovery
description: End-to-end small-molecule drug discovery pipeline covering target identification, virtual screening, docking with AutoDock Vina, pharmacophore modeling, hit-to-lead optimization, QSAR with scikit-learn, and free energy perturbation with OpenMM/Perses. Use this skill whenever the user mentions virtual screening, molecular docking, SMILES-based hit finding, hit-to-lead, PROTAC design, ChEMBL/PDBbind data mining, or lead optimization. Trigger keywords include RDKit, AutoDock Vina, Vina-Rxdock, Pharmit, Perses, OpenMM, QSAR, SMILES, pharmacophore.
license: MIT
compatibility: Requires Python 3.10+ with rdkit, openbabel, vina, openmm, perses, scikit-learn. AutoDock Vina binary or meeko for ligand preparation.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Drug Discovery & Cheminformatics
---

# Drug Discovery

## Overview

Modern small-molecule drug discovery moves through (1) target identification
and validation, (2) hit finding via high-throughput or virtual screening,
(3) hit-to-lead optimization, and (4) lead optimization toward a clinical
candidate. Computational chemistry accelerates every stage: structure- and
ligand-based virtual screening examines millions of compounds (ZINC, Enamine
REAL, MolPort) before any wet-lab assay; docking and pharmacophore modeling
prioritize poses; quantitative structure-activity relationship (QSAR) models
guide SAR; and free energy perturbation (FEP) estimates relative binding
deltas to triage analogs.

This skill wires together canonical open-source tools (RDKit, Open Babel,
AutoDock Vina, OpenMM, Perses, scikit-learn, Meeko, Pharmit) with public data
sources (ChEMBL, PubChem, DrugBank, PDBbind, ZINC) so an agent can plan a
complete hit-to-lead campaign. Outputs are SMILES/SDF ligand lists, docking
pose PDBQT files, scoring tables, and free-energy spreadsheets ready for the
bench chemist.

## When to use this skill

- User asks for **virtual screening** of a target (e.g. "find DDR1 inhibitors").
- User mentions **docking**, **AutoDock Vina**, **Vina-Rxdock**, **SMILES**, **PDBQT**.
- User wants **hit-to-lead** optimization around a known hit series.
- User needs **QSAR** modeling from a ChEMBL/PDBbind assay table.
- User asks about **PROTAC** design, **molecular glue**, or **targeted protein degradation**.
- User asks for **free energy perturbation** (FEP) or **binding affinity** ranking.
- User wants to retrieve and curate ligands from **ChEMBL**, **PubChem**, **DrugBank**.
- Skip for: pure ADMET prediction (use `admet-prediction`), retrosynthesis (use
  `retrosynthesis`), or descriptor/fingerprint work alone (use `cheminformatics`).

## Prerequisites

- Python 3.10+ (3.11 recommended for RDKit 2024+ wheels).
- System tools: `obabel` (Open Babel), `vina` (AutoDock Vina binary), `pdb2pqr30`,
  optionally `reduce` and `prepare_receptor` (ADFR suite).
- Python packages:

```bash
pip install rdkit openbabel-wheel vina meeko openmm perses scikit-learn pandas \
            padelpy chembl_webresource_client pubchempy biopandas tqdm py3Dmol
```

- Optional: `pyscreener` for parallel docking, `MDAnalysis` for trajectory
  analysis, `openmmforcefields` for small-molecule GAFF/SMIRNOFF parameters.

## Core workflows

### Target identification and ligand curation

Pull known actives from ChEMBL, standardize structures, and deduplicate by
canonical SMILES and InChIKey.

```python
from rdkit import Chem
from chembl_webresource_client.new_client import new_client
from rdkit.Chem.MolStandardize.rdMolStandardize import StandardizeSmiles

molecule = new_client.molecule
res = molecule.filter(target_chembl_id="CHEMBL206", pchembl_value__gte=6)[:200]
smiles = []
for r in res:
    s = (r.get("molecule_structures") or {}).get("canonical_smiles")
    if s:
        smiles.append(StandardizeSmiles(Chem.MolFromSmiles(s)))
# Deduplicate on InChIKey first block
seen, kept = set(), []
for m in (Chem.MolFromSmiles(s) for s in smiles):
    if m is None: continue
    key = Chem.MolToInchiKey(m).split("-")[0]
    if key not in seen:
        seen.add(key); kept.append(Chem.MolToSmiles(m))
print(f"{len(kept)} unique actives")
```

### Structure-based virtual screening with AutoDock Vina

Prepare receptor (PDB -> PDBQT) and dock a curated ligand set.

```python
import meeko, subprocess, os, pandas as pd
from rdkit import Chem
from vina import Vina

# Receptor preparation (run obabel externally)
subprocess.run(["obabel", "1kv1.pdb", "-O", "receptor.pdbqt", "-xr"], check=True)

def dock(smiles, name, box_center=(0, 0, 0), box_size=(20, 20, 20)):
    mol = Chem.MolFromSmiles(smiles)
    mol = Chem.AddHs(mol)
    prep = meeko.MoleculePreparation()
    prep.prepare(mol)[0].write_pdbqt(f"{name}.pdbqt")
    v = Vina(sf_name="vina", seed=42, verbosity=0)
    v.set_receptor("receptor.pdbqt")
    v.set_ligand_from_file(f"{name}.pdbqt")
    v.compute_vina_maps(center=box_center, size=box_size)
    v.dock(exhaustiveness=8, n_poses=5)
    return v.energies(n_poses=1)[0][0]

score = dock("CCOc1ccccc1C(=O)Nc1ccccc1", "aspirin_analog")
print(f"best pose: {score:.2f} kcal/mol")
```

### Pharmacophore modeling and ligand-based screening

Build a feature-based pharmacophore from aligned actives with RDKit + Pharmit
query generation; screen an SDF library.

```python
from rdkit import Chem
from rdkit.Chem import rdMolAlign, rdShapeHelpers
from rdkit.Chem.Pharm3D import EmbedLib, Generate, Pharm3D

# Use a reference ligand from the co-crystal as the pharmacophore shape
ref = Chem.MolFromMolFile("ref_ligand.sdf")
feat_factory = Chem.Pharm3D.BuildFeatureFactoryFromMol(ref)
feats = feat_factory.GetFeaturesForMol(ref)
p = Pharm3D.Pharmacophore(feats)
print("feature count:", len(feats))

# Screen a library: keep molecules embedding all features
for mol in Chem.SDMolSupplier("library.sdf"):
    if mol is None: continue
    can_match = Generate.PharmacophoreMatch(p, feat_factory, mol)
    if can_match:
        bounds = rdMolAlign.GetBestAlignmentTransform(ref, mol)
```

### Hit-to-lead QSAR with scikit-learn

Train a regression model on PDBbind-style binding data using Morgan
fingerprints and rank virtual-screening hits.

```python
import pandas as pd
from rdkit import Chem
from rdkit.Chem import AllChem
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error

df = pd.read_csv("pdbbind_smiles.csv")  # columns: smiles, pkd
fps = [AllChem.GetMorganFingerprintAsBitVect(
         Chem.MolFromSmiles(s), 2, nBits=1024).ToList() for s in df.smiles]
import numpy as np
X = np.array(fps); y = df.pkd.values
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
rf = RandomForestRegressor(n_estimators=400, n_jobs=-1, random_state=42)
rf.fit(Xtr, ytr)
pred = rf.predict(Xte)
print(f"R2={r2_score(yte, pred):.2f} MAE={mean_absolute_error(yte, pred):.2f}")
```

### Free energy perturbation with OpenMM/Perses

Compute relative binding free energy between two analogs in the binding site.

```python
from perses.app import relative_point_mutation_setup as rpms
from perses.app.relative_setup import RelativeFEPSetup
import openmm

setup = RelativeFEPSetup(
    ligand_file="ligands.sdf",
    protein_pdb="receptor.pdb",
    old_ligand_index=0, new_ligand_index=1,
    forcefield_files=["amber14/protein.ff14SB.xml", "openff-2.1.0.offxml"],
    small_molecule_forcefields="openff-2.1.0",
    phases=["complex", "solvent"],)

from perses.trajectory import topology
# Run hybrid topology FEP via multistate (repex) sampler
from openmmtools.multistate import HybridRepexSampler
# (full FEP cycle omitted for brevity; see Perses docs)
```

## Best practices

- Standardize molecules **before** screening: tautomer canonicalization,
  neutralization, salt stripping, and InChIKey deduplication.
- Always run **docking controls**: re-dock the co-crystal ligand and confirm
  RMSD < 2 A as a positive control before running virtual screening.
- Set the docking box from the **co-crystal ligand centroid +/- 5 A** plus
  box dimensions covering the active site cavity; do not dock into a guessed box.
- Use multiple scoring functions (Vina, Vina-Rxdock, smina vinardo) and rank by
  consensus rather than a single score.
- Filter virtual-screening hits with property and PAINS filters *before*
  purchasing; use `admet-prediction` for early ADMET.
- Sample chemical space widely: ZINC + Enamine REAL for diversity, then focused
  libraries around a privileged scaffold.
- Confirm docking pose with short MD (10-50 ns OpenMM) before synthesis;
  50 ns of explicit solvent catches clashes a static pose hides.
- Track provenance: SMILES source, InChIKey, docking score, pose PDBQT path,
  preparation provenance in a CSV.
- Use `exhaustiveness=32` or higher for final poses; the default 8 is for triage.
- Save poses as multi-model PDBQT and inspect top-3 with py3Dmol or NGLView.

## Common pitfalls

- Treating a docking score as an absolute free energy: it is a *ranking*
  surrogate only, ~1-2 kcal/mol noise.
- Ignoring protonation states: a histidine flip or charged lysine can flip a
  pose entirely. Use `pdb2pqr` and PropKa (or Schrodinger's `prepwizard`
  equivalent in open tools) to assign states at pH 7.4.
- Receptor and ligand atom types mismatched between force fields. Always
  regenerate parameters with the same `openff-2.x` or GAFF2 line for both.
- Failing to cap ligand protein termini or include cofactors (e.g. heme, ZN)
  in docking - they often coordinate the ligand.
- Using PDB structures without checking resolution, B-factors in the binding
  pocket, or missing loops; prefer sub-2.5 A structures and check ALA Lab.
- Mixing stereochemistry in a screen: a 50/50 R/S mix halves effective
  screening; enumerate stereoisomers explicitly.
- Docking covalent ligands with a non-covalent scoring function (use
  `covalent=True` in smina or specialized forcefields).
- Trusting QSAR extrapolation: never predict far outside training Tanimoto
  similarity (Tanimoto < 0.4 to training set).

## Worked example

Goal: find novel BACE1 (beta-secretase) inhibitors from Enamine REAL,
docked against PDB 4D8L, filtered by QSAR.

```python
# 1) Prepare receptor
import subprocess, os
subprocess.run(["pdb2pqr30", "--pH=7.4", "4d8l.pdb", "4d8l.pqr"], check=True)
subprocess.run(["obabel", "4d8l.pqr", "-O", "receptor.pdbqt", "-xr"], check=True)

# 2) Load library (small demo slice)
import pandas as pd
from rdkit import Chem
from rdkit.Chem.MolStandardize.rdMolStandardize import StandardizeSmiles

lib = pd.read_csv("enamine_sample.csv")  # columns: smiles, compound_id
lib["std"] = lib.smiles.map(lambda s: Chem.MolToSmiles(
    Chem.MolFromSmiles(StandardizeSmiles(Chem.MolFromSmiles(s)))))

# 3) Quick property filter (Lipinski + PAINS)
from rdkit.Chem import Descriptors, FilterCatalog
params = FilterCatalog.FilterCatalogParams()
params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
catalog = FilterCatalog.FilterCatalog(params)

def ok(m):
    return (Descriptors.MolWt(m) <= 500 and Descriptors.NumHDonors(m) <= 5
            and Descriptors.NumHAcceptors(m) <= 10 and not catalog.HasMatch(m))

lib["mol"] = lib["std"].map(Chem.MolFromSmiles)
lib = lib[lib.mol.map(ok)].reset_index(drop=True)
print(f"{len(lib)} compounds pass filters")

# 4) Dock top 50 (placeholder; see Core workflows for full dock())
# for i, row in lib.head(50).iterrows():
#     lib.at[i, "vina"] = dock(row.std, f"hit_{i}")

# 5) QSAR ranking using a pretrained BACE model (see QSAR sub-workflow)
# preds = rf.predict(fps_for_lib)
# final = lib.assign(qsar=preds).sort_values("qsar", ascending=False).head(20)
```

The output CSV contains `compound_id, smiles, vina_score, qsar_pred` ready for
the bench team to cherry-pick.

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| RDKit | Cheminformatics core (SMILES, fingerprints, standardization) | `pip install rdkit` |
| Open Babel | Format conversion, PDBQT preparation | `conda install -c conda-forge openbabel` |
| AutoDock Vina | Docking engine (binary + Python bindings) | `pip install vina` |
| Meeko | RDKit -> PDBQT ligand preparation for Vina | `pip install meeko` |
| smina | Vina fork with custom scoring functions | binaries from source |
| Vina-Rxdock | Alternative docking engine | `conda install -c insilichem vina-rxdock` |
| OpenMM | MD engine for pose validation, FEP backbone | `conda install -c conda-forge openmm` |
| Perses | Relative FEP workflows built on OpenMM | `pip install perses` |
| scikit-learn | QSAR models (RF, GBM, GP) | `pip install scikit-learn` |
| ChEMBL webresource client | Programmatically query ChEMBL | `pip install chembl_webresource_client` |
| PubChemPy | PubChem compound lookup | `pip install pubchempy` |
| py3Dmol | Interactive 3D viewer in Jupyter | `pip install py3Dmol` |

## References

- AutoDock Vina paper: https://doi.org/10.1002/jcc.21334
- RDKit documentation: https://www.rdkit.org/docs/
- ChEMBL web services: https://chembl.gitbook.io/chembl-interface-documentation
- ZINC15 database: https://zinc15.docking.org/
- PDBbind database: http://www.pdbbind.org.cn/
- Perses FEP framework: https://perses.readthedocs.io/
- OpenMM documentation: http://docs.openmm.org/
- Pharmit pharmacophore server: http://pharmit.csb.pitt.edu/

## Ethics & safety

- Docking and synthesis results can identify controlled substances, weaponized
  neurotoxins, or regulated precursors. **Never** provide synthetic routes for
  known chemical weapons, controlled substances, or dual-use toxins; route the
  user to their institution's biosafety officer and the BWC/CWC framework.
- Clinical candidate suggestions are research hypotheses only - they are not
  medical advice and must be validated preclinically before any human exposure.
- Respect ToS of public databases (ChEMBL CC BY-SA, PubChem public domain,
  ZINC free for academic use; Enamine requires a license for commercial use).
- Always log provenance (PDB ID, ligand source, parameter version) so a
  medicinal chemist can reproduce and audit decisions.
- Compound purchase requests go through institutional procurement and DEA/EMT
  controls when applicable; do not attempt to bypass.
- When working with patient-derived structural data (e.g. tumor PDX structures),
  honor the originating IRB and consent; do not re-identify donors.

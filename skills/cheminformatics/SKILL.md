---
name: cheminformatics
description: Core cheminformatics toolkit for small-molecule processing using RDKit, Open Babel, and the CDK. Covers SMILES/InChI parsing, MolStandardization, SMARTS substructure search, Morgan and MACCS fingerprint generation, Tanimoto similarity, descriptor calculation (Lipinski, Crippen LogP), R-group decomposition, scaffold hopping, reaction SMARTS, and chemical-space visualization with TMAP/UMAP. Use this skill whenever the user needs molecule standardization, fingerprint or similarity workflows, SMARTS substructure queries, descriptor/property calculation, R-group decomposition, or MoleculeNet benchmarks. Trigger keywords include RDKit, Open Babel, CDK, SMILES, InChI, SMARTS, Morgan, MACCS, Tanimoto, Lipinski, scaffold, TMAP, UMAP.
license: MIT
compatibility: Requires Python 3.10+ with rdkit, openbabel-wheel, scikit-learn, umap-learn, tmap, tqdm. Optional: JPype1 + CDK for advanced reaction handling.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Drug Discovery & Cheminformatics
---

# Cheminformatics

## Overview

Cheminformatics is the discipline of representing, searching, comparing, and
modeling small molecules in software. The core object is the `Mol` (molecular
graph) built from SMILES or InChI; from it we derive canonical forms,
fingerprints, substructures, descriptors, and 2D/3D conformations. RDKit is
the de-facto open-source standard, with Open Babel for format I/O and the
Chemistry Development Kit (CDK) used for Java-side workflows.

This skill wires RDKit, Open Babel, scikit-learn, TMAP, and UMAP into
copy-pasteable workflows: standardize a library, generate fingerprints and
similarity matrices, do SMARTS substructure search, compute physico-chemical
descriptors, perform R-group decomposition around a scaffold, run reaction
SMARTS, and visualize chemical space. Public benchmarks such as MoleculeNet
provide test sets for downstream ADMET and QSAR modeling.

## When to use this skill

- User needs to **standardize** SMILES/InChI, neutralize, desalt, deduplicate.
- User wants **SMARTS** substructure search across a compound library.
- User asks for **Morgan fingerprints**, **MACCS keys**, **Tanimoto similarity**, or
  **nearest-neighbor lookup**.
- User wants **Lipinski**, **Crippen LogP**, **TPSA**, or other **descriptors**.
- User wants **R-group decomposition** or **scaffold hopping** around a hit series.
- User wants to enumerate or apply **reaction SMARTS** (e.g. amide formation).
- User wants to visualize **chemical space** (TMAP, UMAP) or compare libraries.
- Skip for: docking and free energy calculations (use `drug-discovery`),
  ADMET/toxicity prediction (use `admet-prediction`), or retrosynthesis
  planning (use `retrosynthesis`).

## Prerequisites

- Python 3.10+ (3.11 recommended for RDKit 2024+ wheels).
- System tools: `obabel` (Open Babel) command line for batch format conversion.
- Python packages:

```bash
pip install rdkit openbabel-wheel scikit-learn umap-learn tqdm pandas matplotlib
pip install tmap tamkin  # for TMAP layouts
pip install molvs        # extra standardization rules
```

- Optional: `jpype1` + CDK for reaction enumeration requiring Java chemistry
  tooling; `mordred` for ~1800 descriptors; `selfies` for guaranteed-valid
  string representations for ML.

## Core workflows

### Standardization and canonical forms

Clean a list of messy SMILES through neutralization, salt stripping,
tautomer canonicalization, and deduplication by InChIKey.

```python
from rdkit import Chem
from rdkit.Chem.MolStandardize.rdMolStandardize import (
    StandardizeSmiles, TautomerEnumerator)

def standardize(smiles: str) -> str | None:
    m = Chem.MolFromSmiles(smiles)
    if m is None: return None
    m = StandardizeSmiles(m)          # neutralize, uncharge, desalt
    m = TautomerEnumerator().Canonicalize(m)  # canonical tautomer
    return Chem.MolToSmiles(m)

raw = ["c1ccccc1", "C1=CC=CC=C1", "CN(Br)c1ccccc1Cl", "[Na].[O-]C(=O)c1ccccc1"]
seen, kept = set(), []
for s in raw:
    std = standardize(s)
    if std is None: continue
    key = Chem.InchiToInchiKey(Chem.MolToInchi(Chem.MolFromSmiles(std)))
    if key not in seen:
        seen.add(key); kept.append(std)
print(kept)  # canonical, deduplicated
```

### Fingerprints and Tanimoto similarity

Build a Morgan fingerprint matrix and a Tanimoto similarity search index.

```python
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem

mols = [Chem.MolFromSmiles(s) for s in ["CCO", "CCCO", "c1ccccc1", "CCC(=O)O"]]
fps = [AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=1024) for m in mols]

# Pairwise Tanimoto
sim = DataStructs.BulkTanimotoSimilarity(fps[0], fps)
print("sim to ethanol:", [round(x, 2) for x in sim])

# Nearest-neighbor lookup with a query
query = AllChem.GetMorganFingerprintAsBitVect(
    Chem.MolFromSmiles("c1ccccc1O"), 2, nBits=1024)
sims = DataStructs.BulkTanimotoSimilarity(query, fps)
best = max(range(len(sims)), key=sims.__getitem__)
print("nearest:", Chem.MolToSmiles(mols[best]), round(sims[best], 3))
```

### SMARTS substructure search

Find all anilides (aniline amide) and a Bayer-privileged scaffold in a
library.

```python
from rdkit import Chem

anilide = Chem.MolFromSmarts("[cX3]1ccccc1C(=O)N")
mols = [Chem.MolFromSmiles(s) for s in
        ["c1ccccc1NC(=O)C", "CC(=O)NCc1ccccc1", "O=C(Nc1ccccc1)C"]]
hits = [m for m in mols if m.HasSubstructMatch(anilide)]
for h in hits:
    atoms = h.GetSubstructMatches(anilide)
    print(Chem.MolToSmiles(h), "matches:", atoms)
```

### Descriptor and property calculation

Compute Lipinski and Crippen descriptors for a list of molecules.

```python
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, Lipinski, rdMolDescriptors

def descriptors(smiles: str) -> dict:
    m = Chem.MolFromSmiles(smiles)
    if m is None: return {}
    return {
        "MW": round(Descriptors.MolWt(m), 2),
        "LogP": round(Crippen.MolLogP(m), 2),
        "TPSA": round(rdMolDescriptors.CalcTPSA(m), 2),
        "HBD": Lipinski.NumHDonors(m),
        "HBA": Lipinski.NumHAcceptors(m),
        "RotB": Lipinski.NumRotatableBonds(m),
        "Rings": rdMolDescriptors.CalcNumRings(m),
        "violations": sum([
            Descriptors.MolWt(m) > 500, Crippen.MolLogP(m) > 5,
            Lipinski.NumHDonors(m) > 5, Lipinski.NumHAcceptors(m) > 10]),
    }

for s in ["CCO", "CC(=O)c1ccccc1O", "O=C(Nc1ccc(Cl)cc1)c1ccc(Cl)cc1"]:
    print(s, descriptors(s))
```

### R-group decomposition and reaction SMARTS

Decompose a series around a benzodiazepine core, then enumerate an amide
reaction to expand the library.

```python
from rdkit import Chem
from rdkit.Chem import AllChem, rdRGroupDecomposition

core = Chem.MolFromSmiles("c1ccc2c(c1)C(=O)N(CC)C2")
mols = [Chem.MolFromSmiles(s) for s in
        ["O=C1N(C)Cc2ccccc2C1", "O=C1N(CC)c2cc(Cl)ccc2C1"]]
res, unmatched = rdRGroupDecomposition.RGroupDecompose(
    [core], mols, asSmiles=True)
for r in res:
    print(r)  # dict of R1, R2, core smiles

# Enumerate an amide: acid + amine -> amide
rxn = AllChem.ReactionFromSmarts("[C:1][C:2](=[O:6])O[C:3]>>[C:1][C:2](=[O:6])[C:3]")
acids = [Chem.MolFromSmiles(s) for s in ["CC(=O)O", "c1ccccc1C(=O)O"]]
amines = [Chem.MolFromSmiles(s) for s in ["NCC", "Nc1ccccc1"]]
products = []
for a in acids:
    for b in amines:
        products.extend(rxn.RunReactants((a, b)))
print(f"{len(products)} amide products enumerated")
```

### Chemical space visualization with TMAP / UMAP

Project a Morgan FP matrix to 2D for library comparison.

```python
import numpy as np, tmap as tm
from rdkit import Chem
from rdkit.Chem import AllChem
from umap import UMAP

smiles_list = [...]  # list of SMILES
fps = [AllChem.GetMorganFingerprintAsBitVect(
    Chem.MolFromSmiles(s), 2, nBits=1024).ToList() for s in smiles_list]
X = np.array(fps, dtype=np.float32)

# TMAP layout (best for chemical space)
lf = tm.LSHForest(dimension=1024, number_of_trees=50)
lf.fit(X)
x_tmap, _ = lf.get_coords_2d()
print("TMAP shape:", x_tmap.shape)

# UMAP alternative
x_umap = UMAP(n_neighbors=15, min_dist=0.1, metric="jaccard").fit_transform(X)
```

## Best practices

- Always standardize before fingerprinting: salts, tautomers, and charges
  blow up Tanimoto neighborhoods.
- Use **2048-bit Morgan** with radius 2 (`AllChem.GetMorganFingerprintAsBitVect`)
  as a default; switch to 1024 for speed, 4096 for very large libraries.
- For substructure search, prefer **SMARTS** over SMILES: SMARTS captures
  aromaticity, ring closures, and atom-type queries (`[c]` not `C`).
- Generate **InChIKey** for deduplication; canonical SMILES can differ across
  RDKit versions but InChIKey first blocks are stable.
- Verify scaffold coverage after R-group decomposition: if `unmatched` > 5%
  your core SMARTS is wrong.
- Plot property distributions before QSAR: MW, LogP, TPSA should match the
  training domain before any prediction.
- Use **scikit-learn's `BulkTanimotoSimilarity`** (one query vs many) - it is
  10x faster than Python loops because it is C-backed.
- Benchmark new descriptors on **MoleculeNet** (BBBP, BACE, HIV, Tox21) before
  trusting them in production.
- When visualizing chemical space, use **TMAP** (preserve topology) for
  publications; UMAP for compact layouts in dashboards.

## Common pitfalls

- Mixing `MolToSmiles` and `MolFromSmiles` without `sanitize=True` produces
  invalid stereochemistry flags.
- Forgetting `Chem.AddHs(m)` before generating 3D conformers gives nonsense
  geometries (no hydrogens to embed).
- Using **MACCS** keys for substructure search: MACCS is a hashed structural
  key, not invertible - use SMARTS for substructure filtering.
- Reading SDF with `Chem.SDMolSupplier` and not calling `.atEnd` / not
  checking for `None` molecules silently drops corrupt entries.
- Storing Morgan fingerprints as Python `int` bitsets instead of
  `ExplicitBitVect` blows up memory 8x; use `BitVectToList` only at I/O.
- Comparing across tautomers: an enol-keto pair can have Tanimoto 0.3 even
  though they are chemically equivalent. Always tautomer-canonicalize.
- Believing **"similar molecules have similar properties"** without checking
  the applicability domain (Tanimoto < 0.4 to training set = unreliable).

## Worked example

A medicinal chemist provides 1000 Enamine REAL smiles. Goal: standardize,
deduplicate, compute descriptors, filter by Lipinski + PAINS, and visualize
chemical space colored by LogP.

```python
import pandas as pd, numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen, AllChem, FilterCatalog
from rdkit.Chem.MolStandardize.rdMolStandardize import StandardizeSmiles
from umap import UMAP
import matplotlib.pyplot as plt

df = pd.read_csv("library.smi", sep="\t", names=["smiles", "id"])
df["std"] = df.smiles.map(lambda s: Chem.MolToSmiles(
    StandardizeSmiles(Chem.MolFromSmiles(s))))
df = df.drop_duplicates("std").reset_index(drop=True)
df["mol"] = df["std"].map(Chem.MolFromSmiles)

# Filters: Lipinski + PAINS
params = FilterCatalog.FilterCatalogParams()
params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
pains = FilterCatalog.FilterCatalog(params)

def ok(m):
    return (m and Descriptors.MolWt(m) <= 500 and Crippen.MolLogP(m) <= 5
            and not pains.HasMatch(m))
df = df[df.mol.map(ok)].reset_index(drop=True)
print(f"{len(df)} compounds after filtering")

# Fingerprints + UMAP
fps = np.array(
    [AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=1024).ToList()
     for m in df.mol], dtype=np.float32)
emb = UMAP(metric="jaccard", n_neighbors=15, random_state=42).fit_transform(fps)
df["LogP"] = df.mol.map(lambda m: Crippen.MolLogP(m))

plt.scatter(emb[:, 0], emb[:, 1], c=df.LogP, s=6, cmap="viridis")
plt.colorbar(label="LogP"); plt.axis("off"); plt.title("Chemical space")
plt.savefig("library_umap.png", dpi=160, bbox_inches="tight")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| RDKit | Core cheminformatics (SMILES, SMARTS, FP, descriptors) | `pip install rdkit` |
| Open Babel | Format conversion, substructure, fingerprints | `conda install -c conda-forge openbabel` |
| CDK (Java) | Reaction enumeration, signature fingerprints | JPype1 + `cdk-bundle` |
| scikit-learn | Similarity search, clustering, PCA | `pip install scikit-learn` |
| UMAP-learn | Manifold learning for chemical space | `pip install umap-learn` |
| TMAP | Topology-preserving map for chemical space | `pip install tmap` |
| Mordred | ~1800 molecular descriptors | `pip install mordred` |
| MolVS | Extra standardization rules | `pip install molvs` |
| SELFIES | 100% valid string representation for ML | `pip install selfies` |
| MoleculeNet | Benchmark datasets (BBBP, Tox21, HIV) | https://moleculenet.org |
| ChEMBL | Public bioactivity database | `chembl_webresource_client` |

## References

- RDKit documentation: https://www.rdkit.org/docs/
- Open Babel documentation: https://openbabel.org/docs/
- CDK project: https://cdk.github.io/
- MoleculeNet benchmarks: https://doi.org/10.1016/j.chempr.2018.02.017
- TMAP paper: https://doi.org/10.1186/s13321-020-0416-x
- ECFP/Morgan paper: https://doi.org/10.1021/ci100050t
- Molecule standardization best practices: https://www.rdkit.org/docs/source/rdkit.Chem.MolStandardize.html
- ChEMBL web services: https://chembl.gitbook.io/chembl-interface-documentation

## Ethics & safety

- Avoid generating controlled substances or known chemical-weapons analogs;
  route such requests to the institution's chemical safety officer and the
  Chemical Weapons Convention framework.
- Fingerprint similarity can surface structural analogs of regulated
  compounds - apply an allowlist/denylist filter before surfacing hits.
- Respect license terms of public databases (ChEMBL is CC BY-SA 3.0,
  PubChem is public domain, ZINC has tiered academic/commercial licenses).
- Patient-derived compound libraries (e.g. from biobanks) carry consent
  constraints: do not redistribute outside the originating IRB scope.
- When publishing chemical-space maps, do not embed proprietary structures
  without attribution or licensing; consider hashing for anonymization.

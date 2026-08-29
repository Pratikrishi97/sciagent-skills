# Example: virtual screen against SARS-CoV-2 main protease

**Skills activated:** `drug-discovery`, `cheminformatics`, `admet-prediction`

## The prompt

> Screen the Enamine REAL diversity set (~1.6M compounds) against the SARS-CoV-2 main protease (PDB 6LU7). Apply Lipinski + PAINS filters, prep the receptor, dock with AutoDock Vina in a box around the catalytic dyad (His41/Cys145) at exhaustiveness=32, rank by Vina score, and shortlist the top 50 for ADMET (hERG, CYP3A4, BBB, solubility).

## What the agent does

`cheminformatics` activates on `RDKit`, `Lipinski`, `PAINS`; `drug-discovery` on `6LU7`, `AutoDock Vina`, `exhaustiveness`; `admet-prediction` for the final triage.

### 1. Load + filter the library

```python
# pip install rdkit-pypi pandas
from rdkit import Chem
from rdkit.Chem import Crippen, Lipinski, Filters
import pandas as pd

def passes_rules(mol):
    if mol is None: return False
    if Lipinski.NumHDonors(mol) > 5 or Lipinski.NumHAcceptors(mol) > 10: return False
    if Crippen.MolLogP(mol) > 5: return False
    if mol.GetNumHeavyAtoms() > 35: return False  # diversity-set cutoff
    return True

# stream SMI in chunks to keep memory bounded
supplier = Chem.SmilesMolSupplier("enamine_diversity.smi", delimiter="\t", titleLine=False)
kept = [m for m in supplier if passes_rules(m)]
print(f"after Lipinski: {len(kept):,}")
```

### 2. PAINS filter

```python
from rdkit.Chem import FilterCatalog
pains = FilterCatalog.FilterCatalogParams()
pains.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
catalog = FilterCatalog.FilterCatalog(pains)
kept = [m for m in kept if not catalog.HasMatch(m)]
```

### 3. Prepare ligands (3D protonation) + receptor

```bash
# protonate + 3D embed + write as SDF
obabel enamine_filtered.smi -O ligands_3d.sdf --gen3d -p 7.4

# prepare the receptor (6LU7 minus the co-crystallized ligand)
prepare_receptor4.py -r 6LU7_noLig.pdb -o 6LU7_receptor.pdbqt
# or: AutoDockTools / Meeko for the box
```

### 4. Dock with Vina

```python
# pip install vina
from vina import Vina
v = Vina(sf_name="vina", seed=1, exhaustiveness=32, num_modes=9)
v.set_receptor("6LU7_receptor.pdbqt")
# catalytic dyad center ~ (-22, 25, 5), box 25 A
v.compute_vina_maps(center=[-22.0, 25.0, 5.0], box_size=[25, 25, 25])
import pandas as pd
top = []
for i, mol in enumerate(Chem.SDMolSupplier("ligands_3d.sdf")):
    mol_pdbqt = f"tmp/lig_{i}.pdbqt"
    # convert via Meeko
    v.set_ligand_from_file(mol_pdbqt)
    v.dock()
    e = v.score()
    top.append((mol.GetProp("_Name"), e[0]))
df = pd.DataFrame(top, columns=["compound","vina_score"]).sort_values("vina_score")
df.head(50).to_csv("top50.csv", index=False)
```

### 5. ADMET triage

```python
# pip install deepchem tensorflow  (or chemprop)
from rdkit import Chem
from deepchem.models import MultitaskRegressor
# load pretrained ADMET models from MoleculeNet (Tox21, hERG, BBB, solubility)
# or query the TDC benchmark hub
```

## Pitfalls the skill surfaces

- The Vina box must enclose the catalytic dyad (His41/Cys145), not the whole protein — docking the whole surface wastes compute and finds spurious hits.
- PAINS filters are advisory, not disqualifying — flag, don't discard, then manually inspect the top hits for known reactive groups.
- Vina scoring is a *ranking* heuristic, not a binding free energy; top-50 hits need FEP or at least a re-dock check before synthesis.
- Protonate at the assay pH (7.4) before 3D embedding — charged states change docking scores by several kcal/mol.

## Ethics & safety

Virtual screening of an existing, public target against a public library is routine open research. The skill refuses weaponization framing and points to institutional review for any pathogen-related wet-lab step.

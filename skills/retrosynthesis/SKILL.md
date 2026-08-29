---
name: retrosynthesis
description: Plan and score retrosynthetic routes for small-molecule targets using template-based (AiZynthFinder from IBM), neural-symbolic (ASKCOS from MIT), and graph-to-graph models. Covers building-block lookup against Enamine and Sigma-Aldrich, reaction class prediction, synthetic accessibility (SA score), route scoring, and one-pot/parallel synthesis planning. Use this skill whenever the user asks about retrosynthesis, synthetic accessibility, route planning, reaction templates, building blocks, AiZynthFinder, ASKCOS, Synthia, or RDKit reaction handling. Trigger keywords include retrosynthesis, AiZynthFinder, ASKCOS, building blocks, SA score, USPTO, reaction templates, parallel synthesis.
license: MIT
compatibility: Requires Python 3.10+ with rdkit, networkx, scipy, and one of: aizynthfinder (IBM), askcos-client, or a local USPTO template model. Optional: rxn4chemistry (IBM RXN service) for cloud-based route prediction.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Drug Discovery & Cheminformatics
---

# Retrosynthesis

## Overview

Retrosynthesis plans the synthetic route from commercially available
building blocks to a target molecule by repeatedly applying **reaction
templates** that break bonds in the target until every leaf is purchasable.
Three algorithm families dominate: (1) **template-based** methods like
AiZynthFinder (IBM) and ASKCOS (MIT) that match the target against a library
of reaction templates extracted from USPTO + Reaxys; (2) **neural
graph-to-graph** models that predict the next reaction step directly; and
(3) **hybrid** systems (Synthia, IBM RXN) that combine both.

A retrosynthesis pipeline needs (a) a template library or trained model,
(b) a building-block catalog (Enamine REAL, Sigma-Aldrich, MolPort), (c) a
**synthetic accessibility (SA) score** to rank routes, and (d) a route
scorer that prices the route and counts steps. This skill wires RDKit,
AiZynthFinder, ASKCOS, the SA scorer from RDKit contrib, and the Enamine
catalog lookup into copy-pasteable workflows.

## When to use this skill

- User asks for a **synthesis route** or **synthetic plan** for a target SMILES.
- User asks whether a molecule is **synthetically accessible**.
- User mentions **AiZynthFinder**, **ASKCOS**, **Synthia**, **IBM RXN**, **route
  planning**, **reaction templates**.
- User asks to find **building blocks** at Enamine, Sigma, or MolPort.
- User wants to score or compare **alternative routes**.
- User asks for **parallel synthesis** or **one-pot** route optimization.
- Skip for: forward reaction prediction alone (use `cheminformatics` reaction
  SMARTS), or ADMET/docking (use those skills).

## Prerequisites

- Python 3.10+ (3.11 recommended).
- System tools: none mandatory; AiZynthFinder ships a USPTO template pack.
- Python packages:

```bash
pip install rdkit aizynthfinder networkx scipy pandas
pip install rd_filters  # SA score + REOS filters
# Optional: askcos2_client (for the MIT cloud ASKCOS service)
# Optional: rxn4chemistry (IBM RXN service, requires API key)
```

- Templates and models:
  - AiZynthFinder USPTO template model (~3 GB) via `aizynthfinder.download_model`
    or hosted locally.
  - Enamine building-block catalog (SMILES + compound_id) - download from
    Enamine REAL (academic license).

## Core workflows

### Synthetic accessibility (SA) score

Quick triage with the RDKit contrib SA scorer (1 = easy, 10 = impossible).

```python
from rdkit import Chem
from rdkit.Chem import RDConfig
import os, sys
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
from sascorer import calculateScore

for s in ["c1ccccc1", "CC(=O)c1ccccc1O",       # aspirin (easy)
          "C[C@@H]1[C@@H]2CC[C@H]3C[C@@H](O)C4CC[C@@H](O)C[C@H]34",
          "CN1c2ccccc2Sc2ccc(Cl)cc21"]:           # complex scaffold
    print(f"{s[:40]:40s} SA={calculateScore(Chem.MolFromSmiles(s)):.2f}")
```

### Template-based retrosynthesis with AiZynthFinder

Run AiZynthFinder with USPTO templates and a stock file of building blocks.

```python
from aizynthfinder.aizynthfinder import AiZynthFinder

finder = AiZynthFinder(
    configfile="aizynthfinder/config.yml",
    templatefile="uspto_templates.h5",   # USPTO 50k template model
    stockfile="enamine_stock.h5",         # building-block catalog
)

finder.target_smiles = "c1ccc(NC(=O)c2ccccc2)cc1"
finder.tree_search()                # MCTS exploration
finder.build_routes()
route = finder.routes[0]
print(f"steps: {len(route.reactions)}")
print(f"in stock: {route.in_stock_count}/{route.total_leaf_count}")
route.to_image().save("route.png")  # SVG/PNG tree visualization
```

### Reaction class prediction (USPTO)

Predict the reaction class for a forward reaction, useful for filtering
templates in route scoring.

```python
from rdkit import Chem
from rxn4chemistry import RXN4ChemistryWrapper  # IBM RXN client
import os

# Local alternative: train a classifier on USPTO 1k-class data
# (use sklearn + Morgan FP to predict USPTO reaction class)
# from sklearn.ensemble import RandomForestClassifier
# model = RandomForestClassifier().fit(X_train, y_train)

rxn = RXN4ChemistryWrapper(os.environ["IBM_RXN_API_KEY"])
predict_response = rxn.predict_reaction(
    "CC(=O)O.c1ccccc1N")               # acid + aniline
# Returns amide-bond formation + product + confidence
print(predict_response)
```

### Building block lookup against Enamine and Sigma

Given a target's precursors, check which are purchasable.

```python
import pandas as pd
from rdkit import Chem
from rdkit.Chem.MolStandardize.rdMolStandardize import StandardizeSmiles

# Load building-block catalog (preprocessed to InChIKey -> catalog_id)
bb = pd.read_hdf("enamine_stock.h5")  # columns: smiles, catalog_id, price_usd
bb_keys = {row.inchikey: row.catalog_id for row in bb.itertuples()}

def lookup(smiles: str) -> dict:
    m = Chem.MolFromSmiles(StandardizeSmiles(Chem.MolFromSmiles(smiles)))
    key = Chem.MolToInchi(m).split("=")[-1]  # truncate InChIKey
    cat_id = bb_keys.get(key)
    return {"purchasable": bool(cat_id), "catalog_id": cat_id}

for s in ["c1ccccc1", "O=C(O)c1ccccc1", "Nc1ccccc1", "Cc1ccccc1"]:
    print(s, lookup(s))
```

### Route scoring and comparison

Score routes by step count, building-block coverage, and SA score; recommend
the cheapest/most accessible.

```python
import pandas as pd
from rdkit.Chem import RDConfig
import os, sys
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
from sascorer import calculateScore
from rdkit import Chem

def score_route(steps: list[dict]) -> dict:
    """steps: list of {'precursors': [...], 'product': str}"""
    sa_total = 0
    in_stock = 0
    for st in steps:
        for s in st["precursors"] + [st["product"]]:
            m = Chem.MolFromSmiles(s)
            if m is not None:
                sa_total += calculateScore(m)
        in_stock += sum(1 for s in st["precursors"] if lookup(s)["purchasable"])
    return {
        "n_steps": len(steps),
        "sa_avg": round(sa_total / max(1, 3 * len(steps)), 2),
        "bb_coverage": in_stock / max(1, 2 * len(steps)),
    }

route_a = score_route([{"precursors": ["CC(=O)O", "Nc1ccccc1"],
                        "product": "CC(=O)Nc1ccccc1"}])
print(route_a)
```

### Parallel synthesis planning

Score a 96-well plate design: enumerate reactant combinations and rank by
SA score and route feasibility.

```python
import itertools
from rdkit import Chem
from rdkit.Chem import AllChem
import pandas as pd

acids = ["CC(=O)O", "c1ccccc1C(=O)O", "O=C(O)c1ccccc1O"]
amines = ["NCC", "Nc1ccccc1", "CC(=O)NCCN", "Nc1ccc(O)cc1"]
amidation = AllChem.ReactionFromSmarts(
    "[C:1][C:2](=[O:6])O.[NH2:3][C:4]>>[C:1][C:2](=[O:6])[NH:3][C:4]")

rows = []
for a, n in itertools.product(acids, amines):
    products = amidation.RunReactants(
        (Chem.MolFromSmiles(a), Chem.MolFromSmiles(n)))
    if products:
        smi = Chem.MolToSmiles(products[0][0])
        rows.append({"acid": a, "amine": n, "product": smi})
pd.DataFrame(rows).to_csv("96_well_amides.csv", index=False)
print(f"{len(rows)} amides enumerated for the plate")
```

## Best practices

- Always start with the **SA score** for quick triage; a target with SA >
  6 needs human review before route planning.
- Use template-based planners (AiZynthFinder, ASKCOS) for **small-med-chem
  scaffolds**; graph-to-graph models are stronger for complex polycyclics.
- Keep the building-block stock file **versioned**; Enamine REAL adds ~50k
  new compounds per release and old SMILES can become unstocked.
- **Cost the route**: assign $ to each building block and weight by step
  count; a 4-step route with $500 precursors may be cheaper than a 2-step
  route with $50k chiral auxiliaries.
- Reconcile **stereochemistry**: retrosynthesis with a stereocenter
  requires either chiral building blocks or asymmetric steps; flag racemic
  retrosynthesis explicitly.
- Use **MCTS** with at least 1000 rollouts for non-trivial targets
  (AiZynthFinder default is 100); increase for rare scaffolds.
- Score and rank **3-5 routes**, never trust a single route; routes fail at
  the bench 30% of the time.
- Cross-check reaction conditions against **Reaxys** or **Pistachio**;
  template predicted reactions may have unrealistic conditions.
- For library synthesis, prefer **robust reactions** (amide formation,
  Suzuki, Buchwald) over sensitive ones (Mitsunobu, ozonolysis).
- Run **REOS** (RDKit's `rd_filters`) for problematic-substructure filtering
  before declaring a route viable.

## Common pitfalls

- Treating retrosynthesis output as ground truth: real-world yields and
  conditions are not in the model; bench chemistry always disagrees.
- Ignoring **protecting groups**: routes that work on paper often need PGs
  for orthogonality, lengthening the actual synthesis by 2-4 steps.
- Missing **functional-group compatibility** (e.g. acid + alcohol ester when
  an amide was expected) - template-based models can mismatch.
- Trusting building-block SMILES without canonicalization; tautomers and
  salts defeat exact-string matching.
- Forgetting **scale-up considerations**: a route viable at 1 mg may
  catastrophically fail at 1 g (exotherms, solubility, purification).
- Using templates trained on USPTO for non-pharma scaffolds (agrochemicals,
  materials) - the template distribution is biased.
- Skipping SA-score triage and going straight to AiZynthFinder wastes 30
  minutes of MCTS on impossible targets.

## Worked example

Goal: plan a synthesis for a candidate BACE1 inhibitor SMILES, score three
routes, and select the cheapest.

```python
import pandas as pd
from rdkit import Chem
from aizynthfinder.aizynthfinder import AiZynthFinder
from rdkit.Chem import RDConfig
import os, sys
sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
from sascorer import calculateScore

target = "O=C(Nc1ccc(F)cc1)c2ccc(C(F)(F)F)cc2"
m = Chem.MolFromSmiles(target)
print(f"SA score: {calculateScore(m):.2f}")  # quick triage

# Run AiZynthFinder (template-based)
finder = AiZynthFinder(
    configfile="aizynthfinder/config.yml",
    templatefile="uspto_templates.h5",
    stockfile="enamine_stock.h5",
)
finder.target_smiles = target
finder.tree_search()
finder.build_routes()
print(f"{len(finder.routes)} routes found")

# Score each route
rows = []
for i, route in enumerate(finder.routes):
    leafs = route.leafs_chemicals  # list of SMILES for leaves
    bb_count = sum(1 for s in leafs if "in_stock" in route.stock_status(s))
    rows.append({
        "route": i,
        "steps": len(route.reactions),
        "leaves": len(leafs),
        "in_stock": bb_count,
        "coverage": round(bb_count / max(1, len(leafs)), 2),
        "sa_avg": round(sum(calculateScore(Chem.MolFromSmiles(s))
                           for s in leafs) / max(1, len(leafs)), 2),
    })
report = pd.DataFrame(rows).sort_values("coverage", ascending=False)
print(report)
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| AiZynthFinder | IBM template-based retrosynthesis (MCTS) | `pip install aizynthfinder` |
| ASKCOS | MIT neural-symbolic retrosynthesis | https://github.com/connorcoley/ASKCOS |
| Synthia (commercial) | Merck expert retrosynthesis system | license required |
| IBM RXN | Cloud-based retrosynthesis (free tier) | `pip install rxn4chemistry` |
| RDKit SA scorer | Synthetic accessibility heuristic | bundled in RDKit contrib |
| rd_filters | REOS + PAINS-style problematic substructure filters | `pip install rd_filters` |
| Reaxys | Literature reaction database | Elsevier subscription |
| Pistachio | NextMove reaction database (USPTO-based) | https://www.nextmovesoftware.com |
| USPTO dataset | 1M+ extracted reactions for training | https://figshare.com/articles/dataset/ |
| Enamine REAL | Building-block catalog (~10B make-on-demand) | https://enamine.net |
| Sigma-Aldrich | Purchasable building-block catalog | https://www.sigmaaldrich.com |

## References

- AiZynthFinder paper: https://doi.org/10.26434/chemrxiv.13033824
- ASKCOS paper: https://doi.org/10.1016/j.chempr.2018.10.006
- USPTO reaction extraction: https://doi.org/10.1021/acs.jcim.9b00235
- IBM RXN service: https://rxn.res.ibm.com
- SA score paper: https://doi.org/10.1186/s13321-018-0322-0
- AiZynthFinder documentation: https://github.com/MolecularAI/aizynthfinder
- Enamine REAL space: https://enamine.net/compound-collections/real-compounds
- Pistachio database: https://www.nextmovesoftware.com/pistachio.html

## Ethics & safety

- Retrosynthesis planning can identify routes to controlled substances,
  chemical-warfare precursors, regulated toxins, or their direct analogs.
  **Do not** provide retrosynthetic routes for known chemical weapons,
  regulated narcotics, or dual-use toxins; route such requests to the
  institution's chemical safety officer and applicable treaty frameworks
  (CWC, BWC, single convention on narcotic drugs).
- When a building-block catalog includes watch-list precursors, flag them
  and require institutional authorization before surfacing.
- Patent and IP: routes derived from Reaxys/Pistachio reflect published
  procedures; respect Elsevier and NextMove licensing terms and do not
  redistribute proprietary reaction data outside the licensed scope.
- For chiral auxiliaries and reagents subject to export control (e.g.
  certain catalysts), do not facilitate procurement bypassing customs.
- Reaction conditions may include hazardous reagents (HF, NaN3, heavy
  metals); always cross-reference an institutional SOP and a chemical
  hygiene plan before scaling. Surface only at a high level in chat output.

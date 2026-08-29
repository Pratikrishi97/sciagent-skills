---
name: protein-analysis
description: Protein sequence and structure analysis toolkit covering BioPython SeqIO and pairwise alignment, Bio.PDB and biotite for PDB parsing, DSSP for secondary structure, AlphaFold structures from EBI and FoldSeek remote homology search, PyMOL scripting for visualization, P2Rank for ligand-binding pocket detection, HDOCK protein-protein docking, OpenMM for molecular dynamics setup, and UniProt, InterPro, Pfam, and PDB for annotation. Use this skill whenever the user asks about protein structure, AlphaFold, FoldSeek, PyMOL, DSSP, P2Rank, HDOCK, OpenMM, UniProt, InterPro, Pfam, PDB parsing, secondary structure, binding pockets, or docking.
license: MIT
compatibility: Requires Python 3.10+ with biopython, biotite, numpy, matplotlib. System tools PyMOL, DSSP (mkdssp), P2Rank, HDOCK, OpenMM. Optional: pdb-tools, pdb2pqr, mdtraj.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Biology & Genomics
---

# Protein Analysis

## Overview

Protein analysis spans sequence (1D), structure (3D), dynamics (4D),
and interactions (complexes). On the sequence side, **BioPython** and
**biotite** parse FASTA, run pairwise and multiple alignments, and
fetch annotations from **UniProt**, **InterPro**, and **Pfam**. On the
structure side, **Bio.PDB** and **biotite** parse PDB and mmCIF files,
**DSSP** assigns secondary structure, **AlphaFoldDB** hosts predicted
structures for almost every UniProt entry, and **FoldSeek** finds
remote homologs by structural alignment. For docking, **P2Rank**
detects ligand-binding pockets, **HDOCK** predicts protein-protein
complexes, and **OpenMM** sets up molecular dynamics. **PyMOL** is the
standard for publication figures.

This skill wires the stack together with copy-pasteable Python
snippets and clear file-format expectations.

## When to use this skill

- User asks to **parse or manipulate** a PDB or mmCIF file.
- User wants to fetch and inspect an **AlphaFold** predicted structure.
- User asks for **FoldSeek** remote homology search.
- User wants **secondary structure** assignment with DSSP.
- User asks for **binding pocket** detection with P2Rank.
- User wants **protein-protein docking** with HDOCK or HADDOCK.
- User needs to set up **molecular dynamics** with OpenMM or OpenMM-
  based force fields (AMBER, CHARMM).
- User wants to render a **PyMOL** publication figure.
- User mentions **UniProt**, **InterPro**, **Pfam**, **PDB**,
  **AlphaFoldDB**, **Ramachandran plot**.
- Skip for: small-molecule docking and ADMET (use `drug-discovery`),
  variant calling (use `genomics`), differential protein abundance
  from mass-spec (use `proteomics`).

## Prerequisites

- Python 3.10+ (3.11 recommended for biotite and OpenMM wheels).
- System tools: `pymol` (open-source build), `mkdssp`, `prank`
  (P2Rank), `hdock` (HDOCK), `pdb-tools` (pip).
- Python packages:

```bash
pip install biopython biotite numpy matplotlib pdb-tools
pip install openmm mdtraj pdb2pqr  # MD workflows
# Optional: py3Dmol for inline notebook visualization
pip install py3Dmol
```

- Reference data: AlphaFoldDB structure downloads from EBI (per-UNIROT
  ID), FoldSeek database (AlphaFold/Proteome) for remote homology.

## Core workflows

### Sequence parsing, alignment, and UniProt annotation with BioPython

Read a FASTA, run pairwise alignment, fetch UniProt annotation, and
translate a coding sequence.

```python
from Bio import SeqIO, pairwise2, ExPASy
from Bio.SeqUtils import seq1
# Parse a FASTA
recs = list(SeqIO.parse("kinases.fasta", "fasta"))
print(f"{len(recs)} sequences; first length {len(recs[0].seq)}")

# Pairwise global alignment (Needleman-Wunsch)
aln = pairwise2.align.globalms(recs[0].seq, recs[1].seq,
                               2, -1, -1, -0.5, one_alignment_only=True)[0]
print(f"score={aln.score}, identity={sum(a==b for a,b in zip(aln.seqA, aln.seqB))/len(aln.seqA):.2f}")

# Fetch UniProt annotation (requires internet; rate-limited)
import requests
r = requests.get("https://www.ebi.ac.uk/proteins/api/features/P04637",
                 headers={"Accept": "application/json"})
features = r.json()
print(f"{features['accession']}: {len(features.get('features', [])} features")
```

### PDB/mmCIF parsing with Bio.PDB and biotite

Load a structure, extract chain A, and compute backbone dihedral
angles.

```python
from Bio.PDB import PDBParser, MMCIFParser
import numpy as np
parser = PDBParser(QUIET=True)
struct = parser.get_structure("1AKE", "1ake.pdb")
chainA = struct["A"]
# Extract CA coordinates
ca = np.array([res["CA"].get_coord() for res in chainA
               if "CA" in res])
print(f"chain A has {len(ca)} CA atoms")

# biotite: Ramachandran angles in a few lines
import biotite.structure as bs, biotite.structure.io.pdb as pdb
file = pdb.PDBFile.read("1ake.pdb")
atom_array = pdb.get_structure(file)
# phi/psi require peptide bonds; biotite has a helper
from biotite.structure import backbone
phi, psi, _ = backbone.dihedral_backbone(atom_array)
print("phi range:", round(np.nanmin(phi), 1), round(np.nanmax(phi), 1))
```

### AlphaFold structures and FoldSeek remote homology

Fetch an AlphaFold predicted structure and run FoldSeek for remote
homologs.

```python
import subprocess, requests, os
# Download AlphaFold PDB for UniProt P04637 (p53)
af_url = "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v4.pdb"
with open("p53_af.pdb", "wb") as fh: fh.write(requests.get(af_url).content)

# Build FoldSeek database and search against AlphaFold/Proteome
subprocess.run(["foldseek", "createdb", "p53_af.pdb", "query_db"], check=True)
subprocess.run(["foldseek", "search", "query_db",
                "afdb50", "result.m8", "tmp",
                "--alignment-type", "2", "-e", "0.001"], check=True)
# result.m8 is BLAST-tab format with TM-score
import pandas as pd
hits = pd.read_csv("result.m8", sep="\t",
    names=["query","target","fident","alnlen","mismatch","gapopen",
           "qstart","qend","tstart","tend","evalue","bits"])
print(hits.nsmallest(5, "evalue")[["target","fident","evalue"]])
```

### Secondary structure with DSSP and pocket detection with P2Rank

Run DSSP on a structure and P2Rank to find ligand-binding pockets.

```python
import subprocess, pandas as pd
# DSSP -> assign H, E, C secondary structure
subprocess.run(["mkdssp", "1ake.pdb", "1ake.dssp"], check=True)
# biotite parses the DSSP output
import biotite.structure.io.dssp as dssp
file = open("1ake.dssp").read()
ss = dssp.DsspFile.read(file)
print(ss["sec_struct"][:20])  # H=helix, E=strand, C=coil

# P2Rank pocket detection
subprocess.run(["prank", "predict", "-f", "1ake.pdb",
                "-o", "prank_out", "-c"], check=True)
pockets = pd.read_csv("prank_out/1ake.pdb_predictions.csv")
print(pockets.nlargest(3, "score")[["name", "score", "center_x"]])
```

### PyMOL scripting and OpenMM MD setup

Render a publication figure with PyMOL and prepare an OpenMM
simulation.

```python
# PyMOL scripting (run via `pymol -c script.py` or `pymol script.pml`)
pml = """
load 1ake.pdb
bg_color white
hide everything, all
show cartoon, chain A
color salmon, chain A
show sticks, resn ATP
color lime, resn ATP
set ray_shadows, 0
ray 2400, 2400
png 1ake.png, dpi=300
"""
open("1ake.pml","w").write(pml)
import subprocess
subprocess.run(["pymol", "-c", "-q", "1ake.pml"], check=True)

# OpenMM setup: solvate a PDB and run a short NVT minimization
from openmm.app import *
from openmm import *
from openmm.unit import *
pdb = PDBFile("1ake_vacuum.pdb")     # protonated + cleaned
forcefield = ForceField("amber14-all.xml", "amber14/tip3p.xml")
modeller = Modeller(pdb.topology, pdb.positions)
modeller.addHydrogens(forcefield, pH=7.0)
modeller.addSolvent(forcefield, padding=1*nanometer, neutralize=True)
system = forcefield.createSystem(modeller.topology,
                                 nonbondedMethod=PME, nonbondedCutoff=1*nanometer,
                                 constraints=HBonds)
integrator = LangevinIntegrator(300*kelvin, 1/picosecond, 2*femtoseconds)
sim = Simulation(modeller.topology, system, integrator)
sim.context.setPositions(modeller.positions)
sim.minimizeEnergy(maxIterations=200)
sim.step(1000)   # 2 ps of NVT
state = sim.context.getState(getPositions=True)
PDBFile.writeFile(sim.topology, state.getPositions(),
                  open("1ake_min.pdb", "w"))
```

## Best practices

- Always **clean** a PDB before MD or docking: remove waters and
  heteroatoms, add missing hydrogens, cap termini, and resolve
  alternate locations with `pdb-tools` (`pdb_selaltloc`, `pdb_delhetatm`,
  `pdb_tidy`).
- Use **AlphaFold pLDDT** as a confidence map: residues with pLDDT
  < 50 are disordered and should not be treated as reliable structure.
- For **FoldSeek**, prefer the AFDB50 database (clustered at 50% seq id)
  for remote homology; full AFDB is too large for ad-hoc searches.
- Run **P2Rank** on the protein with ligand removed (use
  `pdb_delhetatm`) to avoid the trivial self-prediction of the
  co-crystallized ligand site.
- Validate docking models with **HADDOCK or HDOCK** plus manual
  inspection of interface contacts in PyMOL; never report a single
  top-1 docked pose without showing the interface residue network.
- For OpenMM MD, equilibrate (NVT then NPT) before production; running
  production directly from minimization will crash with large forces.
- Use **PDBFixer** or **PDB2PQR** to add hydrogens at a target pH
  before assigning force-field parameters - raw PDBs are missing H
  atoms.
- For Ramachandran analysis, exclude prolines, glycines, and residues
  before a break; outliers often flag register errors.
- When downloading AlphaFold models, prefer the **model_v4** or
  **model_v5** (higher quality) and record the version in metadata.

## Common pitfalls

- Trusting **AlphaFold multimer** predictions for complexes without
  iptTM or pAE confidence scores - low-confidence interfaces are
  indistinguishable from high-confidence ones in the PDB output.
- Forgetting to add hydrogens before MD - the integrator blows up
  because the force field requires explicit H atoms.
- Using **CA-only** structures for docking - HDOCK and HADDOCK need
  all heavy atoms; AlphaFold models have all heavy atoms but PDB
  low-resolution structures may not.
- Mixing **PDB v2 and v3** atom-naming conventions across files -
  AMBER and CHARMM force fields will reject the residue mapping.
- Calling P2Rank pockets on the entire asymmetric unit when ligand is
  present - the bound ligand masks the pocket.
- Treating **FoldSeek's TM-score** as a p-value - it is a structural
  similarity metric; report it alongside e-value and alignment length.
- Forgetting to **protonate** titratable residues at the simulation pH
  with PDB2PQR - the wrong protonation state invalidates a 100-ns
  trajectory.
- Reporting a docking score as binding affinity - HDOCK's score is a
  shape/electrostatics heuristic, not free energy; use MM/PBSA or FEP
  for estimates.

## Worked example

Fetch the AlphaFold model for human p53, find remote homologs with
FoldSeek, assign secondary structure with DSSP, detect the DNA-binding
surface pocket with P2Rank, and render a PyMOL figure.

```python
import subprocess, pandas as pd, requests, os
from openmm.app import PDBFile
import biotite.structure.io.pdb as pdb
import biotite.structure.io.dssp as dssp

# 1) Download AlphaFold p53 model
af_url = "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v4.pdb"
open("p53_af.pdb","wb").write(requests.get(af_url).content)

# 2) FoldSeek remote homology in AFDB50
subprocess.run(["foldseek","createdb","p53_af.pdb","q_db"], check=True)
subprocess.run(["foldseek","search","q_db","afdb50","res.m8","tmp",
                "-e","0.001","--alignment-type","2"], check=True)
hits = pd.read_csv("res.m8", sep="\t", header=None,
    names=["q","t","fid","aln","mm","g","qs","qe","ts","te","ev","bits"])
print(f"{len(hits)} remote homologs, top e-value {hits.ev.min():.1e}")

# 3) DSSP secondary structure
subprocess.run(["mkdssp","p53_af.pdb","p53.dssp"], check=True)
ss = dssp.DsspFile.read(open("p53.dssp").read())
import numpy as np
helix = (ss["sec_struct"] == "H").sum()
sheet = (ss["sec_struct"] == "E").sum()
coil = (ss["sec_struct"] == "C").sum()
print(f"helix {helix}  sheet {sheet}  coil {coil}")

# 4) P2Rank pocket detection (remove waters/heteroatoms first)
subprocess.run(["pdb_delhetatm","p53_af.pdb"], stdout=open("p53_clean.pdb","w"))
subprocess.run(["prank","predict","-f","p53_clean.pdb","-o","prank","-c"], check=True)
pockets = pd.read_csv("prank/p53_clean.pdb_predictions.csv")
print("Top pocket score:", pockets.score.max())

# 5) PyMOL figure
open("p53.pml","w").write("""
load p53_clean.pdb
bg_color white
hide everything
show cartoon, chain A
color skyblue, chain A
spectrum b, blue_to_red
ray 2400, 2400
png p53.png, dpi=300
""")
subprocess.run(["pymol","-c","-q","p53.pml"], check=True)
print("Done: see p53.png")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| BioPython | SeqIO, Bio.PDB, pairwise alignment | `pip install biopython` |
| biotite | Modern structural biology toolkit | `pip install biotite` |
| DSSP (mkdssp) | Secondary structure assignment | https://github.com/cmbi/dssp |
| AlphaFoldDB | Predicted structures for UniProt | https://alphafold.ebi.ac.uk/ |
| FoldSeek | Fast structural similarity search | https://github.com/steineggerlab/foldseek |
| P2Rank | Ligand-binding pocket prediction | https://github.com/rdk/p2rank |
| HDOCK | Protein-protein / protein-DNA docking | http://hdock.phys.hust.edu.cn/ |
| HADDOCK | Data-driven docking | https://www.bonvinlab.org/software/ |
| OpenMM | GPU molecular dynamics engine | `pip install openmm` |
| PyMOL | Structure visualization and rendering | https://github.com/schrodinger/pymol-open-source |
| pdb-tools | PDB file manipulation | `pip install pdb-tools` |
| PDBFixer | Repair missing atoms, protonation | `pip install pdbfixer` |
| mdtraj | Trajectory analysis | `pip install mdtraj` |
| UniProt | Protein annotation database | https://www.uniprot.org/ |

## References

- BioPython documentation: https://biopython.org/wiki/Documentation
- biotite documentation: https://www.biotite-python.org/
- AlphaFold paper: https://doi.org/10.1038/s41586-021-03819-2
- AlphaFoldDB: https://alphafold.ebi.ac.uk/
- FoldSeek paper: https://doi.org/10.1038/s41587-023-01757-0
- DSSP: https://doi.org/10.1002/bip.360221012
- P2Rank paper: https://doi.org/10.1093/bioinformatics/bty450
- OpenMM documentation: https://openmm.org/documentation
- PyMOL documentation: https://pymol.org/dokuwiki/
- UniProt: https://www.uniprot.org/help/about

## Ethics & safety

- Protein structures from clinical isolates (e.g., pathogen spike
  proteins, oncogenic fusions) may be dual-use; share via controlled
  repositories and follow national export-control lists for select
  agents.
- AlphaFold and other structure predictors can predict the structure
  of regulated toxins or engineered enzymes; do not assist with
  prediction of agents on the Australia Group or US Select Agent lists.
- Docking results are research-grade and not clinical decision tools;
  never report a docking score as a therapeutic recommendation to a
  patient or clinician outside the IRB or clinical-trial framework.
- Respect AlphaFoldDB and PDB licenses: AlphaFold structures are CC
  BY 4.0 (attribute DeepMind/EBI), PDB entries are public domain but
  should still be cited by PDB ID.
- PyMOL Open-Source is under the BSD-style license; the Schrodinger
  PyMOL commercial product has a separate EOL - do not redistribute
  commercial builds.

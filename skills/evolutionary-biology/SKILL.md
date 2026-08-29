---
name: evolutionary-biology
description: Evolutionary biology toolkit covering multiple sequence alignment with BioPython AlignIO, phylogenetic reconstruction with Bio.Phylo and DendroPy and ETE3, evolutionary rate estimation with PAML and HyPhy, positive selection and dN/dS testing, molecular clock dating with TreeTime, ancestral sequence reconstruction, population genomics with scikit-allel, and demographic inference with msprime and demes. Use this skill whenever the user asks about phylogenetics, MSA, Bio.Phylo, DendroPy, ETE3, PAML, HyPhy, dN/dS, positive selection, TreeTime, molecular clock, ancestral reconstruction, msprime, demes, coalescent simulation, TimeTree, NCBI Taxonomy, or TreeBASE.
license: MIT
compatibility: Requires Python 3.10+ with biopython, dendropy, ete3, scikit-allel, msprime, demes, numpy, pandas, scipy, matplotlib. System tools PAML (codeml, baseml), HyPhy, IQ-TREE or RAxML for ML tree search, MAFFT or MUSCLE for MSA.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Biology & Genomics
---

# Evolutionary Biology

## Overview

Evolutionary biology reconstructs the history and processes that
shape genetic diversity. The workflow starts with **multiple sequence
alignment** (MAFFT, MUSCLE, ClustalOmega) parsed by **BioPython
AlignIO**. Trees are inferred with maximum-likelihood searchers
(**IQ-TREE**, **RAxML**, **FastTree**) and read with **Bio.Phylo**,
**DendroPy**, or **ETE3**. Evolutionary rates and positive selection
are tested with **PAML** (`codeml`) or **HyPhy** (FEL, MEME, FUBAR);
molecular-clock dating is done with **TreeTime**; ancestral sequences
are reconstructed with `phykit` or PAML `rst`; coalescent simulations
are run with **msprime** + **demes**. Reference resources include
**NCBI Taxonomy**, **TimeTree**, **TreeBASE**, and **Ensembl Compara**.

## When to use this skill

- User asks for **multiple sequence alignment** (MSA) or sequence
  alignment manipulation in Python.
- User wants to build a **phylogenetic tree** with IQ-TREE, RAxML,
  or FastTree.
- User wants to **read, manipulate, or visualize** trees in Newick,
  Nexus, or phyloXML.
- User asks for **dN/dS** ratios or **positive selection** testing
  (FEL, MEME, FUBAR, PAML codeml branch-site).
- User asks for a **molecular clock** or **time-calibrated tree**
  (TreeTime, MCMCtree, BEAST2 via R/Python bridges).
- User wants to run **coalescent simulations** or **demographic
  inference** with msprime, demes, or moments.
- User asks for **population genetics** statistics with scikit-allel.
- User mentions **NCBI Taxonomy**, **TimeTree**, **TreeBASE**,
  **Ensembl Compara**, **PhyloT**, **OneZoom**.
- Skip for: variant calling and GWAS (use `genomics`), single-cell
  analysis (use `transcriptomics`), mass-spec protein quantification
  (use `proteomics`).

## Prerequisites

- Python 3.10+ (3.11 recommended for dendropy 5.x and msprime 1.x).
- System tools: `mafft`, `muscle`, `iqtree2`, `raxml-ng` or `raxmlHPC`,
  `fasttree`, `HyPhy` (HYPHYMP / hyphy), `PAML` (codeml, baseml),
  `TreeTime`.
- Python packages:

```bash
pip install biopython dendropy ete3 scikit-allel msprime demes \
            numpy pandas scipy matplotlib
# Optional: phylopip, phylomast, moments for demographic inference
pip install phykit moments tskit
```

- Reference data: NCBI Taxonomy dump (`taxdump.zip`), a TimeTree
  export for divergence times, Ensembl Compara gene trees for
  orthology.

## Core workflows

### Multiple sequence alignment with BioPython AlignIO

Read sequences, run MAFFT, and parse the alignment.

```python
from Bio import AlignIO, SeqIO
import subprocess
# 1) Write a FASTA of homologous sequences
recs = list(SeqIO.parse("orthologs.fasta", "fasta"))
print(f"{len(recs)} sequences to align")
# 2) Run MAFFT L-INS-i for <200 sequences with remote homologs
subprocess.run(["mafft", "--localpair", "--maxiterate", "1000",
                "--thread", "8",
                "orthologs.fasta"], stdout=open("aln.fasta","w"), check=True)
# 3) Parse and inspect
aln = AlignIO.read("aln.fasta", "fasta")
print(f"{aln.get_alignment_length()} columns, "
      f"{len(aln)} rows")
# Compute column-wise conservation
from collections import Counter
import numpy as np
cons = [Counter(str(rec.seq[c]) for rec in aln).most_common(1)[0][1]
        for c in range(aln.get_alignment_length())]
print(f"mean conservation: {np.mean(cons)/len(aln):.2f}")
```

### Tree inference with IQ-TREE and parsing with Bio.Phylo

Infer a maximum-likelihood tree with bootstrapping, then load it.

```python
import subprocess
from Bio import Phylo
# Infer ML tree with ModelFinderPlus and 1000 ultrafast bootstrap replicates
subprocess.run(["iqtree2", "-s", "aln.fasta", "-m", "MFP",
                "-B", "1000", "-T", "8", "-pre", "tree"], check=True)
# Load and reroot on the outgroup
tree = Phylo.read("tree.treefile", "newick")
tree.root_with_outgroup("OUTGROUP")
# Print a quick ASCII tree
Phylo.draw_ascii(tree, stderr=False)
# Iterate branches
for clade in tree.find_clades(order="level"):
    print(clade.name, "branch length =", round(clade.branch_length or 0, 4))
```

### dN/dS and positive selection with PAML codeml and HyPhy

Run PAML `codeml` branch-site test for positive selection and HyPhy
FEL on the same alignment.

```python
import subprocess, os
# 1) PAML codeml control file for branch-site model A
control = """
seqfile = aln.phylip
treefile = tree.nwk
outfile = codeml.out
mode = 0
seqtype = 1
CodonFreq = 2
model = 2            # branch-site
NSsites = 2          # site classes (0,1,2a,2b)
fix_omega = 0
omega = 1.0
fix_kappa = 0
kappa = 2
Small_Diff = 0.5e-6
verbose = 0
"""
open("codeml.ctl", "w").write(control)
subprocess.run(["codeml", "codeml.ctl"], check=True)
# Parse the BEB posterior probabilities for site classes
with open("codeml.out") as fh:
    text = fh.read()
print("BEB sites section found:", "Bayes Empirical Bayes" in text)

# 2) HyPhy FEL for episodic positive selection at sites
subprocess.run(["hyphy", "fel", "--alignment", "aln.fasta",
                "--tree", "tree.nwk",
                "--output", "fel.json"], check=True)
import json
res = json.load(open("fel.json"))
sites = res["MLE"]["content"]["0"]["MLE"]["sites"]["0"]
sig_sites = [s for s in sites if s.get("p-value", 1) < 0.05]
print(f"{len(sig_sites)} sites under positive selection at p<0.05")
```

### Molecular clock dating with TreeTime

Time-calibrate a tree with sampling dates (e.g., for pathogen
outbreaks).

```python
import pandas as pd
from treetime import TreeTime
import dendropy
# Build a metadata file of tip -> sampling date
meta = pd.read_csv("sampling_dates.csv")   # columns: taxon, date (YYYY-MM-DD)
tree = dendropy.Tree.get(path="tree.nwk", schema="newick")
# Run TreeTime
tt = TreeTime.dates_from_tip_and_outgroup(
    tree=tree, tip_dates=meta.set_index("taxon")["date"].to_dict())
tt.run(clock_rate=None, time_mle=True, branch_length_mode="fixed")
print("RTT regression r^2:", round(tt.date.calendar_date.rtt.r**2, 3))
print("clock rate:", tt.date.clock_rate)
tt.tree.write(path="timetree.nwk", schema="newick")
```

### Coalescent simulation and demographic inference with msprime and demes

Simulate a 2-population model with msprime and resolve demography from
a `demes` model.

```python
import demes, msprime, numpy as np
# 1) Define demography in Demes YAML
yaml = """
description: two-population split
time_units: generations
demes:
  - id: A
    epochs: [{end_time: 1000, start_size: 10000}, {end_time: 0, start_size: 5000}]
  - id: B
    ancestors: [A]
    epochs: [{end_time: 0, start_size: 10000}]
"""
graph = demes.loads(yaml)
# Convert to msprime demography and simulate a 10 Mb region
demog = msprime.Demography.from_demes(graph)
ts = msprime.sim_ancestry(
    samples={"A": 20, "B": 20}, sequence_length=10_000_000,
    recombination_rate=1e-8, demography=demog, random_seed=7)
print(f"{ts.num_trees} trees across 10 Mb")
# Compute pairwise diversity by deme
div_A = ts.diversity(sample_sets=ts.samples(population=0))
div_B = ts.diversity(sample_sets=ts.samples(population=1))
print(f"pi_A = {div_A:.4e}, pi_B = {div_B:.4e}")
```

### Tree manipulation and visualization with ETE3 and DendroPy

Render a tree with ETE3 and compute patristic distances with
DendroPy.

```python
from ete3 import Tree, TreeStyle, NodeStyle
t = Tree("tree.nwk", format=1)
ts = TreeStyle(); ts.mode = "r"; ts.show_leaf_name = True
for n in t.traverse():
    nstyle = NodeStyle(); nstyle["size"] = 10
    n.set_style(nstyle)
t.render("tree.png", tree_style=ts, w=400, units="mm")

# Pairwise patristic distances with Dendropy
import dendropy
tree = dendropy.Tree.get(path="tree.nwk", schema="newick")
pdm = tree.phylogenetic_distance_matrix()
taxa = tree.taxon_namespace
print("distance", taxa[0].label, "<->", taxa[1].label, "=",
      round(pdm(taxa[0], taxa[1]), 4))
```

## Best practices

- Always inspect the alignment before tree inference - **MAFFT
  L-INS-i** for remote homologs (<200 seqs), **MAFFT FFT-NS-2** for
  large datasets; trim unalignable regions with **trimAl** or **Gblocks**
  before ML.
- Use **IQ-TREE ModelFinderPlus** (`-m MFP`) to pick the substitution
  model - the wrong model can change topology and bootstrap support.
- Report **bootstrap support** for every internal node; treat nodes
  with UFboot < 95 as unresolved.
- For positive selection, always run **both** the branch-site test
  (PAML codeml) and **FEL or MEME** (HyPhy); they have complementary
  power and detect different selection regimes (episodic vs pervasive).
- For molecular clocks on pathogen outbreaks, supply **rooting**
  explicitly (e.g., root on the earliest sample or use root-to-tip
  regression) - TreeTime's default root can be misleading.
- For **msprime** simulations, set `recombination_rate` and `mutation
  rate` consistently with the assumed genome - inconsistent rates lead
  to unphysical diversity values.
- Cross-check the **species tree** against the NCBI Taxonomy database
  before reporting gene-tree discordance as LGT - many "anomalies" are
  actually mislabelled taxa.
- Deposit alignments and trees in **TreeBASE** or **TreeBASE-style**
  archives; deposit supplementary trees in Dryad.
- Use **Demes YAML** to document the demographic model - it is
  unambiguous and reproducible across simulation engines.

## Common pitfalls

- Building an MSA with **MSA methods tuned for proteins** on coding
  DNA - align the protein, then back-translate to codon-aware DNA.
- Using **HKY85** when the data need GTR+I+G - under-parameterization
  collapses long branches.
- Trusting PAML `codeml` results without running the **null (omega
  fixed = 1)** model and the LRT - the BEB sites alone are not
  evidence of positive selection.
- Forgetting to set the **outgroup** before saving the tree - most
  downstream tools (TreeTime, codeml) assume a rooted tree.
- Treating ultrametric trees from UPGMA as phylogenies - UPGMA assumes
  a molecular clock, which is violated in most real data.
- Reporting **bootstrap support** as percentages of 100 - UFboot
  support in IQ-TREE is a posterior probability, not a classical
  bootstrap; read the documentation.
- For msprime, mixing **recapitation** with **simplification** without
  understanding that simplification discards ancestral information -
  recompute diversity after recapitation, not before.
- Ignoring **incomplete lineage sorting (ILS)** in species-tree
  inference - gene trees disagree due to ILS, not because of LGT.

## Worked example

End-to-end: align SARS-like spike homologs, build an ML tree, test for
positive selection with HyPhy MEME, and time-calibrate with TreeTime
on sampling dates.

```python
import subprocess, json, pandas as pd
from Bio import AlignIO, Phylo, SeqIO
from treetime import TreeTime
import dendropy

# 1) Align spike homologs with MAFFT (codon-aware not required for spike demo)
subprocess.run(["mafft", "--auto", "--thread", "8",
                "spike_homologs.fasta"], stdout=open("aln.fasta","w"), check=True)
aln = AlignIO.read("aln.fasta", "fasta")
print(f"alignment: {len(aln)} taxa x {aln.get_alignment_length()} cols")

# 2) ML tree with IQ-TREE
subprocess.run(["iqtree2", "-s", "aln.fasta", "-m", "MFP",
                "-B", "1000", "-T", "8", "-pre", "spike"], check=True)
tree = Phylo.read("spike.treefile", "newick")
tree.root_with_outgroup("BatCoV_RaTG13")

# 3) MEME episodic positive selection (HyPhy)
subprocess.run(["hyphy", "meme", "--alignment", "aln.fasta",
                "--tree", "spike.treefile", "--output", "meme.json"], check=True)
meme = json.load(open("meme.json"))
sites = meme["MLE"]["content"]["0"]["MLE"]["sites"]["0"]
sig = [s for s in sites if (s.get("p-value") or 1) < 0.05]
print(f"{len(sig)} sites under episodic positive selection (MEME p<0.05)")

# 4) Time-calibrate with sampling dates (e.g., for outbreak SARS-CoV-2)
meta = pd.read_csv("sampling_dates.csv")   # taxon, date
dtree = dendropy.Tree.get(path="spike.treefile", schema="newick")
tt = TreeTime(dates=meta.set_index("taxon")["date"].to_dict(),
              tree=dtree, aln=aln)
tt.run(clock_rate=None, time_mle=True, branch_length_mode="fixed")
tt.tree.write(path="timetree.nwk", schema="newick")
print(f"clock rate (subs/site/year) = {tt.date.clock_rate:.2e}")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| BioPython | AlignIO, Bio.Phylo, SeqIO, BLAST | `pip install biopython` |
| DendroPy | Tree parsing, distance matrices | `pip install dendropy` |
| ETE3 | Tree visualization, orthology | `pip install ete3` |
| MAFFT | Fast accurate MSA | https://mafft.cbrc.jp/alignment/software/ |
| MUSCLE | Classic MSA | https://www.drive5.com/muscle/ |
| IQ-TREE 2 | Modern ML tree search | http://www.iqtree.org/ |
| RAxML-NG | Maximum-likelihood trees | https://github.com/amkozak/raxml-ng |
| FastTree | Approximate ML for large trees | http://www.microbesonline.org/fasttree/ |
| PAML (codeml) | Evolutionary rate, dN/dS, branch-site | http://abacus.gene.ucl.ac.uk/software/paml.html |
| HyPhy | FEL, MEME, FUBAR for positive selection | https://hyphy.org/ |
| TreeTime | Molecular clock and time-calibration | `pip install phylo-treetime` |
| msprime + tskit | Coalescent simulation | `pip install msprime tskit` |
| demes | Demographic model specification | `pip install demes` |
| moments | Diffusion-based demographic inference | `pip install moments` |
| scikit-allel | Population genetics statistics | `pip install scikit-allel` |

## References

- BioPython tutorial: https://biopython.org/DIST/docs/tutorial/Tutorial.html
- DendroPy documentation: https://dendropy.org/
- IQ-TREE documentation: http://www.iqtree.org/doc/
- PAML documentation: http://abacus.gene.ucl.ac.uk/software/pamlDOC.pdf
- HyPhy documentation: https://www.hyphy.org/
- TreeTime paper: https://doi.org/10.1093/ve/042
- msprime paper: https://doi.org/10.1093/genetics/iyab100
- demes specification: https://popsim-consortium.github.io/demes-spec-docs/main/
- NCBI Taxonomy: https://www.ncbi.nlm.nih.gov/taxonomy
- TimeTree: https://doi.org/10.1093/molbev/msy191 (Kumar et al.)
- TreeBASE: https://treebase.org/

## Ethics & safety

- Phylogenetic analysis of human pathogen sequences (HIV, SARS-CoV-2,
  influenza, tuberculosis) is dual-use - it can identify patient
  source, super-spreaders, and escape variants; do not release
  results that could identify individuals in small outbreaks without
  IRB approval.
- HIV molecular epidemiology has been used to criminalize transmission
  in several jurisdictions - consult the SNPwatch / PANGEA-HIV ethics
  guidance and the 2018 WHO/UNAIDS ethical guidance on phylogenetic
  data use before publishing results tied to geography.
- Ancestry reconstruction from genomic data carries privacy risk for
  related individuals; do not publish haplotype trees of identifiable
  families without consent.
- Pathogen outbreak analysis used for outbreak investigation should
  be communicated to public health authorities first, not to public
  media, to avoid undermining surveillance partnerships.
- Comparative genomics of dual-use research of concern (e.g., gain-of-
  function predictions for select agents) must be reported under the
  relevant oversight framework (NSABB, NHMRC, or national equivalent).
- Respect database licenses: NCBI Taxonomy is public domain, Ensembl
  Compara is OGL, TimeTree has academic-use terms; check before
  redistribution.

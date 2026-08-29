---
name: proteomics
description: Proteomics toolkit covering mass-spectrometry data parsing with pyteomics for mzML and MGF, peptide identification via database search, label-free quantification, DIA analysis with DIA-NN, MaxQuant or FragPipe pipelines, normalization and differential abundance with statsmodels, and pathway analysis with gseapy. Use this skill whenever the user asks about mass spectrometry, MS, MS/MS, mzML, MGF, pyteomics, DIA-NN, MaxQuant, FragPipe, Skyline, label-free quant, LFQ, TMT, iTRAQ, PRIDE, ProteomeXchange, Human Protein Atlas, PeptideAtlas, or gseapy.
license: MIT
compatibility: Requires Python 3.10+ with pyteomics, pandas, numpy, scipy, statsmodels, gseapy, matplotlib. System tools DIA-NN, MaxQuant, FragPipe, MSFragger, and optionally Skyline.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Biology & Genomics
---

# Proteomics

## Overview

Proteomics quantifies the protein complement of cells, tissues, and
biological fluids. Mass spectrometry (MS) is the workhorse instrument:
a chromatographic separation (LC) feeds ions into a tandem MS that
records both precursor (MS1) and fragment (MS2) spectra. Spectra are
stored as **mzML** (and **MGF** for Mascot-generic format); Python
reads them with **pyteomics**. Identification is done by database
search (Mascot, MSFragger, Andromeda) and quantification by label-free
LFQ intensity, isobaric tags (**TMT**, **iTRAQ**), or data-independent
acquisition (**DIA**) analyzed with **DIA-NN**, **MaxQuant**, or
**FragPipe**. Differential abundance testing uses
**statsmodels**/limma-like approaches, and pathway enrichment uses
**gseapy**. Public repositories: **PRIDE** and **ProteomeXchange** for
raw data, **Human Protein Atlas** for tissue-level expression, and
**PeptideAtlas** for peptide evidence.

## When to use this skill

- User asks to **parse mzML or MGF** spectra in Python.
- User wants to run a **DIA-NN**, **MaxQuant**, or **FragPipe**
  pipeline.
- User asks for **label-free quantification (LFQ)** or **TMT/iTRAQ**
  quantification.
- User wants **differential protein abundance** with statistical
  testing (limma-like, t-test with FDR control).
- User wants **pathway or gene-set enrichment** with gseapy.
- User mentions **PRIDE**, **ProteomeXchange**, **Human Protein
  Atlas**, **PeptideAtlas**, **Skyline**, **MSstats**, **mzIdentML**.
- Skip for: protein structure and docking (use `protein-analysis`),
  differential RNA expression (use `transcriptomics`), metabolomics
  pipelines (covered briefly under Tools).

## Prerequisites

- Python 3.10+ (3.11 recommended for pyteomics 4.7+ wheels).
- System tools: `DIA-NN`, `MaxQuant` (Windows or Mono on Linux), or
  `FragPipe` with `MSFragger` and `IonQuant`. Optional: `Skyline` for
  targeted assay development.
- Python packages:

```bash
pip install pyteomics pandas numpy scipy statsmodels gseapy matplotlib
pip install mspy  # optional, for mzML streaming on large files
```

- Reference databases: a UniProt reference proteome FASTA matching
  the sample organism (e.g., UP000005640 for human) and an
  contaminants database (cRAP).

## Core workflows

### mzML and MGF parsing with pyteomics

Stream spectra from an mzML file and extract MS2 scans from MGF.

```python
from pyteomics import mzml, mzidf, mgf, auxiliary
import pandas as pd
# Stream spectra (memory-efficient for large files)
n_ms1 = n_ms2 = 0
for spectrum in mzml.read("sample.mzML", use_index=False):
    if spectrum["ms level"] == 1:
        n_ms1 += 1
    else:
        n_ms2 += 1
    if n_ms1 + n_ms2 > 50000:
        break
print(f"scanned {n_ms1} MS1 + {n_ms2} MS2 in first 50k spectra")

# Convert an MGF to a DataFrame of precursor m/z and charge
mgf_spectra = list(mgf.read("sample.mgf"))
df = pd.DataFrame([
    {"title": s.get("title", "")[:40],
     "precursor_mz": s["params"]["pepmass"][0],
     "charge": int(str(s["params"]["charge"][0]).replace("+", ""))}
    for s in mgf_spectra[:5]])
print(df)
```

### DIA analysis with DIA-NN

Run DIA-NN on a batch of DIA runs with a spectral library (or
library-free with the FASTA).

```python
import subprocess, pandas as pd
# Library-free DIA search against UniProt human FASTA
subprocess.run(["diann",
                "--fasta", "UP000005640.fasta",
                "--fasta-filter", "tr",   # remove reverse
                "--out", "diann_report.tsv",
                "--threads", "16",
                "--mat-threads", "16",
                "--use-quant", "11",
                "--min-corr", "0.3",
                "--corr-pvalue", "1e-5",
                "--mass-acc", "30",       # ppm MS1
                "--min-fr-mass", "300", "--max-fr-mass", "1800"],
    check=True)
# Parse DIA-NN main report
report = pd.read_csv("diann_report.tsv", sep="\t")
proteins = (report.groupby("Protein.Names")["PG.Quantity"]
            .median().sort_values(ascending=False))
print(f"{len(proteins)} protein groups quantified")
```

### Label-free quantification with FragPipe / IonQuant

Run FragPipe (MSFragger + IonQuant) on DDA runs.

```python
import subprocess, pandas as pd
# Configure a FragPipe workflow (fragpipe --config file or GUI export)
subprocess.run(["fragpipe", "--config", "lfq_workflow.config",
                "--dir", "/data/raw"], check=True)
# Combined protein intensity table
prot = pd.read_csv("combined_proteins.tsv", sep="\t")
# Move from wide to long format for analysis
samples = ["c1","c2","c3","t1","t2","t3"]
lfq_cols = [f"Intensity {s}" for s in samples]
long = prot.melt(id_vars=["Protein Ids"],
                 value_vars=lfq_cols,
                 var_name="sample", value_name="intensity")
long["log2_intensity"] = np.log2(long["intensity"].clip(lower=1))
```

### Normalization and differential abundance with statsmodels

Median-normalize LFQ intensities and test for differential abundance
with a moderated-t-like test followed by Benjamini-Hochberg FDR.

```python
import pandas as pd, numpy as np
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

df = pd.read_csv("lfq_wide.csv")  # Protein, c1..c3, t1..t3 (intensity)
samples = df.columns[1:]
intens = np.log2(df[samples].clip(lower=1))
# Median normalization to global median
intens = intens - intens.median(axis=0) + intens.median().mean()
df["log2fc"] = intens[["t1","t2","t3"]].mean(axis=1) - intens[["c1","c2","c3"]].mean(axis=1)

# Two-sample t-test per protein (Welch) with BH FDR
from scipy.stats import ttest_ind
pvals = []
for _, row in intens.iterrows():
    t, p = ttest_ind(row[["t1","t2","t3"]], row[["c1","c2","c3"]],
                     equal_var=False, nan_policy="omit")
    pvals.append(p)
_, fdr, _, _ = multipletests(np.nan_to_num(pvals), method="fdr_bh")
df["pvalue"] = pvals; df["padj"] = fdr
sig = df[(df.padj < 0.05) & (df.log2fc.abs() > 1)]
print(f"{len(sig)} differentially abundant proteins")
```

### Pathway enrichment with gseapy

Run over-representation analysis on the up-regulated proteins against
Reactome and GO Biological Process.

```python
import gseapy
sig_genes = df[(df.padj < 0.05) & (df.log2fc > 1)]["gene_symbol"].tolist()
# Over-representation analysis (ORA)
ora = gseapy.enrichr(gene_list=sig_genes,
                     gene_sets=["GO_Biological_Process_2023",
                                "Reactome_2022"],
                     organism="human", outdir="enrichr_out")
print(ora.res2d.head(10)[["Term", "Adjusted P-value", "Overlap"]])

# GSEA on ranked genes by signed -log10(p)
ranking = df.sort_values("log2fc", ascending=False)[["gene_symbol","log2fc"]]
ranking["metric"] = ranking["log2fc"]
gsea = gseapy.gsea(data=ranking.set_index("gene_symbol")["metric"],
                   gene_sets="Reactome_2022", threads=8,
                   seed=7, outdir="gsea_out")
print(gsea.res2d.head())
```

## Best practices

- Always include a **contaminants database** (cRAP) in the search -
  keratin, trypsin, BSA from sample handling show up everywhere.
- Use **FDR control** at 1% peptide and 1% protein level
  (peptide-spectrum match + protein FDR), and report the FDR method
  (target-decoy).
- For **DIA**, prefer library-free DIA-NN or Spectronaut with the
  FASTA - library quality drives reproducibility, and FASTA-only mode
  reduces inter-lab variability.
- Use **median normalization** for LFQ; for TMT use IRS (internal
  reference scaling) or, when applicable, a TMT bridge channel.
- Filter on **valid values**: require a protein to be quantified in
  at least N-1 of N replicates in at least one group before imputation
  or testing.
- Impute missing intensities from a left-shifted normal distribution
  (typical: 1.8 standard deviations below the mean, 0.3 sd width) -
  never mean-impute, which inflates false positives.
- For **GSEA**, use the entire ranked protein list (not just
  significant ones), and report normalized enrichment score, FDR, and
  leading-edge genes.
- Deposit raw files on **PRIDE / ProteomeXchange** and reference the
  ProteomeXchange ID in any manuscript.
- Report instrument, acquisition mode (DDA / DIA), LC gradient length,
  and the version of DIA-NN / MaxQuant / FragPipe - all are needed to
  reproduce a proteomics result.

## Common pitfalls

- Mixing **forward and reverse decoys** between tools - the FDR
  calculation depends on the decoy convention used in the search
  engine.
- Forgetting the **first-dimension (m/z) calibration** - the search
  reports very few IDs because mass tolerance is too loose.
- Using a **mismatched FASTA** (e.g., UniProt mouse when sample is
  human) - cross-species peptide identification is unreliable beyond
  90% sequence identity.
- Reporting TMT reporter-ion intensities without **TMT batch-effect
  correction** - plex-to-plex variation is large and can dominate
  biology.
- Imputing all missing values identically - low-abundance proteins
  are missing-not-at-random; impute differently for missing-in-one-group
  vs missing-everywhere.
- For DIA, running **library generation** and **quantification** on
  the same samples inflates sensitivity - hold out a validation set.
- Using **MS1 area** for DIA quantification without ion-mobility
  deconvolution - it inflates co-eluting peptide signals.
- Computing fold changes on **non-normalized** reporter intensities -
  the LC-MS run-to-run variation dominates the biology.

## Worked example

End-to-end DIA proteomics: parse an mzML preview, run DIA-NN library-
free, normalize intensities, test for differential abundance, run
Reactome over-representation on the up-regulated proteins.

```python
import subprocess, pandas as pd, numpy as np
from pyteomics import mzml
from scipy.stats import ttest_ind
from statsmodels.stats.multitest import multipletests
import gseapy

# 1) Sanity-check the mzML (preview spectra)
spec = next(mzml.read("sample_t1.mzML"))
print("MS level:", spec["ms level"], "base_peaks:", len(spec["m/z array"]))

# 2) Library-free DIA-NN on all 6 runs (3 control + 3 treated)
runs = " ".join(f"{s}.mzML" for s in ["c1","c2","c3","t1","t2","t3"])
subprocess.run(f"diann --fasta UP000005640.fasta --fasta-filter tr "
               f"--out diann.tsv --threads 16 {runs}", shell=True, check=True)
rep = pd.read_csv("diann.tsv", sep="\t")

# 3) Build protein x sample matrix (use PG.Quantity)
mat = rep.pivot_table(index="Protein.Names", columns="Run",
                      values="PG.Quantity", aggfunc="median")
mat = np.log2(mat.clip(lower=1))
mat = mat - mat.median(axis=0) + mat.median().mean()      # median normalize

# 4) Differential abundance (Welch t-test, BH FDR)
control = ["c1","c2","c3"]; treated = ["t1","t2","t3"]
mat["log2fc"] = mat[treated].mean(axis=1) - mat[control].mean(axis=1)
mat["pvalue"] = mat.apply(
    lambda r: ttest_ind(r[treated], r[control], equal_var=False,
                         nan_policy="omit")[1], axis=1)
_, mat["padj"], _, _ = multipletests(np.nan_to_num(mat["pvalue"]),
                                     method="fdr_bh")

# 5) Reactome over-representation on up-regulated proteins
sig = mat[(mat.padj < 0.05) & (mat.log2fc > 1)].reset_index()
# Use the 'Protein.Ids' field as gene symbols (or map via UniProt)
ora = gseapy.enrichr(gene_list=sig["Protein.Names"].head(500).tolist(),
                     gene_sets="Reactome_2022",
                     organism="human", outdir="ora_out")
top = ora.res2d.sort_values("Adjusted P-value").head(10)
print(top[["Term", "Overlap", "Adjusted P-value"]])
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| pyteomics | mzML, MGF, mzIdentML, pepXML parsing | `pip install pyteomics` |
| DIA-NN | Library-free DIA quantification | https://github.com/vdemichev/DiaNN |
| MaxQuant | DDA quantification (LFQ, TMT, iTRAQ) | https://www.maxquant.org/ |
| FragPipe | MSFragger + IonQuant + Philosopher | https://fragpipe.nesvilab.org/ |
| MSFragger | Database search engine | https://msfragger.nesvilab.org/ |
| Skyline | Targeted assay / SRM / PRM | https://skyline.ms/ |
| MSstats | Statistical modeling of proteomics | `R package: MSstats` |
| statsmodels | Differential abundance testing in Python | `pip install statsmodels` |
| gseapy | GSEA and Enrichr over-representation | `pip install gseapy` |
| pandas / numpy | Tabular + numerical analysis | `pip install pandas numpy` |
| PRIDE / ProteomeXchange | Public MS data repository | https://www.proteomexchange.org/ |
| Human Protein Atlas | Tissue-level expression reference | https://www.proteinatlas.org/ |
| PeptideAtlas | Curated peptide evidence | https://peptideatlas.org/ |
| mzML / PSI-MS | Open mass-spectrometry formats | https://www.psidev.info/ |

## References

- pyteomics documentation: https://pyteomics.readthedocs.io/en/latest/
- DIA-NN paper: https://doi.org/10.1038/s41592-019-0638-x
- MaxQuant paper: https://doi.org/10.1038/nbt.1511
- FragPipe documentation: https://fragpipe.nesvilab.org/docs/
- MSstats paper: https://doi.org/10.1093/bioinformatics/btr445
- gseapy documentation: https://gseapy.readthedocs.io/
- Enrichr: https://doi.org/10.1093/nar/gkne2640 (Kuleshov et al.)
- ProteomeXchange: https://www.proteomexchange.org/
- Human Protein Atlas: https://doi.org/10.1126/science.aap7308
- PSI mzML specification: https://www.psidev.info/mzml

## Ethics & safety

- Clinical proteomic data (plasma, CSF, tissue biopsies) carries the
  same consent constraints as genomics; do not redistribute outside
  the originating IRB / controlled-access tier.
- Imputation and differential analysis on small clinical cohorts can
  produce fragile biomarker panels; require independent validation
  before reporting any clinical utility.
- Pathogen proteomics (e.g., high-containment virus samples) is dual-
  use and may be export-controlled; handle only in approved facilities
  and deposit data through controlled-access repositories.
- PRIDE deposition commits to public release; redact sample
  identifiers that could re-identify rare-disease patients (rare
  disease + small geographic area + age = re-identifiable).
- DIA-NN, MaxQuant, and FragPipe have academic / non-commercial
  licenses; verify commercial licensing before deployment in a
  for-profit pipeline.
- Protein-based clinical tests used for patient management are LDTs
  and require CLIA / CAP / ISO 15189 validation - research pipelines
  must not be used for patient care decisions.

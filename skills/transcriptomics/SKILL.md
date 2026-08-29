---
name: transcriptomics
description: Transcriptomics toolkit covering bulk RNA-seq alignment with STAR or HISAT2, quantification with featureCounts or Salmon and kallisto, differential expression with DESeq2 or pydeseq2 and edgeR, single-cell analysis with Scanpy and AnnData, Leiden clustering and UMAP, marker genes with rank_genes_groups, batch correction with Harmony or scVI, pseudotime with PAGA and diffusion maps. Use this skill whenever the user asks about RNA-seq, single-cell, scRNA-seq, Scanpy, AnnData, UMAP, Leiden, DESeq2, pydeseq2, edgeR, Salmon, kallisto, featureCounts, STAR, HISAT2, Harmony, scVI, PAGA, Cell Ranger, CELLxGENE, GTEx, or GEO.
license: MIT
compatibility: Requires Python 3.10+ with scanpy, anndata, numpy, pandas, scipy, matplotlib. System tools STAR, HISAT2, featureCounts, Salmon, kallisto, Cell Ranger. Optional pydeseq2, scvi-tools, harmonypy, bbknn.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Biology & Genomics
---

# Transcriptomics

## Overview

Transcriptomics measures RNA abundance across cells or tissues, either
in bulk (whole-tissue homogenate) or at single-cell resolution. The
bulk RNA-seq pipeline runs alignment with **STAR** or **HISAT2**,
quantification with **featureCounts** (alignment-based) or **Salmon**
and **kallisto** (quasi-mapping), and differential expression with
**DESeq2** (R) or its Python port **pydeseq2**, with **edgeR** as a
reference alternative. The single-cell pipeline is dominated by
**Scanpy** and its `AnnData` container: QC, normalization, batch
correction with **Harmony** or **scVI**, neighbor graph and **Leiden**
clustering, **UMAP** embedding, marker genes via
`rank_genes_groups`, and pseudotime with **PAGA** or diffusion maps.
10x Genomics **Cell Ranger** produces the count matrix; **CELLxGENE**
hosts published atlases; **GTEx** is the canonical bulk reference for
tissue expression; **GEO** is the primary deposition archive.

## When to use this skill

- User asks about **bulk RNA-seq** or **single-cell RNA-seq** pipelines.
- User wants **differential expression** with DESeq2, edgeR, or
  pydeseq2.
- User wants to **align** RNA-seq reads with STAR or HISAT2 or
  **quantify** transcripts with Salmon or kallisto.
- User asks for **Scanpy**, **AnnData**, **UMAP**, **Leiden** clustering,
  **rank_genes_groups** marker analysis.
- User needs **batch correction** with Harmony, scVI, or BBKNN.
- User asks for **pseudotime** or trajectory inference with PAGA,
  diffusion maps, or DPT.
- User mentions **Cell Ranger**, **CELLxGENE**, **GTEx**, **GEO**,
  **Seurat**, **sparse count matrices**.
- Skip for: variant calling (use `genomics`), protein structures (use
  `protein-analysis`), phylogenetics (use `evolutionary-biology`).

## Prerequisites

- Python 3.10+ (3.11 recommended for scvi-tools and pydeseq2 wheels).
- System tools: `STAR`, `HISAT2`, `samtools`, `featureCounts` (via
  Subread), `Salmon`, `kallisto`, 10x Genomics `cellranger`.
- Python packages:

```bash
pip install scanpy anndata numpy pandas scipy matplotlib
pip install pydeseq2      # Python port of DESeq2
pip install harmonypy     # Harmony batch correction in Python
pip install scvi-tools    # deep generative model batch correction
# Optional: bbknn, scvelo (RNA velocity), cellrank (trajectory)
```

- Annotation: GTF from Ensembl matching the reference genome (e.g.,
  GRCh38.110) and a Salmon k-mer index built on the transcriptome FASTA.

## Core workflows

### Bulk RNA-seq alignment and quantification

Align paired-end reads with STAR, quantify genes with featureCounts,
or run Salmon quasi-mapping for transcript-level TPMs.

```python
import subprocess, pandas as pd
# 1) STAR 2-pass alignment to GRCh38 + GTF annotation
subprocess.run(["STAR", "--runThreadN", "16",
                "--genomeDir", "star_idx_GRCh38",
                "--sjdbGTFfile", "GRCh38.110.gtf",
                "--readFilesIn", "sample_R1.fastq.gz", "sample_R2.fastq.gz",
                "--readFilesCommand", "zcat",
                "--twopassMode", "Basic",
                "--outFileNamePrefix", "sample_", "--outSAMtype", "BAM", "SortedByCoordinate"], check=True)

# 2) gene-level counts via featureCounts
subprocess.run(["featureCounts", "-T", "8", "-p", "-B", "-C",
                "-a", "GRCh38.110.gtf", "-o", "counts.txt",
                "sample_Aligned.sortedByCoord.out.bam"], check=True)
counts = pd.read_csv("counts.txt", sep="\t", comment="#", header=1, index_col=0)
```

For transcript TPMs with Salmon (faster, no alignment):

```python
subprocess.run(["salmon", "quant", "-i", "salmon_idx",
                "-l", "A", "-p", "16",
                "-1", "sample_R1.fastq.gz", "-2", "sample_R2.fastq.gz",
                "-o", "salmon_quant"], check=True)
tpm = pd.read_csv("salmon_quant/quant.sf", sep="\t", index_col=0)["TPM"]
```

### Differential expression with pydeseq2

Run a DESeq2-style analysis in Python on a counts matrix.

```python
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats

counts = pd.read_csv("counts_matrix.csv", index_col=0).T   # genes x samples -> samples x genes
metadata = pd.read_csv("metadata.csv", index_col=0)        # condition column
dds = DeseqDataSet(counts=counts, metadata=metadata,
                   design="~ condition",
                   inference=DefaultInference(n_cpus=8))
dds.deseq2()
res = DeseqStats(dds, contrast=["condition", "treated", "control"])
res.summary()
df = res.results_df
print(df.nsmallest(5, "pvalue")[["baseMean", "log2FoldChange", "padj"]])
```

### Single-cell preprocessing with Scanpy

Load a 10x matrix, filter cells and genes, normalize, log-transform,
find highly variable genes, scale, run PCA, neighbors, Leiden, UMAP.

```python
import scanpy as sc
adata = sc.read_10x_h5("sample_filtered_feature_bc_matrix.h5")
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata.var["mt"] = adata.var_names.str.startswith("MT-")
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)
adata = adata[adata.obs.pct_counts_mt < 20].copy()
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000, flavor="seurat")
adata = adata[:, adata.var.highly_variable].copy()
sc.pp.scale(adata, max_value=10)
sc.tl.pca(adata, n_comps=50)
sc.pp.neighbors(adata, n_neighbors=15, n_pcs=30)
sc.tl.leiden(adata, resolution=0.6)
sc.tl.umap(adata)
sc.pl.umap(adata, color="leiden")
```

### Marker genes and batch correction

Find cluster markers via Wilcoxon, then correct batch effects with
Harmony.

```python
import scanpy as sc, harmonypy as hm
sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon")
markers = sc.get.rank_genes_groups_df(adata, group="0").head(10)
print("cluster 0 markers:", markers.names.tolist())

# Harmony batch correction on the PCA embedding
ho = hm.run_harmony(adata.obsm["X_pca"], adata.obs, "batch")
adata.obsm["X_harmony"] = ho.Z_corr.T
sc.pp.neighbors(adata, use_rep="X_harmony", n_neighbors=15)
sc.tl.leiden(adata, resolution=0.6, key_added="leiden_harmony")
```

For deep batch correction with scVI, train a VAE and use the latent
space for downstream steps.

```python
import scvi
scvi.model.SCVI.setup_anndata(adata, batch_key="batch")
vae = scvi.model.SCVI(adata, n_latent=30)
vae.train(max_epochs=100)
adata.obsm["X_scVI"] = vae.get_latent_representation()
sc.pp.neighbors(adata, use_rep="X_scVI"); sc.tl.umap(adata)
```

### Pseudotime and trajectory with PAGA and diffusion maps

Estimate trajectory structure with PAGA and diffusion pseudotime.

```python
import scanpy as sc
sc.tl.diffmap(adata)
sc.tl.paga(adata, groups="leiden")
sc.pl.paga(adata, color="leiden")
# Choose a root cell from cluster 0 (highest diffusion component 1)
root = adata[adata.obs.leiden == "0"].obs.index[0]
adata.uns["iroot"] = adata.obs_names.get_loc(root)
sc.tl.dpt(adata, n_branchings=1)
sc.pl.scatter(adata, basis="umap", color=["leiden", "dpt_pseudotime"])
```

## Best practices

- Match the reference annotation **build exactly** to the alignment
  reference: a GRCh38 genome needs a GRCh38 GTF (Ensembl release 110),
  not GRCh37.
- For single-cell QC, filter cells by `n_genes`, `total_counts`, and
  `pct_counts_mt` (mitochondrial fraction). Use thresholds informed by
  the tissue, not a hardcoded universal cutoff.
- Use **scran's pooled-size-factors** or **SCTransform** when cell-level
  RNA content varies widely (e.g., tumor vs. stroma); plain
  `normalize_total` distorts heterogeneity.
- Run **Harmony** or **scVI** for batch correction *after* PCA and on
  the embedding, not on raw counts - raw count correction breaks the
  statistical model downstream.
- Always report the number of **highly variable genes** retained, the
  `n_top_genes` value, and the `resolution` used for Leiden - results
  are sensitive to all three.
- For marker genes, use **Wilcoxon rank-sum** (`method="wilcoxon"`)
  with `rank_genes_groups`, and report adjusted p-values, not raw.
- For DESeq2 / pydeseq2, check the size-factor distribution and
  dispersion plot before trusting fold changes - outliers indicate a
  bad sample.
- Document the **Cell Ranger** version when reusing public 10x data -
  the count matrix changes meaningfully across versions.
- Deposit counts on **GEO** with MIAME-compliant metadata; deposit
  processed single-cell objects on **CELLxGENE** Discover for atlas
  reuse.

## Common pitfalls

- Using **raw counts** as input to Scanpy neighbors / UMAP without
  normalization - the Euclidean distance is dominated by library size.
- Filtering genes by `min_cells=3` after subsetting to a cluster - the
  global filter discards genuine cluster-specific genes.
- Forgetting to **set `adata.raw`** before scaling - scaled (z-scored)
  data is fine for PCA but should not be plotted in dot plots or used
  for differential expression.
- Treating **Leiden clusters as cell types** without marker annotation
  - cluster 0 in one batch is not the same biology in another.
- Mixing **GRCh38** and **GRCh37** annotations across samples in a
  multi-sample count matrix - gene IDs and lengths differ and break
  TPM comparisons.
- Running DESeq2 on **TPMs** instead of counts - DESeq2's negative
  binomial model expects raw counts; TPMs violate the assumptions.
- Reporting **log2FoldChange** without shrinkage - use `apeglm` or
  DESeq2's `lfcShrink` to reduce the noise of low-count genes.
- Forgetting to remove **cell-cycle signature** when clustering
  proliferating tissue - cells cluster by S/G2M phase, not cell type.

## Worked example

End-to-end bulk RNA-seq: align with STAR, count genes with
featureCounts, build a counts matrix, run pydeseq2, and produce a
volcano plot.

```python
import subprocess, pandas as pd, numpy as np
import matplotlib.pyplot as plt
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
from pydeseq2.ds import DeseqStats

# 1) Align 3 control + 3 treated samples with STAR (loop omitted for brevity)
# 2) Quantify with featureCounts (one call for all BAMs)
bams = " ".join([f"{s}_Aligned.sortedByCoord.out.bam" for s in
                 ["c1", "c2", "c3", "t1", "t2", "t3"]])
subprocess.run(f"featureCounts -T 8 -p -a GRCh38.110.gtf -o counts.txt {bams}",
               shell=True, check=True)

# 3) Build a counts matrix (genes x samples)
df = pd.read_csv("counts.txt", sep="\t", comment="#", header=1, index_col=0)
counts = df.select_dtypes("number")            # drop non-numeric cols
counts.columns = ["c1","c2","c3","t1","t2","t3"]
counts = counts[~counts.index.str.startswith("__")]  # drop __no_feature etc.

# 4) DESeq2-style analysis
meta = pd.DataFrame({"condition": ["control"]*3 + ["treated"]*3},
                    index=counts.columns)
dds = DeseqDataSet(counts=counts.T, metadata=meta, design="~ condition",
                   inference=DefaultInference(n_cpus=8))
dds.deseq2()
stat = DeseqStats(dds, contrast=["condition","treated","control"])
stat.summary(); res = stat.results_df.dropna()

# 5) Volcano plot
res["-log10p"] = -np.log10(res["pvalue"])
sig = (res.padj < 0.05) & (res.log2FoldChange.abs() > 1)
plt.scatter(res.log2FoldChange, res["-log10p"], s=6, c="grey")
plt.scatter(res.loc[sig, "log2FoldChange"], res.loc[sig, "-log10p"], s=6, c="crimson")
plt.xlabel("log2 FC (treated / control)"); plt.ylabel("-log10 p")
plt.savefig("volcano.png", dpi=150, bbox_inches="tight")
print(f"{sig.sum()} DE genes at |log2FC|>1 and FDR<0.05")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| STAR | Spliced RNA-seq alignment | https://github.com/alexdobin/STAR |
| HISAT2 | Graph-based spliced alignment | https://daehwankimlab.github.io/hisat2/ |
| featureCounts (Subread) | Gene-level read counting | http://bioinf.wehi.edu.au/featureCounts/ |
| Salmon | Quasi-mapping transcript quantification | https://salmon.readthedocs.io/ |
| kallisto | Pseudoalignment quantification | https://pachterlab.github.io/kallisto/ |
| Cell Ranger | 10x Genomics scRNA-seq pipeline | https://www.10xgenomics.com/support/software/cell-ranger |
| Scanpy | Single-cell analysis in Python | `pip install scanpy` |
| AnnData | Annotated data container | `pip install anndata` |
| pydeseq2 | Python port of DESeq2 | `pip install pydeseq2` |
| scvi-tools | Deep generative batch correction | `pip install scvi-tools` |
| harmonypy | Harmony batch correction in Python | `pip install harmonypy` |
| scvelo | RNA velocity | `pip install scvelo` |
| CELLxGENE Discover | Single-cell atlas portal | https://cellxgene.cziscience.com/ |
| GTEx | Bulk tissue reference transcriptome | https://gtexportal.org/ |

## References

- STAR paper: https://doi.org/10.1093/bioinformatics/bts635
- Salmon paper: https://doi.org/10.1038/nmeth.4197
- DESeq2 paper: https://doi.org/10.1186/s13059-014-0550-8
- pydeseq2 paper: https://doi.org/10.1093/bioinformatics/btac482
- Scanpy paper: https://doi.org/10.1186/s13059-017-1382-0
- Harmony paper: https://doi.org/10.1038/s41592-019-0619-0
- scVI paper: https://doi.org/10.1038/s41592-018-0229-2
- PAGA paper: https://doi.org/10.1186/s13059-019-1663-x
- CELLxGENE: https://cellxgene.cziscience.com/
- GTEx Consortium: https://doi.org/10.1038/s41586-020-2493-y

## Ethics & safety

- Single-cell data can re-identify rare donors in small studies; do
  not publish raw genotype information from scRNA-seq demultiplexing
  without consent review.
- Embryonic and fetal tissue transcriptomics must respect the donor
  consent and any jurisdiction-specific restrictions on embryonic
  tissue research.
- Clinical RNA-seq used for oncology patient stratification (e.g.,
  tumor subtype calls) is a Laboratory Developed Test and must follow
  CLIA/CAP validation in the US and equivalent ISO 15189 elsewhere;
  do not deploy a research Scanpy pipeline for clinical decisions.
- Sample metadata (sex, age, ancestry, disease status) is sensitive;
  de-identify before deposition and avoid publishing cell-level
  genotype information from multiplexed (MULTI-seq, cell hashing)
  experiments.
- Dual-use: transcriptomic signatures of pathogen virulence can be
  used for either therapeutic design or offensive bioengineering;
  share through controlled-access archives (e.g., NCBI BioProject with
  dbGaP-tiered access for human data).

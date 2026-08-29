# Example: single-cell differential expression

**Skills activated:** `transcriptomics`, `ml-for-science`

## The prompt

> I have a 10x Genomics `filtered_feature_bc_matrix.h5` from PBMCs, 6 samples (3 control, 3 stimulated). Do standard preprocessing (filter cells/genes, normalize, log1p, HVG, scale, PCA, neighbors, UMAP, Leiden), batch-correct across samples with Harmony, annotate broad cell types with a marker-gene approach, then run differential expression between stimulated and control within each cluster. Save an `AnnData` with all results.

## What the agent does

The `transcriptomics` skill activates on the triggers (`10x`, `AnnData`, `Scanpy`, `Harmony`, `Leiden`, `marker genes`) and `ml-for-science` for the leakage-aware DE design (cells from the same donor are not independent).

### 1. Load + per-sample QC

```python
# pip install scanpy anndata harmonypy scvi-tools
import scanpy as sc
sc.settings.verbosity = 2
samples = {"ctrl_1": "ctrl_1.h5", "ctrl_2": "ctrl_2.h5", "ctrl_3": "ctrl_3.h5",
           "stim_1": "stim_1.h5", "stim_2": "stim_2.h5", "stim_3": "stim_3.h5"}
adatas = {s: sc.read_10x_h5(p) for s, p in samples.items()}
for s, a in adatas.items():
    a.var_names_make_unique()
    a.obs["sample"] = s
    a.obs["condition"] = "stim" if s.startswith("stim") else "ctrl"
adata = sc.concat(adatas, join="outer", label="sample_id")
```

### 2. Filter + normalize + HVG

```python
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata.obs["mt"] = adata.var["mt-"].sum()  # or use adata.var_names.str.match("^MT-")
adata.var["mt"] = adata.var_names.str.startswith("MT-")
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)
adata = adata[adata.obs.pct_counts_mt < 20]
adata.layers["counts"] = adata.X.copy()
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000, batch_key="sample")
```

### 3. PCA + Harmony batch correction + clustering

```python
sc.pp.scale(adata, max_value=10)
sc.tl.pca(adata, n_comps=50)
sc.external.pp.harmony_integrate(adata, key="sample")
sc.pp.neighbors(adata, use_rep="X_pca_harmony", n_neighbors=15)
sc.tl.umap(adata)
sc.tl.leiden(adata, resolution=0.5, key_added="leiden")
```

### 4. Marker genes + cluster annotation

```python
sc.tl.rank_genes_groups(adata, groupby="leiden", method="wilcoxon")
marker_sets = {"T cell": ["CD3D","CD3E","TRAC"],
               "B cell": ["MS4A1","CD79A","CD79B"],
               "Mono":  ["LYZ","S100A8","S100A9"],
               "NK":    ["NKG7","GNLY","KLRD1"]}
# assign each cluster to its best-matching cell type by mean marker expression
```

### 5. Pseudo-bulk DE per cluster (leakage-safe)

```python
# aggregate counts per (donor, cluster) and run DESeq2 via pydeseq2
# pip install pydeseq2
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.default_inference import DefaultInference
pseudobulk = adata.to_df(layer="counts").groupby([adata.obs["donor"], adata.obs["leiden"]]).sum()
# build metadata, run DESeq2 per cluster comparing stim vs ctrl
```

## Pitfalls the skill surfaces

- Never run `sc.tl.rank_genes_groups` on raw counts; it expects log-normalized data.
- Pseudo-bulk (per donor, per cluster) is the correct unit for case/control DE — single-cell-level tests massively inflate N and ignore donor correlation.
- Harmony corrects for sample batch, not for biological condition — keep `condition` out of the covariates Harmony sees.
- Set `adata.uns["log1p"] = "base"` to silence the AnnData deprecation warning.

## Reproducibility

`sc.settings.seed = 1` (or set `random_state` on each stochastic step). Pin scanpy + pydeseq2 versions in `environment.yml`. See the `reproducible-research` skill.

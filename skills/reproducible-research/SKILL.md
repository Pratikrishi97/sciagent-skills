---
name: reproducible-research
description: Make computational research reproducible end-to-end with random seeds, deterministic flags, workflow managers (Snakemake, Nextflow, Prefect), DVC data versioning, containers (Docker, Singularity), and Quarto/Jupyter Book reports archived to Zenodo with DOIs. Use when reproducing experiments, building pipelines, or preparing results for peer review.
license: MIT
compatibility: Requires Python 3.10+ with snakemake, dvc, quarto. Optional: nextflow, singularity/apptainer, docker, zenodo_get.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Data & Visualization
---

# Reproducible Research

## Overview

A result is reproducible when a second researcher, given the inputs, can
regenerate the same outputs bit-for-bit. This skill covers the full stack:
deterministic code (seeds, deterministic kernels), workflow management
(Snakemake, Nextflow, Prefect), data versioning (DVC), containerization
(Docker, Singularity), and report generation (Quarto, Jupyter Book) ending
with archiving on Zenodo and citing the DOI. Following FAIR principles
(Findable, Accessible, Interoperable, Reusable) is treated as a default,
not an afterthought.

## When to use this skill

- You are building a multi-step pipeline (clean -> model -> evaluate -> report).
- You need someone else to be able to rerun your analysis a year later.
- You are preparing a paper, preprint, or supplement that must pass peer
  review of code and data.
- You want a DOI for your analysis bundle.
- You are debugging "works on my machine" issues across HPC, lab workstation,
  and reviewer laptops.

## Prerequisites

- Python 3.10+
- `snakemake` (workflow), `dvc` (data versioning), `quarto` (reports)
- Optional: `nextflow`, `prefect`, `docker`, `apptainer`/`singularity`,
  `zenodo_get`, `jupyter-book`
- System tools: `git`, a container runtime, optionally `mamba` for solving
- pip install:
  ```bash
  pip install snakemake dvc quarto
  pip install prefect zenodo_get
  ```

## Core workflows

### 1. Deterministic code (seeds + flags)

```python
import os, random
import numpy as np

SEED = 20240601
random.seed(SEED)
np.random.seed(SEED)

# PyTorch determinism (if used)
try:
    import torch
    torch.manual_seed(SEED)
    torch.use_deterministic_algorithms(True, warn_only=True)
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
except ImportError:
    pass
```

### 2. Snakemake pipeline

`Snakefile`:
```python
rule all:
    input: "results/figure.pdf"

rule clean:
    input: "data/raw.csv"
    output: "data/clean.parquet"
    shell: "python src/clean.py {input} {output}"

rule model:
    input: "data/clean.parquet"
    output: "results/model.pkl"
    shell: "python src/model.py --in {input} --out {output} --seed 20240601"

rule figure:
    input: "results/model.pkl"
    output: "results/figure.pdf"
    shell: "python src/figure.py {input} {output}"
```

Run: `snakemake -j 4 --use-conda --cores 4`. The `--use-conda` flag ensures
each rule uses the `conda:` env pinned in the rule.

### 3. DVC data versioning

```bash
git init -q && dvc init -q
dvc add data/raw.csv
git add data/raw.csv.dvc .gitignore
git commit -m "version raw data"
dvc remote add -d storage s3://my-bucket/dvc
dvc push
```

Add a DVC pipeline stage:
```bash
dvc stage add -n clean \
  -d src/clean.py -d data/raw.csv \
  -o data/clean.parquet \
  python src/clean.py data/raw.csv data/clean.parquet
dvc repro clean
```

### 4. Reproducible report with Quarto

`report.qmd`:
```yaml
---
title: "Calibration analysis"
author: "Lab X"
date: today
format:
  pdf:
    pdf-engine: xelatex
  html: default
execute:
  echo: true
  seed: 20240601
bibliography: refs.bib
license: CC-BY-4.0
---
```
Build: `quarto render report.qmd`. Commit the rendered HTML alongside the
`.qmd` so reviewers see the exact output.

### 5. Archive to Zenodo

After tagging a release on GitHub, use the Zenodo-GitHub integration to mint
a DOI automatically, or push manually:

```bash
pip install zenodo_get
zenodo_get 1234567            # fetch a record by DOI
# Upload via REST:
curl -H "Authorization: Bearer $ZENODO_TOKEN" \
  -X POST "https://zenodo.org/api/deposit/depositions" \
  -H "Content-Type: application/json"
```

## Best practices

- Pin seeds and capture them in workflow metadata; never rely on system
  entropy for code that must reproduce.
- Use `--use-conda`/`--use-singularity` in Snakemake so rules are isolated.
- Version data with DVC; never commit raw datasets to git.
- Provide a `Makefile` or `justfile` as the entry point for one-command runs.
- Freeze environments with `conda-lock` or `pip-compile` and commit lockfiles.
- Ship containers (Docker or Apptainer) for full stack reproducibility.
- Write tests that compare result hashes against a recorded baseline.
- Archive final outputs to Zenodo/Figshare/Zenodo and cite the DOI in the
  paper.
- Add a `CITATION.cff` file so others can cite the software.
- Document the runtime wall-clock and resource envelope (cores, RAM, GPU)
  in the README.

## Common pitfalls

- Setting `numpy.random.seed` but using a library that ignores it (e.g.
  some CUDA kernels); always also set the deterministic flag.
- Committing `.dvc/cache` to git; only commit the small pointer files.
- Snakemake rules that read from the network without version pins (e.g.
  `wget https://latest.zip`) silently break over time.
- Quarto outputs that depend on the local filesystem for assets that
  reviewers lack; embed with `embed-resources: true`.
- Zenodo uploads that include the `.git` directory; use `.zenodoignore`.
- Mixing conda and pip-installed packages inside one environment; pick one
  channel per environment.
- Forgetting to bump the seed in `metadata` when re-running with new data.
- Containers that bake in absolute paths (`/home/you/...`) break on HPC;
  use `${HOME}` or copy to `/opt`.

## Worked example

A two-stage Snakemake pipeline with DVC-tracked input and a Quarto report.
Directory layout:

```
project/
├── Snakefile
├── data/raw.csv         # dvc-tracked
├── src/clean.py
├── src/model.py
├── report.qmd
└── envs/clean.yaml
```

`Snakefile`:
```python
configfile: "config.yaml"

rule all:
    input: "report.html"

rule clean:
    input: "data/raw.csv"
    output: "data/clean.parquet"
    conda: "envs/clean.yaml"
    shell: "python src/clean.py {input} {output}"

rule model:
    input: "data/clean.parquet"
    output: "results/model.pkl", "results/metrics.json"
    params: seed=config["seed"]
    shell: "python src/model.py --in {input} --out {output.out} --metrics {output.metrics} --seed {params.seed}"

rule report:
    input: "results/metrics.json"
    output: "report.html"
    shell: "quarto render report.qmd --to html"
```

Run:
```bash
dvc add data/raw.csv
git add data/raw.csv.dvc .gitignore
git commit -m "add raw data"
snakemake --use-conda --cores 4 --rerun-incomplete
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| Snakemake | Rule-based workflow manager | `pip install snakemake` |
| Nextflow | DSL for bioinformatics pipelines | install via conda |
| Prefect | Python-native flow orchestration | `pip install prefect` |
| DVC | Data version control | `pip install dvc` |
| Quarto | Scientific publishing system | install quarto-cli |
| Jupyter Book | Book builder from notebooks | `pip install jupyter-book` |
| conda-lock | Reproducible conda lockfiles | `pip install conda-lock` |
| Docker | Container runtime | system install |
| Apptainer | HPC-friendly containers | install Apptainer |
| Zenodo REST | DOI minting and archive | HTTP API |
| CITATION.cff | Citation metadata standard | plain text |

## References

- Snakemake docs: https://snakemake.readthedocs.io/
- Nextflow docs: https://www.nextflow.io/docs/latest/
- DVC tutorial: https://dvc.org/doc/start
- Quarto guide: https://quarto.org/docs/guide/
- Jupyter Book: https://jupyterbook.org/
- FAIR principles: https://www.go-fair.org/fair-principles/
- Zenodo developers guide: https://developers.zenodo.org/
- CFF schema: https://github.com/citation-file-format/citation-file-format

## Ethics & safety

- **Reproducibility** is a research integrity obligation: do not publish
  results whose pipeline cannot be rerun by an independent party.
- **Provenance:** preserve source data hashes and tool versions; record
  them in machine-readable form (`renv`, `requirements.txt` with hashes).
- **Privacy:** strip PII before archival; use `dvc remote` access controls on
  sensitive datasets.
- **Licensing:** attach permissive licenses (MIT, BSD-3) to code, CC-BY-4.0
  to figures and text; respect upstream licenses when repackaging.
- **Auditability:** prefer bit-for-bit reproducibility reports (e.g.
  `repro`/`guix` for binary verification) when stakes are high.

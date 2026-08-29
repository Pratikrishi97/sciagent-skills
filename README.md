# Scientific Agent Skills

> A curated collection of **40 open Agent Skills** that turn coding assistants — Cursor, Claude Code, OpenAI Codex, GitHub Copilot, Gemini CLI — into a stronger research partner for science and engineering work.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Skills](https://img.shields.io/badge/Skills-40-brightgreen.svg)](#available-skills)
[![Agent Skills Standard](https://img.shields.io/badge/Agent%20Skills-1.0-purple.svg)](https://agentskills.io)
[![Agent Plugins](https://img.shields.io/badge/Agent%20Plugins-1.0-teal.svg)](https://agent-plugins.org)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/Pratikrishi97/scientific-agent-skills/skills.yml?label=CI)](https://github.com/Pratikrishi97/scientific-agent-skills/actions)
[![Contributions welcome](https://img.shields.io/badge/Contributions-welcome-ff69b4.svg)](./CONTRIBUTING.md)

---

Whether you're calling variants, screening a compound library, training a deep model on microscopy, running a climate reanalysis on an HPC cluster, or drafting a grant — your AI coding assistant usually knows *a little* about your domain. **Scientific Agent Skills** gives it a deep, opinionated, copy-pasteable manual for the workflow you're actually doing, written by people who run these pipelines for a living.

Each skill is a single `SKILL.md` file written to the open [Agent Skills](https://agentskills.io) specification. Drop it into `~/.claude/skills/`, `~/.agents/skills/`, `.cursor/rules/`, or upload it as a Codex bundle — and your assistant suddenly follows domain best practices instead of guessing.

---

## Table of contents

- [Why this exists](#why-this-exists)
- [What's included](#whats-included)
- [Quick start](#quick-start)
- [Prerequisites](#prerequisites)
- [Available skills](#available-skills)
- [How it works](#how-it-works)
- [Agent compatibility](#agent-compatibility)
- [Worked examples](#worked-examples)
- [Listing & validating skills](#listing--validating-skills)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)
- [Contributing](#contributing)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Citation](#citation)
- [License](#license)
- [Star history](#star-history)
- [Acknowledgments](#acknowledgments)

---

## Why this exists

Coding assistants are generalists. They write a Pandas `groupby` fine, but ask one to "run a GWAS" or "do a virtual screen against SARS-CoV-2 main protease" and you'll get something that *looks* right and quietly isn't — wrong reference assembly, inverted docking box, a CNN that leaks future data into training, a Cox model that violates proportional hazards. The fix isn't a bigger model; it's giving the one you already have the same domain checklist a senior PhD uses.

**Scientific Agent Skills** is that checklist, as data:

- **Open standard.** Every skill is a plain `SKILL.md` with YAML frontmatter. No proprietary format, no walled garden. Works in any agent that supports the [Agent Skills](https://agentskills.io) or [Agent Plugins](https://agent-plugins.org) specs.
- **Python-first, but prose.** Examples reference the canonical scientific Python libraries (BioPython, RDKit, PySCF, astropy, xarray, MONAI, PyTorch, Qiskit, ...). Skills are not runtime code — they are instructions an agent loads on demand.
- **Progressive disclosure.** Agents only pay tokens for the catalog (name + description, ~80 tokens each) until a skill is activated. You can install all 40 and they cost almost nothing until you ask about one.
- **Audit-able.** A stdlib-only scanner (`scan_skills.py`) enforces the contract on every PR. No frontmatter drift, no broken links, no compiled artifacts sneaking into a skill folder.

## What's included

**40 skills across 11 categories**, each with: a one-paragraph *what + when*, prerequisites, 3–5 runnable core workflows, best practices, common pitfalls, a worked end-to-end example, a tools/libraries table, canonical references, and an ethics & safety note.

| Category | Skills |
|---|---|
| Biology & Genomics | genomics, transcriptomics, protein-analysis, proteomics, evolutionary-biology |
| Drug Discovery & Cheminformatics | drug-discovery, cheminformatics, admet-prediction, retrosynthesis |
| Clinical & Medical Research | clinical-research, medical-imaging, epidemiology, clinical-nlp |
| Chemistry & Materials | computational-chemistry, materials-science, reaction-modeling |
| Physics & Astronomy | computational-physics, astrophysics, quantum-computing |
| Machine Learning & Statistics | ml-for-science, deep-learning, scientific-computing, biostatistics |
| Geospatial & Earth Science | geospatial-analysis, climate-science, remote-sensing |
| Data & Visualization | data-visualization, reproducible-research, scientific-data-management |
| Lab & Automation | lab-automation, experimental-design, instrument-integration |
| Research Infrastructure | reproducible-environments, hpc-computing, notebook-best-practices |
| Knowledge & Communication | literature-review, citation-management, scientific-writing, grant-writing, scientific-presentations |

## Quick start

Pick **one** of the four install methods. They all install the same skills; the only difference is *where* the files land so your agent can find them.

### Option 1 — One-liner with the `skills` CLI (recommended)

```bash
npx skills add Pratikrishi97/scientific-agent-skills          # user-level, cross-host (~/.agents/skills/)
npx skills add Pratikrishi97/scientific-agent-skills --agent claude-code
npx skills add Pratikrishi97/scientific-agent-skills --agent cursor --skill genomics
```

### Option 2 — Install as an Agent Plugins bundle

The repo ships a `plugin.json` (Agent Plugins 1.0.0 manifest). Cursor, Codex, GitHub Copilot, and VS Code can install the whole repo as one portable plugin:

```bash
# Cursor: Settings → Agent Plugins → Install local plugin → point at this repo
# Codex CLI:
codex plugins install .
```

### Option 3 — GitHub CLI skill installer

```bash
gh skill install Pratikrishi97/scientific-agent-skills                    # all skills
gh skill install Pratikrishi97/scientific-agent-skills genomics           # one skill
gh skill install Pratikrishi97/scientific-agent-skills --agent cursor
```

### Option 4 — Plain copy (no tooling required)

```bash
git clone https://github.com/Pratikrishi97/scientific-agent-skills.git
cd scientific-agent-skills

# install all skills for Claude Code (user-level)
python scripts/install_skills.py --agent claude-code --all

# or a single skill into the current Cursor project
python scripts/install_skills.py --agent cursor --skill genomics --project

# or just copy by hand:
cp -r skills/genomics ~/.claude/skills/
```

See where each agent stores skills:

```bash
python scripts/install_skills.py --paths
```

After installing, restart your editor / agent session. Mention the domain in your prompt and the right skill activates automatically:

> "I have paired-end RNA-seq FASTQs from a case/control study. Do differential expression and call markers."

Cursor / Claude Code / Codex will load `transcriptomics` (and `biostatistics` for the stats) and follow the canonical Scanpy + pydeseq2 workflow instead of improvising.

## Prerequisites

- **Python 3.10+** for the repo's tooling (scanner, installer, converter). The skills themselves are prose + Python examples; individual skills declare their own library requirements in the `compatibility` frontmatter field.
- An **Agent Skills-compatible editor/CLI**:
  - Claude Code (`~/.claude/skills/`)
  - Cursor (`.cursor/rules/*.mdc` or `~/.agents/skills/`)
  - OpenAI Codex (upload the `skills/` directory as a bundle)
  - GitHub Copilot / Gemini CLI (`~/.agents/skills/`)
- Optional, for the tooling only: `pip install pyyaml` (the scanner falls back to a stdlib parser if PyYAML is missing).

## Available skills

The full list, grouped by category. Run `python scan_skills.py --list` after cloning to see the live, always-current catalog.

### Biology & Genomics
- **genomics** — variant calling (FASTQ→BAM→VCF→annotation), GWAS, population genetics. Triggers: VCF, BAM, GATK, DeepVariant, PLINK, BioPython.
- **transcriptomics** — bulk + single-cell RNA-seq. Triggers: Scanpy, AnnData, DESeq2, UMAP, Leiden, scVI, Cell Ranger.
- **protein-analysis** — sequence + structure + dynamics. Triggers: PDB, AlphaFold, FoldSeek, DSSP, PyMOL, OpenMM.
- **proteomics** — mass spec, DIA, quant, pathway. Triggers: pyteomics, DIA-NN, MaxQuant, MSstats, gseapy.
- **evolutionary-biology** — alignment, phylogenetics, selection, demography. Triggers: IQ-TREE, PAML, HyPhy, msprime, scikit-allel.

### Drug Discovery & Cheminformatics
- **drug-discovery** — virtual screening, docking, hit-to-lead, FEP. Triggers: Vina, ZINC, ChEMBL, Perses.
- **cheminformatics** — RDKit, fingerprints, similarity, scaffolds. Triggers: SMILES, InChI, Morgan, Tanimoto, SMARTS.
- **admet-prediction** — ADMET, tox, PAINS, pkCSM. Triggers: hERG, CYP, BBB, SwissADME, DeepChem, chemprop.
- **retrosynthesis** — route planning, synth accessibility. Triggers: AiZynthFinder, ASKCOS, USPTO, Reaxys.

### Clinical & Medical Research
- **clinical-research** — trials, CDISC, EHR, survival. Triggers: SDTM, ADaM, OMOP, FHIR, lifelines, CONSORT.
- **medical-imaging** — DICOM, MONAI, segmentation, de-id. Triggers: pydicom, SimpleITK, nnU-Net, BraTS, TCIA.
- **epidemiology** — SIR/SEIR, R estimation, surveillance. Triggers: EpiNow2, Rt, GISAID, outbreak, vaccine efficacy.
- **clinical-nlp** — de-identification, medical NER, terminologies. Triggers: MedSpaCy, scispaCy, UMLS, SNOMED-CT, ICD-10, Presidio.

### Chemistry & Materials
- **computational-chemistry** — DFT, MD, QM/MM, solvation. Triggers: PySCF, ASE, OpenMM, xtb, Gaussian, ORCA.
- **materials-science** — crystals, phase diagrams, ML potentials. Triggers: pymatgen, mp-api, MACE, CHGNet, Materials Project.
- **reaction-modeling** — TS search, kinetics, networks. Triggers: NEB, Cantera, RMG-Py, CHEMKIN, Arrhenius.

### Physics & Astronomy
- **computational-physics** — PDEs, FFT, ODEs, autodiff. Triggers: SciPy, NumPy, JAX, FEniCSx, Dedalus, solve_ivp.
- **astrophysics** — FITS, WCS, coordinates, catalogs. Triggers: astropy, photutils, specutils, astroquery, poliastro, yt.
- **quantum-computing** — circuits, VQE/QAOA, open systems. Triggers: Qiskit, PennyLane, Cirq, QuTiP, OpenFermion.

### Machine Learning & Statistics
- **ml-for-science** — sklearn pipelines, leakage-safe CV, SHAP. Triggers: scikit-learn, cross-validation, group CV, SHAP, imbalanced-learn.
- **deep-learning** — PyTorch training loops, mixed precision, DDP. Triggers: nn.Module, DataLoader, accelerate, MLflow, gradient checkpointing.
- **scientific-computing** — NumPy/SciPy/SymPy/Numba/Dask/xarray. Triggers: einsum, solve_ivp, sparse, jit, broadcasting, xarray.
- **biostatistics** — power, multiple comparisons, survival, mixed models, Bayes. Triggers: statsmodels, lifelines, PyMC, bootstrap, FDR, Cohen's d.

### Geospatial & Earth Science
- **geospatial-analysis** — GeoPandas, rasterio, routing. Triggers: GeoDataFrame, sjoin, EPSG, rasterstats, osmnx, folium.
- **climate-science** — xarray, CF, regridding, CMIP6. Triggers: netCDF, CESM, intake-esm, xESMF, cartopy, ERA5.
- **remote-sensing** — Sentinel/Landsat, STAC, indices. Triggers: rasterio, satpy, STAC, torchgeo, NDVI, s2cloudless.

### Data & Visualization
- **data-visualization** — publication figures, color-blind palettes. Triggers: matplotlib, seaborn, plotly, cartopy, viridis, rcParams.
- **reproducible-research** — seeds, Snakemake, DVC, Quarto, Zenodo. Triggers: random_state, Snakemake, DVC, Quarto, FAIR, DOI.
- **scientific-data-management** — Parquet/Zarr/HDF5, catalogs, FAIR. Triggers: h5py, Zarr, Intake, CF, schema.org, s3fs.

### Lab & Automation
- **lab-automation** — LIMS, Opentrons, plate readers. Triggers: Opentrons, labware, Tecan, BMG, ELN.
- **experimental-design** — DOE, factorial, RSM, power. Triggers: pyDOE2, Box-Behnken, central composite, BoTorch, power analysis.
- **instrument-integration** — PyVISA, SCPI, DAQ, logging. Triggers: PyVISA, PyMeasure, nidaqmx, SCPI, GPIB.

### Research Infrastructure
- **reproducible-environments** — conda, uv, Docker, Singularity. Triggers: environment.yml, conda-lock, uv, Dockerfile, Apptainer.
- **hpc-computing** — SLURM, mpi4py, dask-jobqueue. Triggers: sbatch, srun, mpi4py, dask-jobqueue, gres, QoS.
- **notebook-best-practices** — papermill, jupytext, nbval. Triggers: papermill, jupytext, nbconvert, %memit, ipywidgets.

### Knowledge & Communication
- **literature-review** — PRISMA, PubMed, OpenAlex, meta-analysis. Triggers: systematic review, PRISMA, ASReview, Rayyan, forest plot.
- **citation-management** — BibTeX, Zotero, CSL, Crossref. Triggers: bibtexparser, pyzotero, habanero, CSL-JSON, anystyle, ORCID.
- **scientific-writing** — IMRaD, LaTeX, Quarto, preprints. Triggers: pylatex, Quarto, Overleaf, bioRxiv, CRediT, structured abstract.
- **grant-writing** — NIH/NSF/Horizon, biosketch, DMS plan. Triggers: Specific Aims, NIH RePORTER, NSF PAPPG, DMS, broader impacts.
- **scientific-presentations** — reveal.js, Beamer, posters. Triggers: Quarto revealjs, Beamer, Marp, A0 poster, accessibility.

## How it works

Every skill is a folder under `skills/<name>/SKILL.md`. The `SKILL.md` is plain Markdown with a small YAML header:

```yaml
---
name: genomics
description: Variant calling, GWAS, and population genetics. Use when the user has
  FASTQ/BAM/VCF files, mentions GATK/DeepVariant/PLINK/BioPython, or asks about
  reference assemblies, annotation, or association testing.
license: MIT
compatibility: Requires Python 3.10+ with pysam, biopython, cyvcf2.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Biology & Genomics
---

# Genomics workflows

## Overview
...
```

The body is unrestricted Markdown — typically 300–500 lines of: overview, *when to use*, prerequisites, core workflows (each a minimal runnable snippet), best practices, common pitfalls, a worked end-to-end example, a tools table, references, and an ethics note.

**Progressive disclosure.** Host agents load *only* the catalog (name + description, ~80 tokens per skill) at startup. When your prompt matches a skill's trigger keywords, the host loads that one skill's full body. The other 39 stay out of context. This is why you can install all 40 and your context budget barely moves until you ask.

**The contract, enforced.** `scan_skills.py` checks, on every PR, that every `SKILL.md`:

- has parseable YAML frontmatter,
- declares `name` matching its folder, lowercase and regex-clean,
- declares `description` (1–1024 chars) with trigger keywords,
- keeps the body under 500 lines (warning, not failure),
- references other files with relative paths only one level deep,
- ships no compiled Python (`.pyc`, `__pycache__/`, `.so`),
- ships a `tests/<name>/` suite if it includes a `scripts/` directory.

Run it yourself:

```bash
python scan_skills.py --validate     # enforce the contract (exit 1 on failure)
python scan_skills.py --list          # one-line catalog
python scan_skills.py --categories    # grouped by category
python scan_skills.py --tree          # indented tree
python scan_skills.py --show genomics # pretty-print one skill's metadata
python scan_skills.py --json          # machine-readable manifest
```

## Agent compatibility

The same `SKILL.md` files work across every agent that supports the open Agent Skills standard. Where each one stores them:

| Agent | User-level path | Project-level path | Notes |
|---|---|---|---|
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` | Auto-discovers on session start. `CLAUDE.md` redirects to `AGENTS.md`. |
| **Cursor** | `~/.agents/skills/` or `~/.cursor/skills/` | `.agents/skills/` or `.cursor/rules/*.mdc` | Use `scripts/to_mdc.py` to emit native `.mdc` rules. |
| **OpenAI Codex / ChatGPT** | uploaded bundle | uploaded bundle | Zip `skills/` (≤50 MB, ≤500 files). Attach via `tools[].environment.skills`. |
| **GitHub Copilot** | `~/.copilot/skills/` | `.github/copilot/skills/` | Also reads `AGENTS.md`. |
| **Gemini CLI** | `~/.agents/skills/` | `.agents/skills/` | Honors the cross-host convention. |
| **Any Agent Skills client** | `~/.agents/skills/` | `.agents/skills/` | The cross-host convention most clients scan. |

Project-level skills override user-level on name collisions. To convert skills into Cursor's native `.mdc` format (with `description`/`globs`/`alwaysApply` frontmatter):

```bash
python scripts/to_mdc.py --out .cursor/rules          # all skills
python scripts/to_mdc.py --out ~/.cursor/rules --skill genomics
```

## Worked examples

A few prompts that reliably trigger the right skill(s). Full, runnable versions live in [`examples/`](./examples).

**Genomics — call variants from paired-end reads**
> "I have paired-end Illumina FASTQs (R1/R2) from 12 samples against GRCh38. Run QC, align with BWA-MEM2, mark duplicates, call SNPs/indels with GATK HaplotypeCaller in GVCF mode, joint-genotype, hard-filter, and annotate with SnpEff. Give me a MultiQC report at the end."

**Drug discovery — virtual screen a compound library**
> "Screen the Enamine REAL diversity set (~1.6M) against the SARS-CoV-2 main protease (PDB 6LU7). Apply Lipinski + PAINS filters, prep the receptor with Meeko, dock with AutoDock Vina in an exhaustiveness=32 box around the catalytic dyetad, rank by score, and shortlist the top 50 for ADMET."

**Climate — compute a regional climatology**
> "Download ERA5 monthly 2m temperature (1950–2023) for the Indian subcontinent from the Copernicus CDS, compute the 1991–2020 climatology and anomalies, regrid to 0.25° with xESMF, and make a Robinson projection map of the 2023 anomaly with cartopy."

**Clinical NLP — de-identify radiology reports**
> "I have 5,000 free-text radiology reports. De-identify them with Presidio + scispaCy, extract findings with MedSpaCy, map to UMLS/SNOMED-CT, and output FHIR `DocumentReference` resources. Never echo real PHI to me."

**Reproducibility — ship a pipeline**
> "Wrap my Scanpy + DESeq2 single-cell workflow in a Snakemake pipeline with a DVC-tracked input/output, an `environment.yml` pinned with conda-lock, and a Docker image. Validate it runs end-to-end on a tiny test fixture."

## Listing & validating skills

```bash
# human-readable catalog
python scan_skills.py --list

# grouped by category
python scan_skills.py --categories

# tree view
python scan_skills.py --tree

# one skill's full metadata
python scan_skills.py --show genomics

# machine-readable manifest (for catalogs, docs generators, websites)
python scan_skills.py --json > skills-manifest.json

# enforce the contract — used by CI, exits 1 on failure
python scan_skills.py --validate
```

## Troubleshooting

**My agent doesn't pick up a skill I just installed.**
Restart the editor / agent session. Most agents scan the skills directory only at startup. Verify the file is where the agent expects:
```bash
python scripts/install_skills.py --paths
ls ~/.claude/skills/genomics/SKILL.md   # for Claude Code
ls ~/.agents/skills/genomics/SKILL.md    # cross-host
```

**The scanner says my new skill is invalid.**
Run `python scan_skills.py --show <name>` for a detailed report. The most common causes: `name` doesn't match the folder, `description` is empty or over 1024 chars, the body exceeds 500 lines (warning), or a relative link escapes more than one level. The scanner prints the exact rule that failed.

**Cursor ignores my skills.**
Cursor's native format is `.cursor/rules/*.mdc`, not `.md`. Either drop skills into `~/.agents/skills/` (Cursor reads the cross-host convention) or convert them:
```bash
python scripts/to_mdc.py --out .cursor/rules
```

**A code snippet in a skill fails to run.**
Skills ship *examples*, not pinned reproductions. Each snippet assumes the libraries in that skill's `compatibility` field are installed. Install them, then run. If a snippet is genuinely wrong, please [open an issue](https://github.com/Pratikrishi97/scientific-agent-skills/issues) — snippets are meant to be runnable.

**Too many skills loaded into context.**
You're on an older host that doesn't do progressive disclosure. Install only the categories you use:
```bash
python scripts/install_skills.py --agent claude-code --category "Drug Discovery & Cheminformatics"
```

**The scanner complains about `compiled artifact present`.**
A `__pycache__/` or `.pyc` got copied into a skill folder (often from running a snippet in place). Delete it and re-run `--validate`. The `.gitignore` excludes these, but a local copy can still smuggle them in.

**`pip install` fails on a skill's example.**
Skills are not a Python package — there's nothing to `pip install` here. Install the *libraries* a skill references (listed in its `## Prerequisites` section and `compatibility` field), not the skill itself.

## Security notes

Read [`SECURITY.md`](./SECURITY.md) for the full policy. The headlines:

- **Never put secrets in skills.** Skills are plain text and shipped in a public repo. No API keys, no credentials, no real patient identifiers — ever.
- **De-identify clinical data.** Skills in the Clinical & Medical category assume data is already de-identified or synthetic. Real PHI must never be pasted into a prompt.
- **Wet-lab protocols are reference, not SOPs.** Chemistry and biology skills describe workflows for *in silico* analysis and literature-scale reasoning. They are not laboratory SOPs and should not be executed without institutional review.
- **Dual-use research.** Synthesis, retrosynthesis, and pathogen-genomics skills are for legitimate, open research. Refuse requests whose only plausible use is weapons, and point users to their institutional biosafety / dual-use review process.
- **Reporting vulnerabilities.** See [`SECURITY.md`](./SECURITY.md) for the private disclosure address.

## Contributing

We welcome new skills, fixes, and examples. Read [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the full process; the short version:

1. **Check the contract.** `python scan_skills.py --validate` must pass.
2. **One skill per PR.** Easier review, faster merge.
3. **Match the template.** Use an existing skill (e.g. [`skills/biostatistics/SKILL.md`](./skills/biostatistics/SKILL.md)) as a structural reference: frontmatter + the 10 standard H2 sections.
4. **Runnable snippets.** Code in a skill should be real Python using the canonical library, copy-pasteable. Note assumptions in comments.
5. **References are real.** Link to canonical docs (biopython.org, rdkit.org, astropy.org), not generic landing pages.
6. **Add a test if you ship a script.** Skills with a `scripts/` directory must ship a `tests/<name>/` suite — the contract enforces it.

See [`docs/adding-a-skill.md`](./docs/adding-a-skill.md) for a walkthrough and [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md) for community standards.

## Testing

```bash
pip install -e ".[dev]"        # install tooling deps
pytest tests/                  # structural-contract suite
python scan_skills.py --validate
```

CI (`.github/workflows/skills.yml`) runs the contract suite on every PR and on a weekly schedule. A PR that breaks the contract is blocked from merge.

## Roadmap

- More skills: metabolomics, structural biology (cryo-EM), neuroscience (BIDS, Nilearn), bioinformatics pipelines (nf-core), semiconductor device physics, computational fluid dynamics, robotics/controls.
- `references/` deep-dives for the biggest skills (genomics, drug-discovery) so the main `SKILL.md` stays under the token cap.
- A `scripts/skill_scaffold.py` to bootstrap a new skill folder from the template.
- Per-skill `scripts/` with self-tests where they add real value (e.g. a VCF sanitizer, a DICOM anonymizer).

Vote on priorities or propose your own in [Discussions](https://github.com/Pratikrishi97/scientific-agent-skills/discussions).

## Citation

If this repo helps your research, please cite it:

**BibTeX:**
```bibtex
@misc{scientific_agent_skills,
  title  = {Scientific Agent Skills: A curated collection of open Agent Skills for science and engineering},
  author = {Scientific Agent Skills Contributors},
  year   = {2025},
  url    = {https://github.com/Pratikrishi97/scientific-agent-skills},
  note   = {version 1.0.0}
}
```

**APA:**
> Scientific Agent Skills Contributors. (2025). *Scientific agent skills: A curated collection of open Agent Skills for science and engineering* (version 1.0.0). https://github.com/Pratikrishi97/scientific-agent-skills

**MLA:**
> Scientific Agent Skills Contributors. "Scientific Agent Skills: A Curated Collection of Open Agent Skills for Science and Engineering." 2025, GitHub, version 1.0.0, github.com/Pratikrishi97/scientific-agent-skills.

## License

[MIT](./LICENSE) © Scientific Agent Skills Contributors. Individual skills may declare a different license in their `license:` frontmatter field; absent one, the repo-wide MIT license applies.

## Star history

<!-- star-history placeholders; replace Pratikrishi97 after rename -->
<a href="https://star-history.com/#Pratikrishi97/scientific-agent-skills&Date">
 <img src="https://api.star-history.com/svg?repos=Pratikrishi97/scientific-agent-skills&type=Date" alt="Star History" width="500" />
</a>

## Acknowledgments

- The [Agent Skills](https://agentskills.io) and [Agent Plugins](https://agent-plugins.org) standard bodies for the portable, agent-agnostic format these skills are written to.
- Every upstream scientific Python project — BioPython, RDKit, PySCF, astropy, xarray, MONAI, PyTorch, Qiskit, pymatgen, GeoPandas, Snakemake, and dozens more — whose APIs these skills document.
- The researchers who reviewed early drafts of the clinical, drug-discovery, and genomics skills for accuracy.

Built by scientists, for anyone who'd rather their AI assistant knew what a Cox model actually assumes.

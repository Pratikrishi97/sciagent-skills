# Contributing to Scientific Agent Skills

First, thank you. Scientific computing has a long tail of workflows, and the only way this library covers them all is if domain experts contribute the skills they actually use. Whether it's one typo fix or a whole new category, it's welcome.

This document is the source of truth for how contributions land. The contract is enforced by `scan_skills.py` and CI — if your PR is green, you're almost done.

## Code of conduct

Participation in this project is governed by the [Contributor Covenant 2.1](./CODE_OF_CONDUCT.md). Please be excellent to each other.

## Quick path (small fixes)

Typos, dead links, clearer wording, one-line code fixes:

1. Fork & branch.
2. Edit the file. Run `python scan_skills.py --validate`.
3. Open a PR with a one-line description. No issue required.

## Adding a new skill

### 1. Pick the name and category

- `name` is lowercase, `[a-z0-9-]` only, no leading/trailing or consecutive hyphens. It must equal the skill folder name. Good: `single-cell-rna-seq`. Bad: `single_cell_RNAseq`, `-genomics-`, `genomics--vcf`.
- One concept per skill. If you can split it, split it. `cheminformatics` and `admet-prediction` are separate skills, not one.

### 2. Scaffold the folder

```bash
mkdir -p skills/<your-skill>
$EDITOR skills/<your-skill>/SKILL.md
```

### 3. Write the SKILL.md

Use [`skills/biostatistics/SKILL.md`](./skills/biostatistics/SKILL.md) as a structural reference. Required:

- **YAML frontmatter** with `name`, `description`, and at minimum `license`, `compatibility`, `metadata.version`, `metadata.skill-author`, `metadata.category`. See the [frontmatter spec](#frontmatter-reference) below.
- **The 10 standard H2 sections** in order:
  1. `## Overview`
  2. `## When to use this skill`
  3. `## Prerequisites`
  4. `## Core workflows` (3–5 `###` sub-workflows, each with a minimal runnable Python snippet)
  5. `## Best practices`
  6. `## Common pitfalls`
  7. `## Worked example`
  8. `## Tools & libraries` (a markdown table)
  9. `## References`
  10. `## Ethics & safety`

### 4. Write runnable code

Every code snippet should be real Python using the canonical library for the domain, copy-pasteable. Note assumptions in comments:

```python
# assumes: pip install scanpy anndata
import scanpy as sc
adata = sc.read_h5ad("pbmc.h5ad")
sc.pp.filter_cells(adata, min_genes=200)
```

Not pseudocode. Not "do the analysis." Real API calls.

### 5. Add references and assets (optional)

- Long deep-dives go in `skills/<name>/references/*.md`, linked from the main body with a **relative path, one level deep** (e.g. `[CDISC SDTM](references/cdisc-sdtm.md)`).
- Templates, sample data, or non-code assets go in `skills/<name>/assets/`.
- If you ship a runnable helper script, it goes in `skills/<name>/scripts/` and you MUST also ship a test in `tests/<name>/`. The contract enforces this.

### 6. Validate and test

```bash
python scan_skills.py --validate     # must exit 0
python scan_skills.py --show <name>  # confirm metadata renders
pytest tests/                          # contract suite
```

### 7. Open the PR

- One skill per PR (or one category if they're tightly related).
- PR title: `skill: add <name>` or `skill(<category>): add <name>`.
- Description: what the skill does, the canonical libraries it references, and a one-line trigger example ("activates when the user says: ...").

## Frontmatter reference

```yaml
---
name: my-skill                    # REQUIRED, must match folder, [a-z0-9-]
description: ...                  # REQUIRED, 1-1024 chars, include trigger keywords
license: MIT                      # optional, defaults to repo MIT
compatibility: Requires Python 3.10+ with foo, bar.   # optional, <=500 chars
metadata:                          # optional, all values must be strings
  version: "1.0.0"
  skill-author: Your Name
  category: Your Category
allowed-tools: Bash(git:*) Read   # optional, experimental (pre-approved tools)
---
```

### Description writing tips

The `description` is the single most important field — it's all the agent sees until it decides to activate the skill. Make it say **what** the skill does and **when** to use it, and include the trigger keywords a researcher would actually type.

Good:
> Differential expression and marker-gene analysis for bulk and single-cell RNA-seq. Use when the user has count matrices, AnnData/h5ad files, or mentions DESeq2/edgeR/Scanpy/pydeseq2, UMAP, Leiden, or Cell Ranger.

Bad:
> Helps with RNA-seq data analysis.

## Style guide

- **Voice.** Direct, concrete, second-person. "Use `sc.pp.normalize_total`" not "the data should be normalized."
- **Snippets.** Real API calls, <30 lines each, runnable given the libraries. Assume the `compatibility` env.
- **References.** Canonical docs only (e.g. https://rdkit.org/docs, https://docs.astropy.org). No marketing pages, no Medium posts.
- **Length.** 280–480 lines is the sweet spot. The 500-line cap is a hard warning; move depth to `references/`.
- **ASCII-safe.** Use `-` bullets, not unicode dashes. Avoid non-ASCII in YAML values.
- **No secrets.** No real API keys, tokens, patient IDs, or private URLs.

## Reviewing PRs

Maintainers check, in order:

1. Contract passes (`scan_skills.py --validate`, `pytest tests/`).
2. The skill is on-topic for science/engineering.
3. Snippets are real and approximately runnable.
4. References are canonical.
5. Description contains trigger keywords.
6. Ethics & safety note is present and sensible.

## Release process

- Semantic versioning (`MAJOR.MINOR.PATCH`). Skill-level versions live in `metadata.version`; repo-level version lives in `pyproject.toml` and `plugin.json`.
- A new skill is a MINOR bump. A fix to an existing skill is a PATCH bump. Breaking changes to the frontmatter contract are MAJOR.
- [`CHANGELOG.md`](./CHANGELOG.md) is updated on every release.

## Attribution

Contributors are credited in the release notes. If you'd like a recurring maintainer role, say so in a PR — we're growing the team.

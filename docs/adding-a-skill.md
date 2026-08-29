# Adding a skill — walkthrough

This is the step-by-step version of [`CONTRIBUTING.md`](../CONTRIBUTING.md). By the end you'll have a new skill that passes the contract and is ready for a PR.

## 1. Choose the skill

You're adding a skill because you keep doing the same workflow and your assistant keeps getting it slightly wrong. Write down, in one sentence each:

- **What** the skill does (the workflow, end to end).
- **When** an agent should pick it up (the trigger keywords a user types).
- **The canonical library** for the domain (the one a senior researcher reaches for first).

If you can't answer all three crisply, the skill isn't ready — keep refining the scope until you can.

### Example (real)

> **What:** Build a reproducible bioinformatics pipeline with Nextflow + nf-core modules.
> **When:** User mentions Nextflow, nf-core, Groovy DSL, `nextflow run`, Docker/Singularity containers, or workflow orchestration for genomics/proteomics.
> **Canonical lib:** Nextflow + nf-core.

That's a skill. Call it `nextflow-pipelines` (lowercase, hyphen-separated).

## 2. Scaffold the folder

```bash
cd scientific-agent-skills
mkdir -p skills/nextflow-pipelines
$EDITOR skills/nextflow-pipelines/SKILL.md
```

## 3. Write the frontmatter

```yaml
---
name: nextflow-pipelines
description: Build reproducible bioinformatics pipelines with Nextflow and the
  nf-core module library. Use when the user mentions Nextflow, nf-core, Groovy
  DSL, nextflow run, or workflow orchestration for genomics, proteomics, or
  bulk/single-cell analysis, or asks to wrap a multi-step pipeline in containers.
license: MIT
compatibility: Requires Nextflow 23.04+ and Java 17. Python examples use
  nf-core/tools and rich.
metadata:
  version: "1.0.0"
  skill-author: Your Name
  category: Research Infrastructure
---

# Nextflow & nf-core pipelines
```

Notes:
- `name` **exactly equals** the folder name. The scanner rejects mismatches.
- `description` includes the trigger keywords ("Nextflow", "nf-core", "Groovy DSL", "nextflow run", "workflow orchestration"). This is what makes the agent pick the skill up.
- No colons inside the `description` value unless you quote the whole value. PyYAML mis-parses unquoted `key: value` pairs.

## 4. Write the 10 standard sections

Use [`skills/biostatistics/SKILL.md`](../skills/biostatistics/SKILL.md) as a structural template. The headings, in order:

1. `## Overview` — 2–4 sentences.
2. `## When to use this skill` — bullets of trigger scenarios.
3. `## Prerequisites` — Python version, libraries, `pip install` line, system tools.
4. `## Core workflows` — 3–5 `###` sub-workflows, each a short explanation + a minimal runnable Python/Nextflow snippet (<30 lines).
5. `## Best practices` — 6–10 concrete bullets.
6. `## Common pitfalls` — 5–8 bullets.
7. `## Worked example` — one end-to-end example with code.
8. `## Tools & libraries` — markdown table `| Tool | Purpose | Install |`.
9. `## References` — 4–8 canonical links.
10. `## Ethics & safety` — data sensitivity, licensing, dual-use.

## 5. Keep it under 500 lines

The contract warns (not fails) when a body exceeds 500 lines. If you're over, move depth into `references/`:

```
skills/nextflow-pipelines/
├── SKILL.md                  # the catalog + summary
├── references/
│   ├── module-design.md      # deep dive on nf-core module structure
│   └── config-profiles.md    # deep dive on configuration profiles
```

Link from the main body with a **relative path, one level deep**:

```markdown
For the full module-design pattern, see [Module design](references/module-design.md).
```

The scanner rejects `../` chains longer than one level and any absolute path.

## 6. Add assets or scripts (optional)

- `assets/` — templates, sample configs, small reference data.
- `scripts/` — runnable helpers. **If you ship `scripts/`, you must ship `tests/<skill-name>/`.** The contract enforces this — a skill folder with `scripts/` but no test directory fails validation.

## 7. Validate

```bash
# must exit 0
python scan_skills.py --validate

# confirm metadata renders
python scan_skills.py --show nextflow-pipelines

# contract suite
pytest tests/
```

If `--validate` fails, the scanner prints the exact rule that failed. The most common fixes:

| Error | Fix |
|---|---|
| `name must equal parent directory name` | rename the folder or the `name` field so they match |
| `description length must be 1-1024` | shorten or lengthen the description |
| `name must match [a-z0-9]+(-[a-z0-9]+)*` | lowercase, single hyphens, no leading/trailing/consecutive hyphens |
| `link escapes more than one level` | move the target file so it's one folder deep, or inline the content |
| `compiled artifact present` | `rm -rf __pycache__` inside the skill folder |
| `ships scripts/ but tests/<name>/ is missing` | add `tests/<name>/test_basic.py` |

## 8. Open the PR

- One skill per PR.
- Title: `skill: add nextflow-pipelines`.
- Body: what the skill does, the canonical library, and a one-line trigger example.
- CI runs `scan_skills.py --validate` + `pytest tests/` automatically.

A maintainer will review for: contract compliance, on-topic scope, runnable snippets, canonical references, trigger keywords, and a sensible ethics note. Most PRs merge within a few days.

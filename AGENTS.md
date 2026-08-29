# Scientific Agent Skills — Agent Instructions

> This file is the cross-agent instruction manifest. Cursor, Codex, Gemini CLI,
> and other agents that auto-load `AGENTS.md` will read this on session start.
> Claude Code users: a thin `CLAUDE.md` pointer in this repo redirects here.

You are working inside the **Scientific Agent Skills** repository — a curated
collection of open Agent Skills (`SKILL.md` files) that help coding assistants
act as stronger research partners for science and engineering work.

## What this repo is (and is not)

- It is **a library of skills**, not an importable Python package. The `skills/`
  directory contains one folder per skill, each with a `SKILL.md` written to
  the [open Agent Skills specification](https://agentskills.io/specification).
- It is **agent-agnostic**. The same `SKILL.md` files work in Claude Code
  (`.claude/skills/`), Cursor (`.cursor/rules/` or `~/.agents/skills/`),
  OpenAI Codex (uploaded bundles), GitHub Copilot, and Gemini CLI
  (`~/.agents/skills/`).
- It is **Python-first**. Examples reference Python scientific libraries
  (NumPy, SciPy, pandas, BioPython, RDKit, scikit-learn, PyTorch, xarray, etc.),
  but skills are prose + examples — they are not runtime code.

## Repository layout

```
scientific-agent-skills/
├── skills/                 # 40 skills, one folder each (flat)
│   └── <skill-name>/
│       └── SKILL.md        # required; YAML frontmatter + instructions
│       └── references/     # optional; on-demand deep-dive docs
│       └── scripts/        # optional; runnable helpers (needs tests/)
│       └── assets/          # optional; templates/data
│       └── LICENSE.txt      # optional; per-skill license override
├── scripts/                # repo tooling (scanner, validator, installer)
├── examples/               # one worked example per skill category
├── docs/                   # long-form documentation
├── tests/                  # structural-contract pytest suite
├── .github/workflows/      # CI: skill validation + security scan
├── plugin.json             # Agent Plugins 1.0.0 manifest
├── pyproject.toml          # repo tooling metadata only
├── scan_skills.py          # repo-wide structural contract scanner
└── README.md
```

## The Agent Skills contract (enforced by `scan_skills.py`)

Every `skills/<name>/SKILL.md` MUST:

1. Have **YAML frontmatter** delimited by `---`.
2. Declare `name` — lowercase, `[a-z0-9-]` only, no leading/trailing or
   consecutive hyphens, and **equal to its parent directory name**.
3. Declare `description` — 1–1024 chars describing **what** it does and **when**
   to use it (include trigger keywords so the agent picks it up reliably).
4. (Optional) Declare `license`, `compatibility`, `metadata` (string→string map,
   use uniquely-named keys such as `version`, `skill-author`, `category`).
5. Keep the body **under 500 lines / ~5000 tokens**. Push depth into
   `references/`, `scripts/`, `assets/`.
6. Reference other files with **relative paths, one level deep**.
7. Ship **no compiled Python** (`*.pyc`, `__pycache__/`) inside a skill folder.
8. If it ships a `scripts/` directory, it MUST ship a `tests/<skill-name>/`
   suite in the repo.

## How to discover skills

```bash
# List every skill with its category, version, and one-line description
python scan_skills.py --list

# Validate the whole repo against the Agent Skills contract
python scan_skills.py --validate

# Pretty-print one skill's full metadata
python scan_skills.py --show genomics

# Export a machine-readable manifest (JSON) for catalogs / docs generators
python scan_skills.py --json > skills-manifest.json
```

## When you (the agent) should pick a skill

Pick a skill when the user's request **matches its `description` trigger
keywords**. Do not load every skill at once — skills use progressive disclosure:
the catalog (name + description) is cheap; the full body loads on activation.

If no skill matches, fall back to general coding assistance and surface the
catalog via `python scan_skills.py --list` so the user can scope the request.

## Style & tone

- Be concrete. Show minimal runnable Python, not pseudocode.
- Prefer the canonical scientific library for the domain.
- Always note reproducibility (seeds, versions, environment) where it matters.
- Surface ethical/safety constraints (clinical data, dual-use research,
  patient privacy, PII) before demonstrating a workflow.

## Security boundaries (read before generating code)

- Never invent API keys, credentials, or patient identifiers.
- De-identify clinical data; never output real PHI.
- Treat wet-lab protocols as reference only — they are not SOPs.
- Chemical/biological synthesis guidance is for legitimate research only;
  refuse obvious dual-use / weapons requests and point to institutional review.

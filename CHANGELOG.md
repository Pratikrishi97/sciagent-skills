# Changelog

All notable changes to SciAgent Skills are documented here. The format
is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the
project adheres to [Semantic Versioning](https://semver.org/).

## [1.1.0] — 2025

### Changed
- **Renamed the repository** from `scientific-agent-skills` → `sciagent-skills`. The new name is shorter, brandable, and distinct while keeping the same "science + agent + skills" meaning. GitHub auto-redirects the old URL, so existing links keep working.
- Rebranded the project's human-readable name from "Scientific Agent Skills" → "SciAgent Skills" across the README, AGENTS.md, CONTRIBUTING.md, SECURITY.md, CHANGELOG.md, plugin.json, pyproject.toml, and all 40 SKILL.md files.
- Bumped `plugin.json` `version` to `1.1.0` and added a `title` field ("SciAgent Skills") for richer Agent Plugins manifests.

### Migration notes
- If you cloned the old URL, your remote will keep working (GitHub redirects), but you can update it with:
  ```bash
  git remote set-url origin https://github.com/Pratikrishi97/sciagent-skills.git
  ```
- If you installed skills with `npx skills add Pratikrishi97/scientific-agent-skills`, the redirect means it still works; for a clean install use `Pratikrishi97/sciagent-skills` instead.

## [1.0.0] — 2025

### Added
- Initial release with **40 skills across 11 categories**:
  - Biology & Genomics (5): genomics, transcriptomics, protein-analysis, proteomics, evolutionary-biology
  - Drug Discovery & Cheminformatics (4): drug-discovery, cheminformatics, admet-prediction, retrosynthesis
  - Clinical & Medical Research (4): clinical-research, medical-imaging, epidemiology, clinical-nlp
  - Chemistry & Materials (3): computational-chemistry, materials-science, reaction-modeling
  - Physics & Astronomy (3): computational-physics, astrophysics, quantum-computing
  - Machine Learning & Statistics (4): ml-for-science, deep-learning, scientific-computing, biostatistics
  - Geospatial & Earth Science (3): geospatial-analysis, climate-science, remote-sensing
  - Data & Visualization (3): data-visualization, reproducible-research, scientific-data-management
  - Lab & Automation (3): lab-automation, experimental-design, instrument-integration
  - Research Infrastructure (3): reproducible-environments, hpc-computing, notebook-best-practices
  - Knowledge & Communication (5): literature-review, citation-management, scientific-writing, grant-writing, scientific-presentations
- `scan_skills.py` — stdlib-only contract scanner (list, validate, show, json, categories, tree).
- `scripts/install_skills.py` — multi-agent installer (Claude Code, Cursor, Codex, Gemini, Copilot, cross-host).
- `scripts/to_mdc.py` — converter from Agent Skills `SKILL.md` to Cursor native `.mdc` rules.
- `plugin.json` — Agent Plugins 1.0.0 manifest for one-command install in Cursor / Codex / Copilot / VS Code.
- `tests/_meta/test_structure.py` — pytest structural-contract suite used by CI.
- `pyproject.toml` with `[project.optional-dependencies]` for `dev` and `scanner`.
- `AGENTS.md` + `CLAUDE.md` pointer for cross-agent repo instructions.
- `.github/workflows/skills.yml` and `.github/workflows/security-scan.yml` CI.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, this `CHANGELOG.md`.
- `docs/` with `adding-a-skill.md`, `agent-compatibility.md`, `troubleshooting.md`, `architecture.md`.
- `examples/` with one worked example per category.

### Contract
- Every `skills/<name>/SKILL.md` MUST declare `name` (lowercase `[a-z0-9-]+`,
  matching the folder), `description` (1–1024 chars), and is encouraged to
  declare `license`, `compatibility`, and a `metadata` map.
- Bodies should stay under 500 lines (warning, not failure).
- File references must be relative and one level deep.
- No compiled Python (`__pycache__/`, `*.pyc`, `*.so`) inside skill folders.
- A skill shipping `scripts/` must also ship `tests/<name>/`.

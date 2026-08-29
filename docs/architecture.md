# Architecture

How the repo is put together and why.

## Design principles

1. **Plain text, open standard.** Every skill is a `SKILL.md` written to the [Agent Skills](https://agentskills.io) specification. No proprietary format, no build step, no runtime. The repo is readable by humans and machines alike.
2. **Agent-agnostic.** The same files work in Claude Code, Cursor, Codex, Copilot, and Gemini. Per-agent adapters (`scripts/install_skills.py`, `scripts/to_mdc.py`) handle the one difference that matters: *where* each agent stores skills.
3. **Python-first, prose not code.** Examples reference the canonical scientific Python library for each domain. Skills are not importable modules; they are instructions an agent loads on demand.
4. **Progressive disclosure.** Catalog (name + description) is cheap; the full body loads on activation; `references/` load only on demand. The 40-skill catalog costs ~3,000 tokens; loading one skill costs ~1,500.
5. **Audit-able contract.** A stdlib-only scanner enforces the frontmatter contract on every PR. No silent drift.

## Repo layout

```
scientific-agent-skills/
├── skills/                 # 40 skills, flat (one folder each)
│   └── <name>/
│       ├── SKILL.md          # required: frontmatter + 10 standard sections
│       ├── references/       # optional: on-demand deep-dives
│       ├── scripts/          # optional: runnable helpers (requires tests/<name>/)
│       ├── assets/           # optional: templates / sample data
│       └── LICENSE.txt       # optional: per-skill license override
├── scripts/                # repo tooling (installer, mdc converter)
├── examples/               # one worked example per category
├── docs/                   # long-form docs
├── tests/                  # structural-contract pytest suite
│   └── _meta/test_structure.py
├── .github/workflows/      # CI: contract + security
├── plugin.json             # Agent Plugins 1.0.0 manifest
├── pyproject.toml          # repo tooling metadata (not a published package)
├── scan_skills.py          # the contract scanner / catalog lister
├── AGENTS.md               # cross-agent repo instructions (auto-loaded)
├── CLAUDE.md               # thin pointer to AGENTS.md for Claude Code
└── README.md
```

### Why flat `skills/` with `metadata.category`?

The Agent Skills spec requires `name` to equal the *immediate* parent directory. We could nest `skills/biology/genomics/SKILL.md` (the immediate parent is `genomics`, so the spec holds), but many agents' discovery code globs `skills/*/SKILL.md` one level deep. A flat layout maximizes compatibility, and the `metadata.category` field preserves the human-facing grouping. The scanner groups by `metadata.category` for `--categories` and `--tree`.

## The contract

`scan_skills.py` is the single source of truth. On every PR it checks that each `skills/<name>/SKILL.md`:

1. has YAML frontmatter delimited by `---`,
2. declares `name` (lowercase `[a-z0-9-]+`, matching the folder),
3. declares `description` (1–1024 chars),
4. (optional) declares `license`, `compatibility`, `metadata`, `allowed-tools` with correct types and lengths,
5. keeps the body under 500 lines (warning, not failure),
6. references files with relative paths one level deep,
7. ships no compiled Python,
8. ships `tests/<name>/` if it ships `scripts/`.

The scanner is stdlib-only (PyYAML optional, with a small fallback parser) so it runs in any CI without a virtualenv.

## Progressive disclosure, in detail

| Tier | What loads | When | Token cost |
|---|---|---|---|
| Catalog | `name` + `description` of every installed skill | at session start | ~80 tokens × N skills |
| Instructions | the full `SKILL.md` body | when a user prompt matches a description's triggers | ~1,500 tokens × 1 skill |
| Resources | files under `references/`, `scripts/`, `assets/` | when the agent follows a link from the body | variable |

This is why the catalog can list 40 skills and still leave most of the context budget for your actual work.

## Tooling

| Tool | Purpose |
|---|---|
| `scan_skills.py` | list, validate, show, json, categories, tree — the contract enforcer |
| `scripts/install_skills.py` | copy skills into the right dir per agent (claude-code, cursor, codex, gemini, copilot, generic) |
| `scripts/to_mdc.py` | convert Agent Skills `SKILL.md` to Cursor native `.mdc` rules |
| `tests/_meta/test_structure.py` | pytest contract suite (re-exports `scan_skills`) |
| `plugin.json` | Agent Plugins 1.0.0 manifest for one-command bundle install |
| `pyproject.toml` | tooling-only metadata; not a published package |

## CI

`.github/workflows/skills.yml` runs on every PR and weekly:

- `python scan_skills.py --validate` — the contract.
- `pytest tests/` — the structural suite.
- `python scripts/install_skills.py --paths` — sanity-check the installer.

`.github/workflows/security-scan.yml` runs the Cisco AI Skill Scanner over the skills if available (optional; CI degrades gracefully if the tool isn't installed).

## Why not a published Python package?

A skill is a `SKILL.md`, not an importable module. Publishing to PyPI would imply `pip install` and `import`, neither of which applies. The `pyproject.toml` exists only to declare the repo's *tooling* dependencies (`pyyaml`, `pytest`, `skills-ref`, `cisco-ai-skill-scanner`) and to make the repo discoverable to tools that look for one. Skills themselves are installed by copying into your agent's skills directory.

## Extensibility points

- **New skills:** add `skills/<name>/SKILL.md`, run `--validate`, open a PR. See [`docs/adding-a-skill.md`](./adding-a-skill.md).
- **New agent targets:** add an entry to `AGENT_PATHS` in `scripts/install_skills.py` with the agent's user-level and project-level skill paths. The rest of the installer works unchanged.
- **New catalog renderers:** add a function to `scan_skills.py` (e.g. `render_markdown` for a docs site) and wire it into the `argparse` group.
- **Per-skill deep-dives:** add `references/*.md` files and link them from the main body with a relative one-level path.

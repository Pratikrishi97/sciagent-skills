# Troubleshooting

Common issues, in rough order of frequency.

## The agent doesn't pick up a skill I just installed

**Restart the editor / agent session.** Most agents scan the skills directory only at startup. Verify the file is where the agent expects:

```bash
python scripts/install_skills.py --paths      # print each agent's paths
ls ~/.claude/skills/genomics/SKILL.md          # Claude Code
ls ~/.agents/skills/genomics/SKILL.md          # cross-host (Cursor, Gemini, Copilot)
```

If the file is missing, re-run the installer for your agent (see the [Quick start](../README.md#quick-start)).

## The scanner says my skill is invalid

```bash
python scan_skills.py --show <name>      # detailed report
python scan_skills.py --validate         # all skills, with exact rule failures
```

| Error | Cause | Fix |
|---|---|---|
| `frontmatter parse error` | YAML is malformed | check for unquoted colons in `description`/`compatibility` values; quote the whole value |
| `name must equal parent directory name` | folder and `name` differ | rename the folder or the `name` so they match |
| `name must match [a-z0-9]+(-[a-z0-9]+)*` | uppercase, underscore, or doubled hyphen | lowercase, single hyphens only |
| `description length must be 1-1024` | empty or too long | rewrite |
| `unknown frontmatter key 'x'` | a key not in the allowed set | move it under `metadata:` or remove |
| `metadata.x must be a string` | non-string YAML value | quote it: `version: "1.0.0"` |
| `link escapes more than one level` | a `../` chain longer than one | inline the content or move the target file closer |
| `absolute path used in link` | `/abs/...` in a link | use a relative path |
| `compiled artifact present` | `__pycache__/` or `*.pyc` inside the skill | `rm -rf` it; `.gitignore` should prevent recurrence |
| `ships scripts/ but tests/<name>/ is missing` | a `scripts/` dir with no test | add `tests/<name>/test_basic.py` |
| `body is N lines (> 500)` (warning) | over the soft cap | move depth to `references/` |

## Cursor ignores my skills

Cursor's native format is `.cursor/rules/*.mdc`, not `.md`. Two options:

```bash
# option 1: cross-host convention (Cursor reads this alongside .cursor/rules)
python scripts/install_skills.py --agent cursor --all        # user-level ~/.agents/skills/

# option 2: convert to native .mdc
python scripts/to_mdc.py --out .cursor/rules                  # all skills
python scripts/to_mdc.py --out .cursor/rules --skill genomics # one skill
```

After either, restart Cursor.

## A code snippet in a skill fails to run

Skills ship *examples*, not pinned reproductions. Each snippet assumes the libraries in that skill's `## Prerequisites` section and `compatibility` frontmatter are installed. Install them, then run:

```bash
# example: genomics needs pysam + biopython
pip install pysam biopython cyvcf2
```

If a snippet is genuinely wrong (the API has changed, a function name is off), please [open an issue](https://github.com/Pratikrishi97/sciagent-skills/issues) — snippets are meant to be runnable.

## Too many skills loaded into context

You're on a host that doesn't do progressive disclosure, or you marked `.mdc` rules `alwaysApply: true`. Install only what you need:

```bash
python scripts/install_skills.py --agent claude-code --category "Drug Discovery & Cheminformatics"
python scripts/install_skills.py --agent claude-code --skill genomics --skill transcriptomics
```

For Cursor `.mdc`, never use `--always` for the whole repo — reserve `alwaysApply: true` for the handful of rules you want permanently in context.

## `pip install` fails

There's nothing to `pip install` here — the repo is a library of plain-text skills, not an importable package. Install the *libraries* a skill references (in its `## Prerequisites` section), not the skill itself:

```bash
# wrong
pip install sciagent-skills        # not a thing

# right — install what a skill needs
pip install scanpy anndata pydeseq2        # for the transcriptomics skill
```

The repo's `pyproject.toml` only declares tooling deps (`pyyaml`, `pytest`) for the scanner and tests.

## `python scan_skills.py` itself errors

The scanner is stdlib-only and runs on Python 3.10+. If it fails:

```bash
python3 --version                           # must be 3.10+
python3 -c "import ast; print('ok')"        # sanity check
python3 scan_skills.py --help               # confirm argparse works
```

If PyYAML is installed (`pip install pyyaml`) the scanner uses it for full YAML fidelity; otherwise it falls back to a small stdlib parser that handles the frontmatter we use. The fallback is fine for validation.

## The `to_mdc.py` converter produces rules Cursor doesn't activate

Check the generated `.mdc` frontmatter. A rule activates when **any** of these is true:

- `alwaysApply: true` (always in context), OR
- `globs` matches the file you're editing, OR
- `description` matches the current task (the agent decides), OR
- you `@mention` the rule by name.

If none applies, the rule never loads. By default `to_mdc.py` writes a `description` only — so activation depends on the agent reading the description and matching it to your prompt. For always-on rules, pass `--always`.

## I added a skill but CI is red

CI runs `scan_skills.py --validate` and `pytest tests/` on every PR. Common red causes:

- Frontmatter YAML doesn't parse (unquoted colon in a value).
- `name` doesn't match the folder.
- A relative link is broken or escapes too many levels.
- You added `scripts/` without `tests/<name>/`.

Run locally:

```bash
python scan_skills.py --validate
pytest tests/
```

Both must be green before the PR will merge.

## The skill activates but the agent does the wrong thing

The `description` is the only signal the agent has at activation time. If it activates the wrong skill, the description is too broad. Tighten it to the specific workflow and the specific libraries, and list the trigger keywords a researcher would actually type. Compare:

> **Too broad:** "Helps with data analysis."
> **Right:** "Differential expression and marker-gene analysis for bulk and single-cell RNA-seq. Use when the user has count matrices, AnnData/h5ad files, or mentions DESeq2/edgeR/Scanpy/pydeseq2, UMAP, Leiden, or Cell Ranger."

## Still stuck

- [Open an issue](https://github.com/Pratikrishi97/sciagent-skills/issues) with the exact command, the output, and the skill name.
- [Start a discussion](https://github.com/Pratikrishi97/sciagent-skills/discussions) for "how do I..." questions.

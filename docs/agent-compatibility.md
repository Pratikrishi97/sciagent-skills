# Agent compatibility

The same `SKILL.md` files work across every coding assistant that supports the open [Agent Skills](https://agentskills.io) or [Agent Plugins](https://agent-plugins.org) standards. This document is the authoritative matrix of *where each agent stores skills* and *how each one discovers them*.

## Where each agent stores skills

| Agent | User-level | Project-level | Auto-loads `AGENTS.md`? |
|---|---|---|---|
| **Claude Code** | `~/.claude/skills/<name>/SKILL.md` | `.claude/skills/<name>/SKILL.md` | yes (also `CLAUDE.md`) |
| **Cursor** | `~/.agents/skills/` (cross-host) or `~/.cursor/skills/` | `.agents/skills/` or `.cursor/rules/*.mdc` | yes (`AGENTS.md`) |
| **OpenAI Codex / ChatGPT** | uploaded bundle (zip) | uploaded bundle | yes (`AGENTS.md`) |
| **GitHub Copilot** | `~/.copilot/skills/` | `.github/copilot/skills/` | yes (`AGENTS.md`) |
| **Gemini CLI** | `~/.agents/skills/` | `.agents/skills/` | yes (`AGENTS.md`) |
| **Any Agent Skills client** | `~/.agents/skills/` | `.agents/skills/` | varies |

**Precedence:** project-level overrides user-level on name collisions.

## Install cheatsheet

```bash
# Claude Code — all skills, user-level
python scripts/install_skills.py --agent claude-code --all

# Cursor — one skill, current project
python scripts/install_skills.py --agent cursor --skill genomics --project

# Cross-host convention (Cursor, Gemini, Copilot all read this)
python scripts/install_skills.py --agent generic --category "Biology & Genomics"

# Codex — bundle the skills dir and upload via the API / chat UI
zip -r scientific-skills.zip skills/ AGENTS.md plugin.json
# Then attach as a skills bundle on the Responses API:
#   tools[].environment.skills = "bundle-id"

# Plain copy (always works, no tooling)
cp -r skills/genomics ~/.claude/skills/
```

## Cursor-specific notes

Cursor's native rule format is `.cursor/rules/*.mdc` with frontmatter `description` / `globs` / `alwaysApply`. Plain `.md` files in `.cursor/rules/` are **ignored**. Two paths:

1. **Use the cross-host convention.** Drop skills into `~/.agents/skills/` or `.agents/skills/`. Cursor reads these alongside its native rules.
2. **Convert to `.mdc`.** The repo ships a converter:
   ```bash
   python scripts/to_mdc.py --out .cursor/rules          # all skills
   python scripts/to_mdc.py --out ~/.cursor/rules --skill genomics
   python scripts/to_mdc.py --always                      # mark all rules alwaysApply: true
   ```

`.mdc` frontmatter mapping:

| Agent Skills field | `.mdc` field | Notes |
|---|---|---|
| `description` | `description` | copied verbatim; Cursor uses it to decide activation |
| (none) | `globs` | optional; file patterns that auto-attach the rule |
| (none) | `alwaysApply` | optional bool; if `true`, the rule is always in context |

## Codex-specific notes

OpenAI Codex / ChatGPT consume skills as **uploaded bundles**, not local files:

- Zip the `skills/` directory (≤50 MB, ≤500 files, ≤25 MB per file).
- Attach the bundle via the Responses API: `tools[].environment.skills = "<bundle-id>"`.
- Codex does case-insensitive name matching and loads one `SKILL.md` per bundle by default; for multi-skill bundles, the catalog (name + description) is loaded and individual skills activate on trigger.
- `AGENTS.md` at the bundle root is read as repo-level guidance (Codex honors it).

## Progressive disclosure

Every supported agent implements three-tier progressive disclosure:

1. **Catalog** (always loaded): each skill's `name` + `description`, ~80 tokens. Costs almost nothing.
2. **Instructions** (loaded on activation): the full `SKILL.md` body when a user prompt matches the description's trigger keywords.
3. **Resources** (loaded on demand): files under `references/`, `scripts/`, `assets/` linked from the body, read only when the agent needs the depth.

This is why you can install all 40 skills and your context budget barely moves. Don't be shy about installing the whole repo.

## Verification checklist

After installing, confirm your agent sees the skills:

- **Claude Code:** `ls ~/.claude/skills/*/SKILL.md | wc -l` should equal the number you installed. Restart `claude` and ask "what skills do you have?".
- **Cursor:** `ls ~/.agents/skills/*/SKILL.md` or `ls .cursor/rules/*.mdc`. Restart Cursor; trigger a skill with a domain-specific prompt.
- **Codex:** check the bundle is attached in the API response's `tools[].environment.skills`; query with a domain prompt.
- **Gemini / Copilot:** `ls ~/.agents/skills/*/SKILL.md`; restart the CLI.

If a skill doesn't activate, the most common cause is a `description` without trigger keywords — the agent has nothing to match on. Fix the description, reinstall.

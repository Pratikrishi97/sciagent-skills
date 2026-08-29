#!/usr/bin/env python3
"""
install_skills.py — install SciAgent Skills into your coding assistant.

The same `SKILL.md` files work across Claude Code, Cursor, OpenAI Codex,
GitHub Copilot, and Gemini CLI — but each stores skills in a different place.
This helper copies the skills you select into the right folder for the agent(s)
you use, so you only have to run one command.

Usage
-----
    # install ALL skills for Claude Code (user-level)
    python scripts/install_skills.py --agent claude-code --all

    # install a single skill into the current Cursor project
    python scripts/install_skills.py --agent cursor --skill genomics --project

    # install a category into the cross-host ~/.agents/skills/ dir
    python scripts/install_skills.py --agent generic --category "Drug Discovery & Cheminformatics"

    # list where each agent stores skills (dry run, no writes)
    python scripts/install_skills.py --paths

The script copies directories verbatim; it never modifies the source repo.
Existing skill folders are overwritten (re-installed). It prints a summary of
where each skill landed so you can verify in your editor.

This tool is optional. You can also just `cp -r skills/genomics ~/.claude/skills/`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# Where each agent stores skills. Keys map to --agent.
# "user" => global install; "project" => current working directory.
AGENT_PATHS = {
    "claude-code": {
        "user": Path.home() / ".claude" / "skills",
        "project_dotdir": ".claude/skills",
    },
    "cursor": {
        # Cursor honors the cross-host convention in addition to .cursor/rules
        "user": Path.home() / ".agents" / "skills",
        "project_dotdir": ".agents/skills",
    },
    "codex": {
        # Codex consumes uploaded bundles; for local agent guidance use AGENTS.md.
        # We still drop skills under ~/.codex/skills for codex-cli users.
        "user": Path.home() / ".codex" / "skills",
        "project_dotdir": ".codex/skills",
    },
    "gemini": {
        "user": Path.home() / ".agents" / "skills",
        "project_dotdir": ".agents/skills",
    },
    "copilot": {
        "user": Path.home() / ".copilot" / "skills",
        "project_dotdir": ".github/copilot/skills",
    },
    "generic": {
        # The cross-host Agent Skills convention supported by many clients.
        "user": Path.home() / ".agents" / "skills",
        "project_dotdir": ".agents/skills",
    },
}


def available_skills() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def available_categories() -> set[str]:
    cats: set[str] = set()
    for p in available_skills():
        text = p.read_text(encoding="utf-8")
        m = _frontmatter(text)
        if m and m.get("metadata", {}).get("category"):
            cats.add(m["metadata"]["category"])
    return cats


def _frontmatter(text: str) -> dict | None:
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    close = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if close is None:
        return None
    fm = "\n".join(lines[1:close])
    try:
        import yaml  # type: ignore

        return yaml.safe_load(fm) or {}
    except Exception:
        # minimal fallback
        out: dict = {}
        for line in fm.splitlines():
            mm = __import__("re").match(r"([\w-]+):\s*(.*)$", line)
            if mm and mm.group(2):
                out[mm.group(1)] = mm.group(2).strip().strip("\"'")
        return out


def install_skill(src_dir: Path, dest_root: Path) -> str:
    dest = dest_root / src_dir.name
    dest_root.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src_dir, dest)
    return str(dest)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="install_skills.py",
        description="Install SciAgent Skills into your coding assistant.",
    )
    p.add_argument(
        "--agent",
        choices=list(AGENT_PATHS),
        default="generic",
        help="which assistant to install for (default: generic / cross-host)",
    )
    p.add_argument("--all", action="store_true", help="install every skill")
    p.add_argument("--skill", action="append", default=[], help="install a single skill (repeatable)")
    p.add_argument("--category", help="install every skill in a category")
    p.add_argument("--project", action="store_true",
                   help="install into the current project (./<dotdir>) instead of user-level")
    p.add_argument("--paths", action="store_true", help="print where each agent stores skills and exit")
    p.add_argument("--dry-run", action="store_true", help="show what would happen, write nothing")
    args = p.parse_args(argv)

    if args.paths:
        print("Where each agent stores skills:\n")
        for a, dirs in AGENT_PATHS.items():
            print(f"  {a:12s}  user:    {dirs['user']}")
            proj = dirs["project_dotdir"]
            print(f"              project: ./{proj}\n")
        return 0

    # resolve destination
    if args.agent not in AGENT_PATHS:
        print(f"unknown agent: {args.agent}")
        return 2
    if args.project:
        dest_root = Path.cwd() / AGENT_PATHS[args.agent]["project_dotdir"]
    else:
        dest_root = AGENT_PATHS[args.agent]["user"]

    # choose skills
    chosen: list[Path] = []
    if args.all:
        chosen = [p.parent for p in available_skills()]
    elif args.skill:
        for name in args.skill:
            d = SKILLS_DIR / name
            if not d.is_dir():
                print(f"  skip: no skill named {name!r}")
                continue
            chosen.append(d)
    elif args.category:
        for p in available_skills():
            m = _frontmatter(p.read_text(encoding="utf-8")) or {}
            if m.get("metadata", {}).get("category") == args.category:
                chosen.append(p.parent)
        if not chosen:
            print(f"no skills in category {args.category!r}")
            print(f"available categories: {sorted(available_categories())}")
            return 1
    else:
        p.error("choose --all, --skill NAME, or --category NAME")

    if not chosen:
        print("nothing to install")
        return 1

    print(f"Installing {len(chosen)} skill(s) for {args.agent!r} -> {dest_root}\n")
    for d in chosen:
        if args.dry_run:
            print(f"  would install: {d.name} -> {dest_root / d.name}")
            continue
        target = install_skill(d, dest_root)
        print(f"  ✓ {d.name:24s} -> {target}")

    print(f"\nDone. Restart your editor / agent session to pick up the new skills.")
    if args.agent == "claude-code":
        print("Tip: run `claude` again in your project — Claude Code auto-discovers .claude/skills/.")
    if args.agent == "cursor":
        print("Tip: Cursor reads ~/.agents/skills/ and .agents/skills/. For .mdc rules use the converter in scripts/to_mdc.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

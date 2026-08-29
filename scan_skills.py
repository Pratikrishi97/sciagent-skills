#!/usr/bin/env python3
"""
scan_skills.py — structural contract scanner for the Scientific Agent Skills repo.

This is the single source of truth for the Agent Skills contract in this repo.
It validates that every skills/<name>/SKILL.md conforms to the open Agent
Skills specification (https://agentskills.io/specification) and gives humans
and CI a fast way to discover what's included.

Usage
-----
    python scan_skills.py                       # default: --list
    python scan_skills.py --list                # list all skills w/ metadata
    python scan_skills.py --validate            # enforce the contract; exit 1 on failure
    python scan_skills.py --show <skill>        # pretty-print one skill's metadata
    python scan_skills.py --json                # emit machine-readable manifest
    python scan_skills.py --categories          # list skills grouped by category
    python scan_skills.py --tree                # indented tree view by category
    python scan_skills.py --help                # this help

Exit codes
----------
    0  success / all skills valid
    1  one or more skills violate the contract

The scanner is dependency-free (stdlib only) so it runs in any CI without a
virtualenv. PyYAML is optional — if unavailable, a small built-in parser is
used for frontmatter only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
SKILLS_DIR = REPO_ROOT / "skills"

# ---- Contract constants (from the open Agent Skills specification) -----------
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DESC_MIN_LEN = 1
DESC_MAX_LEN = 1024
NAME_MIN_LEN = 1
NAME_MAX_LEN = 64
COMPAT_MAX_LEN = 500
META_VALUE_MAX_LEN = 1024
SKILL_MAX_LINES = 500  # soft cap; warned, not failed
LICENSE_MAX_LEN = 200
ALLOWED_TOP_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
FORBIDDEN_BYTECODE = ("__pycache__", ".pyc", ".pyo", ".so", ".dylib")


# ---- Small YAML frontmatter parser (stdlib fallback) -------------------------
def parse_frontmatter(text: str) -> tuple[dict[str, Any], str] | tuple[None, str]:
    """Parse YAML frontmatter delimited by '---' lines. Returns (meta, body)."""
    if not text.startswith("---"):
        return None, "missing leading '---' delimiter"
    lines = text.splitlines()
    # find closing delimiter
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break
    if close_idx is None:
        return None, "missing closing '---' delimiter"
    fm_text = "\n".join(lines[1:close_idx])
    body = "\n".join(lines[close_idx + 1 :])

    # Try real PyYAML first for fidelity (handles nested maps, quotes, etc.)
    try:
        import yaml  # type: ignore

        meta = yaml.safe_load(fm_text) or {}
        if not isinstance(meta, dict):
            return None, "frontmatter must be a YAML mapping"
        return meta, body
    except Exception:
        pass

    # stdlib fallback: only handles simple key: value and one-level nested map
    meta: dict[str, Any] = {}
    cur_map_key: str | None = None
    for raw in fm_text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith(" ") or line.startswith("\t"):
            # nested entry under cur_map_key
            if cur_map_key is None:
                return None, f"indented line without parent: {raw!r}"
            m = re.match(r"\s+([\w-]+):\s*(.*)$", line)
            if not m:
                return None, f"bad nested line: {raw!r}"
            k, v = m.group(1), m.group(2).strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            elif v.startswith("'") and v.endswith("'"):
                v = v[1:-1]
            if not isinstance(meta[cur_map_key], dict):
                meta[cur_map_key] = {}
            meta[cur_map_key][k] = v
            continue
        m = re.match(r"([\w-]+):\s*(.*)$", line)
        if not m:
            return None, f"bad line: {raw!r}"
        k, v = m.group(1), m.group(2).strip()
        cur_map_key = k
        if v == "":
            meta[k] = {}
        elif v.startswith('"') and v.endswith('"'):
            meta[k] = v[1:-1]
        elif v.startswith("'") and v.endswith("'"):
            meta[k] = v[1:-1]
        else:
            meta[k] = v
    return meta, body


# ---- Data model --------------------------------------------------------------
@dataclass
class Skill:
    name: str
    path: Path
    description: str = ""
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    allowed_tools: str | None = None
    body_lines: int = 0
    category: str = "Uncategorized"
    version: str = ""
    author: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def dir_name(self) -> str:
        return self.path.parent.name

    def to_manifest(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": str(self.path.relative_to(REPO_ROOT)),
            "category": self.category,
            "version": self.version,
            "author": self.author,
            "license": self.license,
            "compatibility": self.compatibility,
            "description": self.description,
            "body_lines": self.body_lines,
        }


# ---- Scanner ----------------------------------------------------------------
def find_skills() -> list[Path]:
    """Return every skills/<name>/SKILL.md path, sorted."""
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def validate_relative_refs(body: str, skill_dir: Path) -> list[str]:
    """File references must be relative and one level deep."""
    errs: list[str] = []
    # match markdown links and bare relative paths
    link_re = re.compile(r"\]\(([^)]+)\)")
    seen: set[str] = set()
    for m in link_re.finditer(body):
        target = m.group(1).split("#", 1)[0].split(" ")[0]
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if target.startswith("/"):
            errs.append(f"absolute path used in link: {target} (use relative paths)")
            continue
        if target not in seen:
            seen.add(target)
        # one level deep: no nested '../' chains beyond parent
        depth = target.count("../")
        if depth > 1:
            errs.append(f"link escapes more than one level: {target}")
    return errs


def check_bytecode(skill_dir: Path) -> list[str]:
    """Reject compiled Python artifacts inside a skill folder."""
    errs: list[str] = []
    for p in skill_dir.rglob("*"):
        if p.name == "__pycache__" or p.suffix in (".pyc", ".pyo", ".so", ".dylib"):
            errs.append(f"compiled artifact present: {p.relative_to(REPO_ROOT)}")
    return errs


def load_skill(path: Path) -> Skill:
    skill = Skill(name=path.parent.name, path=path)
    if not path.is_file():
        skill.errors.append("SKILL.md missing")
        return skill

    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    if meta is None:
        # in the error case, `body` holds the error message
        skill.errors.append(f"frontmatter parse error: {body}")
        return skill

    # unknown top-level keys
    for k in meta:
        if k not in ALLOWED_TOP_KEYS:
            skill.warnings.append(f"unknown frontmatter key '{k}'")

    # name
    name = meta.get("name", "")
    if not isinstance(name, str) or not name:
        skill.errors.append("'name' field is required and must be a string")
    else:
        if name != skill.dir_name:
            skill.errors.append(
                f"'name' ({name!r}) must equal parent directory name ({skill.dir_name!r})"
            )
        if not NAME_RE.match(name):
            skill.errors.append(
                f"'name' ({name!r}) must match [a-z0-9]+(-[a-z0-9]+)* "
                "(lowercase, no leading/trailing/consecutive hyphens)"
            )
        if not (NAME_MIN_LEN <= len(name) <= NAME_MAX_LEN):
            skill.errors.append(
                f"'name' length must be {NAME_MIN_LEN}-{NAME_MAX_LEN} chars"
            )
        skill.name = name

    # description
    desc = meta.get("description", "")
    if not isinstance(desc, str) or not desc:
        skill.errors.append("'description' field is required")
    else:
        if not (DESC_MIN_LEN <= len(desc) <= DESC_MAX_LEN):
            skill.errors.append(
                f"'description' length must be {DESC_MIN_LEN}-{DESC_MAX_LEN} chars (got {len(desc)})"
            )
        skill.description = desc

    # license (optional)
    lic = meta.get("license")
    if lic is not None:
        if not isinstance(lic, str):
            skill.errors.append("'license' must be a string")
        elif len(lic) > LICENSE_MAX_LEN:
            skill.errors.append(f"'license' too long (>{LICENSE_MAX_LEN} chars)")
        else:
            skill.license = lic

    # compatibility (optional)
    compat = meta.get("compatibility")
    if compat is not None:
        if not isinstance(compat, str):
            skill.errors.append("'compatibility' must be a string")
        elif len(compat) > COMPAT_MAX_LEN:
            skill.errors.append(f"'compatibility' too long (>{COMPAT_MAX_LEN} chars)")
        else:
            skill.compatibility = compat

    # metadata (optional, must be map of str->str)
    mdata = meta.get("metadata")
    if mdata is not None:
        if not isinstance(mdata, dict):
            skill.errors.append("'metadata' must be a mapping")
        else:
            for mk, mv in mdata.items():
                if not isinstance(mv, str):
                    skill.errors.append(f"metadata.{mk} must be a string")
                elif len(mv) > META_VALUE_MAX_LEN:
                    skill.errors.append(f"metadata.{mk} too long")
            skill.metadata = {str(k): str(v) for k, v in mdata.items()}
            skill.category = skill.metadata.get("category", "Uncategorized")
            skill.version = skill.metadata.get("version", "")
            skill.author = skill.metadata.get("skill-author", skill.metadata.get("author", ""))

    # allowed-tools (optional, experimental)
    at = meta.get("allowed-tools")
    if at is not None:
        if not isinstance(at, str):
            skill.errors.append("'allowed-tools' must be a string")
        else:
            skill.allowed_tools = at

    # body checks
    skill.body_lines = len(body.splitlines())
    if skill.body_lines > SKILL_MAX_LINES:
        skill.warnings.append(
            f"SKILL.md body is {skill.body_lines} lines (> {SKILL_MAX_LINES}); "
            "consider moving detail to references/"
        )

    # relative refs
    skill.errors.extend(validate_relative_refs(body, path.parent))

    # no bytecode
    skill.errors.extend(check_bytecode(path.parent))

    # scripts/ without tests/ (structural contract)
    if (path.parent / "scripts").is_dir():
        test_dir = REPO_ROOT / "tests" / skill.dir_name
        if not test_dir.is_dir():
            skill.warnings.append(
                f"ships scripts/ but tests/{skill.dir_name}/ is missing (required by contract)"
            )

    return skill


def load_all() -> list[Skill]:
    return [load_skill(p) for p in find_skills()]


# ---- CLI renderers ----------------------------------------------------------
def render_list(skills: list[Skill]) -> int:
    if not skills:
        print("No skills found under skills/")
        return 0
    print(f"Found {len(skills)} skills\n")
    w = max(len(s.name) for s in skills)
    for s in sorted(skills, key=lambda x: (x.category, x.name)):
        cat = s.category[:24]
        ver = s.version or "-"
        print(f"  {s.name:<{w}}  [{cat:<24}] v{ver:<6}  {s.description[:70]}")
    return 0


def render_categories(skills: list[Skill]) -> int:
    cats: dict[str, list[Skill]] = {}
    for s in skills:
        cats.setdefault(s.category, []).append(s)
    for cat in sorted(cats):
        print(f"\n## {cat}  ({len(cats[cat])})")
        for s in sorted(cats[cat], key=lambda x: x.name):
            ver = f" v{s.version}" if s.version else ""
            print(f"  - {s.name}{ver} — {s.description[:88]}")
    return 0


def render_tree(skills: list[Skill]) -> int:
    cats: dict[str, list[Skill]] = {}
    for s in skills:
        cats.setdefault(s.category, []).append(s)
    print("scientific-agent-skills/")
    for cat in sorted(cats):
        print(f"├── {cat}/")
        items = sorted(cats[cat], key=lambda x: x.name)
        for i, s in enumerate(items):
            last = i == len(items) - 1
            branch = "└──" if last else "├──"
            print(f"│   {branch} {s.name}")
    return 0


def render_show(skills: list[Skill], name: str) -> int:
    matches = [s for s in skills if s.name == name]
    if not matches:
        print(f"No skill named {name!r}. Run --list to see available skills.")
        return 1
    s = matches[0]
    print(f"name:         {s.name}")
    print(f"path:         {s.path.relative_to(REPO_ROOT)}")
    print(f"category:     {s.category}")
    print(f"version:      {s.version or '(none)'}")
    print(f"author:       {s.author or '(none)'}")
    print(f"license:      {s.license or 'MIT (repo default)'}")
    print(f"compatibility:{s.compatibility or '(none)'}")
    print(f"body lines:   {s.body_lines}")
    print(f"description:  {s.description}")
    if s.metadata:
        print("metadata:")
        for k, v in s.metadata.items():
            print(f"  {k}: {v}")
    if s.warnings:
        print("warnings:")
        for w in s.warnings:
            print(f"  - {w}")
    return 0


def render_json(skills: list[Skill]) -> int:
    manifest = {
        "schema": "scientific-agent-skills/manifest/v1",
        "count": len(skills),
        "categories": sorted({s.category for s in skills}),
        "skills": [s.to_manifest() for s in sorted(skills, key=lambda x: (x.category, x.name))],
    }
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


def render_validate(skills: list[Skill]) -> int:
    failures = [s for s in skills if s.errors]
    print(f"Validated {len(skills)} skills against the Agent Skills contract.")
    if not failures:
        nwarn = sum(len(s.warnings) for s in skills)
        print(f"\033[32m✓ all skills valid\033[0m ({nwarn} warnings)")
        for s in skills:
            for w in s.warnings:
                print(f"  warn: {s.name}: {w}")
        return 0
    print(f"\033[31m✗ {len(failures)} skill(s) failed\033[0m\n")
    for s in failures:
        print(f"  {s.name}:")
        for e in s.errors:
            print(f"    ✗ {e}")
        for w in s.warnings:
            print(f"    ⚠ {w}")
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="scan_skills.py",
        description="List and validate the Agent Skills in this repository.",
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument("--list", action="store_true", help="list all skills (default)")
    g.add_argument("--validate", action="store_true", help="enforce the contract")
    g.add_argument("--show", metavar="NAME", help="pretty-print one skill's metadata")
    g.add_argument("--json", action="store_true", help="emit a JSON manifest")
    g.add_argument("--categories", action="store_true", help="group skills by category")
    g.add_argument("--tree", action="store_true", help="indented category tree")
    args = p.parse_args(argv)

    skills = load_all()

    if args.validate:
        return render_validate(skills)
    if args.show:
        return render_show(skills, args.show)
    if args.json:
        return render_json(skills)
    if args.categories:
        return render_categories(skills)
    if args.tree:
        return render_tree(skills)
    return render_list(skills)


if __name__ == "__main__":
    sys.exit(main())

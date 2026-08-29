#!/usr/bin/env python3
"""
Re-export the repo's scanner contract as a pytest suite so CI enforces it.

These tests are the structural contract: every PR that adds or edits a skill
must keep the repo valid. Run with `pytest tests/`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# load the scanner as a module (it lives at repo root, not a package)
_spec = importlib.util.spec_from_file_location(
    "scan_skills", REPO_ROOT / "scan_skills.py"
)
scan = importlib.util.module_from_spec(_spec)
# register BEFORE exec_module so the @dataclass decorator can resolve
# its own module via sys.modules (otherwise it raises AttributeError).
sys.modules["scan_skills"] = scan
assert _spec.loader is not None
_spec.loader.exec_module(scan)


@pytest.fixture(scope="module")
def skills():
    return scan.load_all()


def test_at_least_one_skill(skills):
    assert len(skills) >= 1, "no skills found under skills/"


def test_every_skill_validates(skills):
    failures = [s for s in skills if s.errors]
    msgs = []
    for s in failures:
        msgs.append(f"{s.name}: {s.errors}")
    assert not failures, "contract violations:\n" + "\n".join(msgs)


def test_names_unique(skills):
    names = [s.name for s in skills]
    assert len(names) == len(set(names)), f"duplicate skill names: {names}"


def test_descriptions_have_trigger_keywords(skills):
    # cheap heuristic: a good description should mention what/when
    too_short = [s.name for s in skills if len(s.description) < 40]
    assert not too_short, f"descriptions too short (needs trigger keywords): {too_short}"


def test_no_bytecode_in_skills(skills):
    for s in skills:
        for e in s.errors:
            assert "compiled artifact" not in e, f"{s.name}: {e}"


def test_manifest_json_is_serializable(skills):
    import json

    out = {"skills": [s.to_manifest() for s in skills]}
    json.dumps(out)  # must not raise

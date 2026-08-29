<!-- Thanks for contributing! Keep this short. -->

## Summary
<!-- One or two sentences. What does this PR add or fix? -->

## Type
<!-- Check one -->
- [ ] new skill
- [ ] fix to an existing skill
- [ ] tooling / docs / CI
- [ ] breaking contract change

## Contract
<!-- Must be green before review -->
- [ ] `python scan_skills.py --validate` exits 0
- [ ] `pytest tests/` passes
- [ ] one skill per PR (or one tightly-related category)
- [ ] the 10 standard H2 sections are present, in order
- [ ] snippets are real Python using the canonical library
- [ ] references are canonical docs (not marketing pages)
- [ ] `Ethics & safety` section is present and specific
- [ ] no secrets / no real PHI / no compiled artifacts

## Skill frontmatter (if a new skill)
```
name: ...
description: ...
metadata.category: ...
```

## Trigger example
<!-- A one-line prompt that should activate this skill -->
> "..."

# Security Policy

SciAgent Skills is a library of plain-text `SKILL.md` instructions. The skills themselves are not executable code and run with whatever privileges your coding assistant already has. The security considerations are therefore about *what the skills tell the agent to do*, not about the repo running anything itself.

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.x     | yes       |

We patch the latest `main` and cut patch releases for security-relevant fixes.

## Reporting a vulnerability

**Do not open a public issue for security reports.**

Email: `security@<Pratikrishi97>.dev` (replace with your real address) with the subject `sciagent-skills security report`. You will receive an acknowledgement within 72 hours. We coordinate disclosure and credit reporters in the release notes unless they prefer to remain anonymous.

Please include:

- A description of the issue and its impact.
- A minimal reproduction (a skill snippet, a prompt, or a config).
- Affected versions / commits.
- Any suggested fix.

## Threat model

1. **Prompt injection via skill content.** A malicious skill could instruct the agent to exfiltrate data or run destructive commands. **Mitigation:** only install skills from sources you trust. Review any third-party skill's `SKILL.md` before installing. The `allowed-tools` experimental frontmatter field lets a skill pre-approve a limited tool surface — prefer skills that use it.
2. **Secrets in skills.** Skills are plain text in a public repo. **Rule:** never put API keys, tokens, credentials, or real patient identifiers in a skill. Snippets should use placeholders (`<YOUR_API_KEY>`), `os.environ.get(...)`, or local-only config.
3. **Clinical data and PHI.** Skills in the Clinical & Medical Research category assume data is already de-identified or synthetic. **Rule:** never paste real PHI into a prompt. Use synthetic datasets (MIMIC-IV is already de-identified but still treat with care) and assume any text you send to a hosted assistant may be logged.
4. **Dual-use research.** Synthesis, retrosynthesis, and pathogen-genomics skills are for legitimate, open research. **Rule:** refuse requests whose only plausible use is weapons, and refer users to their institutional biosafety committee (IBC) / dual-use research of concern (DURC) review process.
5. **Lab safety.** Chemistry and biology skills describe *in silico* workflows and literature-scale reasoning. **Rule:** they are not laboratory SOPs. Wet-lab execution requires institutional review, PPE, and proper training — none of which a skill can substitute for.
6. **Supply chain.** Skills may recommend `pip install` lines. **Mitigation:** only recommend packages from PyPI with established maintainership; prefer conda-forge for compiled scientific libraries. The repo's own dependencies (`pyproject.toml`) are pinned and scanned by CI.

## Hardening checklist for skill authors

- [ ] `description` includes trigger keywords but no secrets.
- [ ] `compatibility` lists the libraries the skill needs; nothing exotic.
- [ ] Snippets use `os.environ.get()` for any credential, never a literal.
- [ ] Clinical/genomics snippets operate on de-identified or synthetic data.
- [ ] `Ethics & safety` section is present and specific (not boilerplate).
- [ ] No `curl | bash`, no `eval`, no `exec` of remote content.
- [ ] `allowed-tools` (if used) is the minimal set the skill actually needs.

## Incident response

1. Confirm the scope (which skill, which version, which agents).
2. Mark the affected skill folder with a `SECURITY-NOTE.md` describing the issue and workaround.
3. Cut a patch release; update `CHANGELOG.md` with a `security` entry.
4. Publish a GitHub Security Advisory and request a CVE if warranted.
5. Notify known downstream consumers (the `plugin.json` marketplace, if listed).

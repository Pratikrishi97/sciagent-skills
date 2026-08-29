---
name: grant-writing
description: Draft competitive grant applications for NIH (R01/R21/K), NSF, and EU Horizon Europe. Use for Specific Aims, Significance, Innovation, Approach, budget justification, biosketch, Data Management and Sharing (DMS) plans, broader impacts, letters of support, and resubmission strategy. Triggers include "Specific Aims", "NIH R01", "NSF", "Horizon Europe", "biographical sketch", "DMS plan", "broader impacts", "NIH RePORTER", "PAPPG".
license: MIT
compatibility: Requires Python 3.10+ with requests, jinja2, pandoc, and a TeX distribution for PDF assembly. NIH/NSF submissions are done via grants.gov / Research.gov with institutional approval; this skill drafts and assembles materials locally.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Knowledge & Communication
---

# Grant Writing

## Overview

A grant application is a persuasive, structured document that convinces
reviewers a project is **significant** (it matters), **innovative** (it
is new), and **feasible** (the team can do it). Funders prescribe the
structure, the format, and the review criteria; the agent's job is to
write to those constraints. This skill covers the pipeline for three of
the largest funders in the world:

- **NIH** (R01, R21, R03, K awards): Specific Aims (1 page), Research
  Strategy (Significance, Innovation, Approach; 6/12 pages), Biosketch
  (NIH biographical sketch, 5 pages), Data Management and Sharing Plan
  (DMS, 1 page), Budget Justification, Letters of Support.
- **NSF** (Career, Core, EAGER, RaMP): Project Summary (1 page),
  Project Description (15 pages including Broader Impacts and Results
  from Prior NSF Support), Biosketch (2 pages), Data Management Plan,
  Budget and Budget Justification (5 pages).
- **EU Horizon Europe**: Concept, Objectives, Methodology (Part B1),
  Implementation (work packages, deliverables, milestones), Consortium
  description, Budget (personnel, equipment, travel, other, indirect).

For each, this skill drafts the prose, justifies the budget with Python,
queries `NIH RePORTER` and `NSF Award Search` for related prior work, and
assembles the materials into a single PDF for institutional review.

## When to use this skill

- You are writing a new **NIH R01/R21/R03/K** application.
- You are writing an **NSF** proposal (CAREER, Core, EAGER, etc.).
- You are writing an **EU Horizon Europe** proposal (RIA, IA, CSA).
- You need to draft a **Specific Aims** page or a **biosketch**.
- You need a **Data Management and Sharing (DMS) Plan** or **DMP**.
- You need a **budget justification** that totals to the cap.
- You are responding to a **resubmission** (NIH A1) and need to write
  the introduction and Strengths/Weaknesses response.
- You need **Broader Impacts** (NSF) or **Impact/Exploitation** (EU).

Do NOT use this skill for project reports (use `scientific-writing`) or
for conference talks (use `scientific-presentations`).

## Prerequisites

- Python 3.10 or newer.
- Libraries:
  ```bash
  pip install requests jinja2 pyyaml python-docx
  ```
- Pandoc and a TeX distribution for PDF assembly:
  `sudo apt install pandoc texlive-full latexmk`.
- Institutional **Sponsored Programs Office (SPO)** to submit through
  grants.gov / Research.gov / Funding & Tenders Portal. The agent drafts
  locally; the SPO submits.
- For NIH RePORTER and NSF Award Search no API key is required.

## Core workflows

### 1. Draft Specific Aims (1 page, NIH/NSF-canonical structure)

```python
from jinja2 import Template
template = Template("""
# Specific Aims
{{ hypothesis }}

Aim 1: {{ aim1 }}
Aim 2: {{ aim2 }}
Aim 3: {{ aim3 }}

Expected outcome: {{ outcome }}.
Innovative because {{ innovation }}.
""".strip())
text = template.render(
    hypothesis="...",
    aim1="Determine the role of X in Y using single-cell ...",
    aim2="Test whether inhibiting X reverses Y in a model ...",
    aim3="Validate X as a biomarker in a clinical cohort ...",
    outcome="... mechanistic, preclinical, and translational evidence ...",
    innovation="... integrates spatial transcriptomics with ...")
open("specific_aims.md", "w").write(text)
```

### 2. Justify the budget with Python (NIH modular or detailed)

```python
def budget(person_years, salary, fringe=0.29, inflation=0.03, years=5):
    rows = []
    for y in range(years):
        base = salary * (1 + inflation) ** y
        rows.append({"year": y+1, "salary": base,
                     "fringe": base*fringe,
                     "total": base*(1+fringe)})
    return rows
for r in budget(person_years=0.5, salary=125000, fringe=0.29, years=5):
    print(r)
# Add tuition, equipment, travel, materials, publication, indirect (F&A)
```

### 3. Biosketch (NSF 2-page / NIH 5-page)

```python
from jinja2 import Template
tpl = Template("""# Biographical Sketch
Name: {{ name }}, {{ title }}
Position: {{ position }}
Education:
{% for e in edu %}- {{ e }}
{% endfor %}

Appointments:
{% for a in appts %}- {{ a }}
{% endfor %}

Products (last 5 years):
{% for p in prods %}- {{ p }}
{% endfor %}

Synergistic Activities:
{% for s in syn %}- {{ s }}
{% endfor %}
""")
open("biosketch.md","w").write(tpl.render(
    name="Ada Lovelace", title="Associate Professor",
    position="Dept. of Computational Biology, Example University",
    edu=["PhD 2014, Stanford University", "BS 2009, MIT"],
    appts=["2020-present: Associate Professor", "2014-2020: Assistant Professor"],
    prods=["Lovelace A. (2024). ...", "Lovelace A., Turing A. (2023). ..."],
    syn=["Organizer, Regional Code Club",
         "Advisory board, Public Data Initiative",
         "Mentor, 4 PhD students"]))
```

### 4. Data Management and Sharing Plan (DMS, 1 page)

```python
from jinja2 import Template
dms = Template("""# Data Management and Sharing Plan
## Data types
{{ types }}

## Tools, standards, formats
{{ standards }}

## Storage and access
{{ access }}

## Preservation
{{ preservation }}

## Sharing
{{ sharing }}

## Oversight
{{ oversight }}
""".strip()).render(
    types="Genomic (FASTQ, BAM, VCF), imaging (OME-TIFF), code (Python).",
    standards="Genome Reference Consortium GRCh38, FAIRsharing standards.",
    access="NCBI SRA, BioStudies; institutional AWS S3 during the project.",
    preservation="10 years per NIH policy; Zenodo DOIs for code releases.",
    sharing="Immediate release on publication; controlled-access for PII.",
    oversight="PI and data manager; quarterly FAIR-compliance audits.")
open("dms.md","w").write(dms)
```

### 5. Query NIH RePORTER for related prior work

```python
import requests
url = "https://api.reporter.nih.org/v2/projects/search"
payload = {"criteria": {"project_nums":["R01AI123456"],
                         "fiscal_years":[2020,2021,2022,2023,2024]}}
r = requests.post(url, json=payload, timeout=30).json()
for p in r["results"][:5]:
    print(p["project_title"], "|", p["agency_administrator"])
```

## Best practices

- **Read the funding opportunity announcement (FOA/NOFO) end to end**
  before drafting; the page limits, review criteria, and required
  attachments are non-negotiable.
- Lead with a **central hypothesis** and **2-4 Specific Aims**; reviewers
  remember a one-sentence thesis if it is in the first paragraph.
- Use a **Gantt chart** or work-package table to show feasibility over
  the project period; reviewers score feasibility heavily.
- Provide **preliminary data** for every Aim; if there is no preliminary
  data, that Aim is at risk of being scored as too risky.
- Address **rigor** (sample size justification, sex as a biological
  variable, authentication of biological resources) and
  **reproducibility** explicitly in Approach — NIH requires it.
- Write **broader impacts** (NSF) that are concrete and measured: names
  of partner schools, expected reach, evaluation plan. Vague "will train
  graduate students" fails review.
- Show the **team** can do it: each Aim needs a co-Investigator with
  preliminary data in that area; no single PI cover-all.
- For **resubmissions** (NIH A1), write a 1-page Introduction naming
  each prior weakness, your response, and the page where it is
  addressed; do not relitigate the original critique.
- Use **plain language** in the Aims page; reviewers skim in 15 minutes
  — your Aims page must stand alone.
- **Numbers must reconcile**: Aims page narrative, budget, and DMS plan
  must all show the same years, the same data volumes, and the same
  co-investigators. Reviewers and SPOs catch discrepancies.

## Common pitfalls

- Aims that are independent projects rather than coordinated steps
  toward a single hypothesis.
- Innovation section that lists methods ("we use single-cell RNA-seq")
  — innovation is the conceptual advance, not the technique.
- Approach written without alternative approaches and pitfalls; reviewers
  score feasibility higher when risks and mitigations are explicit.
- Budget that asks for 100% effort on a single PI across two large
  grants — NIH caps at 12 person-months per person across R01s in
  practice.
- No preliminary data for the most innovative Aim — the riskiest work
  needs the most preliminary evidence.
- Broader Impacts (NSF) that are generic ("promote diversity") rather
  than specific ("Partner with X HBCU; co-mentor 2 REU students/year;
  release all code under MIT").
- Data Management Plan copied from another proposal and not edited for
  the actual data types in this project — desk-reject trigger.
- Biosketch with >5-year products or >2 pages (NSF); reviewers reject
  without review.
- Resubmission that ignores the prior critique; NIH asks "what changed?"
  and reviewers look for the answer in the Introduction.

## Worked example

Drafting the Specific Aims and DMS for a fictional NIH R01: "Mechanism
of microglial dysfunction in early Alzheimer's disease."

```python
from jinja2 import Template
aims = Template("""
# Specific Aims (R01, 1 page)
Alzheimer's disease (AD) progresses silently for decades before cognitive
decline. Microglia enter a senescent state that may drive this window.
Our **central hypothesis** is that TREM2 loss drives microglial senescence
early in AD, and reactivating TREM2 reverses it.

**Aim 1. Characterize microglial senescence in early AD.** We will
profile 200 postmortem samples (Braak I-III vs controls) with snRNA-seq
and spatial transcriptomics.

**Aim 2. Test causality in humanized mice.** A knock-in mouse carrying
the R47H TREM2 variant will be crossed with App NL-G-F and rescued with
a small-molecule TREM2 agonist.

**Aim 3. Validate biomarkers in CSF.** A 200-subject cohort will be
screened for senescence-derived CSF proteins.

**Expected outcomes**: a mechanistic, preclinical, and translational
chain from gene to biomarker.

**Innovation**: integrates spatial transcriptomics and a first-in-class
TREM2 agonist, in human, mouse, and CSF cohorts.
""".strip())
open("specific_aims.md", "w").write(aims.render())
```

DMS plan (excerpt):

```python
from jinja2 import Template
dms = Template("""
# Data Management and Sharing Plan
## Data types
snRNA-seq (h5ad, ~5TB), spatial transcriptomics (tiff+json, ~10TB),
CSF proteomics (csv, ~10MB), code (Python).

## Standards
BICAN Cell Registry, HCA Tier 1 Metadata, FAIRsharing.

## Storage & access
Institutional S3 during project; NCBI GEO/SRA on publication; Zenodo for
code releases with a DOI per release.

## Preservation
10 years per NIH policy (NOT-OD-21-013).

## Sharing
Release at time of publication (open access); CSF proteomics released as
controlled access via dbGaP if PII is present.

## Oversight
PI + data manager; quarterly FAIR-compliance audits using FAIRshake.
""".strip())
open("dms.md", "w").write(dms.render())
```

Assemble with `pandoc specific_aims.md dms.md -o application.pdf`.

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| jinja2 | Templating for Aims, biosketch, DMS, budget | `pip install jinja2` |
| requests | NIH RePORTER, NSF Award Search APIs | `pip install requests` |
| python-docx | Generate biosketch .docx for institutional templates | `pip install python-docx` |
| pandoc | Assemble markdown chapters into a single PDF | https://pandoc.org |
| latexmk | Automated LaTeX build loop | `apt install latexmk` |
| NIH RePORTER API | Find related prior NIH awards | https://api.reporter.nih.gov |
| NSF Award Search | Find related prior NSF awards | https://www.nsf.gov/awardsearch |
| grants.gov | Federal submission portal | https://www.grants.gov |
| Research.gov | NSF submission portal | https://www.research.gov |
| FAIRshake | FAIR-compliance self-assessment | https://fairshake.digital/ |
| DMPRoadmap / DMPOnline | Institutional DMP authoring | https://dmptool.org |
| NIH Sample Applications | Real funded applications | https://www.niaid.nih.gov/grants-contracts/sample-applications |

## References

- NIH Grants & Funding policy library: https://grants.nih.gov/policy/
- NIH DMS Policy (NOT-OD-21-013): https://grants.nih.gov/grants/guide/notice-files/NOT-OD-21-013.html
- NIH Biosketch format page: https://grants.nih.gov/grants/forms/biosketch.htm
- NSF PAPPG (Proposal & Award Policies & Procedures Guide): https://www.nsf.gov/policies/pappg
- EU Horizon Europe Programme Guide: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guide/programme-guide_horizon_en.pdf
- NIH RePORTER API: https://api.reporter.nih.gov/
- NSF Award Search: https://www.nsf.gov/awardsearch/
- NIAID sample applications & summary statements: https://www.niaid.nih.gov/grants-contracts/sample-applications

## Ethics & safety

- **Truthful claims.** Every preliminary result must be in your lab's
  notebooks; never invent pilot data, sample sizes, or collaborations.
- **Authorship/credit on the team.** Use a Key Personnel table with
  person-months per person; named individuals consent to the effort.
- **Conflict of interest.** Disclose financial COIs (equity, consultancy,
  patents) for every key person; NIH and NSF both require this.
- **Plagiarism.** Do not copy boilerplate from funded proposals without
  permission; even your own prior boilerplate must be re-cited.
- **Rigor and reproducibility.** State sample-size justification, sex as
  biological variable, authentication of cell lines and antibodies, and
  randomization/blinding.
- **Human subjects and animals.** Reference the IRB/IACUC approval
  numbers and the inclusion of women, minorities, and children per NIH
  policy.
- **Data sharing.** DMS plans are binding; failure to share can result
  in funding restrictions on future awards.
- **AI use disclosure.** Disclose AI assistance in drafting, analysis,
  or budget assembly per NIH Notice NOT-OD-25-117 (or the current NIH
  guidance). AI cannot be a co-Investigator or be credited as personnel.

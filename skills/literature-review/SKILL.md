---
name: literature-review
description: Plan, execute, and report systematic literature reviews and meta-analyses. Use when running PRISMA 2020-compliant searches, screening PubMed/Crossref/OpenAlex/Semantic Scholar, deduplicating records, building citation networks, or performing meta-analysis. Triggers include "systematic review", "PRISMA", "PubMed", "semantic search", "citation graph", "meta-analysis", "ASReview".
license: MIT
compatibility: Requires Python 3.10+ with biopython, habanero, pyzotero, requests, pandas, networkx, matplotlib, asreview, pymeta. NCBI E-utilities require an email and an NCBI API key for higher rates.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Knowledge & Communication
---

# Literature Review

## Overview

A literature review is a structured, reproducible survey of the published
record on a question. Done well it is more than a reading list: it is an
audit trail from the search strategy, through screening, to a synthesis
(narrative, scoping, or meta-analytic). This skill covers the full pipeline
that a research agent can execute programmatically:

1. Translate a research question (PICO/PECO/SPIDER) into multi-database
   search strings.
2. Search PubMed (NCBI E-Utilities), Crossref, OpenAlex, and Semantic
   Scholar, normalize to a common schema, and deduplicate.
3. Screen title/abstract and full text using a published checklist and, when
   the result set is large, active learning (ASReview).
4. Build citation networks (forward/backward snowballing) with networkx.
5. Extract effect sizes and run a meta-analysis (random-effects DerSimonian
   and Laird, or fixed-effect) and render a forest plot.

Outputs follow the PRISMA 2020 reporting standard (flow diagram, search
strings, exclusions, included-items list).

## When to use this skill

- You need a **systematic review** following PRISMA 2020 (medicine, public
  health, ecology, education, social sciences).
- You need a **scoping review** (Arksey & O'Malley / JBI) mapping a field.
- You are doing a **rapid review** with a documented shortcut.
- You need to **snowball** an included-paper set forward and backward.
- You need a **meta-analysis** with forest plot and heterogeneity stats.
- You need a **bibliometric / citation network** view of a topic.
- You need to **deduplicate** records pulled from several databases before
  screening.

Do NOT use this skill for a single-paper lookup — use the
`citation-management` skill instead.

## Prerequisites

- Python 3.10 or newer.
- Install canonical libraries:
  ```bash
  pip install biopython habanero pyalex requests pandas networkx matplotlib
  pip install asreview pymeta
  ```
- Accounts / keys:
  - **NCBI API key** (https://www.ncbi.nlm.nih.gov/account/settings/) —
    raises E-utilities rate from 3 req/s to 10 req/s. Set `NCBI_API_KEY`.
  - **OpenAlex** — polite-pool email recommended; set `OPENALEX_EMAIL`.
  - **Semantic Scholar** — optional API key (https://www.semanticscholar.org/product/api)
    for higher limits; set `S2_API_KEY`.
  - **Crossref** — polite-pool email; set `CROSSREF_EMAIL`.
- A project workspace with `protocol.md`, `searches/`, `records/`,
  `screening/`, `analysis/`, `prisma/`.

## Core workflows

### 1. Build a PICO-grounded search string and run it on PubMed

```python
from Bio import Entrez
import os, json, time
Entrez.email = os.environ["NCBI_EMAIL"]
Entrez.api_key = os.environ.get("NCBI_API_KEY", "")

query = (
    '("low back pain"[MeSH] OR "low back pain"[tiab]) AND '
    '("exercise therapy"[MeSH] OR "motor control exercise"[tiab]) AND '
    '("randomized controlled trial"[pt])'
)
handle = Entrez.esearch(db="pubmed", term=query, retmax=500, sort="relevance")
ids = Entrez.read(handle)["IdList"]
print(f"PubMed hits: {len(ids)}")

# Fetch records in batches of 100 to stay under rate limits
records = []
for i in range(0, len(ids), 100):
    h = Entrez.efetch(db="pubmed", id=",".join(ids[i:i+100]),
                      rettype="medline", retmode="xml")
    records.extend(Entrez.read(h)["PubmedArticle"])
    time.sleep(0.34)  # ~3 req/s without API key
json.dump(records, open("records/pubmed.json", "w"))
```

### 2. Query OpenAlex and Semantic Scholar for coverage and citation graph

```python
import pyalex, requests, os
pyalex.settings.email = os.environ["OPENALEX_EMAIL"]
works = pyalex.Works().search("motor control exercise low back pain").get(per_page=200)
print(f"OpenAlex hits: {len(works)}")

def s2_refs(doi, limit=100):
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    url += f"?fields=title,year,references.title,references.year&limit={limit}"
    headers = {"x-api-key": os.environ.get("S2_API_KEY", "")}
    return requests.get(url, headers=headers, timeout=30).json()
```

### 3. Deduplicate records and stage for screening (Rayyan / CSV)

```python
import pandas as pd
from rapidfuzz import fuzz
df = pd.read_csv("records/merged.csv")
df["norm_title"] = (df["title"].str.lower().str.strip()
                              .str.replace(r"[^\w\s]", "", regex=True))
keep = []
for i, row in df.iterrows():
    if any(fuzz.token_set_ratio(row["norm_title"], df.loc[j, "norm_title"]) > 95
           and abs(int(row["year"]) - int(df.loc[j, "year"])) < 2
           for j in keep):
        continue
    keep.append(i)
dedup = df.loc[keep].reset_index(drop=True)
dedup.to_csv("records/dedup.csv", index=False)
```

### 4. Active-learning screening with ASReview

```python
# One-time: convert dedup.csv to ASReview 0.x dataset
# asreview simulate records/dedup.csv --n_prior_included 5 --n_prior_excluded 5
# Then run an interactive screening:
#   asreview link records/dedup.asreview
# Export labeled set:
#   asreview export records/dedup.asreview -o screening/labeled.csv
```

### 5. Random-effects meta-analysis with forest plot

```python
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from pymeta.linalg import rma  # or use statsmodels/PUB_Bonett
# Hedges g and variances per study:
df = pd.read_csv("analysis/effects.csv")
# Random-effects via DerSimonian-Laird (illustrative; use metafor/R via rpy2 for production)
w = 1.0 / df["var"]
Q = (w * (df["g"] - (w*df["g"]).sum()/w.sum())**2).sum()
df_w = len(df) - 1
tau2 = max(0, (Q - df_w) / (w.sum() - (w*w).sum()/w.sum()))
w_re = 1.0 / (df["var"] + tau2)
pooled = (w_re * df["g"]).sum() / w_re.sum()
se = np.sqrt(1.0 / w_re.sum())
print(f"pooled g = {pooled:.3f}  95% CI {pooled-1.96*se:.3f} to {pooled+1.96*se:.3f}")
```

## Best practices

- Write and **register the protocol** (PROSPERO, OSF) BEFORE running the
  search; document PICO, databases, dates, limits, and the screening rules.
- Translate the question into **database-specific syntax** — MeSH for
  PubMed, Emtree for Embase, free-text for Scopus; never copy-paste the
  same string across databases.
- Report the search with **PRISMA 2020**: identification, screening,
  eligibility, included; document exclusions with reasons.
- Keep **one record per row**, one column per database field; never drop
  PMIDs/DOIs — they are your join keys.
- Document every database, date, and number of hits in a `searches/log.md`.
- Use **two independent screeners** for title/abstract and full text;
  record a Cohen kappa for agreement.
- Cap automated screening at a defensible threshold and **keep a human in
  the loop** for the included set.
- Pre-register the meta-analysis model (random vs fixed); report I-squared,
  tau-squared, prediction interval, and a funnel plot.
- Archive the raw JSON responses from each API so the review is
  **reproducible** years later even if APIs change.
- Version everything: protocol, search strings, datasets, scripts, report
  — push to a public OSF or Zenodo record at submission.

## Common pitfalls

- Treating PubMed as the entire literature — Embase, Scopus, Web of Science,
  grey literature, and trial registries add studies that PubMed misses.
- Search strings built from natural-language synonyms without MeSH/Emtree
  explode; coverage and recall suffer.
- Failing to deduplicate before screening — same study counted twice
  inflates apparent yield and biases meta-analysis.
- Letting ASReview (or any active-learning tool) fully automate inclusion;
  always review its "stopped" set manually before locking the included list.
- Combining effect sizes with the wrong unit (SMD vs OR vs RR) or pooling
  pre/post versus between-group differences in the same forest plot.
- Reporting only pooled estimate and p-value; omit I-squared, prediction
  interval, subgroup analyses, and risk-of-bias (RoB 2 / ROBINS-I).
- Over-stating conclusions from 2-3 small studies, or ignoring publication
  bias/funnel-plot asymmetry.
- Not saving the exact API responses — the same query tomorrow may return a
  different result set, breaking reproducibility.

## Worked example

A PRISMA 2020-compliant mini-review: "Motor control exercise for chronic
non-specific low back pain, RCTs 2015-2025".

```python
# 1) Search
from Bio import Entrez
import os, json
Entrez.email = os.environ["NCBI_EMAIL"]
q = ('("motor control exercise"[tiab] OR "core stabilization"[tiab]) AND '
     '"low back pain"[MeSH] AND 2015:2025[dp] AND "randomized controlled trial"[pt]')
ids = Entrez.read(Entrez.esearch(db="pubmed", term=q, retmax=200))["IdList"]
arts = Entrez.read(Entrez.efetch(db="pubmed", id=",".join(ids),
                                 rettype="medline", retmode="xml"))["PubmedArticle"]
json.dump(arts, open("records/pubmed.json", "w"))

# 2) Normalize to a CSV
import pandas as pd
rows = [{"pmid": a["MedlineCitation"]["PMID"],
         "title": a["MedlineCitation"]["Article"]["ArticleTitle"],
         "year": a["MedlineCitation"]["Article"]["Journal"]["JournalIssue"]["PubDate"].get("Year","")}
        for a in arts]
pd.DataFrame(rows).to_csv("records/pubmed.csv", index=False)

# 3) Screen with ASReview (CLI shown)
#    asreview link records/pubmed.csv --label-included 1,5,9 --label-excluded 2,3,4
#    asreview export records/pubmed.asreview -o screening/included.csv

# 4) Snowball included set forward via OpenAlex
import pyalex, os
pyalex.settings.email = os.environ["OPENALEX_EMAIL"]
snowball = []
for doi in pd.read_csv("screening/included.csv")["doi"].dropna():
    w = pyalex.Works(doi)
    snowball.extend([r["doi"] for r in w.get(references=True)[:50]])
print(f"forward snowball candidates: {len(set(snowball))}")
```

The final `prisma/flow.md` records: identification (n from PubMed, n from
OpenAlex snowball), screening (n excluded by title/abstract), eligibility
(n excluded at full text, with reasons), included (n quantitative, n
qualitative).

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| biopython (Bio.Entrez) | NCBI E-Utilities: PubMed, MeSH, GEO | `pip install biopython` |
| habanero | Crossref, DataCite, ContentNegotiation | `pip install habanero` |
| pyalex | OpenAlex works, concepts, citations | `pip install pyalex` |
| semanticscholar (Python) | Semantic Scholar Graph API | `pip install semanticscholar` |
| ASReview | Active-learning screening (ELAS, NB, logistic) | `pip install asreview` |
| Rayyan | Collaborative screening (web app) | https://rayyan.qcri.org |
| networkx | Citation graph, snowball traversal | `pip install networkx` |
| pandas | Record normalization, dedup, export | `pip install pandas` |
| rapidfuzz | Fuzzy-title deduplication | `pip install rapidfuzz` |
| pymeta / statsmodels | Random-effects meta-analysis | `pip install pymeta statsmodels` |
| matplotlib | Forest, funnel, PRISMA flow plots | `pip install matplotlib` |
| RoB 2 / ROBINS-I | Risk-of-bias assessment (templates) | rob-tools / robvis (R + Python CLI) |

## References

- PRISMA 2020 statement and checklist: https://www.prisma-statement.org/
- NCBI E-Utilities documentation: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- OpenAlex API documentation: https://docs.openalex.org/
- Semantic Scholar Graph API: https://api.semanticscholar.org/api-docs/graph
- Crossref REST API: https://api.crossref.org/swagger-ui/
- ASReview documentation: https://asreview.readthedocs.io/
- Cochrane Handbook for Systematic Reviews: https://training.cochrane.org/handbook
- PROSPERO international prospective register: https://www.crd.york.ac.uk/prospero/

## Ethics & safety

- **Honest reporting.** Never cherry-pick studies or omit unfavourable
  results; report every database searched, every date, and every
  exclusion reason.
- **Authorship and contribution.** Use the CRediT taxonomy to record each
  reviewer's role (search, screening, data extraction, analysis, writing,
  supervision). State competing interests for every author.
- **Plagiarism.** Paraphrase and cite; never copy abstracts verbatim into
  the review. Direct quotes need quotation marks and a citation.
- **Citation accuracy.** Use DOIs as the primary key; verify every
  included reference against the source PDF before publication.
- **Risk of bias.** Report RoB 2 (RCTs) or ROBINS-I (non-randomized) for
  every included study; do not pool studies with critical risk of bias
  without sensitivity analysis.
- **Patient/public involvement.** If the review concerns patients,
  document PPI in protocol, screening, and write-up.
- **Data sharing.** Deposit the search strings, dedup CSV, screening
  decisions, and analysis scripts in a public OSF or Zenodo record with a
  DOI at submission.

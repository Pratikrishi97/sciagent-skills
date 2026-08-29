# Example: systematic review with PRISMA + meta-analysis

**Skills activated:** `literature-review`, `citation-management`

## The prompt

> Run a systematic review on "effect of statins on major adverse cardiovascular events in primary prevention". Search PubMed + OpenAlex, dedupe, screen titles/abstracts with ASReview, extract effect sizes from included RCTs, do a DerSimonian-Laird random-effects meta-analysis with a forest plot, and generate a PRISMA 2020 flow diagram + a BibTeX file of included studies.

## What the agent does

`literature-review` on `PRISMA`, `PubMed`, `OpenAlex`, `ASReview`, `meta-analysis`; `citation-management` for the BibTeX export.

### 1. Search PubMed (Entrez) + OpenAlex

```python
# pip install biopython pyalex rapidfuzz pymeta matplotlib networkx
from Bio import Entrez
Entrez.email = "you@example.org"
query = 'statin*[tiab] AND ("primary prevention"[tiab] AND ("randomized controlled trial"[pt]))'
handle = Entrez.esearch(db="pubmed", term=query, retmax=2000)
pmids = Entrez.read(handle)["IdList"]
print(f"PubMed hits: {len(pmids)}")

import pyalex
works = list(pyalex.Works().search("statin primary prevention randomized").get(per_page=200, n=10))
print(f"OpenAlex hits: {len(works)}")
```

### 2. Dedupe

```python
from rapidfuzz import fuzz
keys = [f"{p['title'][:80]}" for p in records]  # build from both sources
deduped, seen = [], []
for rec in records:
    if any(fuzz.ratio(rec["title"][:80], s) > 92 for s in seen): continue
    seen.append(rec["title"][:80]); deduped.append(rec)
print(f"after dedupe: {len(deduped)}")
```

### 3. Active-learning screening (ASReview)

```bash
# export the deduped set as a RIS file, then:
asreview simulate deduped.ris --n_included 25 --model nb --query_max 200 -o screening.asreview
```

### 4. Extract + meta-analyze

```python
import numpy as np
# events_t / n_t for treatment, events_c / n_c for control, per included RCT
# compute log OR + SE, fit DerSimonian-Laird random effects
log_or = np.log((et*nc) / (ec*nt))
se = np.sqrt(1/et + 1/nt + 1/nc + 1/ec)
w = 1/(se**2 + np.var(log_or, ddof=1))
pooled = np.sum(w*log_or)/np.sum(w)
print(f"pooled OR = {np.exp(pooled):.2f} (95% CI ...)")
```

### 5. PRISMA flow diagram + BibTeX

```python
import bibtexparser
bib = bibtexparser.Library([bibtexparser.Entry(entry_type="article", key=r["doi"],
    fields={"title": r["title"], "author": r["authors"], "year": str(r["year"]),
            "journal": r["venue"], "doi": r["doi"]}) for r in included])
open("included.bib","w").write(bibtexparser.write(bib))
# PRISMA flow diagram: matplotlib boxes + arrows (counts: identified, screened, eligible, included)
```

## Pitfalls the skill surfaces

- Register the protocol on PROSPERO/OSF **before** screening — post-hoc protocol changes are a publication-bias red flag.
- ASReview accelerates screening but you still must screen all titles flagged by the model — it's triage, not a substitute for human review.
- Random-effects meta-analysis with <10 studies is fragile; report heterogeneity (I², τ²) and consider a leave-one-out sensitivity.
- Funnel-plot asymmetry (Egger's test) signals publication bias — report it honestly, don't trim-and-fill silently.
- Two independent reviewers should screen; Cohen's kappa for agreement is expected in the writeup.

## Reproducibility

Pin library versions; save the ASReview project file (`*.asreview`), the BibTeX, and the PRISMA counts in a reproducible Quarto report (`scientific-writing` skill). Deposit on OSF for a DOI.

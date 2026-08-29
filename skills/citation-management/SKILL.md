---
name: citation-management
description: Build, edit, and convert bibliographies across BibTeX, RIS, CSL-JSON, and EndNote. Use for Zotero and Mendeley automation, DOI and Crossref lookup, in-text citation parsing, CSL style rendering, and deduplication of reference libraries. Triggers include "BibTeX", "Zotero", "Mendeley", "CSL", "anystyle", "DOI lookup", "pyzotero", "bibtexparser".
license: MIT
compatibility: Requires Python 3.10+ with bibtexparser, pyzotero, habanero, citeproc-py, anystyle, requests. Zotero account and library ID + private API key for pyzotero; Crossref polite-pool email recommended.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Knowledge & Communication
---

# Citation Management

## Overview

A citation manager is the spine of a reproducible writing workflow. It
stores references with stable identifiers (DOI, PMID, ORCID, ISBN),
renders them in any of thousands of styles, and inserts in-text citations
and reference lists into manuscripts written in LaTeX, Word, Markdown, or
Quarto. This skill covers the programmatic side of that pipeline:

- Reading and writing BibTeX, RIS, CSL-JSON, and EndNote XML.
- Automating Zotero via `pyzotero` (collections, items, attachments,
  notes, tags).
- Looking up and verifying DOIs via `habanero` (Crossref) and the Crossref
  ContentNegotiation API (returns CSL-JSON directly).
- Parsing free-text reference lists with `anystyle` into structured
  fields.
- Rendering references with Citation Style Language (CSL) via
  `citeproc-py`.
- Deduplicating libraries by fuzzy title + year + first-author.
- Integrating ORCID to disambiguate authors.

Outputs are stable, version-controlled bibliographies that any word
processor or typesetting system can consume.

## When to use this skill

- You need to **build or curate a Zotero/Mendeley library** from a list
  of DOIs or PMIDs.
- You need to **convert** between BibTeX, RIS, CSL-JSON, or EndNote XML
  for journal or preprint submission.
- You need to **render references** in a specific journal style (Nature,
  APA 7, Chicago, IEEE, Vancouver) using CSL.
- You need to **parse unstructured reference lists** (PDF bibliography,
  pasted text) into structured records.
- You need to **deduplicate** a merged library before submission.
- You need to **verify** that every DOI in your manuscript resolves and
  points to the right work.
- You need to **attach author ORCIDs** to references.

Do NOT use this skill for systematic search/screening — use the
`literature-review` skill. The two compose: search in
`literature-review`, manage the resulting library here.

## Prerequisites

- Python 3.10 or newer.
- Install canonical libraries:
  ```bash
  pip install bibtexparser pyzotero habanero citeproc-py anystyle
  pip install requests rapidfuzz
  ```
- Accounts / keys:
  - **Zotero user ID** (numeric, https://www.zotero.org/settings/keys) and
    a **private API key** with library read/write; set `ZOTERO_USER_ID` and
    `ZOTERO_API_KEY`.
  - **Crossref polite-pool email**; set `CROSSREF_EMAIL`.
  - **ORCID public API** requires no key for reads; the member API needs
    credentials.
- The `anystyle` CLI also needs Ruby (`gem install anystyle`) for full
  accuracy; the Python wheel includes a basic model.

## Core workflows

### 1. Round-trip a BibTeX file with bibtexparser

```python
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
with open("refs.bib") as fh:
    db = bibtexparser.load(fh)
# Normalize all DOIs to lowercase, add a checksum-friendly key
for e in db.entries:
    if "doi" in e:
        e["doi"] = e["doi"].lower().lstrip("https://doi.org/")
        e["ID"] = e["doi"].replace("/", "_")
writer = BibTexWriter()
writer.indent = "  "
with open("refs_normalized.bib", "w") as fh:
    fh.write(writer.write(db))
```

### 2. Add items to a Zotero collection via pyzotero

```python
from pyzotero import zotero
import os
z = zotero.Zotero(os.environ["ZOTERO_USER_ID"], "user",
                  os.environ["ZOTERO_API_KEY"])
col = [c for c in z.collections() if c["data"]["name"] == "Project X"][0]
template = z.item_template("journalArticle")
template.update({
    "title": "A Phase 3 Trial of Drug X in Chronic Disease",
    "creators": [{"creatorType": "author", "firstName": "Ada",
                  "lastName": "Lovelace"}],
    "DOI": "10.1000/xyz123", "date": "2025-04-01",
    "publicationTitle": "NEJM", "volume": "372", "pages": "1-10",
    "collections": [col["key"]],
})
resp = z.create_items([template])
print("created:", resp["success"]["0"])
```

### 3. Resolve DOIs via Crossref and fetch CSL-JSON

```python
from habanero import Crossref
import requests, os
cr = Crossref(mailto=os.environ["CROSSREF_EMAIL"])
work = cr.works(ids="10.1038/s41586-021-03819-2")["message"]
print(work["title"][0], work.get("DOI"))

# ContentNegotiation -> CSL-JSON directly (no parsing needed)
headers = {"Accept": "application/vnd.citationstyles.csl+json"}
csl = requests.get("https://doi.org/10.1038/s41586-021-03819-2",
                   headers=headers, timeout=30).json()
```

### 4. Parse a free-text reference list with anystyle

```python
# CLI: anystyle -f json parse references.txt
# Python (basic model):
import anystyle
refs = anystyle.parse("Lovelace, A. (2025). A Phase 3 Trial of Drug X. NEJM, 372(1), 1-10.",
                      format="csl")  # list of dicts
```

### 5. Render references with a CSL style (citeproc-py)

```python
from citeproc import CitationStylesStyle, CitationItem, formatter
from citeproc.source.json import CiteProcJSON
import json
src = CiteProcJSON(json.load(open("refs.csl.json")))
style = CitationStylesStyle("styles/apa.csl", validate=False)
bib = style.bibliography()
items = [CitationItem(doi) for doi in [r["id"] for r in src.data]]
for k, v in bib.make_bibliography(items).items():
    print(v[0])
```

## Best practices

- Use the **DOI as the primary key** for every record; never invent a key
  from the title — collides and breaks dedup.
- Pick **one canonical format per project** (CSL-JSON internally; export to
  BibTeX/RIS for submission). Convert on the way out, not in storage.
- **Version the bibliography** in git — `.bib` files diff cleanly, .ris
  and JSON do too.
- Run `habanero.content_negotiation` once per record on import to **fetch
  authoritative metadata** and overwrite your hand-typed fields.
- Keep authors in `familyName`/`givenName` pairs in CSL-JSON; BibTeX
  `author = {Lovelace, Ada}` round-trips cleanly when Last, First is used.
- Use the **Zotero group library** for shared projects (read/write for
  co-authors, public read for reviewers).
- Tag records with the **project name and acquisition date** so re-runs
  are auditable.
- Validate CSL-JSON against the CSL schema before submission.
- Pin **CSL style versions** by commit hash in your repo; styles change
  and silently alter formatting.
- For ORCID integration, store `author.orcid` as a CSL-JSON extension
  field; the CSL-JSON spec reserves this for round-tripping.

## Common pitfalls

- Mixing entry types (`@article` vs `@inproceedings`) for the same work
  — the journal name ends up in the `booktitle` slot and the style prints
  garbage.
- Brace-balanced but **unprotected titles** in BibTeX break case
  preservation; wrap proper nouns: `{YouTube}`, `{pH}`.
- Double-encoded HTML entities (`&amp;amp;`) in fields after multiple
  round-trips — sanitize with `html.unescape` on import.
- The Zotero API rate limit (≈ 1 request/8 s for writes); batch
  `create_items` and back off on 429.
- Treating Mendeley's deprecated API as current — Elsevier retired the
  public Mendeley API in 2024; export to BibTeX and migrate to Zotero.
- Trusting `anystyle` on full-text references without spot-checking; the
  model is 90-95% accurate, so plan a manual pass.
- Forgetting to **deduplicate** before submission — same DOI twice under
  two different keys renders as two list items in many CSL styles.
- Hard-coding style names (`"apa"`) instead of CSL file paths; the
  resolved style may differ from what your journal actually requires.

## Worked example

End-to-end: take a list of DOIs, build a Zotero collection, then export a
BibTeX file and an APA-formatted bibliography.

```python
# 1) Resolve DOIs to CSL-JSON via Crossref ContentNegotiation
import requests, json
dois = ["10.1038/s41586-021-03819-2", "10.1126/science.abc1234",
        "10.1016/j.cell.2024.01.010"]
hdrs = {"Accept": "application/vnd.citationstyles.csl+json"}
records = []
for doi in dois:
    r = requests.get(f"https://doi.org/{doi}", headers=hdrs, timeout=30)
    if r.status_code == 200:
        records.append(r.json())
json.dump(records, open("refs.csl.json", "w"), indent=2)

# 2) Push to Zotero collection
from pyzotero import zotero
import os
z = zotero.Zotero(os.environ["ZOTERO_USER_ID"], "user",
                  os.environ["ZOTERO_API_KEY"])
col = z.create_collections([{"name": "DOI ingest",
                             "parentCollection": False}])
colkey = z.last_modified_collection_version
template = z.item_template("journalArticle")
for rec in records:
    item = dict(template)
    item["title"] = rec.get("title", "")
    item["DOI"] = rec["DOI"]
    item["date"] = rec.get("published", {}).get("date-parts", [[""]])[0][0]
    item["creators"] = rec.get("author", [])
    item["publicationTitle"] = rec.get("container-title", "")
    z.create_items([item])

# 3) Export BibTeX for LaTeX submissions
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
db = bibtexparser.bibdatabase.BibDatabase()
db.entries = [{
    "ENTRYTYPE": "article", "ID": r["DOI"].replace("/", "_"),
    "title": "{" + r.get("title","") + "}",
    "author": " and ".join(f"{a.get('family','')}, {a.get('given','')}"
                           for a in r.get("author",[])),
    "journal": r.get("container-title", ""),
    "year": str(r.get("published",{}).get("date-parts",[[None]])[0][0] or ""),
    "doi": r["DOI"],
} for r in records]
w = BibTexWriter()
open("refs.bib","w").write(w.write(db))
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| bibtexparser | Read/write BibTeX, normalize entries | `pip install bibtexparser` |
| pyzotero | Zotero API: collections, items, attachments, notes | `pip install pyzotero` |
| habanero | Crossref works, ContentNegotiation, DataCite | `pip install habanero` |
| citeproc-py | Render CSL-JSON with .csl style sheets | `pip install citeproc-py` |
| anystyle | Parse free-text references into CSL-JSON | `gem install anystyle` or `pip install anystyle` |
| requests | DOI resolution and ContentNegotiation | `pip install requests` |
| rapidfuzz | Fuzzy-title dedup of merged libraries | `pip install rapidfuzz` |
| CSL style repository | 10,000+ journal styles (Zotero styles) | https://www.zotero.org/styles |
| Mendeley (reference-only) | GUI-only now (public API retired) | desktop client |
| ORCID public API | Author disambiguation by ORCID iD | https://api.orcid.org |
| BibTeX-tidy | Format and sort .bib files | `npm i -g bibtex-tidy` |
| JabRef | Cross-platform BibTeX editor (GUI) | https://www.jabref.org |

## References

- Zotero Web API v3 documentation: https://www.zotero.org/support/dev/web_api/v3
- pyzotero documentation: https://pyzotero.readthedocs.io/
- Crossref REST API: https://api.crossref.org/swagger-ui/
- Crossref ContentNegotiation: https://citation.crosscite.org/docs.html
- Citation Style Language specification: https://docs.citationstyles.org/
- CSL style repository (Zotero styles): https://www.zotero.org/styles
- anystyle CLI reference: https://anystyle.io/
- ORCID public API: https://info.orcid.org/documentation/api-tutorials/

## Ethics & safety

- **Citation accuracy is a moral obligation.** Always verify a DOI
  resolves to the work you intend; do not cite by memory or guess.
- **No citation cartels.** Never agree to reciprocal or coerced citation;
  flag suspected citation manipulation to editors.
- **Honest attribution.** Capture every author, use ORCID where available,
  and respect the CRediT taxonomy for contributor roles.
- **Originality.** Citing a source does not license you to copy its text
  verbatim without quotes; paraphrase and attribute.
- **Self-citation transparency.** Disclose self-citations in cover letters
  and conflict-of-interest statements.
- **Author name disambiguation.** Use ORCID iDs in CSL-JSON; never invent
  author initials to "fit" a style.
- **Data sharing.** When you submit the manuscript, share the underlying
  `.bib`/CSL-JSON file under a permissive license so reviewers and future
  readers can audit your reference list.
- **No metadata fabrication.** If a field is unknown, leave it blank
  rather than inventing volume/issue/page numbers.

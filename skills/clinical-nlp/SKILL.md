---
name: clinical-nlp
description: Clinical and biomedical natural-language processing pipeline covering de-identification with scrubadub and Microsoft Presidio, medical named-entity recognition with MedSpaCy and scispaCy, concept normalization to UMLS/MetaMap concepts and SNOMED-CT/ICD-10 codes, relation extraction (drug-disease, device complication), ClinicalBERT fine-tuning, RADLEX concepts for radiology reports, and FHIR NLP integration. Use this skill whenever the user asks about de-identification (PHI/HIPAA), medical NER, MedSpaCy, scispaCy, ClinicalBERT, UMLS, MetaMap, SNOMED-CT, ICD-10 coding, RADLEX, or NLP on clinical notes. Trigger keywords include PHI, HIPAA, scrubadub, Presidio, MedSpaCy, scispaCy, ClinicalBERT, Bio_ClinicalBERT, UMLS, MetaMap, SNOMED-CT, ICD-10, RADLEX, de-identification.
license: MIT
compatibility: Requires Python 3.10+ with spacy, scispacy, medspacy, scrubadub, presidio-analyzer, transformers, torch. Optional: medcat for UMLS concept normalization (requires UMLS license).
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Clinical & Medical Research
---

# Clinical NLP

## Overview

Clinical NLP extracts structured information from free-text clinical notes
(admission notes, discharge summaries, radiology reports, pathology reports)
while rigorously de-identifying protected health information (PHI). The
canonical stack is: (1) **de-identification** with `scrubadub` (regex-based)
and `Presidio` (learned NER + regex), (2) **medical NER** with MedSpaCy
(rule-based + scispaCy models), (3) **concept normalization** to UMLS CUIs
via MedCAT or MetaMap, with downstream SNOMED-CT and ICD-10 mappings, (4)
**relation extraction** for drug-disease and dose-frequency associations,
and (5) **ClinicalBERT** fine-tuning on masked notes for classification
tasks (mortality, length-of-stay, ICD coding).

This skill wires each tool into copy-pasteable workflows and emphasizes
the cardinal rule: **never output real PHI**.

## When to use this skill

- User asks to **de-identify** clinical notes (PHI, HIPAA).
- User wants **medical NER** (drugs, diseases, procedures, anatomy).
- User wants to **normalize concepts** to UMLS, SNOMED-CT, or ICD-10.
- User wants to fine-tune **ClinicalBERT** or **Bio_ClinicalBERT** on notes.
- User asks about **radiology report** parsing (findings, impressions,
  RADLEX).
- User mentions **scrubadub**, **Presidio**, **MedSpaCy**, **scispaCy**,
  **MetaMap**, **MedCAT**, **UMLS**, **SNOMED-CT**, **ICD-10**, **RADLEX**.
- Skip for: clinical trial design and statistical analysis (use
  `clinical-research`), medical-image analysis (use `medical-imaging`),
  general epidemiology (use `epidemiology`).

## Prerequisites

- Python 3.10+ (3.11 recommended; PyTorch 2.x for transformer workflows).
- System tools: Java 11+ if using the MetaMap server; UMLS Metathesaurus
  download (license required for full concept normalization).
- Python packages:

```bash
pip install spacy scispacy medspacy scrubadub presidio-analyzer \
            presidio-anonymizer transformers torch
pip install https://github.com/allenai/scispacy/releases/download/...
# (e.g. en_core_sci_sm, en_core_sci_md, en_ner_bc5cdr_md)
# Optional: medcat (requires UMLS license), metamap-tagger
```

- Note: scispaCy models are ~500MB; the install URL pattern is documented
  at https://allenai.github.io/scispacy/.

## Core workflows

### De-identification with scrubadub and Presidio

Strip PHI from a discharge summary.

```python
import scrubadub, scrubadub_filters
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.predefined_recognizers import SpacyRecognizer

text = """Patient John Doe, MRN 12345, born 1962-03-04, presented on
2024-05-12. Lives at 100 Main St, Springfield, IL 62704.
Phone 217-555-0143. Email j.doe@example.com."""

# scrubadub default classifiers + custom filters
scrubber = scrubadub.Scrubber()
scrubber.add_detector(scrubadub.detectors.DateDetector)
scrubber.add_detector(scrubadub.detectors.EmailDetector)
print(scrubber.clean(text))

# Presidio (learned NER + regex)
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()
results = analyzer.analyze(text=text, language="en",
    entities=["PERSON", "DATE_TIME", "PHONE_NUMBER", "EMAIL_ADDRESS",
              "US_SSN", "ADDRESS"])
print(anonymizer.anonymize(text=text, analyzer_results=results).text)
```

### Medical NER with scispaCy and MedSpaCy

Extract chemicals, diseases, and procedures.

```python
import spacy
nlp = spacy.load("en_ner_bc5cdr_md")  # chemicals + diseases
doc = nlp("Patient started on metformin 500 mg BID for type 2 diabetes; "
          "followed up for chronic kidney disease and hypertension.")
for ent in doc.ents:
    print(f"{ent.label_:15s} {ent.text}")

# MedSpaCy pipeline + clinical sectionizer
import medspacy
nlp2 = medspacy.load()
nlp2.add_pipe("medspacy_sectionizer")
doc2 = nlp2("HPI: 65 yo M with chest pain. Assessment: NSTEMI. Plan: ASA "
            "81 mg, Atorvastatin 40 mg, angiography.")
for sec in doc2._.sections:
    print(f"[{sec.category}] {sec.text[:60]}...")
```

### Concept normalization to UMLS CUIs with MedCAT

Map a recognized disease span to a UMLS Concept Unique Identifier.

```python
from medcat.cat import CAT
# Load a pre-trained MedCAT pack (e.g. medmen_wtoken_2021_2024)
cat = CAT.load_model_pack("/path/to/medcat_pack")
text = "Patient has Type 2 diabetes mellitus and stage III CKD."
ents = cat.get_entities(text)["entities"]
for eid, ent in ents.items():
    print(f"{ent['source_value']:35s} -> CUI {ent['cui']} "
          f"({ent['pretty_name']}, conf {ent['confidence']:.2f})")
```

### ICD-10 and SNOMED-CT mapping

Map a list of normalized concepts to billing codes.

```python
import pandas as pd
# Bridge from CUI -> ICD10/SNOMED via UMLS MRCONSO.RRF
mrconso_cols = ["CUI", "LAT", "SAB", "TTY", "CODE", "STR"]
mrconso = pd.read_csv("MRCONSO.RRF", sep="|", header=None,
                     usecols=range(18), low_memory=False)
# Filter to ICD10CM (SAB=ICD10CM) and SNOMEDCT_US
for cui in ["C0011847", "C0011849"]:  # diabetes mellitus
    rows = mrconso[(mrconso[0] == cui) & (mrconso[2].isin(
        ["ICD10CM", "SNOMEDCT_US"]))]
    for _, r in rows.iterrows():
        print(cui, r[2], r[4], r[-1])
```

### ClinicalBERT fine-tuning for classification

Fine-tune Bio_ClinicalBERT for a 30-day readmission task.

```python
import torch
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          Trainer, TrainingArguments, DataCollatorWithPadding)
from datasets import Dataset

tok = AutoTokenizer.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
model = AutoModelForSequenceClassification.from_pretrained(
    "emilyalsentzer/Bio_ClinicalBERT", num_labels=2)

ds = Dataset.from_csv("discharge_with_labels.csv")  # note_text, label
ds = ds.map(lambda x: tok(x["note_text"], truncation=True, max_length=512),
            batched=True)
args = TrainingArguments(
    output_dir="./clinical_bert_readmit",
    per_device_train_batch_size=8, per_device_eval_batch_size=16,
    num_train_epochs=3, learning_rate=2e-5, weight_decay=0.01,
    evaluation_strategy="epoch", save_strategy="epoch",
    load_best_model_at_end=True, metric_for_best_model="roc_auc")
trainer = Trainer(model=model, args=args,
                  train_dataset=ds["train"], eval_dataset=ds["test"],
                  tokenizer=tok)
trainer.train()
```

### Relation extraction (drug-disease, dose)

Extract drug-disease and drug-dose-frequency triples from a discharge summary.

```python
import spacy, medspacy
from medspacy.ner import TargetRule
from medspacy.visualization import visualize_ent

nlp = medspacy.load()
nlp.get_pipe("medspacy_target_matcher").add([
    TargetRule("metformin", "DRUG", pattern="metformin"),
    TargetRule("diabetes", "DISEASE", pattern=r"diabetes(?:\s+mellitus)?"),
    TargetRule("500 mg", "DOSE", pattern=r"\d+\s*mg"),
    TargetRule("BID", "FREQUENCY", pattern="BID"),
])

text = "Patient on metformin 500 mg BID for type 2 diabetes."
doc = nlp(text)
drugs = [e for e in doc.ents if e.label_ == "DRUG"]
diseases = [e for e in doc.ents if e.label_ == "DISEASE"]
# Heuristic: link drug to nearest disease in same sentence
for d in drugs:
    target = min((dis for dis in diseases if dis.sent == d.sent),
                 key=lambda x: abs(x.start - d.start), default=None)
    print(f"{d.text} -- treats --> {target.text if target else 'N/A'}")
```

### Radiology report parsing with RADLEX

Parse a chest CT report and extract findings linked to RADLEX concepts.

```python
import spacy
nlp = spacy.load("en_core_sci_sm")  # generic biomedical NER
report = """FINDINGS: Right upper lobe nodule, 8 mm. No pleural effusion.
IMPRESSION: 8 mm RUL nodule. Recommend follow-up CT in 6 months."""
doc = nlp(report)
print([f"{e.text} ({e.label_})" for e in doc.ents])
# Map to RADLEX IDs (RL101, RL003, etc.) via a curated dictionary.
radlex = {"nodule": "RID39927", "pleural effusion": "RID29220"}
for sent in doc.sents:
    for term, rid in radlex.items():
        if term.lower() in sent.text.lower():
            print(f"{term} -> RADLEX {rid}")
```

### FHIR NLP integration

Push de-identified NLP findings as FHIR Observation resources.

```python
from fhir.resources.observation import Observation
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding

obs = Observation(
    **{
        "status": "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "laboratory"}]}],
        "code": {"coding": [{
            "system": "http://snomed.info/sct",
            "code": "44054006", "display": "Type 2 diabetes mellitus"}]},
        "valueString": "Type 2 diabetes noted in discharge summary",
        "subject": {"reference": "Patient/deid-001"},
    }
)
print(obs.json())
```

## Best practices

- De-identify **before** any NER or model inference; never let PHI enter
  the model forward pass.
- Use **two de-identification systems** in series (scrubadub regex +
  Presidio learned NER) - one alone misses ~5-10% of PHI per published
  evaluations.
- For **MedSpaCy** pipelines, prefer `medspacy.load()` over `spacy.load()`
  - it bundles the sectionizer, target matcher, and negation detection.
- Evaluate NER with **strict span overlap** (gold span = predicted span),
  not partial overlap; clinical NER is held to a stricter bar than open
  domain.
- Fine-tune **Bio_ClinicalBERT**, not vanilla BERT - the pretraining corpus
  (MIMIC-III discharge summaries) matters.
- Use **Longformer-based clinical models** (`allenai/longformer-clinical`)
  for notes > 512 tokens; truncation loses discharge diagnoses.
- For ICD coding, train a **multi-label** model with positive-class
  weights; ICD coding is highly imbalanced.
- Validate UMLS mappings on a held-out sample; MedCAT has 80-90% precision
  on common concepts but can drop on rare diseases.
- Document the **scispaCy model version** in any pipeline; bc5cdr_md and
  biocreative models differ in label set.
- Honor **HIPAA** and your institution's IRB; if PHI is needed for
  downstream ML, route through a Trusted Research Environment (TRE) with
  audit logging.

## Common pitfalls

- Trusting Presidio's default recognizers without adding a custom
  recognizer for **medical-record numbers** (MRN) and **device serial
  numbers** - they look like random alphanumeric strings and slip through.
- Letting ClinicalBERT see PHI during fine-tuning; the model **memorizes**
  PHI from MIMIC-style notes and can emit it later.
- Truncating long discharge summaries; if the patient's diagnosis is in
  the Assessment section after the 512-token cutoff, the model loses it.
- Mixing UMLS CUI versions across runs; the CUI namespace changes between
  Metathesaurus releases.
- Forgetting **negation detection** ("no evidence of pneumonia") - raw
  NER flags "pneumonia" as positive; ConText / negspacy is essential.
- Reporting **de-identified** text as fully safe - residual re-ID risk
  remains (rare diseases + small geographic area + age + occupation).
- Treating **MetaMap** as ground truth; it has well-known precision/recall
  tradeoffs - use it as a baseline and spot-check.
- Confusing ICD-10-CM (US clinical modification) with ICD-10-PCS
  (procedures) or WHO ICD-10 - they have different code sets.

## Worked example

Goal: de-identify, run medical NER, normalize concepts to UMLS, and emit
FHIR Observations for a stack of discharge summaries.

```python
import pandas as pd, json
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
import medspacy
from fhir.resources.observation import Observation

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()
nlp = medspacy.load()
nlp.add_pipe("medspacy_sectionizer")

notes = pd.read_csv("discharge_notes.csv")  # text, note_id
observations = []
for _, row in notes.iterrows():
    text = row["text"]
    res = analyzer.analyze(text=text, language="en", entities=[
        "PERSON", "DATE_TIME", "PHONE_NUMBER", "EMAIL_ADDRESS",
        "US_SSN", "ADDRESS"])
    deid = anonymizer.anonymize(text=text,
                                analyzer_results=res).text
    doc = nlp(deid)
    for ent in doc.ents:
        if ent.label_ in ("DISEASE", "CHEMICAL", "PROCEDURE"):
            obs = Observation(
                status="final",
                code={"coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "TBD",  # map via UMLS in production
                    "display": ent.text}]},
                valueString=ent.text,
                subject={"reference": f"Patient/deid-{row['note_id']}"},
            )
            observations.append(json.loads(obs.json()))
print(f"{len(observations)} observations extracted")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| scrubadub | Regex-based de-identification | `pip install scrubadub` |
| Presidio | Learned NER + regex de-identification | `pip install presidio-analyzer presidio-anonymizer` |
| scispaCy | Biomedical NER models (bc5cdr, biocreative) | https://allenai.github.io/scispacy/ |
| MedSpaCy | Clinical NLP pipeline (sections, negation) | `pip install medspacy` |
| MedCAT | UMLS concept normalization | `pip install medcat` (UMLS license required) |
| MetaMap | NLM's concept mapping server (Java) | https://metamap.nlm.nih.gov/ |
| ClinicalBERT | Clinical-domain BERT models | https://huggingface.co/emilyalsentzer/Bio_ClinicalBERT |
| transformers | Fine-tuning ClinicalBERT, BioGPT | `pip install transformers` |
| fhir.resources | FHIR R4 model construction | `pip install fhir.resources` |
| UMLS Metathesaurus | Concept crosswalks (SNOMED, ICD, RxNorm) | https://www.nlm.nih.gov/research/umls/ |
| RADLEX | Radiology lexicon (RSNA) | https://www.rsna.org/RadLex.aspx |

## References

- Presidio documentation: https://microsoft.github.io/presidio/
- scispaCy paper: https://doi.org/10.18653/v1/W19-5019
- MedSpaCy: https://github.com/medspacy/medspacy
- MedCAT paper: https://doi.org/10.1016/j.jbi.2021.103846
- ClinicalBERT paper: https://doi.org/10.1088/1361-6579/ab41ae
- Bio_ClinicalBERT model card: https://huggingface.co/emilyalsentzer/Bio_ClinicalBERT
- UMLS reference: https://www.nlm.nih.gov/research/umls/
- FHIR Clinical reasoning (CDS Hooks): https://hl7.org/fhir/clinicalreasoning/

## Ethics & safety

- **Never output real PHI** to the user, log files, or external services.
  Always run de-identification first; if PHI appears in model output, the
  pipeline has failed and must be re-engineered.
- De-identified data still carries **residual re-identification risk**;
  expert determination under HIPAA is the gold standard, Safe Harbor is
  the floor. Disclose the method used in any data release.
- Clinical NLP findings are **research signals** not diagnoses - never
  communicate findings to patients or clinicians outside the study team
  or a validated clinical decision-support pathway cleared by the FDA /
  IRB.
- UMLS Metathesaurus usage requires acceptance of the **UMLS Metathesaurus
  License**; do not redistribute UMLS content outside the licensed scope.
- SNOMED-CT has country-specific licensing (e.g. SNOMED-CT US has NLM
  licensing; the UK extension requires TRS licensing). Verify before
  redistribution.
- For MIMIC-III/IV note corpora, follow the PhysioNet credentialed user
  agreement; do not share derived datasets outside the agreement.
- If a clinical-decision-support system is intended for patient care, it
  is **Software as a Medical Device** and requires FDA clearance before
  deployment. Treat all model outputs as research until cleared.
- When fine-tuning ClinicalBERT, document the training corpus, note any
  PHI exposure during training, and follow institutional policy on
  model release (some IRBs prohibit redistribution of models trained on
  identifiable data).

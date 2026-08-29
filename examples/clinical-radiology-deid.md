# Example: de-identify radiology reports and extract findings

**Skills activated:** `clinical-nlp`, `medical-imaging`

## The prompt

> I have 5,000 free-text radiology reports (CT abdomen/pelvis). De-identify them with Presidio + scispaCy, extract findings with MedSpaCy, map to UMLS/SNOMED-CT, and output FHIR `DocumentReference` resources. Never echo real PHI back to me — show only synthetic examples.

## What the agent does

`clinical-nlp` activates on `Presidio`, `scispaCy`, `MedSpaCy`, `UMLS`, `SNOMED-CT`, `FHIR`; `medical-imaging` for the modality context (CT abdomen/pelvis).

### 1. De-identify with Presidio

```python
# pip install presidio-analyzer presidio-anonymizer spacy
# python -m spacy download en_core_web_lg
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()
# add a custom radiology recognizer for accession numbers / case IDs

def deidentify(text):
    results = analyzer.analyze(text=text, language="en",
                              entities=["PERSON","LOCATION","DATE_TIME","PHONE_NUMBER",
                                        "EMAIL_ADDRESS","US_SSN","INJURY","MEDICAL_LICENSE"])
    return anonymizer.anonymize(text=text, analyzer_results=results).text
```

### 2. Extract findings with MedSpaCy

```python
# pip install medspacy
import medspacy
nlp = medspacy.load()
# medspacy ships target_matchers, section detection, assertion + negation
docs = list(nlp.pipe(deidentified_reports))
for d in docs[:1]:
    for ent in d.ents:
        print(ent.text, ent.label_, ent._.is_negated, ent._.section.category)
```

### 3. Map to UMLS/SNOMED-CT

```python
# Use scispaCy's linker for UMLS CUIs
# pip install scispacy
# pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/link_v2023-01-30/en_core_sci_lg-0.5.3.tar.gz
import spacy
nlp = spacy.load("en_core_sci_lg")
nlp.add_pipe("scispacy_linker",
             config={"linker_name": "umls", "max_entities_per_mention": 1,
                     "threshold": 0.85, "filter_for_definitions": True})
```

### 4. Output FHIR DocumentReference resources

```python
# pip install fhir.resources
import json
from fhir.resources.documentreference import DocumentReference
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding

def to_fhir(report_id, modality, content_html, findings):
    return DocumentReference(
        status="current",
        type=CodeableConcept(coding=[Coding(system="http://loinc.org", code="18748-4")]),
        content=[{"attachment": {"contentType": "text/html", "data": content_html}}],
        context={"related": [{"reference": f"Observation/{f['id']}"} for f in findings]},
    ).model_dump()
```

## Pitfalls the skill surfaces

- Presidio's default recognizers miss radiology-specific patterns (accession numbers, "Room 4A"); add custom recognizers.
- "No evidence of X" is a *negated* finding — MedSpaCy's assertion module handles this; naive NER will mislabel negatives as present.
- Never echo the original report text back to the user (or to the LLM's own context). Operate on the de-identified version only and show synthetic examples.
- FHIR resources need a real `Patient` reference in production; for the pipeline skeleton use a placeholder and note the integration step.

## Ethics & safety

Even de-identified text is sensitive — it can still be re-identified in combination with other data. Treat the output with the same care as the input. Never paste real reports into a hosted assistant; use a local-only pipeline for real PHI.

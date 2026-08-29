---
name: lab-automation
description: Automate wet-lab and bench workflows with Opentrons protocols, plate-reader output parsers (Tecan, BMG), LIMS/ELN APIs, and lab-data pipelines that land in Parquet with full provenance. Use when controlling liquid handlers, scheduling experiments, parsing instrument exports, or integrating a LIMS.
license: MIT
compatibility: Requires Python 3.10+ with opentrons, pandas, pyarrow, requests. Optional: labman, structlog, s3fs for cloud staging.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Lab & Automation
---

# Lab Automation

## Overview

Modern wet labs combine robotic liquid handlers, plate readers, automated
sample tracking, and a LIMS/ELN. This skill covers the canonical open-source
stack for lab automation: the Opentrons Protocol API for liquid handlers,
parsers for plate-reader exports (Tecan, BMG), Labguru/SampleSeer LIMS APIs,
scheduling with labman, and the data pipeline that lands clean Parquet
files with provenance metadata. The unifying principle is: every sample has
a unique ID, every action is logged, and every readout lands in a
queryable table within minutes.

## When to use this skill

- You are writing a protocol for an Opentrons robot.
- You need to convert plate-reader CSV/XML exports into tidy tables.
- You are building a LIMS integration (Samples -> ELN -> storage).
- You need to schedule multi-day cell-culture + assay workflows.
- You want to ship clean Parquet + a manifest to a downstream analysis
  pipeline.

## Prerequisites

- Python 3.10+
- Core: `opentrons` (robot API), `pandas`, `pyarrow`, `requests`,
  `pyyaml`, `structlog`
- Optional: `labman`, `s3fs`, `boto3`, `pyserial` (for custom hardware)
- System: an Opentrons OT-2/Flex running Protocol API v2.x; or simulation
  only with `opentrons_simulate`
- pip install:
  ```bash
  pip install opentrons pandas pyarrow requests pyyaml structlog
  pip install s3fs boto3
  ```

## Core workflows

### 1. Opentrons liquid handler protocol

```python
# transfer.py — Opentrons Protocol API v2
metadata = {"apiLevel": "2.20", "author": "Lab X"}

def run(protocol):
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", 1)
    src = protocol.load_labware("nest_12_reservoir_15ml", 2)
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", 3)
    p300 = protocol.load_instrument("p300_single", "right", tip_racks=[tiprack])

    p300.transfer(50, src["A1"], plate.wells_by_name(), mix_after=(2, 50),
                  new_tip="always", blow_out=True, blowout_location="source well")
```

Simulate before scheduling on the robot: `opentrons_simulate transfer.py`.

### 2. Parse plate-reader output (Tecan/BMG)

```python
import pandas as pd
from pathlib import Path

def parse_tecan_xlsx(path: str) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Result", header=None, engine="openpyxl")
    # Detect the well/OD layout block
    block = raw.iloc[5:13, 1:13]   # 8 rows x 12 cols
    block.columns = [f"{chr(65+r)}{c+1}" for r in range(8) for c in range(12)]
    long = block.stack().reset_index()
    long.columns = ["row", "col", "value"]
    long["well"] = long["row"] + long["col"].astype(str)
    return long[["well", "value"]]

df = parse_tecan_xlsx("run_2024-06-01.xlsx")
df["plate_id"] = Path("run_2024-06-01.xlsx").stem
df["acquired_at"] = pd.Timestamp.utcnow()
```

### 3. LIMS API integration (Labguru example)

```python
import requests, os

BASE = "https://your_lab.labguru.com/api/v1"
TOKEN = os.environ["LABGURU_TOKEN"]

def list_samples(project_id: int) -> list[dict]:
    r = requests.get(f"{BASE}/samples.json",
                     params={"token": TOKEN,
                             "project_id": project_id},
                     timeout=30)
    r.raise_for_status()
    return r.json()["samples"]

def create_sample(name: str, project_id: int) -> dict:
    r = requests.post(f"{BASE}/samples.json",
                      params={"token": TOKEN},
                      json={"sample": {"name": name, "project_id": project_id}},
                      timeout=30)
    r.raise_for_status()
    return r.json()["sample"]
```

### 4. Schedule experiments with labman

```python
# Schedule a 5-day assay run
import datetime as dt

schedule = [
    {"day": 0,  "task": "seed cells",   "duration_h": 1, "robot": "OT-2-A"},
    {"day": 1,  "task": "treat",        "duration_h": 2, "robot": "OT-2-B"},
    {"day": 3,  "task": "fix",          "duration_h": 1, "robot": "OT-2-A"},
    {"day": 4,  "task": "read plate",   "duration_h": 1, "robot": "Tecan-Spark"},
]
for s in schedule:
    s["start"] = dt.date(2024, 6, 1) + dt.timedelta(days=s["day"])

import json
print(json.dumps(schedule, indent=2, default=str))
```

### 5. CSV -> Parquet lab data pipeline

```python
import pandas as pd, json, hashlib, pyarrow.parquet as pq
from pathlib import Path

def ingest_run(run_dir: str, manifest: dict) -> None:
    p = Path(run_dir)
    plate_files = sorted(p.glob("*.xlsx"))
    frames = []
    for f in plate_files:
        df = pd.read_excel(f, sheet_name="Result", engine="openpyxl")
        df = df.melt(id_vars=["well"], var_name="channel", value_name="signal")
        df["source_file"] = f.name
        df["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out["manifest"] = json.dumps(manifest)
    out["ingested_at"] = pd.Timestamp.utcnow()
    pq.write_table(
        table=pd.DataFrame(out).convert_dtypes().to_arrow(),
        where=p / "clean.parquet",
        compression="zstd",
    )
```

## Best practices

- Use one operator-wide `manifest.json` per run capturing operator, robot
  IDs, tip lot, reagent lot, software version, and timestamp.
- Always run `opentrons_simulate` in CI before deploying to a physical
  robot; never deploy un-simulated protocols.
- Treat labware definitions as code; pin labware definitions to a fork of
  the Opentrons labware repo and never edit in place.
- Sample IDs are immutable; if you must rename, link old to new in the LIMS.
- Set a single source of truth for timestamps: UTC, ISO-8601, with offset.
- Never trust the plate-reader's auto-export; write your own parser that
  validates rows=8, cols=12 and rejects surprises.
- Land instrument output in Parquet with `zstd` compression and a manifest
  column; this pays back forever when joining runs downstream.
- Keep the lab LIMS API token in a secret manager (Vault, AWS Secrets
  Manager); never commit it.
- Log every API call to the LIMS with `structlog` and a request ID; this is
  the only way to reconcile discrepancies.
- Back up freezer inventory nightly; cold-storage samples have no version
  control in the LIMS by default.

## Common pitfalls

- Hardcoding labware offsets (`plate["A1"]` x/y in mm) that break when the
  labware vendor ships a new revision.
- Plate-reader exports that use empty rows as separators break the
  naive `pd.read_excel`; use `header=None` and slice manually.
- LIMS tokens embedded in notebooks get pushed to git; rotate immediately
  if exposed.
- Mixing local time and UTC in schedules double-counts wells; pick UTC
  and convert at display time.
- Opentrons protocols that read tips as a dict crash silently if a tip is
  missing; check `tip_racks` integrity at the start of `run`.
- Storing raw Excel in Parquet without the original bytes means lossy
  re-reads; keep the raw files alongside Parquet with SHA-256 manifest.
- Forgetting to mark the run "complete" in the LIMS leaves downstream
  pipelines waiting; add a `mark_complete` step at the end of the script.
- Pipette calibration drift over months; record `pipette_id` and
  `calibration_date` in every manifest.

## Worked example

A complete run: schedule a 3-day assay, run an Opentrons transfer, read the
plate, ingest the export into Parquet, register the run in the LIMS.

```python
# 1. Opentrons protocol (simulated locally first)
# transfer.py — see Core workflow 1, save to protocols/transfer.py
# Validate:
#   $ opentrons_simulate protocols/transfer.py

# 2. Read plate (assumed already executed on Tecan Spark)
import pandas as pd, hashlib, json, pyarrow.parquet as pq
from pathlib import Path
import structlog

log = structlog.get_logger()
run_dir = Path("runs/2024-06-01")
manifest = {
    "operator": "jdoe", "robot": "OT-2-A", "plate_reader": "Tecan-Spark",
    "reagent_lot": "LOT-2024-05-12", "software_version": "v2.20",
}

def ingest(run_dir: Path, manifest: dict) -> Path:
    dfs = []
    for f in sorted(run_dir.glob("*.xlsx")):
        df = pd.read_excel(f, sheet_name="Result", engine="openpyxl")
        df = df.melt(id_vars=["well"], var_name="channel", value_name="signal")
        df["source_file"] = f.name
        df["sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
        dfs.append(df)
    out = pd.concat(dfs, ignore_index=True)
    out["manifest"] = json.dumps(manifest)
    out["ingested_at"] = pd.Timestamp.utcnow()
    parq = run_dir / "clean.parquet"
    out.to_parquet(parq, compression="zstd", index=False)
    log.info("ingest_complete", file=str(parq), rows=len(out))
    return parq

# 3. Register in LIMS
import requests, os
def register_in_lims(parq: Path, manifest: dict) -> int:
    r = requests.post(
        "https://your_lab.labguru.com/api/v1/samples.json",
        params={"token": os.environ["LABGURU_TOKEN"]},
        json={"sample": {"name": parq.stem,
                         "project_id": 42,
                         "description": json.dumps(manifest)}},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["sample"]["id"]

ingest(run_dir, manifest)
register_in_lims(run_dir / "clean.parquet", manifest)
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| Opentrons API | Liquid handler protocol engine | `pip install opentrons` |
| opentrons_simulate | Local protocol simulator | shipped with `opentrons` |
| pandas | Plate data wrangling | `pip install pandas` |
| openpyxl | Parse Tecan Excel exports | `pip install openpyxl` |
| pyarrow | Parquet writer | `pip install pyarrow` |
| structlog | Structured lab logs | `pip install structlog` |
| requests | LIMS HTTP client | `pip install requests` |
| labman | Wet-lab scheduling | install via conda |
| s3fs | Cloud staging of runs | `pip install s3fs` |
| boto3 | S3 / inventory push | `pip install boto3` |
| pyserial | Custom hardware control | `pip install pyserial` |
| pyyaml | Manifest I/O | `pip install pyyaml` |

## References

- Opentrons Protocol API docs: https://docs.opentrons.com/v2/
- Opentrons labware library: https://labware.opentrons.com/
- Labguru API: https://my.labguru.com/apidoc/
- Structlog docs: https://www.structlog.org/
- Pandas I/O docs: https://pandas.pydata.org/docs/user_guide/io.html
- Labman (open source): https://github.com/jdereus/labman
- Sample tracking with FreezerPro: https://www.freezerpro.com/
- FAIR for lab data: https://www.go-fair.org/fair-principles/

## Ethics & safety

- **Sample integrity:** never reuse a barcode across runs; rotate expired
  reagent lots and refuse to run protocols whose lots have expired.
- **Safety:** hard-pause robot motion if a tip is missing; do not silently
  skip wells.
- **Provenance:** every measurement must trace back to a sample ID,
  reagent lot, instrument ID, and operator ID.
- **Privacy:** LIMS records may contain patient-identifiable metadata; use
  role-based access and avoid PII in unencrypted Parquet on shared storage.
- **Auditability:** keep structured logs of every API call to the LIMS;
  these are the only source of truth when reconciling discrepancies.

# Example: Opentrons PCR prep + plate design

**Skills activated:** `lab-automation`, `experimental-design`

## The prompt

> I have a 96-well PCR prep: 8 samples × 3 replicates × 3 primer pairs + NTC, on an Opentrons Flex with a 96-channel pipette. Lay out the plate using a randomized block design (to avoid edge/column effects), generate the Opentrons protocol, and output a plate map CSV the LIMS can ingest. Total reaction volume 20 µL: 10 µL master mix, 1 µL template, 1 µL primers (10 µM each), 8 µL water.

## What the agent does

`lab-automation` activates on `Opentrons`, `labware`, `plate map`; `experimental-design` on `randomized block`, `replicates`.

### 1. Randomized block layout

```python
# pip install pyDOE2 pandas
import numpy as np, pandas as pd
rng = np.random.default_rng(1)
samples = [f"S{i}" for i in range(1, 9)]
primers = [f"P{i}" for i in range(1, 4)]
reps = 3
wells = [f"{r}{c:02d}" for r in "ABCDEFGH" for c in range(1, 13)]
# build the design matrix
treatments = [(s, p, r) for s in samples for p in primers for r in range(1, reps+1)]
# + 4 NTC = 8*3*3 + 4 = 76 wells; fill remaining with blanks
order = rng.permutation(len(treatments))
assignments = {wells[i]: treatments[order[i % len(treatments)]] for i in range(96)}
plate_map = pd.DataFrame([{"well": w, "sample": a[0], "primer": a[1], "rep": a[2]}
                          if a else {"well": w, "sample": "NTC", "primer":"-", "rep":0}
                          for w, a in assignments.items()])
plate_map.to_csv("plate_map.csv", index=False)
```

### 2. Opentrons protocol (Flex, 96-channel)

```python
# file: pcr_prep.py
from opentrons import protocol_api
metadata = {"apiLevel": "2.14"}

def run(protocol: protocol_api.ProtocolContext):
    tiprack = protocol.load_labware("opentrons_96_tiprack_300ul", "1")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "2")
    plate = protocol.load_labware("nest_96_wellplate_100ul_pcr_full_skirt", "3")
    pipette = protocol.load_instrument("flex_8channel_1000", "left", tip_racks=[tiprack])

    master_mix = reservoir["A1"]
    # add 10 uL master mix to every well, column by column with the 8-channel
    for col in plate.columns():
        pipette.pick_up_tip()
        pipette.aspirate(10 * 8, master_mix)   # 8 channels * 10 uL
        pipette.dispense(10 * 8, [plate.wells()[i] for i in col])
        pipette.drop_tip()
    # template + primers per the plate map (omitted for brevity)
```

### 3. LIMS-ready CSV

The `plate_map.csv` above is LIMS-ready — one row per well, columns for sample/primer/replicate. Pair it with a `samplesheet.csv` (sample metadata) and a `protocol.json` (run parameters) for full provenance.

## Pitfalls the skill surfaces

- Randomize, don't fill row-by-row — column/edge effects in thermocyclers are real and a randomized block design absorbs them.
- The 96-channel pipette aspirates 8 channels at once; for a 96-well dispense you iterate by column, aspirating `8 × volume` per column.
- Master mix first, template + primers last — keeps cross-contamination low and avoids pre-mixing primers before the polymerase is in the wells.
- Track tips: a fresh tip per column (or per well for high-stringency work). Reusing tips across samples is the single most common source of false positives in qPCR.

## Ethics & safety

Opentrons protocols are reference, not SOPs. Validate against your institution's qPCR SOP and run a no-template control on every plate. Wet-lab execution requires training, PPE, and proper waste handling.

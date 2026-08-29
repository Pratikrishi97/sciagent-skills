---
name: instrument-integration
description: Connect to scientific instruments over GPIB, USB, and TCP/IP with PyVISA and PyMeasure, capture data with nidaqmx, run measurement loops, and capture provenance metadata with python logging and structlog. Use when controlling a bench instrument, querying a SCPI identity, or building a measurement loop.
license: MIT
compatibility: Requires Python 3.10+ with pyvisa, pyvisa-py, pymeasure, nidaqmx. Optional: pyserial, structlog, h5py for direct streaming.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Lab & Automation
---

# Instrument Integration

## Overview

Connecting to bench instruments (oscilloscopes, sourcemeters, multimeters,
spectrometers, lock-ins) and data acquisition cards turns a laptop into a
lab controller. The canonical Python stack is PyVISA (VISA resource manager
+ SCPI over GPIB/USB/TCPIP), PyMeasure (measurement-loop orchestration), and
nidaqmx for National Instruments DAQ cards. Every measurement should run
inside a structured-log envelope (python `logging` + `structlog`) that
captures instrument IDs, serial numbers, timestamps, and a measurement
hash. This skill covers SCPI queries, async-friendly loops, metadata
capture, and clean teardown so that a crash mid-run leaves the instrument
in a known state.

## When to use this skill

- You are controlling an instrument over GPIB, USB, or TCP/IP from Python.
- You need to query an instrument's `*IDN?` SCPI identity.
- You are building a measurement loop (sweep + collect + plot).
- You need NI DAQmx for analog/digital I/O.
- You want logs that reconstruct who measured what with which hardware.

## Prerequisites

- Python 3.10+
- Core: `pyvisa`, `pyvisa-py` (pure-python backend; no NI-VISA needed),
  `pymeasure`, `nidaqmx`, `pyserial`
- Logging: `structlog`
- Optional: `h5py` (for live HDF5 writes), `pyqtgraph` (for live plots)
- System: for VISA hardware access, `pyvisa-py` is recommended; if using
  NI-VISA, install the NI-VISA runtime
- pip install:
  ```bash
  pip install pyvisa pyvisa-py pymeasure nidaqmx pyserial structlog
  pip install h5py pyqtgraph
  ```

## Core workflows

### 1. List resources and query identity

```python
import pyvisa

rm = pyvisa.ResourceManager("@py")  # use pyvisa-py backend
print(rm.list_resources())
# ('USB0::0x0957::0x0411::MY123456::0::INSTR', 'GPIB0::5::INSTR', ...)

with rm.open_resource("USB0::0x0957::0x0411::MY123456::0::INSTR") as inst:
    inst.timeout = 5000
    inst.read_termination = "\n"
    print(inst.query("*IDN?"))
    # -> 'Keysight,Model XYZ,MY123456,A.01.02'
    inst.write("*RST")  # reset to known state
```

### 2. SCPI sweep and capture

```python
import pyvisa, structlog
import numpy as np

log = structlog.get_logger().bind(instrument="kepco")
rm = pyvisa.ResourceManager("@py")

def sweep_iv(start=0.0, stop=1.0, n=11):
    with rm.open_resource("USB0::0x0957::0x0411::MY123456::0::INSTR") as inst:
        inst.read_termination = "\n"
        results = []
        for v in np.linspace(start, stop, n):
            inst.write(f"SOUR:VOLT {v}")
            measured = float(inst.query("MEAS:VOLT?"))
            current = float(inst.query("MEAS:CURR?"))
            log.info("point", set_v=float(v),
                     meas_v=measured, meas_i=current)
            results.append((v, measured, current))
        return np.array(results, dtype="f4")
```

### 3. PyMeasure measurement loop

```python
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.experiment import Procedure, Worker
from pymeasure.experiment.results import Results
from pymeasure.display import Plotter

class IVProcedure(Procedure):
    start = 0.0; stop = 1.0; npts = 11
    def execute(self):
        sm = Keithley2400("GPIB::24")
        sm.reset()
        for v in np.linspace(self.start, self.stop, self.npts):
            self.emit("progress", 100 * (v - self.start) / (self.stop - self.start))
            sm.apply_voltage(v)
            self.emit("v", v); self.emit("i", sm.current)

results = Results(IVProcedure(), "iv.csv")
worker = Worker(results)
worker.run()
```

### 4. NI DAQmx analog input

```python
import nidaqmx
from nidaqmx.constants import AcquisitionType

with nidaqmx.Task() as task:
    task.ai_channels.add_ai_voltage_chan("Dev1/ai0")
    task.timing.cfg_samp_clk_timing(rate=1000,
                                    sample_mode=AcquisitionType.FINITE,
                                    samps_per_chan=100)
    data = task.read(number_of_samples_per_channel=100)
    print(f"mean={sum(data)/len(data):.4f} V")
```

### 5. Structured logging + provenance

```python
import structlog, hashlib, json, datetime as dt
from pathlib import Path

log = structlog.get_logger().bind(
    run_id="run-2024-06-01",
    operator="jdoe",
    script_version="0.3.0",
)
log.info("start", timestamp=dt.datetime.utcnow().isoformat())

def write_hdf5_with_metadata(path, array, attrs):
    import h5py
    with h5py.File(path, "w") as f:
        d = f.create_dataset("signal", data=array, compression="gzip")
        d.attrs["instrument_id"] = "KEPCO-BITS-123456"
        d.attrs["firmware"] = "A.01.02"
        d.attrs["operator"] = "jdoe"
        d.attrs["started_at"] = dt.datetime.utcnow().isoformat()
        for k, v in attrs.items():
            d.attrs[k] = v
        f.attrs["provenance_sha256"] = hashlib.sha256(
            json.dumps(attrs, sort_keys=True).encode()
        ).hexdigest()
```

## Best practices

- Use `pyvisa-py` (`@py`) backend so the stack runs without the proprietary
  NI-VISA runtime; switch to `@ni` only if you need hardware-specific
  features.
- Always send `*RST` after opening an instrument so the start state is
  reproducible.
- Wrap instrument access in `with` blocks; the connection closes on exit.
- Prefer SCPI `query()` over `write()`+`read()` for round-trip commands.
- Set `read_termination` to the instrument's documented terminator (often
  `\n`); unconfigured reads hang on `timeout`.
- Log every setpoint/measurement as structured JSON to a file
  (`measurement.log`), not just stdout.
- Capture `*IDN?` and firmware version on connect and stash them as HDF5
  attrs; reviewers will ask.
- For NI-DAQ cards, set `AcquisitionType.FINITE` and a known sample rate;
  continuous acquisition needs an explicit buffer-polling thread.
- Use `pyserial` for any vendor that ships RS-232 (still common on
  lock-ins, gas controllers, and older spectrometers).
- Run any heavy compute (FFT, fitting) on a separate thread/process so the
  measurement loop never blocks on `inst.query`.

## Common pitfalls

- Calling `inst.read()` after `inst.write("MEAS:VOLT?")` instead of
  `query()`, leaving termination bytes in the buffer for the next call.
- Forgetting `read_termination` causes indefinite hangs on `query`.
- Opening multiple `ResourceManager` objects in parallel is safe with
  pyvisa-py, but with NI-VISA each open has a license cost.
- NI-DAQmx continuous mode without a polling loop drops samples silently;
  set `samps_per_chan` and read in chunks.
- Hardcoded GPIB addresses that differ per physical lab; read from a
  YAML config instead.
- Live plots in the main thread block the SCPI loop; use a separate
  matplotlib animation or pyqtgraph and a queue.
- Writing raw bytes to CSV loses precision; prefer HDF5 with `gzip`.
- Forgetting `*RST` on the same instrument that another script left in
  some weird mode yields impossible readings.
- ASRL/serial ports that don't close leak file descriptors; wrap them
  in `with` blocks.

## Worked example

A complete I-V sweep with metadata: open a Keithley 2400 over GPIB, sweep
0-1 V, log every point, write an HDF5 file with provenance, and restore
the instrument to a safe state.

```python
import pyvisa, structlog, numpy as np
import h5py, hashlib, json, datetime as dt

log = structlog.get_logger().bind(run_id="iv-2024-06-01", operator="jdoe")

def run_iv(gpib_addr=24, npts=11, out_path="iv_run.h5"):
    rm = pyvisa.ResourceManager("@py")
    addr = f"GPIB0::{gpib_addr}::INSTR"
    with rm.open_resource(addr) as sm:
        sm.read_termination = "\n"; sm.timeout = 5000
        idn = sm.query("*IDN?")
        log.info("connect", resource=addr, idn=idn)
        sm.write("*RST")
        sm.write(":SENS:FUNC 'CURR'")
        rows = []
        try:
            for v in np.linspace(0, 1.0, npts):
                sm.write(f":SOUR:VOLT {v}")
                measured_v = float(sm.query(":MEAS:VOLT?"))
                measured_i = float(sm.query(":MEAS:CURR?"))
                log.info("point", set_v=float(v),
                         meas_v=measured_v, meas_i=measured_i)
                rows.append((v, measured_v, measured_i))
            arr = np.array(rows, dtype="f4")
        finally:
            sm.write("*RST")  # safe-state teardown
    attrs = {"instrument_id": idn, "operator": "jdoe",
             "started_at": dt.datetime.utcnow().isoformat(),
             "npts": npts}
    with h5py.File(out_path, "w") as f:
        d = f.create_dataset("iv", data=arr, compression="gzip")
        for k, v in attrs.items():
            d.attrs[k] = v
        f.attrs["provenance_sha256"] = hashlib.sha256(
            json.dumps(attrs, sort_keys=True).encode()
        ).hexdigest()
    log.info("write_complete", file=out_path, rows=len(arr))

if __name__ == "__main__":
    run_iv()
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| pyvisa | VISA resource manager | `pip install pyvisa` |
| pyvisa-py | Pure-Python VISA backend | `pip install pyvisa-py` |
| pymeasure | Measurement loop framework | `pip install pymeasure` |
| nidaqmx | NI DAQmx API | `pip install nidaqmx` |
| pyserial | RS-232 instruments | `pip install pyserial` |
| structlog | Structured logging | `pip install structlog` |
| h5py | Provenance-rich data files | `pip install h5py` |
| pyqtgraph | Real-time plotting | `pip install pyqtgraph` |
| libtiepie | TiePie scopes/AWGs | `pip install libtiepie` |
| python-usbtmc | Pure-Python USBTMC | `pip install usbtmc` |
| click | CLI for measurement scripts | `pip install click` |

## References

- PyVISA tutorial: https://pyvisa.readthedocs.io/
- PyVISA-py backend: https://pyvisa-py.readthedocs.io/
- PyMeasure docs: https://pymeasure.readthedocs.io/
- NI-DAQmx Python: https://nidaqmx-python.readthedocs.io/
- SCPI spec (IVI Foundation): https://www.ivifoundation.org/
- structlog: https://www.structlog.org/
- h5py provenance pattern: https://docs.h5py.org/
- libtiepie docs: https://www.tiepie.com/en/libtiepie-sdk-python

## Ethics & safety

- **Instrument safety:** always teardown with `*RST` and set voltage/current
  to safe defaults in a `finally` block; unhandled exceptions can leave
  sources driving outputs.
- **Provenance:** log the `*IDN?` and firmware of every instrument in every
  run; reviewers must be able to verify which hardware produced which data.
- **Concurrency:** never call the same VISA resource from multiple threads
  without a lock; the underlying socket is not thread-safe.
- **Privacy:** avoid logging patient-identifiable sample labels in raw
  instrument logs.
- **Calibration:** record the instrument's last calibration date in the
  metadata; refuse to publish results from out-of-calibration instruments.

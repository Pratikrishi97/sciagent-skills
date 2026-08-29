---
name: scientific-data-management
description: Manage scientific data at scale with Parquet/Feather/HDF5/Zarr/netCDF, CF-compliant metadata, Intake and Frictionless catalogs, and S3-backed data lakes via s3fs/fsspec. Use when storing arrays or tables, designing a dataset schema, versioning data with DVC, or publishing to Dataverse/Zenodo.
license: MIT
compatibility: Requires Python 3.10+ with pandas, pyarrow, h5py, zarr, xarray, intake, frictionless, s3fs, fsspec.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Data & Visualization
---

# Scientific Data Management

## Overview

Scientific datasets are increasingly large (multi-TB), multi-dimensional, and
shared across labs. Choosing the right storage format dramatically affects
cost and reproducibility: CSV for 1M rows, Parquet/Feather for medium tabular,
HDF5 for hierarchical arrays, Zarr for cloud-native chunked arrays, and
netCDF/CF for gridded earth-system data. This skill covers format selection,
metadata conventions (CF, Dublin Core, schema.org Dataset), catalogs
(Intake, Frictionless), S3/cloud access (`s3fs`, `fsspec`), and versioning
with DVC. FAIR is the default goal: findable, accessible, interoperable,
reusable.

## When to use this skill

- You are choosing a file format for experimental or simulated data.
- You have arrays too big for memory and need chunked reads.
- You are publishing a dataset with a DOI and need CF/Dublin Core metadata.
- You need to assemble a data lake on S3 with a queryable catalog.
- You need to version datasets the way git versions code.

## Prerequisites

- Python 3.10+
- Core: `pandas`, `pyarrow`, `h5py`, `zarr`, `xarray`, `netcdf4`
- Catalogs: `intake`, `frictionless` (== `frictionless-py`)
- Cloud: `s3fs`, `fsspec`, `aiohttp`
- Versioning: `dvc`
- pip install:
  ```bash
  pip install pandas pyarrow h5py zarr xarray netcdf4 intake frictionless
  pip install s3fs fsspec dvc
  ```

## Core workflows

### 1. Format selection by use case

| Format | Use case | Notes |
|---|---|---|
| CSV | Small human-in-place data | wasteful at scale, no schema |
| Parquet | Medium/large tabular, columnar | default for query/analytics |
| Feather | Inter-process interchange | Arrow IPC, fast r/w |
| HDF5 | Hierarchical arrays + attrs | lab instruments, mat files |
| Zarr | Chunked, cloud-native N-D arrays | parallel writes, S3-friendly |
| netCDF | Gridded, CF-compliant | climate, ocean, remote sensing |
| N5 | Big-image / microscopy | Spark/HPC-friendly |

### 2. HDF5 with h5py (groups, attrs, chunking)

```python
import h5py, numpy as np

with h5py.File("experiment.h5", "w") as f:
    f.attrs["title"] = "Calibration run 2024-06-01"
    f.attrs["convention"] = "CF-1.10"
    g = f.create_group("trials/trial_01")
    arr = np.random.default_rng(0).normal(size=(1000, 1000))
    dset = g.create_dataset("signal", data=arr,
                            chunks=(100, 100),
                            compression="gzip", compression_opts=4,
                            shuffle=True)
    dset.attrs["units"] = "volts"
    dset.attrs["sample_rate_hz"] = 1000.0
    dset.attrs["long_name"] = "Photodiode signal"
```

### 3. Zarr for chunked, cloud-native arrays

```python
import zarr
import numpy as np

# Cloud store on S3 (anonymous read example)
store = zarr.storage.FSStore("s3://zarr-bucket/exp.zarr", anon=True)
root = zarr.open_group(store, mode="a")
root.attrs.update(convention="CF-1.10", title="Demo", history="2024-06-01")
arr = root.create_array("signal", shape=(10_000, 1_000), chunks=(1_000, 1_000),
                        dtype="f4", overwrite=True)
arr.attrs["units"] = "volts"
arr[0:1000, :] = np.random.default_rng(0).normal(size=(1000, 1000)).astype("f4")
```

### 4. CF-compliant netCDF with xarray

```python
import xarray as xr
import numpy as np, pandas as pd

temp = 15 + 8 * np.random.default_rng(0).normal(size=(12, 180, 360))
ds = xr.Dataset(
    {"temperature": (["time", "lat", "lon"], temp, {"units": "degC",
                                                     "long_name": "Surface temperature"})},
    coords={"time": pd.date_range("2024-01-01", periods=12, freq="MS"),
            "lat": np.linspace(-90, 90, 180), "lon": np.linspace(-180, 180, 360)},
    attrs={"title": "Synthetic monthly climatology",
           "Conventions": "CF-1.10",
           "institution": "Lab X"},
)
ds.to_netcdf("clim.nc", engine="netcdf4")
```

### 5. Data catalog with Intake and Frictionless

Intake catalog `catalog.yaml`:
```yaml
sources:
  trials:
    driver: parquet
    args:
      urlpath: s3://lab-bucket/trials.parquet
      storage_options:
        anon: true
    metadata:
      cf_conventions: CF-1.10
      doi: 10.5281/zenodo.1234567
```

Read:
```python
import intake
cat = intake.open_catalog("catalog.yaml")
df = cat.trials.read()
```

Frictionless descriptor:
```yaml
# dataset.yaml
name: trials
path: s3://lab-bucket/trials.parquet
format: parquet
schema:
  fields:
    - {name: trial_id, type: integer}
    - {name: timestamp, type: datetime}
    - {name: signal, type: number}
```
Validate: `frictionless validate dataset.yaml`.

## Best practices

- Pick the format by access pattern (column scans -> Parquet; random
  multi-D reads -> Zarr/HDF5).
- Always tag units in dataset attrs (`"units": "volts"`); never rely on
  the column name encoding units.
- Add a `Conventions` attr (`CF-1.10`) and a `history` line; reviewers
  scan for these first.
- Use chunk shapes that match your read pattern; chunk too small wastes
  index space, too large wastes I/O.
- Compress with `gzip`/`blosc`/`zstd`; modern Parquet defaults are good
  enough, do not hand-tune unless profiling.
- Version datasets with DVC alongside code; pin the S3 ETag or checksum in
  metadata.
- Publish catalogs to Intake-ESM or Frictionless; do not invent your own
  catalog YAML format.
- Archive to Zenodo or Dataverse with a DOI; add the DOI to the catalog
  metadata.
- Prefer Apache Arrow (`pyarrow`) over `fastparquet` for Parquet I/O;
  the upstream investment is significantly larger.
- Test reads from a fresh kernel before publishing; never publish a
  dataset you cannot re-open.

## Common pitfalls

- CSV for arrays over 1M rows balloons 3-5x the size of Parquet and loses
  types silently.
- HDF5 with default chunking on small datasets produces enormous files;
  set `chunks=None` for small arrays.
- Zarr stores that aren't compressed bloat 2-3x; pick a codec (`blosc`,
  `zstd`).
- netCDF files with `time` as `int32` seconds break CF; use `datetime64`
  or CF time units explicitly.
- Intake catalogs with anonymous S3 reads that depend on requester-pays
  buckets silently fail; set `requester_pays=True`.
- Frictionless validation passed locally but the published DOI points to a
  renamed file; always re-validate after upload.
- Forgetting `mode="w"` on `h5py.File` appends and can collide with
  existing datasets; use `mode="r+"` for safe reads/writes.
- Schema drift between Parquet writes breaks downstream pandas readers;
  pin `pyarrow` version in the environment.

## Worked example

End-to-end: write a CF-compliant netCDF of synthetic temperature, register
it in an Intake catalog, version it with DVC, and publish metadata to
Zenodo (DOI: 10.5281/zenodo.1234567).

```python
# Step 1: write CF-compliant netCDF (see Core workflow 4)
import xarray as xr, numpy as np, pandas as pd
temp = 15 + 8 * np.random.default_rng(0).normal(size=(12, 180, 360))
ds = xr.Dataset(
    {"temperature": (["time", "lat", "lon"], temp,
                     {"units": "degC", "long_name": "Surface temperature"})},
    coords={"time": pd.date_range("2024-01-01", periods=12, freq="MS"),
            "lat": np.linspace(-90, 90, 180), "lon": np.linspace(-180, 180, 360)},
    attrs={"Conventions": "CF-1.10",
           "title": "Synthetic monthly climatology",
           "institution": "Lab X",
           "source": "synthetic", "history": "2024-06-01 created by demo.py"})
ds.to_netcdf("data/clim.nc", engine="netcdf4")
```

```bash
# Step 2: version with DVC
dvc add data/clim.nc
git add data/clim.nc.dvc .gitignore
git commit -m "version clim.nc v1"

# Step 3: register in catalog
cat > catalog.yaml <<EOF
sources:
  climatology:
    driver: netcdf
    args:
      urlpath: data/clim.nc
    metadata:
      cf_conventions: CF-1.10
      doi: 10.5281/zenodo.1234567
EOF

# Step 4: publish to Zenodo (one-shot)
curl -H "Authorization: Bearer $ZENODO_TOKEN" \
  -F "metadata[title]=Synthetic climatology" \
  -F "metadata[upload_type]=dataset" \
  -F "metadata[license]=CC-BY-4.0" \
  -F "metadata[creators][0][name]=Lab, X" \
  -F "files[1]filedata=@data/clim.nc" \
  https://zenodo.org/api/deposit/depositions
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| pandas | Tabular I/O and ops | `pip install pandas` |
| pyarrow | Arrow / Parquet / Feather | `pip install pyarrow` |
| h5py | HDF5 read/write | `pip install h5py` |
| zarr | Chunked cloud-native arrays | `pip install zarr` |
| xarray | N-D labeled arrays | `pip install xarray` |
| netcdf4 | netCDF read/write | `pip install netcdf4` |
| intake | Data catalogs | `pip install intake` |
| frictionless | Dataset validation | `pip install frictionless` |
| s3fs | S3 filesystem for pandas/xarray | `pip install s3fs` |
| fsspec | Generic filesystem abstraction | `pip install fsspec` |
| dvc | Data version control | `pip install dvc` |
| zenodo_get | Fetch records by DOI | `pip install zenodo_get` |

## References

- pyarrow documentation: https://arrow.apache.org/docs/python/
- h5py user guide: https://docs.h5py.org/
- zarr tutorial: https://zarr.readthedocs.io/
- xarray docs: https://docs.xarray.dev/
- CF conventions: https://cfconventions.org/
- Intake-ESM catalog spec: https://intake-esm.readthedocs.io/
- Frictionless framework: https://framework.frictionlessdata.io/
- FAIR principles: https://www.go-fair.org/fair-principles/

## Ethics & safety

- **Provenance:** every dataset must record its creator, license, history,
  and source; never publish un-attributed data.
- **Privacy:** strip PII before archival; aggregate or encrypt when needed.
- **Integrity:** checksum-published data; archive the SHA-256 alongside the
  DOI and the catalog entry.
- **Interoperability:** prefer open, non-proprietary formats (Parquet,
  netCDF, Zarr) over vendor formats; ensure downstream tooling exists.
- **Equity:** do not put research datasets behind commercial paywalls; use
  CC-BY-4.0 or CC0 for data and MIT/BSD for code.

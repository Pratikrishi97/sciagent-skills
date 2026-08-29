---
name: remote-sensing
description: Satellite imagery analysis using rasterio, GDAL, satpy, sentinelhub, pystac-client, torchgeo, and s2cloudless. Use when reading Sentinel-2, Landsat 8/9, or MODIS imagery, computing spectral indices like NDVI and NBR, cloud masking with QA bands or s2cloudless, accessing imagery via STAC catalogs, training deep learning models on imagery with torchgeo, doing time-series compositing, or processing SAR data.
license: MIT
compatibility: Requires Python 3.10+ with rasterio, numpy, matplotlib, shapely. Optional extras include satpy, sentinelhub, pystac-client, stackstac, torchgeo, s2cloudless, rioxarray, planetary-computer.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Geospatial & Earth Science
---

# Remote Sensing

## Overview

Remote sensing is the science of measuring Earth surface properties from above — satellites (Landsat 8/9, Sentinel-1/2/3/5P, MODIS, NOAA-20, PlanetScope), aircraft, and drones. The Python stack is converging on a small set of canonical tools: **rasterio + GDAL** for low-level raster I/O, **pystac-client + stackstac** for discovering and stacking imagery via STAC catalogs, **satpy** for satellite-format readers (Sentinel-2 L1C/L2A, MODIS, VIIRS), **sentinelhub** for cloud API access, **s2cloudless** for cloud masking, **rioxarray** for labeled array workflows, and **torchgeo** for deep learning on imagery.

This skill covers the canonical workflows: raster I/O with rasterio + GDAL, Sentinel-2 and Landsat access via sentinelhub or satpy, spectral indices (NDVI, NBR, NDSI), cloud masking (QA band, s2cloudless), STAC catalog access with pystac-client, ML on imagery with torchgeo, time-series compositing, and SAR processing basics. Data sources include USGS Landsat, ESA Sentinel Hub, and Microsoft Planetary Computer.

## When to use this skill

- You are reading GeoTIFF imagery and computing band math (NDVI, NBR, NDWI).
- You need Sentinel-2 L1C/L2A or Landsat C2 L2 imagery, either locally or from a cloud API.
- You need to mask clouds using the QA band or s2cloudless ML-based detector.
- You are discovering imagery via STAC catalogs (Microsoft Planetary Computer, Element 84, USGS).
- You want to train or fine-tune a CNN on imagery with torchgeo (e.g., BigEarthNet, EuroSAT, Sen12MS).
- You want to build cloud-free seasonal composites from many overlapping scenes.
- You are processing SAR (Sentinel-1 GRD) — calibration, speckle filtering, thresholding.
- You want to track phenology, snow cover, or burned area from multi-temporal imagery.

## Prerequisites

- Python 3.10+
- rasterio >= 1.3, numpy >= 1.24, matplotlib >= 3.7, shapely >= 2.0

```bash
pip install rasterio numpy matplotlib shapely
# Optional
pip install pystac-client stackstac satpy sentinelhub s2cloudless rioxarray torchgeo planetary-computer
```

GDAL must be installed system-wide or via conda: `conda install -c conda-forge gdal`.

## Core workflows

### Raster I/O and spectral indices with rasterio

```python
import rasterio
import numpy as np

with rasterio.open("s2_l2a.tif") as src:
    profile = src.profile
    blue, green, red, nir, swir = (src.read(i).astype("float32") for i in (1, 2, 3, 8, 11))
    # Each band's geotransform, CRS, and shape are inherited

def safe_nd(a, b, eps=1e-9):
    return (a - b) / (a + b + eps)

ndvi = safe_nd(nir, red)
nbr  = safe_nd(nir, swir)
ndwi = safe_nd(green, nir)

# Write NDVI as a new GeoTIFF with the same georeferencing
out = profile.copy()
out.update(count=1, dtype="float32")
with rasterio.open("ndvi.tif", "w", **out) as dst:
    dst.write(ndvi.astype("float32"), 1)
```

### Sentinel-2 access via sentinelhub and STAC catalogs

```python
from sentinelhub import SHConfig, BBox, CRS, SentinelHubRequest, MimeType, DataCollection
import datetime as dt

config = SHConfig()
config.sh_client_id = "YOUR_ID"; config.sh_client_secret = "YOUR_SECRET"

bbox = BBox(bbox=[-122.6, 37.7, -122.4, 37.8], crs=CRS.WGS84)
request = SentinelHubRequest(
    evalscript="""
        function setup() {return {input: [B02,B03,B04,B08], output: {bands: 4, sampleType: "FLOAT32"};}}
        function evaluatePixel(s) {return [s.B02, s.B03, s.B04, s.B08];}
    """,
    input_data=[DataCollection.SENTINEL2_L2A.from_request(
        SentinelHubRequest.input_data_request(time_interval=("2024-06-01", "2024-09-01")))],
    responses=[MimeType.TIFF],
    bbox=bbox, size=(512, 512),
    config=config,
)
img = request.get_data()[0]   # (H, W, 4)
```

For STAC-based discovery (no auth needed for public collections):

```python
import pystac_client, stackstac
import xarray as xr

catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1")
search = catalog.search(
    collections=["sentinel-2-l2a"],
    intersects={"type": "Polygon", "coordinates": [[
        [-122.6, 37.7], [-122.4, 37.7], [-122.4, 37.9], [-122.6, 37.9], [-122.6, 37.7]]]},
    datetime="2024-06-01/2024-09-01",
    query={"eo:cloud_cover": {"lt": 20}},
)
items = list(search.get_items())
stack = stackstac.stack(items, assets=["B02", "B03", "B04", "B08"], epsg=32610, resolution=10)
ndvi = (stack.sel(band="B08") - stack.sel(band="B04")) / (stack.sel(band="B08") + stack.sel(band="B04") + 1e-9)
composite = ndvi.median("time").compute()
```

### Cloud masking (QA band, s2cloudless)

```python
from s2cloudless import S2PixelCloudDetector
import numpy as np
import rasterio

cloud_detector = S2PixelCloudDetector(threshold=0.4, average_over=4, dilation_size=2)
with rasterio.open("s2_l1c_20m.tif") as src:
    bands = np.stack([src.read(i) for i in range(1, src.count + 1)], axis=-1)  # (H, W, B)
bands = (bands / 10000.0).astype("float32")   # to reflectance
prob = cloud_detector.get_cloud_probability_maps(bands)   # (H, W)
mask = cloud_detector.get_cloud_masks(bands)              # bool (H, W)
clear = np.where(mask[..., 0], np.nan, bands[..., 0])
```

For Landsat Collection 2, the `QA_PIXEL` band encodes cloud, cloud shadow, snow, and water as bit flags — use `rasterio` + bit manipulation or `xr.where`.

### torchgeo deep learning on imagery

```python
from torch.utils.data import DataLoader
from torchgeo.datasets import EuroSAT
from torchgeo.trainers import ClassificationTask
import pytorch_lightning as pl

ds = EuroSAT(root="eurosat", split="train", download=True)
loader = DataLoader(ds, batch_size=64, shuffle=True, num_workers=4)
task = ClassificationTask(model="resnet18", in_channels=13, num_classes=10, loss="ce", lr=1e-3)
trainer = pl.Trainer(max_epochs=10, accelerator="gpu" if torch.cuda.is_available() else "cpu")
trainer.fit(model=task, train_dataloaders=loader)
```

torchgeo ships models pretrained on Sentinel-2 (e.g., SatMAE, Scale-MAE) and datasets aligned with the major benchmarks (BigEarthNet, EuroSAT, Sen12MS, NAIP).

### Time-series compositing

```python
import xarray as xr
# Build a cloud-free monthly median composite from a 90-day Sentinel-2 series
stack = stackstac.stack(items, assets=["B04", "B08"], resolution=10, epsg=32610)
stack = stack.where(stack > 0)
ndvi = (stack.sel(band="B08") - stack.sel(band="B04")) / (stack.sel(band="B08") + stack.sel(band="B04"))
monthly = ndvi.resample(time="1MS").median("time").compute()
```

### SAR processing basics (Sentinel-1 GRD)

```python
import rasterio, numpy as np
from scipy.ndimage import uniform_filter
with rasterio.open("s1_grd_vv.tif") as src:
    vv = src.read(1).astype("float32")
# Convert DN to dB (after calibration; this assumes already calibrated sigma0)
vv_db = 10 * np.log10(np.maximum(vv, 1e-6))
# Simple Lee speckle filter (3x3)
mean = uniform_filter(vv_db, size=3)
var = uniform_filter((vv_db - mean) ** 2, size=3)
lee = mean + (var / (var + 0.5)) * (vv_db - mean)
```

## Best practices

- Always convert raw DN to physical reflectance (Sentinel-2 L2A: divide by 10000) or sigma0 (Sentinel-1 GRD: use sentinelhub or snappy) before computing indices.
- Use the QA band or s2cloudless on every analysis scene — unmasked clouds produce wildly wrong NDVI and burned-area estimates.
- Use STAC catalogs (Planetary Computer, Element 84 earth-search, USGS LandsatLook STAC) for cloud-native discovery; never download terabytes blindly.
- For time-series analysis, mask each scene independently, then composite — compositing before masking bleeds cloud contamination into the median.
- Pick the correct pixel scale for analysis: Sentinel-2 has 10 m / 20 m / 60 m bands; resampling 20 m to 10 m by `rasterio.enums.Resampling.bilinear` is fine for state-like variables.
- Match Sentinel-1 polarization to the use case: VV for water/surface roughness, VH for vegetation structure, ratio (VV-VH) for wetland detection.
- Use `rioxarray` for any workflow that benefits from labeled arrays (`rio.reproject`, `rio.clip`, `rio.write_crs`).
- For ML on imagery, use `torchgeo`'s `DataLoader` with a custom `collate_fn` that handles variable-size chips; never pad images manually with zeros (it leaks into indices).
- For very large STAC stacks, use `dask` chunking via `stackstac.stack(..., chunksize=...)` to avoid OOM.
- Validate by visual spot-check: always render a small RGB or false-color composite before publishing derived products.

## Common pitfalls

- **Dividing raw DN values** without converting to reflectance first — NDVI computed on DN can flip sign near bright targets.
- **Skipping cloud masking.** A single unmasked cloud can drop a region's mean NDVI by 0.3.
- **Wrong EPSG for stacking.** Sentinel-2 tiles are in UTM zones; mixing zones silently misaligns pixels. Force a common EPSG via `stackstac.stack(..., epsg=32610)`.
- **Confusing L1C (TOA reflectance) with L2A (surface reflectance).** L1C needs extra atmospheric correction (Sen2Cor or s2processing) before computing surface indices.
- **Wrong Sentinel-1 orbit direction.** Mixing ascending and descending passes corrupts time-series statistics; standardize on one.
- **Treating GeoTIFF as a 2D image.** Geotransform and CRS are part of the data; reading with PIL or `skimage.io` silently drops them.
- **Memory blow-up on STAC stacks.** A 100-scene Sentinel-2 stack at 10 m over a region can be 50+ GB; always `chunks=` it.
- **Forgetting `nodata` handling.** Sentinel-2 uses 0 as nodata; without masking, indices at scene edges become 0/0 = NaN or huge spikes.

## Worked example

Compute a cloud-free summer NDVI composite over a region using STAC + s2cloudless + stackstac.

```python
import pystac_client, stackstac, planetary_computer as pc
import numpy as np, xarray as xr
import rasterio
from matplotlib import pyplot as plt
from s2cloudless import S2PixelCloudDetector

aoi = {"type": "Polygon", "coordinates": [[
    [-122.6, 37.7], [-122.4, 37.7], [-122.4, 37.9], [-122.6, 37.9], [-122.6, 37.7]]]}

catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=pc.sign_inplace,
)
search = catalog.search(
    collections=["sentinel-2-l2a"],
    intersects=aoi, datetime="2024-06-01/2024-09-01",
    query={"eo:cloud_cover": {"lt": 50}},
)
items = list(search.get_items())
print(f"found {len(items)} scenes")

stack = stackstac.stack(items, assets=["B04", "B08", "SCL"],
                       epsg=32610, resolution=10,
                       chunksize={"time": 1, "x": 2048, "y": 2048})

# Use the Sentinel-2 Scene Classification Layer (SCL) for cloud masking
# SCL = 3 is cloud shadows, 8-10 are cloud, medium and high prob.
scl = stack.sel(band="SCL")
clear = ~scl.isin([3, 8, 9, 10, 11])

red = stack.sel(band="B04").where(clear)
nir = stack.sel(band="B08").where(clear)
ndvi = (nir - red) / (nir + red + 1e-9)

summer = ndvi.median("time").compute()
print(f"composite shape: {summer.shape}, mean NDVI: {float(summer.mean()):.3f}")

fig, ax = plt.subplots(figsize=(9, 7))
im = ax.imshow(summer, cmap="YlGn", vmin=0, vmax=0.8)
ax.set_title("Summer 2024 cloud-free NDVI composite")
plt.colorbar(im, ax=ax, label="NDVI", shrink=0.7)
fig.savefig("ndvi_summer.png", dpi=140, bbox_inches="tight")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| rasterio | Raster I/O, reprojection, windows (GDAL) | `pip install rasterio` |
| GDAL | Underlying C++ raster/vector library | `conda install gdal` |
| satpy | Satellite-format readers (S2, MODIS, VIIRS) | `pip install satpy` |
| sentinelhub | Cloud API access to S1/S2/S3/L8 | `pip install sentinelhub` |
| pystac-client | STAC catalog search and discovery | `pip install pystac-client` |
| stackstac | Stack STAC items into xarray/dask | `pip install stackstac` |
| rioxarray | rasterio + xarray integration | `pip install rioxarray` |
| s2cloudless | ML-based cloud detection for Sentinel-2 | `pip install s2cloudless` |
| torchgeo | Deep learning datasets/models for Earth obs | `pip install torchgeo` |
| planetary-computer | Microsoft Planetary Computer access | `pip install planetary-computer` |
| xarray-spatial | Raster ops in xarray | `pip install xrspatial` |
| snappy / snapista | Sentinel-1/2/3 toolbox bindings | `pip install snapista` |

## References

- [rasterio documentation](https://rasterio.readthedocs.io/en/stable/)
- [satpy documentation](https://satpy.readthedocs.io/en/stable/)
- [sentinelhub-py documentation](https://sentinelhub-py.readthedocs.io/en/latest/)
- [pystac-client documentation](https://pystac-client.readthedocs.io/en/stable/)
- [stackstac documentation](https://stackstac.readthedocs.io/en/latest/)
- [torchgeo documentation](https://torchgeo.readthedocs.io/en/stable/)
- [s2cloudless (Lightning docs)](https://github.com/sentinel-hub/sentinel2-cloud-detector)
- [USGS Landsat](https://www.usgs.gov/landsat-missions)
- [ESA Sentinel Hub](https://www.sentinel-hub.com/)
- [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
- [STAC specification](https://github.com/radiantearth/stac-spec)

## Ethics & safety

- **Licensing and redistribution.** Landsat and Sentinel-2 are open (US public domain / CC-BY). Maxar, PlanetScope, and commercial imagery are not redistributable — verify before embedding in publications or models.
- **Cloud API credentials.** Store Sentinel Hub and Planetary Computer keys in environment variables, never in notebooks. Use `os.environ["SH_CLIENT_SECRET"]`, never paste secrets in committed code.
- **Privacy from high-resolution imagery.** Sub-meter commercial imagery can re-identify individuals and vehicles; do not use it to track individuals, vehicles at private residences, or other sensitive activities.
- **Provenance and reproducibility.** For each derived product, record the scene IDs, processing level (L1C / L2A), baseline dates, and cloud-mask version. STAC catalogs make this auditable.
- **Indigenous and territorial rights.** High-resolution imagery of Indigenous lands and sacred sites carries special ethical weight; consult community partners before publishing such products.
- **Dual-use / surveillance.** Refuse to assist with imagery-based surveillance of individuals, vehicles, or protests; remote-sensing tools are scientific tools, not surveillance infrastructure.
- **Communicating uncertainty.** Spectral indices and ML products carry noise from atmospheric correction, cloud masking, and sensor drift; report confidence or quality flags alongside published maps.

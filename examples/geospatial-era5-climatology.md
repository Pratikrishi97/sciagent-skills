# Example: ERA5 regional climatology + anomaly map

**Skills activated:** `climate-science`, `geospatial-analysis`, `data-visualization`

## The prompt

> Download ERA5 monthly 2m temperature (1950–2023) for the Indian subcontinent (5–35°N, 65–95°E) from the Copernicus CDS. Compute the 1991–2020 climatology and the 2023 anomaly, regrid to a 0.25° grid with xESMF, and make a Robinson projection map of the 2023 anomaly with cartopy using a diverging color map.

## What the agent does

`climate-science` on `ERA5`, `xarray`, `CF conventions`, `xESMF`; `geospatial-analysis` for the regional subsetting; `data-visualization` for the publication map.

### 1. Download with cdsapi

```python
# pip install cdsapi xarray netCDF4 cfgrib xesmf cartopy matplotlib
import cdsapi, xarray as xr
c = cdsapi.Client()
c.retrieve("reanalysis-era5-single-levels-monthly-means",
    {"product_type":"monthly_averaged_reanalysis","variable":"2m_temperature",
     "year": list(range(1950,2024)), "month": list(range(1,13)),
     "area": [35, 65, 5, 95], "format":"netcdf", "time":"00:00"},
    "era5_t2m_india.nc")
```

### 2. Load + compute climatology + anomaly

```python
ds = xr.open_dataset("era5_t2m_india.nc", engine="netcdf4")
clim = ds["t2m"].sel(time=slice("1991","2020")).groupby("time.month").mean("time")
anom_2023 = ds["t2m"].sel(time="2023").groupby("time.month") - clim
annual_anom = anom_2023.mean("time")  # 2023 mean anomaly vs 1991-2020
```

### 3. Regrid to a regular 0.25° grid with xESMF

```python
import xesmf as xe
import numpy as np
target = xr.Dataset({"lat": ("lat", np.arange(5, 35.01, 0.25)),
                     "lon": ("lon", np.arange(65, 95.01, 0.25))})
regridder = xe.Regridder(annual_anom, target, method="bilinear", reuse_weights=False)
anom_025 = regridder(annual_anom)
```

### 4. Robinson projection map with cartopy

```python
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
fig, ax = plt.subplots(figsize=(9, 5),
                       subplot_kw={"projection": ccrs.Robinson(central_longitude=80)})
anom_025.plot(ax=ax, transform=ccrs.PlateCarree(),
              cmap="RdBu_r", center=0,
              cbar_kwargs={"label":"2m temperature anomaly (K)",
                           "shrink": 0.7},
              levels=np.arange(-3, 3.01, 0.5))
ax.coastlines()
ax.set_title("ERA5 2023 2m temperature anomaly vs. 1991–2020")
fig.savefig("era5_india_2023.png", dpi=200, bbox_inches="tight")
```

## Pitfalls the skill surfaces

- ERA5 is delivered on a reduced Gaussian grid; the CDS API `area` parameter pre-subsets but the grid is still native — regrid before computing regional means, or your area-weighted average will be biased toward high latitudes.
- Anomalies must be against a fixed climatology window (1991–2020 is the current WMO standard); shifting the window changes every number.
- `xarray` operations respect CF metadata — keep `attrs` intact so units survive the arithmetic.
- Robinson is an equal-area pseudocylindrical projection; for regional maps use `PlateCarree` and a tighter `extent` to avoid distortion at the edges.

## Reproducibility

Pin xarray + xESMF + cartopy versions (these are tightly coupled to the conda channel). Cache the regridder weights (`reuse_weights=True` after the first run). Register the dataset with a DOI on Zenodo if you publish — see the `reproducible-research` skill.

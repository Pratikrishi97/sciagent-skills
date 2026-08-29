---
name: climate-science
description: Climate data analysis using xarray, netCDF4, xESMF, intake-esm, Pangeo, dask, cartopy, and regionmask. Use when reading CMIP6/CESM/ERA5 NetCDF files, computing climatologies and anomalies, regridding between grids, applying CF conventions, chunking with dask on the cloud, plotting maps in Robinson or Orthographic projections, masking regions, or running extreme value analysis with scipy.genextreme.
license: MIT
compatibility: Requires Python 3.10+ with xarray, netCDF4, numpy, scipy, cartopy, dask. Optional extras include xesmf, intake-esm, regionmask, cf-xarray, cmocean, extremes.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Geospatial & Earth Science
---

# Climate Science

## Overview

Climate science is built on multi-decade NetCDF archives of atmosphere, ocean, land, and cryosphere fields from reanalyses (ERA5, MERRA-2, JRA-55), coupled climate models (CMIP6, CESM2), and observational datasets (GPCC, CRU, NOAA OISST). The Python stack converges on **xarray + dask + cf-xarray** for labeled multidimensional array analysis, **intake-esm** for cataloging CMIP6, **xESMF** for regridding, **cartopy** for map projections, **regionmask** for region masks, and the **Pangeo** cloud deployment pattern (Zarr on S3/Google Cloud Storage + dask clusters).

This skill covers the canonical workflows: NetCDF I/O with xarray, computing climatologies and anomalies, regridding with xESMF, accessing CMIP6/CESM/ERA5 via intake-esm and Pangeo, dask chunking for out-of-core arrays, cartopy map plotting (Robinson, Orthographic, PlateCarree), region masking with regionmask, and extreme value analysis (return periods, scipy.stats.genextreme). Data sources include Copernicus CDS (ERA5), ESGF (CMIP6), and NOAA/PCMDI.

## When to use this skill

- You are analyzing CMIP6, CESM, ERA5, or any CF-1.x-compliant NetCDF climate data.
- You need to compute climatologies, anomalies, trends, or seasonal averages over multi-decade time series.
- You need to regrid model output from one grid (e.g., 1-degree regular lat/lon) to another (e.g., a 0.25-degree target grid).
- You want to access CMIP6 ensembles without downloading terabytes — `intake-esm` + Pangeo cloud.
- Your array does not fit in RAM and you need dask chunking for out-of-core mean/std/linear-trend.
- You want to plot global maps in Robinson or Orthographic projections.
- You need to mask land-only or ocean-only grid cells, or aggregate by AR6 regions.
- You are estimating return periods or 100-year events with extreme value theory.

## Prerequisites

- Python 3.10+
- xarray >= 2023.8, netCDF4 >= 1.6, scipy >= 1.11, numpy >= 1.24, cartopy >= 0.22

```bash
pip install xarray netCDF4 scipy numpy cartopy matplotlib dask
# Optional
pip install xesmf intake-esm regionmask cf-xarray cmocean extremes gsw
```

Cartopy requires GEOS, PROJ, and Shapely — on Linux install `libgeos-dev libproj-dev` via apt.

## Core workflows

### NetCDF I/O and climatology/anomaly computation

```python
import xarray as xr

ds = xr.open_dataset("era5_t2m_monthly.nc")         # CF-compliant
print(ds["t2m"].dims, ds["t2m"].attrs)

# Monthly climatology (one value per calendar month)
clim = ds["t2m"].groupby("time.month").mean("time")

# Anomaly relative to the 1991-2020 baseline
ref = ds["t2m"].sel(time=slice("1991", "2020")).groupby("time.month").mean("time")
anom = ds["t2m"].groupby("time.month") - ref
```

Use `xr.open_mfdataset("*.nc", chunks={"time": 12})` to lazily chunk large multi-file collections across a dask cluster.

### Regridding with xESMF

```python
import xarray as xr
import xesmf as xe

ds_in = xr.open_dataset("cesm_sst.nc")             # native 1x1 grid
ds_out = xr.Dataset({
    "lat": ("lat", np.arange(-89.5, 90, 1.0)),
    "lon": ("lon", np.arange(-179.5, 180, 1.0)),
})
regridder = xe.Regridder(ds_in, ds_out, method="bilinear", reuse_weights=False)
ds_regrid = regridder(ds_in["SST"])
```

For conservative regridding (e.g., cell-averaged fluxes) use `method="conservative"` — required for energy/mass conservation.

### CMIP6 access via intake-esm and Pangeo

```python
import intake
col = intake.open_esm_datastore(
    "https://storage.googleapis.com/cmip6/pangeo-cmip6.json")
cat = col.search(experiment_id="historical",
                 table_id="Amon",
                 variable_id="tas",
                 source_id="CESM2",
                 member_id="r1i1p1f1")
ds_dict = cat.to_dataset_dict()         # opens Zarr stores in the cloud
ds = list(ds_dict.values())[0].chunk({"time": 240})
global_mean = ds["tas"].weighted(ds["area"]).mean(("lat", "lon"))
```

### Dask chunking for out-of-core computation

```python
ds = xr.open_dataset("era5_30y.nc", chunks={"time": 240, "lat": 180, "lon": 180})
# Operations are lazy until .compute()
trend = ds["t2m"].polyfit(dim="time", deg=1).chunk()  # slopes per cell
trend_computed = trend.compute()                      # triggers dask graph
```

Pick chunk sizes ~100-200 MB per chunk; chunks too small thrash the scheduler, too big spills to disk.

### Cartopy map plotting (Robinson, Orthographic)

```python
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import numpy as np

fig = plt.figure(figsize=(10, 5))
ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
ax.coastlines(resolution="110m")
gl = ds["t2m"].isel(time=-1) - ref.isel(month=ds.time.dt.month[-1].item() - 1)
p = ax.pcolormesh(ds["lon"], ds["lat"], gl,
                  transform=ccrs.PlateCarree(),
                  cmap="RdBu_r", vmin=-5, vmax=5)
ax.set_title("Latest month temperature anomaly")
plt.colorbar(p, ax=ax, orientation="horizontal", pad=0.05, label="K")
```

For polar data use `ccrs.Orthographic(central_latitude=90)` or `ccrs.NorthPolarStereo()`.

### Region masking with regionmask

```python
import regionmask
import numpy as np

# AR6 IPCC reference regions
ar6 = regionmask.defined_regions.ar6.all
mask = ar6.mask(ds["lon"], ds["lat"])                # integer region id per cell
regional = ds["tas"].groupby(mask).mean(("lat", "lon"))
print(regional.isel(region=ar6.map_keys("N.Europe")))
```

### Extreme value analysis

```python
from scipy.stats import genextreme as gev
import numpy as np

# Annual maxima of daily precipitation
annual_max = ds["tp"].resample(time="1YS").max("time").values.ravel()
# Remove NaNs and fit GEV
y = annual_max[~np.isnan(annual_max)]
c, loc, scale = gev.fit(y)                          # shape, loc, scale
# 100-year return level
rl_100 = gev.ppf(1 - 1/100, c, loc=loc, scale=scale)
print(f"100-year return level = {rl_100:.1f} mm/day")
```

Use `c = -xi` conventions carefully — packages differ on sign of the shape parameter.

### Climate indices with xclim

```python
from xclim.indicators.atmos import tx90p, prcptot, rx1day
import xarray as xr

tasmax = xr.open_dataset("era5_tasmax_daily.nc")["tasmax"]
pr = xr.open_dataset("era5_tp_daily.nc")["tp"]

# Percentage of days where Tmax > 90th percentile (warm days)
tx90 = tx90p(tasmax, tas=tasmax, freq="YS")
# Annual total precipitation on wet days
ptot = prcptot(pr, thresh="1 mm/day", freq="YS")
# Annual maximum 1-day precipitation
rx1 = rx1day(pr, freq="YS")
print(f"mean rx1day (1991-2020): {rx1.sel(time=slice('1991', '2020')).mean():.1f} mm")
```

`xclim` enforces CF checks (units, calendar) before computing; the resulting indicators are CF-compliant and ready to publish.

## Best practices

- Keep the CF metadata flowing through computations: use `cf-xarray` (`ds.cf`) for axis/bookkeeping that respects `standard_name`, `units`, and `calendar`.
- Compute climatologies over an explicit baseline period (1991-2020 is WMO standard for current normals) and document it in the methods.
- For regridding flux-like variables (precipitation, radiative flux), use conservative remapping; for state-like variables (temperature), bilinear is fine.
- Prefer `xr.open_mfdataset(..., chunks=...)` over pre-merging files — let dask lazily stitch the time dimension.
- When working on the cloud with Zarr, use `chunks={}` matching the stored chunk shape — random chunk shapes kill dask throughput.
- Always `.compute()` or `.load()` only the final small result; intermediate operations stay lazy.
- For ensemble analysis (e.g., CMIP6 multi-model), use `intake-esm` to assemble per-model datasets, then `xr.concat` along a new `model` dimension.
- Document the calendar (`"gregorian"`, `"noleap"`, `"360_day"`) when computing time statistics — CMIP6 models mix calendars.
- For maps, prefer `Robinson` for global views (equal-area-ish, low polar distortion) and `PlateCarree` for regional; always pass `transform=ccrs.PlateCarree()` to `pcolormesh`.
- For return-period analysis, fit GEV on annual maxima and GPD on peaks-over-threshold; report both shape parameter and the 95% CI from bootstrap.

## Common pitfalls

- **Defaulting to `chunks="auto"`** on cloud Zarr stores — this often splits across stored chunks and causes 100x slowdowns. Match stored chunk shapes.
- **Regridding without checking masks.** Conservative regridding needs cell bounds in the source dataset; if missing, xESMF silently uses nearest-neighbor and the result is wrong.
- **Mixing calendars.** CMIP6 `"360_day"` and observational `"gregorian"` calendars give different day-of-year climatologies; standardize before `groupby("time.month")`.
- **Area-weighted vs arithmetic means.** A naive `.mean(("lat", "lon"))` overweights the poles. Use `ds.weighted(np.cos(np.deg2rad(ds.lat))).mean(("lat", "lon"))`.
- **Forgetting `transform=ccrs.PlateCarree()`** in `pcolormesh` — cartopy silently plots in projection coordinates and the data appears as a thin strip near the equator.
- **`.values` on a chunked array.** Triggers full eager load and OOMs on a 30 GB dataset; use `.compute()` and then `.values`.
- **Confusing `"noleap"` with `"360_day"`.** Both omit Feb 29 but `360_day` shortens every month to 30 days. The CF calendar attribute distinguishes them.
- **Extreme value shape sign.** Some libraries use `c` (SciPy) and others use `xi = -c`. Always check the convention before reporting return levels.

## Worked example

Compute the 1991-2020 monthly temperature climatology and the latest-month anomaly for ERA5 2-m temperature, plot it globally with cartopy, then estimate the 50-year return level of annual max daily precipitation at one grid cell.

```python
import xarray as xr, numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from scipy.stats import genextreme as gev

# Load ERA5 monthly 2-m temperature (any local file or Pangeo cloud)
ds = xr.open_dataset("era5_t2m_monthly.nc")            # var: t2m in K
ref = ds["t2m"].sel(time=slice("1991", "2020")).groupby("time.month").mean("time")
latest = ds["t2m"].isel(time=-1)
anom = latest - ref.isel(month=ds["time"].dt.month[-1].item() - 1)

fig = plt.figure(figsize=(10, 4.5))
ax = fig.add_subplot(1, 1, 1, projection=ccrs.Robinson())
ax.coastlines(resolution="110m", color="grey", lw=0.4)
p = ax.pcolormesh(ds["lon"], ds["lat"], anom,
                  transform=ccrs.PlateCarree(),
                  cmap="RdBu_r", vmin=-6, vmax=6)
ax.set_title(f"ERA5 2-m temperature anomaly, {str(ds.time[-1].values)[:7]}")
plt.colorbar(p, ax=ax, orientation="horizontal", pad=0.05,
             label="Anomaly vs 1991-2020 (K)")
fig.savefig("era5_anomaly.png", dpi=140, bbox_inches="tight")

# 50-year return level of annual max daily precipitation at one cell
dp = xr.open_dataset("era5_tp_daily.nc")["tp"]            # mm/day
am = dp.resample(time="1YS").max("time").sel(lat=52.0, lon=0.0, method="nearest")
y = am.values[~np.isnan(am.values)]
c, loc, scale = gev.fit(y)
rl_50 = gev.ppf(1 - 1/50, c, loc=loc, scale=scale)
print(f"50-year return level = {rl_50:.1f} mm/day (GEV shape = {c:.3f})")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| xarray | Labeled n-dim arrays, NetCDF I/O | `pip install xarray` |
| netCDF4 | NetCDF / HDF5 I/O backend | `pip install netCDF4` |
| dask | Out-of-core chunked arrays | `pip install dask` |
| cartopy | Map projections, coastlines | `pip install cartopy` |
| xesmf | Conservative and bilinear regridding | `pip install xesmf` |
| intake-esm | CMIP6 / CESM catalog access | `pip install intake-esm` |
| regionmask | AR6 and other region masks | `pip install regionmask` |
| cf-xarray | CF-compliant axis handling | `pip install cf-xarray` |
| cmocean | Ocean-friendly colormaps | `pip install cmocean` |
| scipy.stats | GEV/GPD extreme value fitting | `pip install scipy` |
| xclim | Climate indices (TX90p, SPI, etc.) | `pip install xclim` |
| xarray-einstats | Stats on labeled arrays | `pip install xarray-einstats` |

## References

- [xarray documentation](https://docs.xarray.dev/en/stable/)
- [Pangeo documentation](https://pangeo.io/)
- [intake-esm documentation](https://intake-esm.readthedocs.io/en/latest/)
- [xESMF documentation](https://xesmf.readthedocs.io/en/latest/)
- [cartopy documentation](https://scitools.org.uk/cartopy/docs/latest/)
- [regionmask documentation](https://regionmask.readthedocs.io/en/stable/)
- [CF Conventions](https://cfconventions.org/)
- [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/)
- [Earth System Grid Federation (ESGF)](https://esgf-node.llnl.gov/)
- [IPCC AR6 regions (Iturbide et al., 2020)](https://essd.copernicus.org/articles/12/2959/2020/)
- [Cooley, D. — return periods and extremes](https://doi.org/10.1146/annurev-statistics-031221-045733)

## Ethics & safety

- **Climate data integrity.** Trust the upstream source versioning — ERA5 has multiple releases; CMIP6 has versioned `dataset_version` tags; never mix versions in one analysis without flagging.
- **Reproducibility.** Pin `intake-esm` catalog URL and `dataset_version`; cite the ES-DOC/CMIP6 Citation tool for every model run used.
- **Carbon cost of cloud dask.** Spinning up 100-worker clusters for casual analysis has real CO2 cost. Match cluster size to dataset size.
- **Calendars and time conventions.** Mixing calendars silently introduces biases at the day-of-year level — document and standardize.
- **Communication of uncertainty.** Ensemble spread is part of the result; always report the multi-model range, not just the ensemble mean, when discussing projections.
- **Equity and attribution.** Climate-impact attribution (extreme events, loss-and-damage) carries political weight; present probabilities and uncertainties explicitly and avoid overclaiming single-event attribution.
- **Open data and access equity.** Some climate datasets (ERA5, certain CMIP6 outputs) require registration and are bandwidth-heavy. Acknowledge data providers and don't redistribute licensed datasets without authorization.
- **Scenario honesty.** When projecting future changes, clearly label the SSP/RCP scenario driving each result; never present a single-scenario projection as "the" future.



---
name: geospatial-analysis
description: Vector and raster geospatial analysis for science using GeoPandas, rasterio, pyproj, rasterstats, osmnx, networkx, rtree, contextily, and folium. Use when reading shapefiles and GeoJSON, doing spatial joins (sjoin), dissolve, overlay, coordinate reference system (CRS) transformations, raster windowed I/O and reproject, zonal statistics, network routing on OpenStreetMap, basemap tiles, interactive maps, or working with Natural Earth, OpenStreetMap, and GADM boundaries.
license: MIT
compatibility: Requires Python 3.10+ with geopandas, rasterio, pyproj, shapely, matplotlib, folium. Optional extras include rasterstats, osmnx, networkx, rtree, contextily, mapclassify.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Geospatial & Earth Science
---

# Geospatial Analysis

## Overview

Geospatial analysis is the backbone of ecology, public health, urban science, hydrology, conservation, and infrastructure. The Python geospatial stack splits cleanly into two halves: **vector** (points, lines, polygons) and **raster** (gridded bands like satellite imagery or elevation). GeoPandas wraps Shapely + fiona + pyproj for vector operations; rasterio wraps GDAL for raster I/O; rasterstats aggregates rasters over polygons; osmnx + networkx handle street-network routing; rtree provides spatial indexing; contextily and folium cover basemaps and interactive maps.

This skill covers the canonical workflows: reading and writing shapefile/GeoJSON with `geopandas.read_file`, reprojection with `to_crs` (EPSG codes via `pyproj`), attribute and spatial joins (`sjoin`, `sjoin_nearest`), dissolve and overlay operations, raster windowed I/O and reprojection with `rasterio`, zonal statistics with `rasterstats`, street-network routing with `osmnx` + `networkx`, spatial indexing with `rtree`, basemaps with `contextily`, and interactive maps with `folium`. Data sources include Natural Earth (global admin boundaries and physical features), OpenStreetMap (buildings, roads, points of interest), and GADM (administrative boundaries).

## When to use this skill

- You have shapefiles, GeoJSON, or GeoPackage data and need vector operations (intersections, joins, dissolve).
- You are working with raster imagery (GeoTIFF) and need windowed reads, reprojection, or band math.
- You need to aggregate raster values over polygons (zonal statistics).
- You want to compute shortest-path or isochrone routing on a street network.
- You need to render static maps with basemap tiles or interactive maps in a notebook.
- You are working with CRS issues — converting between EPSG:4326 (lon/lat) and a projected CRS for distance/area calculations.
- You are joining field-sampled point data to administrative polygons or raster bioclim layers.

## Prerequisites

- Python 3.10+
- geopandas >= 0.14, rasterio >= 1.3, pyproj >= 3.6, shapely >= 2.0, folium >= 0.15

```bash
pip install geopandas rasterio pyproj shapely matplotlib folium
# Optional
pip install rasterstats osmnx networkx rtree contextily mapclassify
```

On Linux you may also need `libgdal-dev`, `libproj-dev`, `libgeos-dev` via apt.

## Core workflows

### Vector I/O, reprojection, and spatial joins

```python
import geopandas as gpd

# Read Natural Earth country boundaries and city points
countries = gpd.read_file("naturalearth_lowres.zip")
cities = gpd.read_file("naturalearth_cities.zip")

# Project to a world equidistant CRS for distance-based joins (EPSG:4087)
countries_m = countries.to_crs(epsg=4087)
cities_m = cities.to_crs(epsg=4087)

# Spatial join: which country contains each city?
pts = gpd.sjoin(cities_m, countries_m[["geometry", "name"]], how="left",
                predicate="within")
print(pts["name_right"].value_counts().head())
```

### Dissolve and overlay

```python
# Dissolve sub-national polygons into regions by continent
continents = countries.dissolve(by="continent", aggfunc={"pop_est": "sum"})

# Overlay: intersection of two polygon layers (e.g., protected areas and biomes)
protected = gpd.read_file("protected_areas.gpkg")
biomes = gpd.read_file("biomes.gpkg")
overlap = gpd.overlay(protected.to_crs(biomes.crs), biomes,
                      how="intersection")
print(overlap.area.sum() / 1e6, "km^2 protected-biome overlap")
```

### Raster windowed I/O and band math with rasterio

```python
import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
import numpy as np

with rasterio.open("s2.tif") as src:
    # Read a 1024x1024 window without loading the whole scene
    win = Window(2048, 1024, 1024, 1024)
    red = src.read(1, window=win).astype("float32")
    nir = src.read(4, window=win).astype("float32")

# NDVI: (NIR - RED) / (NIR + RED)
ndvi = (nir - red) / (nir + red + 1e-9)

# Write the result with the same georeferencing as the source window
with rasterio.open("s2.tif") as src:
    win_transform = src.window_transform(win)
    profile = src.profile.copy()
    profile.update(count=1, dtype="float32",
                   width=1024, height=1024,
                   transform=win_transform)
    with rasterio.open("ndvi_window.tif", "w", **profile) as dst:
        dst.write(ndvi, 1)
```

### Zonal statistics with rasterstats

```python
from rasterstats import zonal_stats
import geopandas as gpd

# Mean NDVI per county polygon
stats = zonal_stats("counties.gpkg", "ndvi.tif",
                    stats=["mean", "median", "std"], geojson_out=True)
gdf = gpd.GeoDataFrame.from_features(stats)
print(gdf[["name", "mean"]].head())
```

### Street network routing with osmnx and networkx

```python
import osmnx as ox
import networkx as nx

G = ox.graph_from_place("Cambridge, MA, USA", network_type="walk")
orig = ox.geocode("Harvard University, Cambridge, MA")
dest = ox.geocode("MIT, Cambridge, MA")
o = ox.nearest_nodes(G, *reversed(orig))   # lon, lat order
d = ox.nearest_nodes(G, *reversed(dest))
path = nx.shortest_path(G, o, d, weight="length")
m = ox.plot_route_folium(G, path, tiles="OpenStreetMap")
m.save("route.html")
```

### Folium interactive maps and contextily basemaps

```python
import folium, geopandas as gpd, contextily as cx
import matplotlib.pyplot as plt

# Static map with a basemap
fig, ax = plt.subplots(figsize=(8, 8))
gdf = gpd.read_file("sensors.geojson").to_crs(epsg=3857)
gdf.plot(column="pm25", cmap="RdYlGn_r", legend=True, ax=ax, markersize=40)
cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
ax.set_axis_off(); ax.set_title("PM2.5 sensor readings")

# Interactive map
m = folium.Map(location=[42.36, -71.10], zoom_start=13, tiles="CartoDB positron")
for _, r in gdf.to_crs(epsg=4326).iterrows():
    folium.CircleMarker([r.geometry.y, r.geometry.x],
                        radius=r["pm25"] * 2,
                        fill=True, fill_opacity=0.7,
                        color="crimson").add_to(m)
m.save("sensors.html")
```

### Spatial indexing with rtree and nearest-neighbor joins

```python
import geopandas as gpd

# Find the nearest weather station to each air-quality sensor
sensors = gpd.read_file("sensors.gpkg").to_crs(epsg=3857)
stations = gpd.read_file("weather_stations.gpkg").to_crs(epsg=3857)

nearest = gpd.sjoin_nearest(sensors, stations[["geometry", "station_id"]],
                            distance_col="dist_m", how="left",
                            max_distance=5000)
print(nearest[["sensor_id", "station_id", "dist_m"]].head())

# Use the underlying rtree index for custom queries
idx = stations.sindex
for _, sensor in sensors.iterrows():
    candidates = idx.nearest(sensor.geometry, return_all=False)
    print(sensor["sensor_id"], "matches station idx", candidates)
```

## Best practices

- Always check `gdf.crs` and set it explicitly — silently defaulting to EPSG:4326 when data is in a projected CRS is a classic bug.
- Reproject to a metric CRS (UTM zone, or EPSG:4087 for global, EPSG:6933 for equal-area) before computing distances, areas, or buffers — never do metric math in degrees.
- Use spatial indexing (`sjoin`, `sindex`, `rtree`) for joins on large layers; nested Python loops are O(N*M) and unusable past ~10^4 features.
- For raster reads, always pass a `Window` to `read()` when you only need a region — full-scene reads can be GBs.
- Use `rasterio.enums.Resampling` explicitly when reprojecting rasters; default behavior may not match your scientific intent (categorical rasters need `nearest`, continuous need `bilinear` or `cubic`).
- Prefer GeoPackage (`.gpkg`) over shapefile for new outputs — single-file, no DBF limit, supports multiple layers and CRS metadata.
- Verify polygon validity (`gdf.geometry.is_valid`) before joins/overlays — invalid geometries silently produce empty intersections.
- For interactive maps with > 10^4 features, use `folium.plugins.HeatMap` or convert to vector tiles (`lonboard`, `deck.gl`) — drawing 100k CircleMarkers freezes the browser.
- When buffering points for spatial joins, use a metric CRS for the buffer distance, then reproject to the raster/polygon CRS for the actual join.
- For time-aware geospatial data (moving ships, GPS traces), use `movingpandas` or `tracktable`; the standard GeoPandas stack assumes static geometry.

## Common pitfalls

- **Mixing CRSes.** Two layers in different CRSes will silently mis-join or produce empty intersections. Always `to_crs()` first.
- **Computing area in degrees.** Polygon `.area` in EPSG:4326 is in "square degrees" — physically meaningless. Reproject to a metric CRS first.
- **Reading the whole raster.** A Sentinel-2 scene is ~30 GB; never `src.read()` without a window or band subset.
- **`sjoin` default `predicate`.** Modern geopandas renamed `op=` to `predicate=`; using `op` triggers a deprecation warning in recent versions.
- **Floating-point precision in joins.** Points snapped to a coast can fail `within` tests due to sub-meter precision. Use `sjoin_nearest` with a `max_distance` tolerance.
- **Unprojected Web Mercator for analysis.** EPSG:3857 distorts areas heavily near the poles; use it only for basemap display, never for area/distance math.
- **Forgetting `parse_dates` and `crs`** when reading CSV-derived points — `gpd.GeoDataFrame(df, geometry=points, crs="EPSG:4326")` is the safe constructor.
- **Mishandling multipart geometries.** MultiPolygons vs Polygons behave differently in `sjoin`; cast with `.explode()` if you need single-part features.

## Worked example

Estimate mean NDVI within 500 m buffers around air-quality sensors in a city, using a Sentinel-2 NDVI raster and a CSV of sensor locations.

```python
import geopandas as gpd, pandas as pd, rasterio
from rasterstats import zonal_stats
import matplotlib.pyplot as plt
import contextily as cx

# 1. Load sensors as a GeoDataFrame
df = pd.read_csv("sensors.csv", parse_dates=["timestamp"])
gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat),
                       crs="EPSG:4326")
gdf = gdf.to_crs(epsg=3857)              # Web Mercator for buffering
buffers = gdf.copy()
buffers["geometry"] = gdf.buffer(500)    # 500 m radius
buffers = buffers.to_crs("EPSG:4326")    # match NDVI raster CRS

# 2. Zonal stats: mean NDVI per buffer
stats = zonal_stats(buffers, "ndvi_city.tif",
                    stats=["mean", "count"], geojson_out=False)
buffers["ndvi_mean"] = [s["mean"] for s in stats]
buffers["ndvi_count"] = [s["count"] for s in stats]

# 3. Plot sensors + buffers + basemap
fig, ax = plt.subplots(figsize=(9, 9))
buffers.to_crs(epsg=3857).plot(column="ndvi_mean", cmap="YlGn",
                              legend=True, ax=ax, alpha=0.7, edgecolor="k")
gdf.to_crs(epsg=3857).plot(ax=ax, color="crimson", markersize=20)
cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
ax.set_axis_off(); ax.set_title("Mean NDVI within 500 m of PM2.5 sensors")
fig.savefig("sensors_ndvi.png", dpi=140, bbox_inches="tight")
print(buffers[["sensor_id", "ndvi_mean"]].sort_values("ndvi_mean"))
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| geopandas | Vector I/O, joins, dissolve, overlay | `pip install geopandas` |
| shapely | Geometry engine underlying geopandas | `pip install shapely` |
| fiona | Low-level OGR vector I/O | `pip install fiona` |
| pyproj | CRS definitions, transformations | `pip install pyproj` |
| rasterio | Raster I/O and reprojection (GDAL) | `pip install rasterio` |
| rasterstats | Zonal statistics over polygons | `pip install rasterstats` |
| osmnx | OpenStreetMap download + routing | `pip install osmnx` |
| networkx | Graph algorithms (shortest path) | `pip install networkx` |
| rtree / sindex | Spatial indexing for fast joins | `pip install rtree` |
| contextily | Basemap tiles for matplotlib | `pip install contextily` |
| folium | Interactive Leaflet maps | `pip install folium` |
| mapclassify | Choropleth classification schemes | `pip install mapclassify` |

## References

- [GeoPandas documentation](https://geopandas.org/en/stable/)
- [rasterio documentation](https://rasterio.readthedocs.io/en/stable/)
- [pyproj documentation](https://pyproj4.github.io/pyproj/stable/)
- [shapely documentation](https://shapely.readthedocs.io/en/stable/)
- [osmnx documentation](https://osmnx.readthedocs.io/en/stable/)
- [rasterstats documentation](https://pythonhosted.org/rasterstats/)
- [Natural Earth Data](https://www.naturalearthdata.com/)
- [OpenStreetMap](https://www.openstreetmap.org/)
- [GADM administrative boundaries](https://gadm.org/)
- [EPSG registry](https://epsg.io/)
- [contextily providers list](https://contextily.github.io/contextily/stable/providers.html)

## Ethics & safety

- **Privacy of point data.** Locations of residences, hospitals, or sensitive infrastructure must be aggregated or jittered before publication to prevent re-identification.
- **CRS correctness.** A wrong CRS can silently shift results by hundreds of meters — verify every transformation against a known landmark before publishing.
- **Modifiable areal unit problem (MAUP).** Aggregating point data to different administrative boundaries changes the answers. Report sensitivity to boundary choice.
- **Satellite imagery licensing.** Read and respect each provider's license (Sentinel: CC-BY, Landsat: US public domain, Maxar/DigitalGlobe: commercial, do not redistribute raw tiles).
- **Equity.** Geospatial features (sensor density, tree canopy, air quality) often correlate with income and race; surface these correlations explicitly rather than letting them hide inside "model accuracy".
- **Open data ethics.** OpenStreetMap contributions are ODbL-licensed; derivative works must attribute OSM and ship under a compatible license.
- **Boundary disputes.** Natural Earth, GADM, and OSM may disagree on contested borders. Pick one and document it; do not switch sources mid-paper to make a point.
- **Equity in service allocation.** When routing or zoning affects service access (clinics, schools, evacuation), audit outcomes by demographic group before deployment.



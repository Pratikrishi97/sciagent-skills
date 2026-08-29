---
name: data-visualization
description: Build publication-quality and interactive scientific figures with matplotlib, seaborn, plotly, and the wider PyViz stack. Use when creating static figures, statistical plots, multi-panel layouts, interactive dashboards, geospatial maps, or animations from experimental or simulated data.
license: MIT
compatibility: Requires Python 3.10+ with matplotlib, seaborn, plotly, numpy, pandas. Optional: cartopy, bokeh, holoviews, h5py, xarray for advanced workflows.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Data & Visualization
---

# Data Visualization for Science

## Overview

Scientific data visualization converts raw measurements and simulations into
insight. This skill covers the canonical Python stack for both static
publication figures (matplotlib + seaborn) and interactive exploratory
visualizations (plotly, bokeh, holoviews). It emphasizes the matplotlib
object-oriented API, reproducible styling via `rcParams`, color-blind-safe
palettes, and accessibility (alt text, contrast). The goal is figures that
survive peer review: vector PDF/SVG at 300 dpi, legible at column width, and
faithful to the underlying data.

## When to use this skill

- You need a figure for a paper, poster, slide, or preprint.
- You are exploring a new dataset and want interactive plots.
- You need to plot statistical distributions, regressions, or multi-panel
  small-multiple layouts.
- You are building a geospatial map from gridded or vector data.
- You want animations of time-evolving results.
- You need to render large (>1M points) datasets responsively.

## Prerequisites

- Python 3.10+
- Core: `matplotlib`, `seaborn`, `plotly`, `numpy`, `pandas`
- Optional: `cartopy`, `geopandas`, `bokeh`, `holoviews`, `datashader`,
  `h5py`, `xarray`, `ipywidgets`, `ffmpeg-python`
- System tools: a PDF/SVG viewer; for animations, `ffmpeg` on PATH
- pip install:
  ```bash
  pip install matplotlib seaborn plotly numpy pandas
  pip install cartopy bokeh holoviews datashader ipywidgets
  ```

## Core workflows

### 1. Static publication figure (matplotlib OO API)

Always use `Figure` and `Axes` objects. Never call `pyplot.plot` for code that
must be reproducible across notebooks and scripts.

```python
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({
    "figure.dpi": 120, "savefig.dpi": 300,
    "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42,  # editable text in Illustrator
})

rng = np.random.default_rng(42)
x = np.linspace(0, 10, 200)
y = np.sin(x) + rng.normal(0, 0.1, size=x.size)

fig, ax = plt.subplots(figsize=(3.5, 2.5))
ax.scatter(x, y, s=8, alpha=0.6, label="observed")
ax.plot(x, np.sin(x), color="#c0392b", lw=1.5, label="model")
ax.set_xlabel("Time [s]")
ax.set_ylabel("Signal [a.u.]")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig("fig1.pdf")  # vector for publication
fig.savefig("fig1.png", dpi=300)
```

### 2. Statistical plots with seaborn

Use seaborn's figure-level functions (`displot`, `relplot`, `pairplot`) for
faceted statistical visualizations and `twinx` for dual-axis plots.

```python
import seaborn as sns
import pandas as pd

tips = sns.load_dataset("tips")
g = sns.displot(
    data=tips, x="total_bill", hue="smoker", col="time",
    kind="kde", fill=True, height=2.5, common_norm=False,
    palette="viridis",
)
g.set_axis_labels("Total bill [USD]", "Density")
g.savefig("tips.pdf")

# Dual-axis example
fig, ax1 = plt.subplots(figsize=(3.5, 2.5))
ax2 = ax1.twinx()
sns.lineplot(data=tips, x="size", y="total_bill", ax=ax1, color="#2c7fb8")
sns.lineplot(data=tips, x="size", y="tip", ax=ax2, color="#d95f0e")
ax1.set_ylabel("Bill [USD]", color="#2c7fb8")
ax2.set_ylabel("Tip [USD]", color="#d95f0e")
```

### 3. Interactive plots with plotly

Use plotly.express for rapid exploration and `graph_objects` for fine control.
Export to self-contained HTML for sharing.

```python
import plotly.express as px

df = px.data.gapminder().query("year == 2007")
fig = px.scatter(
    df, x="gdpPercap", y="lifeExp", size="pop", color="continent",
    hover_name="country", log_x=True, size_max=45,
    title="Life expectancy vs GDP per capita (2007)",
    color_discrete_sequence=px.colors.qualitative.Safe,
)
fig.update_layout(template="plotly_white", font_size=11)
fig.write_html("gapminder.html", include_plotlyjs="cdn")
fig.show()
```

### 4. Multi-panel small multiples

Use `plt.subplots` with `sharex/sharey` and explicit `Axes` arrays.

```python
fig, axes = plt.subplots(2, 3, figsize=(7, 4), sharex=True, sharey=True)
for ax, (name, sub) in zip(axes.flat, df.groupby("continent")):
    ax.hist(sub["lifeExp"], bins=20, color="#4d4d4d")
    ax.set_title(name, fontsize=8)
fig.supxlabel("Life expectancy")
fig.supylabel("Count")
fig.tight_layout()
fig.savefig("small_multiples.pdf")
```

### 5. Geospatial with cartopy

```python
import cartopy.crs as ccrs
import cartopy.feature as cfeature

fig = plt.figure(figsize=(5, 3))
ax = plt.axes(projection=ccrs.PlateCarree())
ax.coastlines(lw=0.5)
ax.add_feature(cfeature.BORDERS, lw=0.3)
ax.set_extent([-130, -60, 20, 55])
ax.scatter([-100, -80, -70], [40, 35, 45], color="red", transform=ccrs.PlateCarree())
fig.savefig("map.pdf")
```

## Best practices

- Always use the matplotlib OO API (`fig, ax = plt.subplots()`), not `pyplot`
  state machine, in any code you intend to reuse or publish.
- Save vector formats (PDF/SVG) for publication; PNG at 300 dpi only when
  raster is required.
- Set `pdf.fonttype = 42` so journal copy-editors can edit text in Illustrator.
- Pick perceptually uniform, color-blind-safe colormaps: `viridis`, `cividis`,
  `magma`, `inferno`. Avoid jet/rainbow.
- Provide alt text for every figure in the surrounding document.
- Caption each axis with units (`Time [s]`, not `Time`).
- Use `tight_layout()` or `constrained_layout=True` to avoid clipped labels.
- Keep one logical comparison per panel; group related panels with `sharex`/`sharey`.
- Avoid 3D charts unless data is genuinely 3D.
- Re-run the notebook from a fresh kernel before submitting to confirm
  reproducibility.

## Common pitfalls

- Calling `plt.plot` inside functions hides state in `pyplot`; reuse fails
  across cells. Prefer `Axes` objects.
- Saving with `dpi=72` (matplotlib default for some save paths) produces fuzzy
  PDFs in print.
- Using `jet` colormap distorts quantitative data and fails deuteranopia tests.
- Mixing `set_xlabel` after `sns.displot` without using the returned
  `FacetGrid` reference silently no-ops.
- Forgetting `transform=ccrs.PlateCarree()` on cartopy scatter points puts
  data on the wrong projection.
- Plotting millions of points directly overloads the renderer; use
  `datashader` or hexbin aggregation first.
- Animations saved as `.gif` look fine but blow up size; prefer `.mp4` via
  `ffmpeg` and ship a static first-frame fallback.
- Hardcoded colors like `"red"` and `"blue"` reduce readability for
  color-blind viewers; use named hex palettes.

## Worked example

A two-panel publication figure: (a) regression with confidence band,
(b) residual histogram. Inputs are a CSV of (x, y) pairs.

```python
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

plt.rcParams.update({"savefig.dpi": 300, "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False})

df = pd.read_csv("calibration.csv")  # columns: x, y
slope, intercept, r, _, _ = stats.linregress(df.x, df.y)
resid = df.y - (slope * df.x + intercept)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.8, 2.8))
ax1.scatter(df.x, df.y, s=12, color="#2c7fb8", alpha=0.6, label="data")
xs = np.linspace(df.x.min(), df.x.max(), 100)
ax1.plot(xs, slope * xs + intercept, color="#d95f0e", label=f"fit (R2={r**2:.3f})")
ax1.set_xlabel("Concentration [uM]")
ax1.set_ylabel("Absorbance")
ax1.legend(frameon=False)
ax1.text(-0.18, 1.0, "a", transform=ax1.transAxes, fontweight="bold")

ax2.hist(resid, bins=20, color="#4d4d4d")
ax2.axvline(0, color="#d95f0e", lw=1)
ax2.set_xlabel("Residual")
ax2.set_ylabel("Count")
ax2.text(-0.18, 1.0, "b", transform=ax2.transAxes, fontweight="bold")

fig.tight_layout()
fig.savefig("calibration.pdf")
fig.savefig("calibration.png", dpi=300)
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| matplotlib | Static publication figures, OO API | `pip install matplotlib` |
| seaborn | Statistical plotting, built on matplotlib | `pip install seaborn` |
| plotly | Interactive HTML figures | `pip install plotly` |
| bokeh | Interactive plots for the browser | `pip install bokeh` |
| holoviews | Declarative viz, integrates with bokeh/plotly | `pip install holoviews` |
| datashader | Render millions of points | `pip install datashader` |
| cartopy | Geospatial projections and maps | `pip install cartopy` |
| geopandas | Vector geospatial data | `pip install geopandas` |
| xarray | N-D labeled arrays, often plotted with cartopy | `pip install xarray` |
| ipywidgets | Interactive notebook controls | `pip install ipywidgets` |
| ffmpeg | Backend for matplotlib animations | system install |

## References

- matplotlib usage guide: https://matplotlib.org/stable/tutorials/introductory/usage.html
- seaborn tutorial: https://seaborn.pydata.org/tutorial.html
- plotly python docs: https://plotly.com/python/
- Choosing colormaps (color-blind safety): https://matplotlib.org/stable/users/explain/colors/colormaps.html
- cartopy gallery: https://scitools.org.uk/cartopy/docs/latest/gallery/
- HoloViews user guide: https://holoviews.org/user_guide/index.html
- FAIR data principles for figures: https://www.go-fair.org/fair-principles/
- Datashader examples: https://datashader.org/getting_started/index.html

## Ethics & safety

- **Color blindness:** pick `viridis`/`cividis`/`magma` over `jet`; verify with
  a simulator (e.g. Coblis) and avoid red-green encodings for primary
  distinctions.
- **Data integrity:** never rescale axes to exaggerate effects; always show
  zero baselines for bar charts unless a non-zero baseline is explicitly
  justified in the caption.
- **Reproducibility:** set seeds for any jitter/randomization, save the
  source CSV next to the figure, and version the script that produced it.
- **Accessibility:** provide alt text in published HTML/PDF; ensure 4.5:1
  contrast for any text labels.
- **Honesty in interactivity:** brushable and linked views must show all
  data on first render; do not hide the unselected state.

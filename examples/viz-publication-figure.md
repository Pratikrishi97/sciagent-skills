# Example: publication-ready multi-panel figure

**Skills activated:** `data-visualization`

## The prompt

> Make a 3-panel publication figure (A: scatter with regression + bootstrap CI; B: grouped bar with error bars; C: heatmap with annotated cells). All panels share a consistent style: 8pt fonts, viridis + cividis color maps, 300 DPI, PDF + PNG outputs, accessible (color-blind safe, >4.5:1 contrast). Caption-ready.

## What the agent does

The `data-visualization` skill activates on `matplotlib`, `publication`, `multi-panel`, `viridis`.

### 1. Shared rcParams

```python
# pip install matplotlib seaborn numpy scipy
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np
mpl.rcParams.update({
    "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
    "pdf.fonttype": 42,  # editable text in PDF
    "axes.spines.top": False, "axes.spines.right": False,
})
```

### 2. Three panels sharing axes layout

```python
fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.3), constrained_layout=True)

# Panel A: scatter + bootstrap regression
rng = np.random.default_rng(1)
x = rng.normal(0, 1, 60)
y = 0.6*x + rng.normal(0, 0.4, 60)
ax = axes[0]
ax.scatter(x, y, s=10, c=x, cmap="viridis", edgecolor="none", alpha=0.85)
# bootstrap CI band
from scipy.stats import linregress
boots = [linregress(x[r], y[r]) for r in (rng.choice(len(x), len(x)) for _ in range(1000))]
xs = np.linspace(x.min(), x.max(), 50)
lo = np.percentile([[b.slope*xi + b.intercept for xi in xs] for b in boots], 2.5, axis=0)
hi = np.percentile([[b.slope*xi + b.intercept for xi in xs] for b in boots], 97.5, axis=0)
ax.fill_between(xs, lo, hi, color="0.6", alpha=0.3)
ax.set_title("A  Correlation + 95% CI")

# Panel B: grouped bar
ax = axes[1]
means = np.array([[2.1, 2.6, 3.0], [1.8, 2.0, 2.4]])
errs  = np.array([[0.3, 0.4, 0.2], [0.2, 0.3, 0.3]])
groups = ["Ctrl", "Drug"]
time = ["0h", "6h", "24h"]
xpos = np.arange(len(time)); w = 0.35
for i, (g, c) in enumerate(zip(groups, ["#440154", "#21918c"])):
    ax.bar(xpos + (i-0.5)*w, means[i], w, yerr=errs[i], label=g, color=c, capsize=2)
ax.set_xticks(xpos); ax.set_xticklabels(time)
ax.set_ylabel("response (a.u.)"); ax.set_title("B  Dose response"); ax.legend(frameon=False)

# Panel C: heatmap
ax = axes[2]
mat = rng.normal(0, 1, (6, 6))
im = ax.imshow(mat, cmap="cividis", aspect="auto")
for i in range(6):
    for j in range(6):
        ax.text(j, i, f"{mat[i,j]:.1f}", ha="center", va="center", fontsize=6,
                color="white" if mat[i,j] < 0 else "black")
ax.set_title("C  Annotated heatmap")
fig.colorbar(im, ax=ax, shrink=0.7, label="z-score")
fig.savefig("fig1.pdf"); fig.savefig("fig1.png")
```

## Pitfalls the skill surfaces

- `bbox_inches="tight"` saves a trimmed bounding box; it changes pixel dimensions — set `savefig.dpi=300` and let the journal scale.
- `pdf.fonttype=42` keeps text as editable strings (most journals require it); type 3 rasterizes.
- Color-blind safety: viridis/cividis are perceptually uniform and safe; `jet`/`rainbow` are not — never use them.
- Fill_between alpha < 0.4 is invisible in print; bump to 0.3–0.5.
- Annotate heatmap cells with a contrasting color (white on dark, black on light), not a fixed color — fixed black on a dark cividis cell vanishes.

## Reproducibility

Pin matplotlib + seaborn; set the RNG seed; save the script alongside the figure. A Quarto `.qmd` keeps code + figure + caption together (`scientific-writing` skill).

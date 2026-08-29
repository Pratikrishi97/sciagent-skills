---
name: notebook-best-practices
description: Use JupyterLab efficiently with papermill parameterization, nbconvert for HTML/PDF, jupytext for notebook-as-markdown version control, ipywidgets for interactivity, line/cell magics, %debug, %memit memory profiling, and nbval for notebook testing. Use when authoring, parameterizing, testing, or rendering notebooks for science.
license: MIT
compatibility: Requires Python 3.10+ with jupyterlab, papermill, nbconvert, jupytext, ipywidgets, nbval. Optional: matplotlib, plotly, pandas.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Research Infrastructure
---

# Notebook Best Practices

## Overview

Jupyter notebooks are the lingua franca of scientific Python. They are
also a reproducibility hazard when misused: hidden state, out-of-order
cells, embedded outputs that don't match the code. This skill covers
notebook hygiene (clear outputs, run order, version control), parameterization
with papermill, conversion to HTML/PDF with nbconvert, notebook-as-markdown
with jupytext, interactive widgets, line/cell magics (`%debug`, `%memit`,
`%load_ext`), and notebook testing with nbval. The goal is notebooks that
act like reproducible scripts: parameterizable, testable, and committed to
git without surprise state.

## When to use this skill

- You are building an analysis notebook for collaborators.
- You need to parameterize a notebook (e.g. one report per sample).
- You want to convert a notebook to HTML/PDF for a supplement.
- You need to test that a notebook still runs in CI.
- You want to debug a failing cell or profile a slow notebook.

## Prerequisites

- Python 3.10+
- Core: `jupyterlab`, `nbconvert`, `papermill`, `jupytext`, `ipywidgets`,
  `nbval`
- Optional: `matplotlib`, `plotly`, `pandas`, `tqdm`, `line_profiler`,
  `memory_profiler`
- System: `chromium` or `wkhtmltopdf` for PDF rendering via HTML export
- pip install:
  ```bash
  pip install jupyterlab nbconvert papermill jupytext ipywidgets
  pip install nbval line_profiler memory_profiler
  ```

## Core workflows

### 1. Notebook hygiene

```bash
# Strip outputs before committing (jupyterlab built-in):
jupyter nbconvert --clear-output --to notebook \
  --output analysis.ipynb analysis.ipynb

# Use jupytext to pair .ipynb with a markdown twin under git:
jupytext --set-formats ipynb,md analysis.ipynb
# Now `analysis.md` follows `analysis.ipynb`; commit the markdown twin.
```

### 2. Parameterize with papermill

```python
# In analysis.ipynb, put a cell at the top tagged "parameters":
# sample_id: str = "default"
# threshold: float = 0.5
```

```bash
papermill analysis.ipynb outputs/analysis_runA.ipynb \
  -p sample_id RUN-A \
  -p threshold 0.65
```

In Python:
```python
import papermill as pm
pm.execute_notebook(
    "analysis.ipynb",
    "outputs/analysis_runA.ipynb",
    parameters={"sample_id": "RUN-A", "threshold": 0.65},
)
```

### 3. Convert to HTML/PDF with nbconvert

```bash
# Self-contained HTML (embeds images as base64)
jupyter nbconvert --to html --embed-images \
  --output analysis.html analysis.ipynb

# PDF via LaTeX (requires xelatex)
jupyter nbconvert --to pdf --PDFExporter.latex_command=xelatex \
  analysis.ipynb

# Hide code cells in the report
jupyter nbconvert --to html --no-input analysis.ipynb
```

### 4. Interactive widgets

```python
import ipywidgets as widgets
from IPython.display import display
import numpy as np, matplotlib.pyplot as plt

@widgets.interact(freq=(0.1, 5.0, 0.1), amp=(0.5, 5.0, 0.1))
def plot(freq=1.0, amp=1.0):
    x = np.linspace(0, 2 * np.pi, 500)
    fig, ax = plt.subplots(figsize=(6, 2))
    ax.plot(x, amp * np.sin(freq * x))
    ax.set_ylim(-6, 6); plt.show()
```

### 5. Magics, debugging, and profiling

```python
# Reload modules automatically
%load_ext autoreload
%autoreload 2

# Drop into the debugger at the last exception
%debug

# Time a single cell
%timeit np.fft.fft(np.random.normal(size=100_000))

# Profile memory of a single statement
%load_ext memory_profiler
%memit np.random.normal(size=(10_000, 1_000))
```

### 6. Test notebooks with nbval

```bash
# Run the notebook and check outputs match the stored ones
pytest --nbval analysis.ipynb

# Lint-only mode: just check it runs without comparing outputs
pytest --nbval-lax analysis.ipynb
```

## Best practices

- Clear outputs before committing (`git diff` will explode otherwise).
- Use jupytext to pair `.ipynb` with `.md`; commit the markdown twin.
- Tag a cell `parameters` at the top and run with papermill for reports.
- Put imports and constants in the first two cells; document the contract.
- Use `%load_ext autoreload 2` when developing against a local package.
- For long-running cells, print progress with `tqdm.notebook.tqdm`.
- Don't print DataFrames to confirm; assign them and use `display(df.head())`.
- Add `# %%` cell markers if writing notebooks in plain `.py` (vscode,
  jupytext).
- Test critical notebooks in CI with `pytest --nbval`.
- Write a `KernelSpec` with a pinned env name so `papermill` selects the
  right kernel.

## Common pitfalls

- Outputs not cleared before commit bloat the diff and confuse reviewers.
- Cells run out-of-order leaves hidden state; restart-and-run-all is the
  only safe check before publishing.
- Variable name collisions across cells (`df` reused for two different
  DataFrames) silently corrupt downstream analysis.
- Forgetting `--embed-images` in `nbconvert --to html` produces broken
  image links in the published PDF.
- `%autoreload 2` does not reload C extensions; restart the kernel.
- Papermill parameters set on the first cell but the tagged cell is below
  other code that uses them; tag the topmost cell only.
- nbval tests flake on plots (PNG bytes differ across matplotlib versions);
  use `--nbval-lax` or strip outputs in CI first.
- `IPython.display.JSON` of large dicts makes the notebook unrenderable;
  truncate to a sample.

## Worked example

A parameterizable analysis notebook that runs per-sample, publishes to PDF,
and is tested in CI.

`analysis.ipynb` (first cell, tagged `parameters`):
```python
# Parameters cell (do not edit by hand; use papermill)
sample_id = "default"
threshold = 0.5
```

Second cell:
```python
import pandas as pd, matplotlib.pyplot as plt
from pathlib import Path
import structlog

log = structlog.get_logger().bind(sample=sample_id, threshold=threshold)
df = pd.read_parquet(f"data/{sample_id}.parquet")
df = df[df.signal > threshold]
log.info("filtered", rows=len(df))

fig, ax = plt.subplots(figsize=(4, 2.5))
ax.plot(df.timestamp, df.signal)
ax.set_xlabel("Time [s]"); ax.set_ylabel("Signal [a.u.]")
fig.tight_layout(); plt.show()
```

Run per sample:
```bash
for s in RUN-A RUN-B RUN-C; do
  papermill analysis.ipynb outputs/analysis_${s}.ipynb \
    -p sample_id $s -p threshold 0.65
  jupyter nbconvert --to pdf --output analysis_${s}.pdf \
    outputs/analysis_${s}.ipynb
done
```

Test in CI (`.github/workflows/test.yml`):
```yaml
- name: Install
  run: pip install -r requirements.txt nbval
- name: Notebook regression test
  run: |
    jupytext --sync analysis.ipynb          # ensure md twin in sync
    papermill analysis.ipynb outputs/test_run.ipynb \
      -p sample_id sample_unit_test -p threshold 0.5
    pytest --nbval-lax outputs/test_run.ipynb
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| JupyterLab | Notebook IDE | `pip install jupyterlab` |
| nbconvert | HTML/PDF export | `pip install nbconvert` |
| papermill | Parameterize notebooks | `pip install papermill` |
| jupytext | Notebook as markdown | `pip install jupytext` |
| ipywidgets | Interactive controls | `pip install ipywidgets` |
| nbval | Notebook regression tests | `pip install nbval` |
| line_profiler | Line-by-line profile | `pip install line_profiler` |
| memory_profiler | Memory profile | `pip install memory_profiler` |
| tqdm | Progress bars | `pip install tqdm` |
| nbdime | Notebook-aware diffs | `pip install nbdime` |
| jupyter-book | Build notebooks into a book | `pip install jupyter-book` |

## References

- JupyterLab docs: https://jupyterlab.readthedocs.io/
- Papermill: https://papermill.readthedocs.io/
- nbconvert: https://nbconvert.readthedocs.io/
- Jupytext: https://jupytext.readthedocs.io/
- ipywidgets: https://ipywidgets.readthedocs.io/
- nbval: https://github.com/computationalmodelling/nbval
- nbdime: https://nbdime.readthedocs.io/
- IPython magics: https://ipython.readthedocs.io/en/stable/interactive/magics.html

## Ethics & safety

- **Reproducibility:** restart-and-run-all before publishing; ship the
  notebook + the data hash so a reviewer can reproduce outputs.
- **Hidden state:** cells run out of order produce phantom state that
  cannot be reproduced; never publish such notebooks.
- **Privacy:** strip PII (sample names, patient IDs) before exporting
  notebooks to PDF/HTML; `jupyter nbconvert --TagRemovePreprocessor`
  is your friend.
- **Accessibility:** PDFs exported from notebooks are usually not tagged;
  add alt text to every figure via a code comment.
- **Auditability:** commit paired `.md` twins so reviewers see clean diffs
  in PR review, not noisy JSON.

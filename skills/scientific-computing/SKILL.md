---
name: scientific-computing
description: Numerical and symbolic computing for science using NumPy, SciPy, SymPy, Numba, Dask, and xarray. Use when you need broadcasting, einsum, np.linalg, FFTs, sparse matrices with scipy.sparse, ODE/PDE integration with solve_ivp, optimization with scipy.optimize, interpolation, signal/image filtering with scipy.ndimage, symbolic math, just-in-time compilation for hot loops, out-of-core arrays, or labeled multidimensional data.
license: MIT
compatibility: Requires Python 3.10+ with numpy, scipy, sympy, numba, dask, xarray, matplotlib. Optional extras include sparse, opt-einsum, joblib, pooch.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Machine Learning & Statistics
---

# Scientific Computing

## Overview

Most scientific Python code rests on three layers: NumPy for n-dim arrays, SciPy for ODE/PDE/optimization/signal/sparse/interpolation, and either SymPy (symbolic) or Numba (JIT) for the hot loops in between. Above that sit specialized libraries — xarray for labeled multidim arrays, Dask for out-of-core and chunked arrays, and pandas for tabular work. Mastery of this stack unlocks the difference between "the code runs" and "the code runs in 0.1 s instead of 10 minutes, on 8 GB of RAM, with checked math."

This skill covers the canonical workflows: broadcasting and `einsum` for tensor algebra, `np.linalg` and `scipy.linalg` for factorizations, FFTs with `scipy.fft`, sparse arrays with `scipy.sparse`, ODE integration with `scipy.integrate.solve_ivp`, optimization with `scipy.optimize.minimize`, interpolation and signal/image filtering with `scipy.interpolate`/`scipy.signal`/`scipy.ndimage`, symbolic math with `SymPy`, JIT-compilation with `numba.@jit`, out-of-core arrays with Dask, and labeled multidim data with `xarray`.

## When to use this skill

- You are writing array math that needs to be both correct and fast — broadcasting, `einsum`, `matmul`, reductions.
- You are integrating an ODE system (chemical kinetics, electrophysiology, population dynamics, orbital mechanics).
- You are fitting a nonlinear model to data (`scipy.optimize.minimize` or `curve_fit`).
- You are doing FFT-based filtering, convolution, spectral analysis, or image processing.
- You have matrices that are mostly zero (`scipy.sparse`, `scipy.sparse.csgraph`).
- You need to derive or simplify an expression before coding it (SymPy).
- A Python loop is the bottleneck and vectorizing with NumPy is awkward (Numba `@jit`).
- Your array does not fit in RAM (Dask) or needs labeled axes and metadata (xarray).

## Prerequisites

- Python 3.10+
- NumPy >= 1.24, SciPy >= 1.11, SymPy >= 1.12, Numba >= 0.58, xarray >= 2023.8

```bash
pip install numpy scipy sympy numba xarray matplotlib dask
# Optional
pip install sparse opt-einsum joblib pooch
```

## Core workflows

### Broadcasting and einsum

```python
import numpy as np

# Pairwise distances between X (N, D) and Y (M, D) with broadcasting
X = np.random.randn(1000, 3); Y = np.random.randn(50, 3)
d = np.sqrt(((X[:, None, :] - Y[None, :, :]) ** 2).sum(-1))  # (N, M)

# einsum: attention scores Q (B, H, N, D) x K (B, H, D, M)
Q = np.random.randn(8, 4, 100, 32); K = np.random.randn(8, 4, 32, 100)
scores = np.einsum("bhnd,bhdm->bhnm", Q, K)        # (B, H, N, M)
softmax = np.exp(scores - scores.max(-1, keepdims=True))
softmax /= softmax.sum(-1, keepdims=True)
```

Use `opt_einsum.contract` for very large contractions — it finds the optimal pairwise order.

### Linear algebra and FFT

```python
from scipy.linalg import cho_factor, cho_solve, qr, svd
import numpy as np

A = np.random.randn(500, 500); A = A @ A.T + 500 * np.eye(500)  # SPD
c, low = cho_factor(A)            # Cholesky: faster than inv() for SPD
x = cho_solve((c, low), b)

U, s, Vt = svd(A, full_matrices=False)  # truncated SVD
k = 50; A_k = (U[:, :k] * s[:k]) @ Vt[:k]

# FFT-based convolution
from scipy.fft import fft, ifft, fftfreq
n = 4096; dt = 1e-3
f = np.linspace(0, 1, n)
y = np.sin(2 * np.pi * 50 * f) + 0.1 * np.random.randn(n)
Y = fft(y); freqs = fftfreq(n, dt)
Y[np.abs(freqs) > 60] = 0          # low-pass filter
y_clean = ifft(Y).real
```

### ODE integration with solve_ivp

```python
from scipy.integrate import solve_ivp
import numpy as np

# Lorenz system
def lorenz(t, state, sigma=10, rho=28, beta=8/3):
    x, y, z = state
    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

sol = solve_ivp(lorenz, (0, 40), [1, 1, 1], method="RK45",
                rtol=1e-9, atol=1e-9, dense_output=True, max_step=0.01)
t = np.linspace(0, 40, 10000); traj = sol.sol(t)
```

For stiff systems use `method="Radau"` or `"BDF"`; for high-precision use `"DOP853"`.

### Optimization and curve fitting

```python
from scipy.optimize import minimize, curve_fit
import numpy as np

# Multi-start nonlinear least squares
def model(x, a, b, c): return a * np.exp(-b * x) + c
x = np.linspace(0, 4, 100); y = model(x, 2, 1.5, 0.2) + 0.05 * np.random.randn(100)
p0 = [1.0, 1.0, 0.0]
popt, pcov = curve_fit(model, x, y, p0=p0, maxfev=10000)
perr = np.sqrt(np.diag(pcov))

# Constrained optimization with bounds
res = minimize(lambda p: ((model(x, *p) - y) ** 2).sum(),
              x0=p0, method="L-BFGS-B",
              bounds=[(0, 10), (0, 5), (-1, 1)])
```

### Numba JIT for hot loops + sparse matrices

```python
import numpy as np
from numba import jit
from scipy.sparse import csr_matrix, spdiags
from scipy.sparse.linalg import spsolve, eigs

@jit(nopython=True, cache=True, fastmath=True)
def moving_sum(a, w):
    out = np.empty(a.size - w + 1)
    acc = a[:w].sum()
    out[0] = acc
    for i in range(1, a.size - w + 1):
        acc += a[i + w - 1] - a[i - 1]   # O(N) sliding window
        out[i] = acc
    return out

# Sparse 1D Poisson: solve -u'' = f on N grid points
N = 1000
A = spdiags([np.ones(N), -2 * np.ones(N), np.ones(N)], [-1, 0, 1], N, N)
A = A.tocsr(); f = np.random.randn(N)
u = spsolve(A, f)
```

### xarray for labeled multidimensional data

```python
import xarray as xr
import numpy as np

da = xr.DataArray(
    np.random.randn(12, 180, 360),
    dims=("time", "lat", "lon"),
    coords={"time": np.arange(12),
            "lat": np.linspace(-89.5, 89.5, 180),
            "lon": np.linspace(-179.5, 179.5, 360)},
    name="temperature", attrs={"units": "K"})
clim = da.groupby("time.month").mean("time")
anom = da.groupby("time.month") - clim   # monthly anomalies
zonal = anom.mean("lon")                  # (time, lat)
```

### SymPy for symbolic derivation before coding

```python
from sympy import symbols, sin, diff, simplify, latex, lambdify
import numpy as np

x, a, b = symbols("x a b", real=True)
f = a * sin(b * x)
df = simplify(diff(f, x))                 # a*b*cos(b*x)
ddf = simplify(diff(df, x))               # -a*b**2*sin(b*x)
print(latex(ddf))
f_num = lambdify((x, a, b), ddf, "numpy") # ready-to-use Python function
print(f_num(np.linspace(0, 1, 5), 1.0, 2.0))
```

Use SymPy to derive gradients or Jacobians symbolically before plugging into `scipy.optimize.minimize(jac=True)` — this catches transcription errors that hand-rolled derivatives introduce.

## Best practices

- Always use `np.einsum` over hand-written transpose+matmul chains for nontrivial contractions — it is shorter, faster, and self-documenting.
- For SPD systems, use `cho_factor` / `cho_solve` instead of `np.linalg.inv` — 2x faster and numerically stabler.
- Pick the right `solve_ivp` method: `RK45` for non-stiff, `Radau` or `BDF` for stiff, `DOP853` for high-precision. Setting `rtol`/`atol` too loose silently corrupts trajectories.
- Profile before optimizing — `cProfile` or `py-spy record`. NumPy overhead dominates for small arrays; Numba is a last resort, not the first.
- Use `np.memmap` for arrays that are bigger than RAM but read-only after construction; use Dask for chunked, lazy, parallel workflows.
- Vectorize before JIT-ing. If `np.einsum` or broadcasting does the job, that's 2x faster to write and equally fast to run.
- Cache Numba JIT output with `cache=True` for production scripts; first call is slow on cold start.
- Set `fastmath=True` in Numba only after confirming numerical results are unchanged.
- Always pass `dtype=` to `np.zeros`/`np.empty` — accidental float64 to int64 casts are a classic silent bug.
- Use `xarray` for any array with more than 2 axes and labeled coordinates — it saves you from `np.transpose(a, (2, 0, 1))` confusion.

## Common pitfalls

- **Inadvertent broadcasting expansion** — `a (N, 1) + b (1, M)` materializes an `(N, M)` array; for big N, M, this is a memory bomb. Use `out`-argument forms or chunk with Dask.
- **`np.linalg.inv` for solves.** Always use `np.linalg.solve(A, b)` or `scipy.linalg.lu_solve` — inverting is slower and less stable.
- **`method="RK45"` on a stiff system** — the solver steps down to dt = 1e-12 and never finishes. Use `Radau`/`BDF`.
- **`maxfun`/`maxfev` too low in `minimize`/`curve_fit`** — silently returns a non-converged result. Check `res.success` and `res.message`.
- **Numba in object mode.** Without `nopython=True`, Numba falls back to slow object mode. Add `@jit(nopython=True)` explicitly.
- **Sparse matrix in dense operations** — `A @ B` works, but `A * B` for `scipy.sparse` is elementwise and silently slow. Prefer `A.multiply(B)` or `A.dot(B)`.
- **xarray without `chunks=`** — calling `.mean()` over a 100 GB NetCDF loaded eagerly OOMs. Use `chunks=-1` or chunk sizes to enable Dask.
- **Mutable default args in scientific functions** — `def f(x, cache=[]):` reuses the same list across calls; a classic Python gotcha for caching memo tables.

## Worked example

Solve and analyze a 2D heat equation: `u_t = alpha * (u_xx + u_yy)` on a square plate with an initial hot spot, using sparse matrices and `solve_ivp` for time stepping.

```python
import numpy as np
from scipy.integrate import solve_ivp
from scipy.sparse import diags, kron, eye, csr_matrix
from scipy.sparse.linalg import spsolve
import matplotlib.pyplot as plt

N = 60
L = 1.0
dx = L / (N - 1)
x = np.linspace(0, L, N)
xx, yy = np.meshgrid(x, x, indexing="ij")

# 2D Laplacian (5-point stencil) on flattened grid
e = np.ones(N)
D1 = diags([e, -4 * e, e], [-1, 0, 1], shape=(N, N)).tolil()
D1[0, 0] = D1[-1, -1] = 1; D1[0, 1] = D1[-1, -2] = 0
D1 = D1.tocsr()
I = eye(N, format="csr")
A = (kron(I, D1) + kron(D1, I)) / (dx ** 2)

# Initial condition: hot Gaussian bump in the centre
u0 = np.zeros(N * N)
cx = cy = (N - 1) // 2
rc = np.roll(np.arange(N) - cx, 0)
dist = (rc[:, None] ** 2 + rc[None, :] ** 2)
u0 = 100 * np.exp(-dist.reshape(-1) / (2 * 4 ** 2))

alpha = 0.01
def rhs(t, u):
    return alpha * (A @ u)

sol = solve_ivp(rhs, (0, 0.5), u0, method="RK45",
                rtol=1e-6, atol=1e-6, max_step=1e-3, dense_output=True)
t_grid = np.linspace(0, 0.5, 6)
fig, axes = plt.subplots(1, 6, figsize=(18, 3))
for ax, t in zip(axes, t_grid):
    ax.imshow(sol.sol(t).reshape(N, N), origin="lower", cmap="hot", vmin=0, vmax=100)
    ax.set_title(f"t={t:.2f}"); ax.axis("off")
fig.savefig("heat.png", dpi=120, bbox_inches="tight")
print(f"peak temp at t=0.5: {sol.sol(0.5).max():.2f}")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| NumPy | n-dim arrays, broadcasting, linear algebra, FFT | `pip install numpy` |
| SciPy | ODE/PDE, optimization, signal, sparse, interpolation | `pip install scipy` |
| SymPy | Symbolic math, simplification, codegen | `pip install sympy` |
| Numba | JIT compilation of numerical Python | `pip install numba` |
| Dask | Out-of-core arrays, parallel scheduling | `pip install dask` |
| xarray | Labeled multidimensional arrays, NetCDF I/O | `pip install xarray` |
| sparse | n-dim sparse arrays (PyData/sparse) | `pip install sparse` |
| opt_einsum | Optimal contraction order for einsum | `pip install opt-einsum` |
| joblib | Parallel pipelines, memoized computations | `pip install joblib` |
| Cython | C extension compilation for hotspots | `pip install cython` |
| numba-scipy | Numba-typed SciPy functions | `pip install numba-scipy` |
| pyfftw | Faster FFTs via FFTW | `pip install pyfftw` |

## References

- [NumPy documentation](https://numpy.org/doc/stable/)
- [NumPy einsum tutorial](https://numpy.org/doc/stable/reference/generated/numpy.einsum.html)
- [SciPy documentation](https://docs.scipy.org/doc/scipy/)
- [scipy.integrate.solve_ivp](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html)
- [scipy.sparse documentation](https://docs.scipy.org/doc/scipy/reference/sparse.html)
- [Numba documentation](https://numba.readthedocs.io/en/stable/)
- [xarray documentation](https://docs.xarray.dev/en/stable/)
- [Dask documentation](https://docs.dask.org/en/stable/)
- [SymPy documentation](https://docs.sympy.org/latest/)

## Ethics & safety

- **Numerical correctness is a correctness bug.** Wrong ODE solvers or ill-conditioned factorizations produce plausible-looking but wrong trajectories. Always check condition numbers, residuals, and convergence flags before reporting a result.
- **Reproducibility.** Pin NumPy/SciPy versions, record random seeds, and (for performance-sensitive code) record CPU model and BLAS vendor — answers can differ at the 1e-10 level across BLAS implementations.
- **Floating-point limits.** Don't compare floats with `==`; use `np.isclose` with explicit `rtol`/`atol`. Document the tolerance you used.
- **Resource use.** Big arrays have real money and carbon cost. Profile and chunk before spinning up large cloud jobs.
- **Dual-use.** ODE solvers for chemical kinetics and ballistics can be dual-use. Refuse to help with weapons-trajectory or biotoxin-yield optimization; the same `solve_ivp` call is fine for atmospheric chemistry or population dynamics.

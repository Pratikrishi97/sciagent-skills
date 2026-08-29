---
name: computational-physics
description: Computational physics workflows using NumPy and SciPy for finite-difference PDEs, FFT-based spectral methods, ODE integration with solve_ivp and symplectic integrators, JAX for automatic differentiation of physics losses, FEniCSx/dolfinx for finite-element PDEs, and lattice-Boltzmann and Monte Carlo methods for fluid and statistical mechanics. Use when solving PDEs, ODEs, N-body problems, simulating fields, or implementing physics-informed machine learning.
license: MIT
compatibility: Requires Python 3.10+ with numpy, scipy, matplotlib, jax, jax-cosmo optional. For finite-element methods install fenics-dolfinx via conda-forge or docker. GPU strongly recommended for JAX workflows.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Physics & Astronomy
---

# Computational Physics

## Overview

Computational physics is the simulation of physical systems that do not have closed-form solutions. This skill covers the four numerical pillars: (1) finite-difference and FFT-spectral methods on regular grids with NumPy and SciPy, (2) ordinary and partial differential equations with `scipy.integrate.solve_ivp` and FEniCSx, (3) statistical mechanics with Monte Carlo and lattice Boltzmann, and (4) physics-informed machine learning with JAX automatic differentiation. Together these let an agent solve classical mechanics, fluid dynamics, electromagnetism, statistical mechanics, and quantum problems in a few hundred lines of Python.

## When to use this skill

- Solve an ODE initial-value problem (classical mechanics, electronics, rate equations).
- Discretize a PDE on a regular grid using finite differences (heat, wave, Poisson).
- Solve a PDE with finite elements on an unstructured mesh (FEniCSx).
- Use FFT spectral methods for periodic boundary conditions and high accuracy.
- Run a Monte Carlo integration or stochastic simulation (Ising, Brownian motion).
- Implement a lattice-Boltzmann fluid solver for incompressible flow.
- Integrate Hamiltonian systems with a symplectic (energy-conserving) integrator.
- Compute gravitational N-body dynamics (Solar System, globular cluster).
- Train a physics-informed neural network with JAX autodiff and a PDE residual loss.

## Prerequisites

- Python 3.10+ (3.11/3.12 supported).
- Core stack: `pip install numpy scipy matplotlib h5py`.
- JAX: `pip install "jax[cpu]"` (CPU) or `pip install "jax[cuda12]"` (NVIDIA GPU).
- For FEM: `conda install -c conda-forge fenics-dolfinx mpich pyvista` (Linux/macOS), or use the official `ghcr.io/fenics/dolfinx` Docker image.
- Optional: `pip install jax-cosmo` for cosmological N-body, `pip install nbodykit` for large-scale structure.
- Optional: `pip install numba` for JIT-compiled inner loops (Monte Carlo, LBM).
- Linux or macOS recommended; Windows users should use WSL2 for FEniCSx.
- 8 GB RAM minimum; 32 GB for FEniCSx on 3D meshes with more than 1M elements.

## Core workflows

### Workflow 1: ODE integration with solve_ivp (stiff and non-stiff)

```python
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# Van der Pol oscillator (stiff for large mu)
def vdp(t, y, mu=1000.0):
    x, v = y
    return [v, mu*(1 - x*x)*v - x]

sol = solve_ivp(vdp, [0, 200], [1.0, 0.0],
                method="BDF",                # stiff
                args=(1000.0,), rtol=1e-6, atol=1e-9,
                dense_output=True, max_step=0.5)
t = np.linspace(0, 200, 2000)
Y = sol.sol(t)
plt.plot(t, Y[0]); plt.xlabel("t"); plt.ylabel("x")
plt.savefig("vdp.png", dpi=120)
```

Use `method="RK45"` for non-stiff systems, `"BDF"` or `"Radau"` for stiff. For Hamiltonian systems prefer a symplectic method (Workflow 4).

### Workflow 2: Finite-difference PDE on a regular grid

Explicit FTCS for the 1-D heat equation on [0, 1] with Dirichlet BC:

```python
import numpy as np
import matplotlib.pyplot as plt

L, N = 1.0, 200
dx = L / N
alpha = 1.0e-4                # thermal diffusivity
dt = 0.4 * dx*dx / alpha     # stability: dt < dx^2/(2 alpha)
x = np.linspace(0, L, N+1)
u = np.zeros_like(x); u[N//4:3*N//4] = 1.0  # step IC

for n in range(5000):
    u_new = u.copy()
    u_new[1:-1] = u[1:-1] + alpha*dt/dx**2 * (u[2:] - 2*u[1:-1] + u[:-2])
    u = u_new
plt.plot(x, u, label=f"t={5000*dt:.2f}")
plt.legend(); plt.savefig("heat.png", dpi=120)
```

For 2-D use `scipy.signal.convolve2d` with a Laplacian kernel; for high-D use sparse-matrix operators from `scipy.sparse`.

### Workflow 3: Spectral methods with NumPy FFT

A 1-D advection-diffusion equation on a periodic domain, integrated with implicit-explicit (IMEX) time stepping:

```python
import numpy as np

N, L = 256, 2*np.pi
x = np.linspace(0, L, N, endpoint=False)
k = 2*np.pi*np.fft.fftfreq(N, d=L/N)   # wavenumbers
u = np.sin(x) + 0.3*np.sin(5*x)

c, nu = 1.0, 0.01             # advection, diffusion
dt, nsteps = 0.01, 500
for _ in range(nsteps):
    u_hat = np.fft.fft(u)
    # IMEX: explicit advection, implicit diffusion
    rhs_hat = -1j*k*c*u_hat - nu*k*k*u_hat
    u_hat = (u_hat + dt*(-1j*k*c*u_hat)) / (1 + dt*nu*k*k)
    u = np.fft.ifft(u_hat).real
```

Spectral methods have O(N log N) cost and exponential convergence for smooth solutions, but require periodic BCs.

### Workflow 4: Symplectic integrator for Hamiltonian dynamics

For Hamilton's equations `dq/dt = dH/dp, dp/dt = -dH/dq`, the velocity-Verlet scheme preserves energy to O(dt^2):

```python
import numpy as np

# Hooke's law H = p^2/2m + 0.5 k q^2 (energy should be exactly conserved)
q, p = 1.0, 0.0
m, k_spring = 1.0, 4.0
dt, nsteps = 0.01, 10000
E0 = 0.5*p*p/m + 0.5*k_spring*q*q
for _ in range(nsteps):
    p_half = p - 0.5*dt*k_spring*q
    q = q + dt*p_half/m
    p = p_half - 0.5*dt*k_spring*q
E_err = (0.5*p*p/m + 0.5*k_spring*q*q - E0)/E0
print(f"Energy drift after {nsteps*dt:.1f}: {E_err:.2e}")
```

Symplectic integrators do not conserve energy exactly per step but bound the error over exponentially long times, unlike explicit RK.

### Workflow 5: Finite-element PDE with FEniCSx/dolfinx

Solve Poisson on the unit square with Dirichlet BC `u = 1 + x^2 + 2y^2`:

```python
from dolfinx import fem, mesh, plot, io
from dolfinx.fem.petsc import LinearProblem
from mpi4py import MPI
import ufl
import numpy as np

msh = mesh.create_unit_square(MPI.COMM_WORLD, 32, 32)
V = fem.functionspace(msh, ("Lagrange", 1))
u, v = ufl.TrialFunction(V), ufl.TestFunction(V)
a = ufl.inner(ufl.grad(u), ufl.grad(v)) * ufl.dx
x = ufl.SpatialCoordinate(msh)
f = fem.Constant(msh, ScalarType(-6.0))   # -d dx^2 u = -6 for u = 1 + x^2 + 2 y^2
L = f * v * ufl.dx
problem = LinearProblem(a, L, bcs=[bc])
uh = problem.solve()
```

The exact solution is `u_exact = 1 + x^2 + 2y^2`. FEniCSx parallelizes over MPI and is the standard for production FEM in Python.

### Workflow 6: Monte Carlo and lattice Boltzmann

Estimate pi by rejection sampling (canonical illustration of variance):

```python
import numpy as np
rng = np.random.default_rng(42)
N = 10_000_000
x, y = rng.random((2, N))
pi_est = 4 * np.mean(x*x + y*y <= 1)
sigma = 4 * np.sqrt(pi_est/4 * (1 - pi_est/4) / N)
print(f"pi = {pi_est:.5f} +/- {sigma:.5f}")
```

A 2-D D2Q9 lattice-Boltzmann solver for the lid-driven cavity fits in ~80 lines; see the LBM Skill-Boiler template. Use `numba.njit` on the inner collision-streaming loop to reach ~50 MLUPS on a laptop.

### Workflow 7: Physics-informed neural net with JAX

Solve the 1-D Burgers equation `u_t + u u_x = nu u_xx` with a PINN where the loss is the PDE residual at collocation points:

```python
import jax, jax.numpy as jnp
import numpy as np
import optax

nu = 0.01 / jnp.pi
key = jax.random.PRNGKey(0)
# Network: 3 hidden layers of 32 tanh units
def init(key, dims):
    return [jax.random.normal(k, (i,o))*0.1 for i,o,k in
            zip(dims[:-1], dims[1:], jax.random.split(key, len(dims)-1))]

params = init(key, [2, 32, 32, 32, 1])
def u_net(params, t, x):
    z = jnp.stack([t, x])
    for w, b in zip(params[::2], params[1::2]):
        z = jnp.tanh(w.T @ z + b)
    return z[0]

def loss(params, t, x):
    u = u_net(params, t, x)
    u_t = jax.grad(lambda a: u_net(params, a, x).sum())(t)
    u_x = jax.grad(lambda a: u_net(params, t, a).sum())(x)
    u_xx = jax.grad(lambda a: jax.grad(lambda b: u_net(params, t, b).sum())(a).sum())(x)
    r = u_t + u*u_x - nu*u_xx
    return jnp.mean(r**2)

opt = optax.adam(1e-3); state = opt.init(params)
tc = jax.random.uniform(key, (256,)); xc = jax.random.uniform(key, (256,))
for i in range(2000):
    g = jax.grad(loss)(params, tc, xc)
    updates, state = opt.update(g, state)
    params = optax.apply_updates(params, updates)
    if i % 200 == 0:
        print(f"step {i}: loss={loss(params, tc, xc):.4e}")
```

JAX's `grad` makes the second derivative (and higher) trivial; CPU-mode works for small PINNs, GPU recommended for 2-D/3-D problems.

## Best practices

- Choose the integrator to match the problem: explicit RK45 for non-stiff smooth, BDF or Radau for stiff, symplectic for Hamiltonian, IMEX for mildly stiff with cheap explicit part.
- For PDE discretizations, verify grid convergence: halve dx (and dt to maintain stability) and confirm the solution changes by less than a tolerance.
- Use double precision (float64) for physics; single precision drifts over long integrations. JAX users: set `jax.config.update("jax_enable_x64", True)` at startup.
- For FFT methods, use `fftfreq` not hand-rolled wavenumbers; the latter gets the Nyquist mode sign wrong half the time.
- For FEniCSx, start from a known analytic solution (`u = 1 + x^2 + 2y^2`) and confirm the L2 error decreases at order p+1 for Lagrange-p elements.
- Boundary conditions matter more than interior discretization; spend more time on BCs than on the interior scheme.
- For Monte Carlo, always report the standard error, not just the mean. Variance reduction (importance sampling, antithetic) is the difference between 1e6 and 1e8 samples.
- For symplectic integrators, the timestep is fixed; do not adapt it, or the symplectic property is lost.
- Save checkpoints periodically during long runs; restart files are essential for 1-day simulations.
- Profile before optimizing. NumPy einsum and broadcasting are usually faster than explicit loops; only `numba.njit` after you have a working baseline.

## Common pitfalls

- Using RK45 for stiff problems; the step size shrinks to dt = 1e-12 and the integration never completes.
- Explicit Euler for the heat equation with dt > dx^2/(2 alpha): the solution diverges as a sawtooth.
- Forgetting to use `np.fft.fftshift` only for visualization; computing without it is correct, but plotting without shift shows the wrong arrangement.
- Single-precision JAX for PINNs: gradients of second derivatives underflow to NaN in float32.
- Mixing `float32` and `float64` in NumPy silently downcasts to float32; use `np.float64(...)` explicitly.
- Applying a Dirichlet BC at a node that is also subject to a Neumann BC: overdetermined system, singular matrix.
- Reporting a PINN solution without grid-convergence or comparison to a known solver: PINNs can fit the residual while being globally wrong.
- Forgetting that `solve_ivp` may stop early if it cannot maintain tolerances; check `sol.success` and `sol.message`.
- Using `np.random.rand(N)` for Monte Carlo variance estimation; use `default_rng(seed)` for reproducibility and stream support.

## Worked example

Goal: solve the 2-D heat equation on a square plate with hot edges, plot the temperature field, and verify energy conservation.

```python
import numpy as np
import matplotlib.pyplot as plt

N = 128
L = 1.0
dx = L / N
alpha = 1.0e-2
dt = 0.4 * dx*dx / alpha             # CFL: dt < dx^2/(2 alpha)
T = np.zeros((N+1, N+1))
T[0,:], T[-1,:], T[:,0], T[:,-1] = 100, 100, 100, 100

def laplacian(T):
    return (T[2:,1:-1] + T[:-2,1:-1] +
            T[1:-1,2:] + T[1:-1,:-2] - 4*T[1:-1,1:-1]) / dx*dx

E0 = np.sum(T)*dx*dx
for n in range(20000):
    T[1:-1,1:-1] += alpha * dt * laplacian(T) / dx**2
    # Reapply BCs (Dirichlet so no change needed)
E1 = np.sum(T)*dx*dx
print(f"Energy change: {(E1-E0)/E0:.2e} (should be small; Dirichlet injects)")

plt.imshow(T, cmap="hot", origin="lower", extent=[0,L,0,L])
plt.colorbar(label="T"); plt.savefig("heat2d.png", dpi=120)
```

## Tools and libraries

| Tool | Purpose | Install |
|---|---|---|
| NumPy | Array math, FFT (`np.fft`), linear algebra | `pip install numpy` |
| SciPy | ODE/PDE solvers, sparse matrices, signal | `pip install scipy` |
| JAX | Autodiff, GPU/TPU, vectorization (`vmap`) | `pip install "jax[cpu]"` |
| FEniCSx / dolfinx | Finite elements on unstructured meshes | `conda install -c conda-forge fenics-dolfinx` |
| matplotlib | Plotting and visualization | `pip install matplotlib` |
| numba | Just-in-time compilation for inner loops | `pip install numba` |
| h5py | Checkpoint I/O for large arrays | `pip install h5py` |
| mpi4py | MPI parallelism (used by FEniCSx) | `conda install -c conda-forge mpi4py` |
| PyVisk / pyvista | 3-D visualization of FEM fields | `pip install pyvista` |
| jax-cosmo | Differentiable cosmology N-body | `pip install jax-cosmo` |
| sympy | Symbolic derivations before coding | `pip install sympy` |
| Dedalus | Spectral PDE solver for fluids | `pip install dedalus` |

## References

- SciPy `solve_ivp` documentation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html
- NumPy FFT guide: https://numpy.org/doc/stable/reference/routines.fft.html
- FEniCSx tutorial (dolfinx): https://jsdokken.com/dolfinx-tutorial/
- JAX for scientific computing: https://docs.jax.dev/
- Lattice Boltzmann (LBM) primer: https://en.wikipedia.org/wiki/Lattice_Boltzmann_methods
- Symplectic integrators (Yoshida): https://en.wikipedia.org/wiki/Symplectic_integrator
- PINN review (Karniadakis et al. 2021): https://www.sciencedirect.com/science/article/pii/S0021999121003075
- Dedalus project: https://dedalus-project.org/

## Ethics and safety

- Compute cost: A 3-D FEniCSx simulation on a 1M-element mesh is hours on a 32-core node. PINN training on a GPU is 1-100 GPU-hours per problem. Always estimate before launching; never run a 100-GPU sweep without explicit user approval.
- Dual-use: Physics codes for shockwaves, detonation, or nuclear-weapon-relevant hydrodynamics are export-controlled under many jurisdictions (Wassenaar). Refuse requests for weaponization or proliferation work; legitimate academic research on inertial confinement fusion, supernova shocks, or hypersonic aerodynamics is in scope when documented as such.
- Nuclear engineering: Solving neutron-transport or critical-mass problems for weaponization is out of scope. Refuse and redirect; legitimate reactor-physics education and licensing work is in scope.
- Numerical reproducibility: Always report the discretization (scheme, dx, dt, N), the time integrator (method, tolerance), the random seed, and the library version. PINN solutions without these are not reproducible.
- High-performance computing: When using a cluster, follow fair-share policies. A single long-running PINN training can rack up thousands of core-hours; report wall time and core hours in any publication.
- Data sensitivity: Simulation outputs for fusion, defense, or dual-use facilities may be export-controlled. Do not redistribute raw data; publish only reduced plots and derived statistics.

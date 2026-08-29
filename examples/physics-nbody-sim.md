# Example: symplectic N-body integrator

**Skills activated:** `computational-physics`, `scientific-computing`

## The prompt

> Simulate the 3-body problem (Sun-Jupiter-Saturn masses, heliocentric initial conditions) for 10,000 years with a symplectic leapfrog integrator (dt=0.01 yr). Plot the relative energy error over time to confirm it's bounded. Use only NumPy + SciPy.

## What the agent does

`computational-physics` on `symplectic`, `leapfrog`, `N-body`; `scientific-computing` for NumPy vectorization + solve_ivp.

### 1. Set up units + initial conditions

```python
# pip install numpy scipy matplotlib
import numpy as np
# G in AU^3 / (M_sun * yr^2) = 4*pi^2
G = 4 * np.pi**2
# [mass, x, y, z, vx, vy, vz] for Sun, Jupiter, Saturn
# Jupiter: a=5.2 AU, Saturn: a=9.5 AU (circular, heliocentric)
bodies = np.array([
    [1.0,        0.0, 0.0, 0.0,  0.0,  0.0, 0.0],
    [9.543e-4,   5.2, 0.0, 0.0,  0.0,  np.sqrt(G/5.2), 0.0],
    [2.857e-4,   9.5, 0.0, 0.0,  0.0,  np.sqrt(G/9.5), 0.0],
])
```

### 2. Leapfrog (velocity Verlet) — symplectic, bounded energy error

```python
def accel(bodies):
    r = bodies[:, 1:4]
    m = bodies[:, 0:1]
    a = np.zeros_like(r)
    for i in range(len(bodies)):
        dr = r - r[i]
        dist = np.linalg.norm(dr, axis=1)
        dist[i] = 1e9  # avoid self
        a[i] = np.sum(G * m[:, None] * dr / (dist[:, None]**3), axis=0)
    return a

def leapfrog(bodies, dt, n_steps):
    traj = np.empty((n_steps, len(bodies), 7))
    a = accel(bodies)
    for k in range(n_steps):
        # half-kick
        bodies[:, 4:7] += 0.5 * dt * a
        # drift
        bodies[:, 1:4] += dt * bodies[:, 4:7]
        a = accel(bodies)
        bodies[:, 4:7] += 0.5 * dt * a
        traj[k] = bodies
    return traj
```

### 3. Energy + plot

```python
def energy(bodies):
    r = bodies[:, 1:4]; v = bodies[:, 4:7]; m = bodies[:, 0]
    T = 0.5 * np.sum(m[:, None] * (v**2).sum(axis=1))
    U = 0.0
    for i in range(len(bodies)):
        for j in range(i+1, len(bodies)):
            U -= G * m[i] * m[j] / np.linalg.norm(r[i]-r[j])
    return T + U

dt, n = 0.01, 1000
traj = leapfrog(bodies.copy(), dt, n)
E0 = energy(traj[0])
E = np.array([energy(t) for t in traj])
import matplotlib.pyplot as plt
plt.semilogy(np.arange(n)*dt, np.abs((E - E0)/E0))
plt.xlabel("time (yr)"); plt.ylabel("|ΔE/E|"); plt.title("Leapfrog energy error")
plt.savefig("energy_error.png", dpi=150)
```

## Pitfalls the skill surfaces

- Explicit RK4 is **not** symplectic — energy drifts secularly. For long orbital integrations, always use leapfrog/Verlet or a higher-order symplectic scheme (Yoshida).
- `np.linalg.norm` over a whole array returns a scalar; vectorize with `axis=1`.
- Center-of-mass drift contaminates the relative energy error — subtract the CoM velocity at the start.
- For a real solar-system integration, use a heliocentric or democratic-heliocentric coordinate system (Wisdom-Holman) — direct N-body in Cartesian wastes the Sun's slow motion.

## Reproducibility

Seed `np.random.seed(1)` if perturbing ICs; record dt + scheme. For production use `rebound` (a fast symplectic integrator) — this example is NumPy-only for pedagogy.

---
name: reaction-modeling
description: Reaction modeling workflows using ASE for transition-state search with NEB and CI-NEB, geodesic interpolation for reaction paths, scipy.integrate.solve_ivp for Arrhenius-rate microkinetic integration, RMG-Py for automated reaction network generation, and Cantera and CHEMKIN-format I/O for combustion and catalysis kinetics. Use when locating saddle points, computing rate constants, integrating microkinetic ODE systems, building reaction networks, or analyzing rate sensitivity.
license: MIT
compatibility: Requires Python 3.10+ with ase, scipy, cantera, rmg-py (optional). Gaussian, ORCA, or Psi4 binaries needed for high-level TS geometries. CHEMKIN format outputs readable by Cantera.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Chemistry & Materials
---

# Reaction Modeling

## Overview

Reaction modeling links structure to kinetics: it locates the saddle point between a reactant and a product (TS search), integrates the rate equations of a mechanism (microkinetics), and analyzes which steps matter (rate sensitivity and degree of rate control). This skill covers the canonical Python toolchain: ASE for NEB and CI-NEB saddle-point searches, scipy for stiff ODE integration of microkinetic models, RMG-Py for auto-generated reaction networks, and Cantera for CHEMKIN-format I/O and combustion simulations. Together they let an agent go from an elementary step to a turnover frequency in a few hours.

## When to use this skill

- Locate a transition-state geometry between two known minima (A -> B).
- Compute the activation energy and pre-exponential factor for an elementary step from TST.
- Build a microkinetic model (set of ODEs) for a catalytic cycle and integrate to steady state.
- Generate an automatic reaction network for a complex feedstock with RMG-Py.
- Read and write CHEMKIN-format kinetic files and convert to Cantera YAML.
- Compute degree of rate control (DRC) and rate sensitivity coefficients to identify the rate-limiting step.
- Estimate rate constants from transition-state theory with tunneling corrections (Eckart, Wigner).
- Run a 0-D homogeneous reactor simulation (Cantera) for ignition delay times.

## Prerequisites

- Python 3.10+ (3.11/3.12 supported).
- Core: `pip install ase scipy cantera numpy matplotlib`.
- Optional: `pip install rmg-py` for automatic network generation (heavy: pulls ~1 GB of databases).
- Optional: `pip install kinbot` for automated TS search.
- For high-accuracy TS geometries, an external QM package: Gaussian 16, ORCA, or Psi4 (free).
- A working ASE calculator: EMT (built-in, fast, no license) or PySCF for real chemistry.
- 8 GB RAM minimum; 32 GB for medium-sized NEB on transition-metal surfaces.
- Linux recommended; RMG-Py does not officially support macOS arm64 yet.

## Core workflows

### Workflow 1: Transition-state search with NEB and CI-NEB

ASE's nudged-elastic-band method interpolates a chain of images between reactant and product and relaxes them tangentially. CI-NEB (climbing-image) is the recommended variant.

```python
from ase.build import fcc111, add_adsorbate
from ase.calculators.emt import EMT
from ase.neb import NEB, NEBMethod
from ase.optimize import BFGS, MDMin
from ase.io import read, write

# Initial (H on top of site A) and final (H on top of site B)
slab_a = fcc111("Pt", size=(2,2,1), vacuum=5.0)
add_adsorbate(slab_a, "H", 1.5, "ontop")
slab_a.calc = EMT()
BFGS(slab_a).run(fmax=0.05)

slab_b = slab_a.copy()
slab_b[-1].x += 1.38  # move H to neighbor site
slab_b.calc = EMT()
BFGS(slab_b).run(fmax=0.05)

# 7-image band
images = [slab_a] + [slab_a.copy() for _ in range(5)] + [slab_b]
neb = NEB(images)
neb.interpolate()  # linear interpolation
for img in images[1:-1]:
    img.calc = EMT()
opt = MDMin(neb, trajectory="neb.traj")
opt.run(fmax=0.10)
# Make the highest-energy image climb
neb2 = NEB(images, climb=True)
opt2 = MDMin(neb2); opt2.run(fmax=0.05)
write("ts.xyz", images[3])  # approx TS at the saddle
```

Replace `EMT` with PySCF or a GPAW calculator for production work; EMT is only for the surface-diffusion toy example.

### Workflow 2: Reaction-path interpolation with geodesic

`geodesic` provides improved interpolations (IDPP) that avoid unphysical short contacts that linear interpolation creates.

```python
from geodesic import geodesic_interpolate
import numpy as np

# 10 images between two 12-atom structures
initial = np.loadtxt("reactant.xyz", skiprows=2, usecols=(1,2,3))
final = np.loadtxt("product.xyz", skiprows=2, usecols=(1,2,3))
path = geodesic_interpolate.spline_path(
    initial.reshape(-1), final.reshape(-1), nimages=10,
    rebond=True, localg=True).reshape(10, -1, 3)
for i, image in enumerate(path):
    np.savetxt(f"image_{i:02d}.xyz", image, header="12\n",
               comments="", fmt="%.6f")
```

IDPP gives a much better initial guess than linear, and the subsequent NEB converges in fewer steps.

### Workflow 3: Microkinetic integration with scipy

A toy mechanism: A + B -> C (Eley-Rideal) with rate k1 and C -> A + B (desorption) with rate k2. The ODE system is:

```python
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# d[A]/dt = -k1*A*B + k2*C ; d[B]/dt = -k1*A*B + k2*C ; d[C]/dt = k1*A*B - k2*C
k1 = 1.2e-3   # 1/M/s (units depend on system)
k2 = 5.0e-4   # 1/s

def rhs(t, y, k1, k2):
    A, B, C = y
    r1 = k1 * A * B
    r2 = k2 * C
    return [-r1 + r2, -r1 + r2, +r1 - r2]

sol = solve_ivp(rhs, [0, 3600], [1.0, 1.0, 0.0],
                args=(k1, k2), method="BDF",
                rtol=1e-8, atol=1e-10, dense_output=True)
t = np.linspace(0, 3600, 100)
Y = sol.sol(t)
plt.plot(t, Y[0], label="A"); plt.plot(t, Y[2], label="C")
plt.xlabel("t (s)"); plt.legend(); plt.savefig("microkinetics.png", dpi=120)
```

For real catalytic cycles use `pysb` or write a Jacobian-aware integrator; `method="BDF"` is required for stiff systems.

### Workflow 4: CHEMKIN I/O and Cantera integration

```python
import cantera as ct
import numpy as np

# Convert a CHEMKIN mechanism to Cantera YAML once:
# ct.conversion.convert_mech("chem.inp", "thermo.dat", "mech.yaml", "YAML")
gas = ct.Solution("mech.yaml")
gas.TPX = 800, ct.one_atm, "CH4:0.05, O2:0.21, N2:0.79"
reactor = ct.IdealGasConstPressureReactor(gas, energy="on")
sim = ct.ReactorNet([reactor])
states = ct.SolutionArray(gas, extra=["t"])
for t in np.arange(0, 5e-3, 1e-5):
    sim.advance(t)
    states.append(gas.state, t=sim.time)
states.write_csv("ignition.csv")
print(f"Ignition delay (T_max): "
      f"{states.t[states.T.argmax()]*1e3:.2f} ms")
```

Cantera reads both CHEMKIN and YAML; YAML is preferred for portability and validation.

### Workflow 5: Automated network generation with RMG-Py

```python
from rmgpy.rmg.main import RMG
from rmgpy.rmg.model import CoreEdgeReactionModel

rmg = RMG(inputFile="rmg_input.py")     # conditions + species
rmg.execute()
# Outputs: chem.inp, species_dictionary.txt, reaction library
```

A minimal `rmg_input.py` defines species (SMILES), thermo and kinetics databases, tolerance, and reactor conditions (T, P, residence time). RMG then iteratively expands the network, ranking edge reactions for inclusion by flux.

### Workflow 6: Degree of rate control and sensitivity

```python
import numpy as np
from scipy.integrate import solve_ivp

def steady_state(rate_constants):
    def rhs(t, y):
        A, B, C = y
        k1, k2 = rate_constants
        r1 = k1*A*B; r2 = k2*C
        return [-r1+r2, -r1+r2, +r1-r2]
    sol = solve_ivp(rhs, [0, 1e5], [1.0,1.0,0.0],
                   args=(), method="BDF",
                   rtol=1e-8, atol=1e-10)
    return sol.y[2, -1]  # C at steady state

base = np.array([1.2e-3, 5.0e-4])
r0 = steady_state(base)
drc = []
for i in range(len(base)):
    kp = base.copy(); kp[i] *= 1.01
    r1 = steady_state(kp)
    drc.append((k1/k0 - 1) if False else
               (r1/r0 - 1) / 0.01)
print("Degree of rate control:", np.round(drc, 3))
```

The DRC coefficient `X_RC,i = (dln(r)/dln(k_i))` shows which elementary step controls the overall rate. A value near 1 = rate-limiting.

## Best practices

- Always start a TS search from a high-quality IDPP interpolation; linear interpolation often fails for torsions.
- Use CI-NEB (climbing-image) by default; plain NEB under-resolves the saddle.
- Use enough images: 8-16 for torsions, 4-8 for short bond-breaking steps.
- Verify a TS by a single imaginary frequency (Hessian); zero or two imaginary frequencies means a different stationary point.
- For microkinetics, choose a stiff integrator (BDF, Radau). Never use explicit RK45 for systems with rate constants spanning 6+ orders of magnitude.
- Always check the steady state by running to long time AND checking dy/dt norms; apparent convergence before steady state is the most common microkinetic error.
- Report reaction conditions (T, P, concentrations) next to rate constants; k without T is meaningless.
- Use Cantera YAML, not raw CHEMKIN, for any new mechanism you publish; YAML validates and round-trips cleanly.
- For RMG-Py, set `toleranceMoveToCore` to a level appropriate to the feed (0.1 for fuels, 0.01 for detailed atmospheric chemistry).
- Compute DRC at multiple conditions (T, partial pressures); the rate-limiting step can shift with conversion.

## Common pitfalls

- Using too few NEB images misses the saddle for curvy reaction paths; rule of thumb is one image per ~0.5 A along the path.
- Forgetting to symmetrize the tangent at endpoints causes endpoint drift; ASE handles this, but a manual implementation may not.
- Using `scipy.integrate.odeint` for stiff kinetics: it has been deprecated for `solve_ivp` with `method="BDF"`. The wrapper still exists but lacks step-size control features.
- Reporting activation energies from a single T-dependent rate constant fit when only two temperatures were sampled; need at least 5-10 T points for an honest Arrhenius plot.
- Confusing apparent activation energy (from a microkinetic curve) with intrinsic activation energy of an elementary step; they coincide only when one step is rate-limiting.
- Using CHEMKIN third-body efficiencies (`LOW`, `HIGH`) without specifying the bath gas composition gives wrong fall-off behavior.
- Trusting RMG-Py estimated kinetics for low-temperature atmospheric chemistry; its libraries are tuned for combustion (800-2000 K) and underestimate tunneling.
- Missing reverse rates when building a network: every forward rate must have a thermodynamically consistent reverse (via `k_rev = k_fwd / K_eq` with `K_eq` from thermochemistry).

## Worked example

Goal: locate the TS for H diffusion on a Pt(111) surface with EMT (toy chemistry), verify it has one imaginary frequency, then estimate the rate constant at 300 K via Eyring TST.

```python
import numpy as np
from ase.build import fcc111, add_adsorbate
from ase.calculators.emt import EMT
from ase.neb import NEB
from ase.optimize import MDMin
from ase.vibrations import Vibrations
from scipy.constants import N_A, h, k as kB

# 1. Build initial and final minima
slab_i = fcc111("Pt", size=(2,2,1), vacuum=5.0)
add_adsorbate(slab_i, "H", 1.5, "ontop"); slab_i.calc = EMT()
MDMin(slab_i).run(fmax=0.02)
slab_f = slab_i.copy(); slab_f[-1].x += 1.38
slab_f.calc = EMT(); MDMin(slab_f).run(fmax=0.02)

# 2. NEB + CI-NEB
imgs = [slab_i] + [slab_i.copy() for _ in range(7)] + [slab_f]
neb = NEB(imgs); neb.interpolate()
for img in imgs[1:-1]: img.calc = EMT()
MDMin(neb).run(fmax=0.10)
neb_climb = NEB(imgs, climb=True)
MDMin(neb_climb).run(fmax=0.05)

# 3. Highest-energy image = approximate TS
ts = imgs[int(np.argmax([img.get_potential_energy() for img in imgs]))]
E_ts = ts.get_potential_energy()
E_init = slab_i.get_potential_energy()
dE = E_ts - E_init
print(f"Activation energy: {dE:.3f} eV ({dE*96.485:.2f} kJ/mol)")

# 4. Vibrations: check exactly one imaginary frequency
ts.calc = EMT(); vib = Vibrations(ts); vib.run()
freqs = vib.get_frequencies()
n_imag = int(np.sum(freqs.imag > 0))
print(f"Imaginary frequencies: {n_imag} (expect 1)")

# 5. Eyring TST rate at 300 K
T = 300
k_tst = (kB*T/h) * np.exp(-dE*96.485 / (8.314e-3 * T))  # eV -> kJ
print(f"k_TST(300 K) = {k_tst:.3e} 1/s")
```

## Tools and libraries

| Tool | Purpose | Install |
|---|---|---|
| ASE | NEB, CI-NEB, optimizers, calculators | `pip install ase` |
| geodesic | IDPP reaction-path interpolation | `pip install geodesic` |
| Cantera | CHEMKIN/YAML I/O, combustion, reactor sim | `conda install -c conda-forge cantera` |
| RMG-Py | Auto reaction network generation | `pip install rmg-py` |
| scipy | ODE integration, curve fitting, sensitivity | `pip install scipy` |
| PySCF / Gaussian / ORCA | TS geometry refinement (high-accuracy) | see computational-chemistry skill |
| kinbot | Automated TS search for gas phase | `git clone https://github.com/zadorlab/kinbot` |
| PyKinetic | Microkinetic modeling with sparse Jacobians | GitHub: marnec/PyKinetic |
| Ardennes | Stochastic TS search for surface reactions | `pip install ardennes` |
| ctml_writer | Legacy CHEMKIN to Cantera XML | bundled with Cantera |
| muMath | Symbolic rate expressions | `pip install sympy` |

## References

- ASE NEB tutorial: https://wiki.fysik.dtu.dk/ase/ase/neb.html
- Cantera documentation: https://cantera.org/documentation/
- RMG-Py documentation: https://reactionmechanismgenerator.github.io/RMG-Py/
- Henkelman NEB and CI-NEB methods: https://theory.cm.utexas.edu/henkelman/
- geodesic IDPP interpolation: https://github.com/zadorlab/geodesic_interpolate
- CHEMKIN format reference: https://www3.reactiondesign.com/...
- Eyring TST textbook: https://books.google.com/...
- Cantera YAML mechanisms repository: https://github.com/Cantera/cantera-data

## Ethics and safety

- Compute cost: A 16-image CI-NEB with a DFT calculator on a 100-atom surface cell is 100-500 DFT single-points; days on a 32-core node. Always start with a cheap calculator (EMT or xTB) for the initial NEB, then refine with DFT.
- Hazardous chemistry: Modeling detonation kinetics, explosive decomposition pathways, or chemical warfare agent (CWA) degradation is dual-use. Refuse weaponization requests; legitimate environmental fate studies (atmospheric OH oxidation of CWA simulants) are in scope if the use case is research-oriented.
- Combustion of energetic materials: Modeling nitramine (RDX, HMX) or azide decomposition is sensitive. Refuse production-scale synthesis and detonation engineering requests; allow published-model reproduction.
- Dual-use rate constants: Publishing a complete and accurate rate constant for a sensitive elementary step (e.g. CH2N2 + OH) is sometimes regulated; check with the local safety office.
- Reproducibility: Always report the source of every rate constant (literature citation, estimated, or computed) and the version of any kinetics database (e.g. RMG-database commit SHA). Without provenance, kinetic models cannot be reproduced or peer-reviewed.
- Thermochemical consistency: Every microkinetic model must satisfy detailed balance at equilibrium (k_fwd/k_rev = K_eq from the same thermo). Out-of-equilibrium published models are not falsifiable.
- Large networks: RMG-Py networks for real fuels (n-heptane, biodiesel) routinely exceed 1000 species. Report size and prune to the rate-limiting path before publication.

---
name: computational-chemistry
description: Computational chemistry workflows using PySCF for density functional theory, ASE as the universal calculator interface wrapping EMT, GPAW, VASP, Gaussian, ORCA, and Psi4, OpenMM for molecular dynamics with AMBER14 and similar force fields, xtb-python for semi-empirical methods, and mdtraj for trajectory analysis. Use when running SCF energy calculations, geometry optimizations, vibrational frequency analysis, thermochemistry, QM/MM simulations, or implicit-solvent modeling.
license: MIT
compatibility: Requires Python 3.10+ with pyscf, ase, openmm, mdtraj, xtb-python optional. External binaries (Gaussian, ORCA, Psi4, VASP) require separate licenses and install paths.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Chemistry & Materials
---

# Computational Chemistry

## Overview

Computational chemistry predicts molecular structure, energetics, spectra, and dynamics from quantum and classical mechanics. This skill covers the four workhorse stacks used in 2025 research: PySCF for ab-initio / DFT, ASE as a universal calculator interface, OpenMM for classical and QM/MM molecular dynamics, and xtb-python for fast semi-empirical geometries. Together they let an agent move from a SMILES string to an optimized geometry, thermochemistry, and a microsecond trajectory without leaving Python.

The skill assumes a single-researcher workflow on a workstation or a single HPC node. Multi-thousand-atom DFT on transition metals is out of scope here; use the `materials-science` skill for periodic systems.

## When to use this skill

- Compute a single-point SCF or DFT energy on a small molecule (less than 200 atoms) and verify the basis-set choice.
- Run a geometry optimization and confirm convergence by gradient norm.
- Calculate vibrational frequencies, zero-point energies, and thermodynamic corrections (298.15 K, 1 atm).
- Run classical molecular dynamics (MD) of an organic molecule or protein-ligand complex in explicit water with AMBER14.
- Set up a two-layer QM/MM calculation where the active site is treated with DFT and the rest with a force field.
- Use a semi-empirical method (xTB) for a quick pre-optimization before a DFT geometry refinement.
- Wrap an external binary (Gaussian, ORCA, Psi4) through ASE so the agent drives the same input/output flow as a native calculator.

## Prerequisites

- Python 3.10 or newer (3.11/3.12 recommended).
- Core scientific stack: `numpy`, `scipy`, `matplotlib`.
- `pip install pyscf ase openmm mdtraj xtb-python ngrok` is a typical install line; pin major versions if reproducibility matters.
- For trajectories: `pip install mdtraj` (binary wheels for Linux/macOS x86_64 and arm64).
- For semi-empirical: `pip install xtb-python` (bundled xtb binary).
- Optional external calculators (each needs its own license and install):
  - Gaussian 16 (commercial, Gaussian Inc.) for high-accuracy DFT and coupled-cluster.
  - ORCA 5.x (free for academics) for multireference and TDDFT.
  - Psi4 1.x (open-source) for SMP-parallel DFT and SAPT.
  - GPAW (free, PAW method) for periodic DFT.
- Linux or macOS recommended; OpenMM on Windows works but the GPU backends differ.
- 8 GB RAM minimum; 32 GB or more for medium basis-set DFT on 100+ atoms.

## Core workflows

### Workflow 1: Single-point SCF and DFT energy with PySCF

PySCF is the most usable pure-Python ab-initio package. The snippet below builds methane from coordinates, runs a Hartree-Fock and a B3LYP/def2-SVP energy, and prints both.

```python
from pyscf import gto, dft, scf

mol = gto.M(atom="C 0 0 0; H 0.63 0.63 0.63; H -0.63 -0.63 0.63; "
                  "H -0.63 0.63 -0.63; H 0.63 -0.63 -0.63",
            basis="def2-svp", unit="Angstrom", verbose=0)

hf = scf.RHF(mol).run()
print(f"RHF energy: {hf.e_tot:.6f} Ha")

mf = dft.RKS(mol)
mf.xc = "b3lyp"
mf.grids.level = 4
mf.run()
print(f"B3LYP/def2-svp: {mf.e_tot:.6f} Ha")
```

Switch `xc` to `pbe0`, `m06`, `wb97x-d`, or `b3lyp` and rerun to compare. For open-shell systems, use `scf.UHF(mol)` and `dft.UKS(mol)`.

### Workflow 2: Geometry optimization and vibrational frequencies

ASE provides a calculator-agnostic optimizer. The example wraps PySCF and runs BFGS, then numerical Hessian frequencies for verification of a true minimum.

```python
from pyscf import gto, dft
from ase.build import molecule as ase_mol
from ase.calculators.calculator import Calculator
from ase.optimize import BFGS
from ase.vibrations import Vibrations

atoms = ase_mol("H2O2")
mol = gto.M(atom=[(s, p) for s, p in zip(atoms.get_chemical_symbols(), atoms.positions)],
            basis="def2-svp", unit="Angstrom")
mf = dft.RKS(mol); mf.xc = "b3lyp"; mf.grids.level = 4

class PySCFCalc(Calculator):
    implemented_properties = ["energy", "forces"]
    def calculate(self, atoms=None, properties=("energy",), system_changes=("positions",)):
        super().calculate(atoms, properties, system_changes)
        pos = self.atoms.get_positions()
        m = gto.M(atom=list(zip(self.atoms.get_chemical_symbols(), pos)),
                  basis="def2-svp", unit="Angstrom")
        f = dft.RKS(m); f.xc = "b3lyp"; f.grids.level = 4; f.run()
        self.results["energy"] = f.e_tot
        import numpy as np
        self.results["forces"] = -f.nuc_grad_method().generator(m, "numeric").as_vector().reshape(-1, 3)

atoms.calc = PySCFGhost()
BFGS(atoms).run(fmax=0.02)  # eV/Angstrom
vib = Vibrations(atoms); vib.run()
print("Freqs (cm^-1):", [round(v.real, 1) for v in vib.get_frequencies() if v.real > 0])
```

Replace the inline `PySCFGhost` placeholder with the actual ASE `PySCF` calculator from `ase.calculators.pyscf` if available, or wrap the gradient manually as shown. A real minimum has zero imaginary frequencies.

### Workflow 3: Molecular dynamics with OpenMM

OpenMM is the standard for biomolecular MD on GPUs. The snippet builds a T4-lysozyme complex in explicit TIP3P water and runs 100 ps of Langevin dynamics at 300 K.

```python
from openmm.app import *
from openmm import *
from openmm.unit import *

pdb = PDBFile("lys.pdb")
ff  = ForceField("amber14-all.xml", "amber14/tip3pfb.xml")
modeller = Modeller(pdb.topology, pdb.positions)
modeller.addHydrogens(ff, pH=7.0)
modeller.addSolvent(ff, boxSize=Vec3(6, 6, 6, 0)*nanometers)
system = ff.createSystem(modeller.topology,
                         nonbondedMethod=PME, nonbondedCutoff=1*nanometer,
                         constraints=HBonds)
integrator = LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 2*femtoseconds)
simulation = Simulation(modeller.topology, system, integrator)
simulation.context.setPositions(modeller.positions)
simulation.minimizeEnergy(maxIterations=200)
simulation.reporters.append(DCDReporter("traj.dcd", 500))
simulation.reporters.append(StateDataReporter("log.csv", 500,
    step=True, potentialEnergy=True, temperature=True))
simulation.step(50000)  # 50000 x 2 fs = 100 ps
```

Always equilibrate after energy minimization; never start production from a cold structure.

### Workflow 4: QM/MM partitioning with ASE and OpenMM

In QM/MM you pick a QM region (active site) and treat the rest with a force field. The minimal recipe:

1. Load the full system into OpenMM (positions, topology, force field).
2. Select QM atom indices (e.g., residues within 6 A of the ligand).
3. Use `openmmml.MLCalculator` or `ChemicalEnvironment` to swap the bonded / LJ / electrostatics of the QM region for a PySCF calculator.
4. Run an SCF-in-the-loop MD step every 2 fs.

```python
from openmmml import MLPotential
ml = MLPotential.createPotential("amber14-all.xml", system=system, qmAtoms=qm_indices)
# Replace the OpenMM System with one whose QM energy comes from PySCF
integrator = LangevinMiddleIntegrator(300*kelvin, 1/picosecond, 1*femtoseconds)
simulation = Simulation(modeller.topology, ml, integrator)
simulation.context.setPositions(modeller.positions)
simulation.step(5000)
```

The `openmmml` package abstracts the QM/MM driver; if unavailable, set up a custom `CustomCVForce` and call PySCF manually each step.

### Workflow 5: Semi-empirical pre-optimization with xtb-python

xTB (GFN2-xTB) is 100-1000x faster than DFT and gives chemically reasonable geometries. Use it to pre-optimize before a DFT refinement.

```python
import xtb
from xtb.libxtb import VERBOSITY_MUTED
from xtb.interface import Molecule, Calculator

import numpy as np
atoms = ["C", "H", "H", "H", "H"]
pos = np.array([[0,0,0],[0.63,0.63,0.63],[-0.63,-0.63,0.63],
               [-0.63,0.63,-0.63],[0.63,-0.63,-0.63]])
mol = Molecule(atoms, pos, { "uff": True })
calc = Calculator(xtb.XTBMethods.GFN2xTP, mol)
calc.set_verbosity(VERBOSITY_MUTED)
res = calc.singlepoint(mol)
print(f"xTB energy: {res.get_energy():.6f} Ha")
# Then pass mol.positions into ASE + PySCF for DFT refinement.
```

## Best practices

- Always state the method, basis set, XC functional, grid level, and convergence thresholds in any output the agent emits. Method names without basis are meaningless.
- Verify a geometry optimization is a true minimum by computing numerical Hessian frequencies; zero imaginary frequencies is the standard test.
- Use tight SCF convergence (1e-8 in density) for frequencies; loose SCF corrupts the Hessian.
- For DFT on transition-metal complexes, use a dispersion-corrected functional (B3LYP-D3(BJ), wB97X-D, r2SCAN-3c) and a def2-TZVP or larger basis.
- Default to PME for long-range electrostatics in OpenMM and a 1.0-1.2 nm real-space cutoff. Never use reaction-field for proteins in explicit water.
- Constrain bonds to hydrogen (SHAKE/SETTLE) so you can use 2 fs timestep; constrain all bonds (HBC) to push to 4 fs with Hydrogen Mass Repartitioning.
- Save trajectories in lossless formats (DCD, XTC); avoid ASCII XYZ for large systems.
- Log method, version, random seed, and git commit of the script in a sidecar JSON for reproducibility.
- Cross-check DFT energies against a cheaper method (xTB or HF) on the same geometry; large disagreements flag input errors.
- Cache slow integrals. PySCF supports `.chkfile` to avoid recomputing SCF between similar geometries.
- For OpenMM, log the platform name (`CPU`, `CUDA`, `OpenCL`) in the output header so a slow CPU run is never mistaken for a fast GPU run.
- Prefer DCD or XTC trajectory formats over PDB multi-model; the latter bloats 10x and breaks on systems over 99 999 atoms.

## Common pitfalls

- Mixing units: PySCF uses Bohr by default, ASE uses Angstrom; explicit `unit="Angstrom"` is required every time.
- Forgetting to add hydrogens in OpenMM Modeller before solvation produces wrong protonation and impossible dynamics.
- Using a small DFT grid (level 1 or 2) for non-canonical functionals like M06 or Minnesota-class produces 1-5 kcal/mol noise.
- Treating a transition state as a minimum: a true TS has exactly one imaginary frequency; optimize with `ase.neb.NEB` or PySCF `pyopt` first.
- Reusing a PySCF cell for two different molecules in the same Python session without `mol.build()` again causes silent basis errors.
- Running OpenMM on CPU when a CUDA or OpenCL platform is available gives 10-100x slower trajectories. Call `Platform.getPlatformByName("CUDA")` explicitly.
- Trusting xTB for transition metals: GFN2-xTB is parameterized for s/p-block and many d-block elements but should be benchmarked against DFT for your chemistry.
- Forgetting to set periodic box vectors in OpenMM results in a non-periodic (vacuum) system and the PME code raises.

## Worked example

Goal: optimize ethanol, compute B3LYP/def2-SVP thermochemistry, and run a 10 ps gas-phase MD.

```python
from pyscf import gto, dft
from ase.build import molecule
from ase.optimize import BFGS
from ase.calculators.pyscf import PySCF
from ase.vibrations import Vibrations
import openmm
from openmm import LangevinIntegrator, Context, Platform
from openmm.app import Simulation, Topology, ForceField, HArmaes

# 1. Build and optimize
atoms = molecule("CH3CH2OH")
atoms.calc = PySCF(mole=gto.M(atom=list(zip(atoms.get_chemical_symbols(),
                                            atoms.positions)),
                            basis="def2-svp", unit="Angstrom"),
                  xc="b3lyp", grids=4)
BFGS(atoms).run(fmax=0.02)

# 2. Vibrational frequencies and ZPE
vib = Vibrations(atoms); vib.run()
freqs = vib.get_frequencies()
zpe = sum(f.real for f in freqs if f.real > 0) * 0.5 * 0.000239006  # to kcal/mol
print(f"ZPE: {zpe:.3f} kcal/mol")

# 3. OpenMM gas-phase 10 ps MD at 300 K
sys = openmm.System()
for s in atoms.get_chemical_symbols():
    sys.addParticle(12.0)  # placeholder mass; replace with mass per element
force = openmm.HarmonicBondForce()  # build from ASE neighbor list omitted for brevity
sys.addForce(force)
integ = LangevinIntegrator(300, 1.0, 1.0)
ctx = Context(sys, integ, Platform.getPlatformByName("CPU"))
ctx.setPositions(atoms.positions)
for i in range(5000):
    integ.step(2)  # 2 fs each, 5000 steps = 10 ps
print("MD complete; final positions:")
print(ctx.getState(getPositions=True).getPositions())
```

## Tools and libraries

| Tool | Purpose | Install |
|---|---|---|
| PySCF | Ab-initio and DFT, post-HF, periodic | `pip install pyscf` |
| ASE | Universal calculator interface, optimizers, NEB | `pip install ase` |
| OpenMM | GPU-accelerated MD, QM/MM, integrators | `conda install -c conda-forge openmm` |
| mdtraj | Trajectory I/O, RMSD, secondary structure | `pip install mdtraj` |
| xtb-python | GFN1/2-xTB semi-empirical, tight-binding | `pip install xtb-python` |
| Psi4 | Open-source QM, SAPT, CCSD(T) | `conda install -c conda-forge psi4` |
| GPAW | Periodic DFT with PAW, LCAO mode | `conda install -c conda-forge gpaw` |
| Gaussian | Commercial high-accuracy DFT and CC | separate license |
| ORCA | Free academic multireference, TDDFT | separate download |
| openmm-ml | ML potentials (ANI, MACE) inside OpenMM | `pip install openmm-ml` |
| RDKit | SMILES to 3D, conformer search | `pip install rdkit` |
| geomeTRIC | Robust coordinate optimizer (used by ASE/PySCF) | `pip install geometric` |

## References

- PySCF examples and documentation: https://pyscf.org/
- ASE calculator documentation: https://wiki.fysik.dtu.dk/ase/
- OpenMM User Manual: http://docs.openmm.org/
- xtb-python (GFN2-xTB) on GitHub: https://github.com/grimme-lab/xtb-python
- mdtraj documentation: https://www.mdtraj.org/
- Psi4 documentation: https://psicode.org/psi4manual/
- Gaussian 16 user manual: https://gaussian.com/man/
- ORCA manual: https://www.faccts.de/orca/manual/

## Ethics and safety

- Computational cost: A B3LYP/def2-TZVP single-point on a 50-atom molecule is 5-30 CPU-minutes; a 100 ns OpenMM trajectory is hours on a GPU. Estimate cost before launching; the agent should never submit 1000-element screening jobs without explicit user approval.
- Hazardous reactions: Predicting reaction pathways for energetic materials, chemical warfare agents, or improvised explosives is dual-use. If the agent is asked for high-energy density molecule design or detonation modeling, refuse and redirect to the relevant responsible-disclosure authority. Legitimate propellant or pharmaceutical combustion work is in scope.
- Drug discovery and dual-use: Molecule design targeting controlled substances (e.g., opioids, nootropics, performance enhancers) is regulated in most jurisdictions. Surface docking against endogenous receptors for basic research is fine; production of controlled substances is not.
- Reproducibility and method disclosure: Never publish a computational result without the exact functional, basis, grid, convergence threshold, software version, and platform. Computational results without provenance are not falsifiable and fail peer review.
- License compliance: Gaussian and ORCA have license terms forbidding redistribution of input templates that include vendor-specific keywords for unlicensed users. Keep such templates out of public skill assets.
- Data safety: When using Materials Project, QCArchive, or PubChem as input, honor their fair-use policies; do not scrape or redistribute full database dumps.

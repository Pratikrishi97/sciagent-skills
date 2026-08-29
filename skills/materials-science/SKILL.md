---
name: materials-science
description: Materials science workflows using pymatgen for crystal structure I/O and analysis, the Materials Project API via mp-api for property lookup, phase-diagram construction with pymatgen, MACE and CHGNet graph-neural-network ML potentials for fast relaxations, ASE and GPAW for periodic DFT, and defect and Pourbaix calculations. Use when reading or writing CIF and POSCAR files, computing formation energies, simulating XRD patterns, building convex-hull phase diagrams, or screening materials by properties.
license: MIT
compatibility: Requires Python 3.10+ with pymatgen, mp-api, ase, matgl (MACE), chgnet. GPAW or VASP binary needed for periodic DFT. Materials Project API key required for mp-api access.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Chemistry & Materials
---

# Materials Science

## Overview

Modern computational materials science is built around three Python pillars: pymatgen for crystal-structure manipulation, the Materials Project REST API for property lookups, and graph-neural-network interatomic potentials (MACE, CHGNet) that relax structures at DFT accuracy 1000x faster. This skill covers the canonical pipeline: read a CIF or POSCAR file, query the Materials Project for known phases, build a convex-hull phase diagram, run an ML relaxation, then refine with periodic DFT (ASE/GPAW or VASP via interface). It also covers point-defect formation energies and Pourbaix diagrams for electrochemical stability.

## When to use this skill

- Parse a CIF or VASP POSCAR into a Structure object and write it back out in another format.
- Query the Materials Project for materials by formula, spacegroup, band gap, or formation energy.
- Build a binary or ternary convex-hull phase diagram and find the stable phases at a composition.
- Use a universal ML interatomic potential (MACE-MP-0, CHGNet) for fast structure relaxation and energy ranking.
- Run a periodic DFT single-point or relaxation with GPAW through ASE.
- Compute a point-defect formation energy (vacancy, substitution, interstitial) and the associated charge-state transition levels.
- Construct a Pourbaix diagram (pH vs. potential) for an aqueous stability study of a battery cathode or catalyst.
- Simulate a powder XRD pattern for phase identification.

## Prerequisites

- Python 3.10+ (3.11/3.12 recommended; pymatgen dropped 3.9 support in 2024).
- Core stack: `pip install pymatgen mp-api ase matgl chgnet`.
- For MACE potentials via PyTorch: `pip install torch>=2.1` (CPU build works for small cells; CUDA for production).
- For periodic DFT: install GPAW (`conda install -c conda-forge gpaw`) or have a VASP binary and license.
- Set the Materials Project API key once: `mp-api` reads it from the `MP_API_KEY` environment variable or via `~/.pmgrc.yaml` (`PMG_MAPI_KEY: <key>`).
- Optional: OQMD, AFLOW, NOMAD REST clients (`pip install nomad-lab aflow`).
- 8 GB RAM for ML potentials on cells up to ~200 atoms; 32 GB+ for GPAW DFT on 100-atom supercells.
- Linux or macOS recommended; GPAW on Windows requires WSL2.

## Core workflows

### Workflow 1: Crystal structure I/O and analysis with pymatgen

```python
from pymatgen.core import Structure, Lattice
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

# Build rock-salt MgO
lat = Lattice.cubic(4.21)
s = Structure(lat, ["Mg","O","Mg","O"],
              [[0,0,0],[0.5,0,0],[0.5,0.5,0.5],[0,0.5,0.5]])
s.to(filename="MgO.cif")               # write CIF
s2 = Structure.from_file("MgO.cif")    # read back
spa = SpacegroupAnalyzer(s2)
print("spacegroup:", spa.get_spacegroup_number(), spa.get_crystal_system())
prim = spa.get_primitive_standard_structure()
print(f"primitive cell: {prim.num_sites} sites, "
      f"{prim.volume:.2f} A^3")
```

`pymatgen.io.vasp.inputs.Poscar` and `pymatgen.io.cif.CifParser` handle the same surface for VASP POSCAR files and CIF from crystallographic databases.

### Workflow 2: Materials Project queries via mp-api

```python
from mp_api.client import MPRester
import os

with MPRester(api_key=os.environ["MP_API_KEY"]) as mpr:
    # Stable MgO phases
    docs = mpr.materials.search(
        chemsys="Mg-O", fields=["material_id","formula_pretty",
                                "energy_above_hull","band_gap","density"])
    for d in docs[:5]:
        print(d.material_id, d.formula_pretty,
              f"E_hull={d.energy_above_hull:.3f} eV",
              f"Eg={d.band_gap:.2f} eV")
    # Get the full structure for one
    s = mpr.get_structure_by_id("mp-1265")
    s.to(filename="mp-1265_MgO.cif")
```

Filter with `num_sites`, `volume`, `symmetry`, or `theoretical`. MPRester caches responses locally to reduce API load.

### Workflow 3: Phase diagram construction with pymatgen

```python
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter
from pymatgen.core import Composition
import os

with MPRester(os.environ["MP_API_KEY"]) as mpr:
    entries = mpr.get_entries_in_chemsys(["Li","Fe","O"])

pd = PhaseDiagram(entries)
# Formation energy of LiFeO2 at the convex hull
c = Composition("LiFeO2")
print(f"LiFeO2 formation energy: {pd.get_form_energy_per_atom(c):.3f} eV/atom")
# Decomposition of an off-hull composition
decomp = pd.get_decomposition(Composition("Li2FeO3"))
print("Decomposes to:", {str(k.composition): v for k,v in decomp.items()})

PDPlotter(pd, show_unstable=0.05).plot()   # opens matplotlib window
```

Ternary convex hulls are computed automatically from the entries. `show_unstable=0.05` plots phases within 50 meV/atom of the hull.

### Workflow 4: Fast ML relaxation with MACE or CHGNet

```python
from ase.build import bulk
from mace.calculators import MACECalculator   # matgl distribution

atoms = bulk("Si","diamond",a=5.43)
atoms.calc = MACECalculator(model_paths="medium",
                            device="cpu",
                            default_dtype="float64")
atoms.rattle(stdev=0.05)                      # perturb to non-equilibrium
from ase.optimize import BFGS
BFGS(atoms).run(fmax=0.01)                    # eV/A
print(f"E_final = {atoms.get_potential_energy():.4f} eV")
print(f"a_relaxed = {atoms.cell[0,0]:.3f} A")
```

CHGNet is interchangeable: `from chgnet.model import StructOptimizer; opt = StructOptimizer(); r = opt.optimize(atoms)`.

### Workflow 5: Periodic DFT with ASE + GPAW

```python
from ase.build import bulk
from gpaw import GPAW, PW, FermiDirac

atoms = bulk("Si","diamond",a=5.43)
atoms.calc = GPAW(mode=PW(400),                # plane-wave cutoff 400 eV
                 xc="PBE",
                 kpts=(4,4,4),                # Monkhorst-Pack
                 occupations=FermiDirac(0.05), # smearing
                 txt="si.txt")
print(f"E_total = {atoms.get_potential_energy():.4f} eV")
# Forces for relaxation
from ase.optimize import BFGS
BFGS(atoms).run(fmax=0.02)
```

For VASP, swap the calculator: `from ase.calculators.vasp.vasp import Vasp; atoms.calc = Vasp(...)` with `VASP_PP_PATH` set in the environment.

### Workflow 6: Point-defect formation energy

```python
from pymatgen.analysis.defects import ChargedDefect
# Build a Mg vacancy in MgO, charge 0
host = Structure.from_file("MgO.cif")
defect = ChargedDefect(host, defect_type="vacancy",
                       site_index=0, charge=0)
# formation energy = E_def - E_host - sum(n_i mu_i) + q E_Fermi
# Requires chemical potentials from the phase diagram and Fermi level from DOS.
print(f"Defect structure file written: {defect.to_file('V_Mg.cif')}")
```

For a complete defect workflow use `pymatgen-analysis-defects` (`pip install pymatgen-analysis-defects`) which automates the supercell generation, charge-state enumeration, and finite-size corrections (Kumagai-Oba).

### Workflow 7: Simulated powder XRD

```python
from pymatgen.analysis.diffraction.xrd import XRDCalculator
from pymatgen.core import Structure

s = Structure.from_file("MgO.cif")
calc = XRDCalculator(wavelength="CuKa")   # Cu K-alpha, 1.5418 A
pattern = calc.get_pattern(s)
# Two-theta, intensity pairs
peaks = list(zip(pattern.x, pattern.y))
print("Top 5 peaks:")
for two_theta, I in sorted(peaks, key=lambda p: -p[1])[:5]:
    print(f"  2theta = {two_theta:.3f} deg, I/I0 = {I:.1f}")
calc.show_plot(s)  # matplotlib figure of the pattern
```

The simulated pattern is useful for phase identification against an experimental scan; report the wavelength alongside any comparison.

## Best practices

- Always set the MP_API_KEY in a shell rc file or `~/.pmgrc.yaml`; never hard-code in scripts that may be shared.
- Use the primitive standard structure for DFT inputs; supercells are made from it with `Structure.make_supercell([n,n,n])`.
- Run ML potentials on the same major version of PyTorch throughout a project; mix-and-match produces inconsistent energies.
- Verify ML-relaxed structures by re-optimizing the lowest-energy candidates with explicit DFT before publishing.
- Convergence-test k-points and plane-wave cutoff for the property of interest: energy differences converge slower than absolute energies.
- Use a moderate smearing (FermiDirac 0.05 eV or Methfessel-Paxton order 1) for metals; insulators can use fixed occupations.
- Report formation energies per atom, not per formula unit, so they are comparable across chemistries.
- For Pourbaix, keep the water window (1.23 V at pH 0) in mind; phases stable outside the water window are not viable aqueous candidates.
- Tag every structure with provenance (MP ID, ML potential name and version, or DFT settings) in a sidecar JSON.
- Cache ML and DFT results on disk (`ase.db`) rather than re-running expensive jobs.
- For XRD simulation, use Cu K-alpha (lambda = 1.5418 A) as the default unless the experiment specifies otherwise; report the wavelength alongside the simulated pattern.
- For Pourbaix diagrams, set the competing phases explicitly; the auto-generated list from Materials Project can miss metastable hydroxides that control the aqueous stability window.
- When relaxing with MACE, set `dispersion_corr=True` if available; dispersion changes cell volumes of layered materials by 1-3 percent.
- For high-throughput screening, store all candidates in an `ase.db` row per structure with key-value pairs (formula, spacegroup, hull energy) so SQL-like filtering works downstream.

## Common pitfalls

- Using `Structure.from_file` on a non-standard CIF (e.g. with `_cell_measurement_` lines from old ICSD) silently drops symmetry; pre-process with `CifParser(...,occupancy_tolerance=1.0)`.
- Forgetting to pass `default_dtype="float64"` to MACE on CPU gives 1-2 meV/atom float32 noise that breaks hull decisions.
- Searching Materials Project without `chemsys` filter returns thousands of irrelevant entries and burns your daily API quota.
- Relaxing an ML structure with VASP `PREC=accurate` defaults but `ENCUT=ENMAX` (basis-set minimum) under-converges; set ENCUT explicitly to 1.3x ENMAX.
- Mixing structures with different standard primitive cell definitions across papers leads to wrong formation energies; use `SpacegroupAnalyzer.get_primitive_standard_structure()`.
- Forgetting to neutralize a charged defect supercell with a homogeneous background (Lany-Zunger) before taking energy differences gives wrong formation energies by 1+ eV.
- Using MACE-MP-0 outside its training domain (actinides, very heavy elements) gives uncontrolled errors; benchmark against DFT.
- Saving structures with `to(fmt="json")` then loading with `from_dict(json.loads(...))` works but loses provenance; use `Structure.to(filename="...", fmt="json")` and `Structure.from_file(...)`.

## Worked example

Goal: Find all stable Li-Fe-O phases on Materials Project, identify LiFeO2, relax an MLperturbed supercell with MACE, then refine with GPAW PBE.

```python
import os
from mp_api.client import MPRester
from pymatgen.analysis.phase_diagram import PhaseDiagram
from pymatgen.core import Structure, Composition
from mace.calculators import MACECalculator
from ase.optimize import BFGS
from ase.io import read
from gpaw import GPAW, PW, FermiDirac

# 1. Pull entries and build phase diagram
with MPRester(os.environ["MP_API_KEY"]) as mpr:
    entries = mpr.get_entries_in_chemsys(["Li","Fe","O"])
pd = PhaseDiagram(entries)
e_hull = pd.get_form_energy_per_atom(Composition("LiFeO2"))
print(f"LiFeO2 hull energy: {e_hull:.3f} eV/atom")

# 2. Get the LiFeO2 structure
with MPRester(os.environ["MP_API_KEY"]) as mpr:
    liife = mpr.get_structure_by_id("mp-758885")  # ICSD Cu-type
liife.make_supercell([2,2,2])              # 96-atom cell
liife.to(filename="LiFeO2_supercell.cif")

# 3. MACE relaxation
atoms = read("LiFeO2_supercell.cif")
atoms.calc = MACECalculator(model_paths="medium", device="cpu",
                            default_dtype="float64")
atoms.rattle(stdev=0.04)
BFGS(atoms).run(fmax=0.02)
print(f"MACE energy: {atoms.get_potential_energy():.3f} eV")

# 4. GPAW single-point on the MACE-relaxed structure
atoms.calc = GPAW(mode=PW(500), xc="PBE", kpts=(2,2,2),
                  occupations=FermiDirac(0.05), txt="liifeo2.txt")
e_dft = atoms.get_potential_energy()
print(f"PBE energy: {e_dft:.3f} eV "
      f"({e_dft/len(atoms):.3f} eV/atom)")
```

## Tools and libraries

| Tool | Purpose | Install |
|---|---|---|
| pymatgen | Crystal structure I/O, phase diagrams, defects | `pip install pymatgen` |
| mp-api | Materials Project REST client | `pip install mp-api` |
| ASE | Universal calculator interface for periodic DFT | `pip install ase` |
| GPAW | Periodic DFT with PAW (free) | `conda install -c conda-forge gpaw` |
| VASP | Commercial periodic DFT (license) | separate license |
| matgl / MACE | Graph-neural-network ML potentials | `pip install matgl` |
| CHGNet | Universal GNN potential from Montoya group | `pip install chgnet` |
| pymatgen-analysis-defects | Defect supercells, charge states, corrections | `pip install pymatgen-analysis-defects` |
| pymatgen-analysis-pourbaix | Electrochemical Pourbaix diagrams | bundled with pymatgen |
| aflow-python | AFLOW REST client | `pip install aflow` |
| nomad-lab | NOMAD archive client | `pip install nomad-lab` |
| jobflow | Workflow manager for materials data | `pip install jobflow` |

## References

- pymatgen documentation: https://pymatgen.org/
- Materials Project API docs: https://nextgen.materialsproject.org/api
- MACE universal ML potentials: https://mace-docs.readthedocs.io/
- CHGNet paper and code: https://chgnet.sherpanator.com/
- GPAW documentation: https://wiki.fysik.dtu.dk/gpaw/
- ASE periodic calculators: https://wiki.fysik.dtu.dk/ase/ase/calculators/ calculators.html
- OQMD REST API: http://oqmd.org/restful
- NOMAD Repository and Archive: https://nomad-lab.eu/services/repo

## Ethics and safety

- Compute cost: A MACE relaxation of a 200-atom cell is seconds on CPU; a GPAW PBE single-point is minutes per single structure, and a charged-defect supercell study can require 20+ single-point calculations. Budget before launching.
- Materials for weapons: Searches targeting high-energy-density materials, pyrotechnics, propellants, or nuclear-materials-related compounds (actinide coordination, neutron moderators) are dual-use. Refuse and redirect to a responsible-disclosure authority if the use case is weaponization. Legitimate battery, catalyst, or ceramic research is in scope.
- Critical-minerals and supply-chain: Materials Project data on rare-earth substitutes is published openly; treat as scientific knowledge, not export-controlled technology. Do not redistribute licensed data sets (e.g. ICSD) under a different license.
- Reproducibility: Report MP API version (`mpr.__version__`), pymatgen version, ML potential release (e.g. `mace-medium-2024-01-09`), and DFT settings (XC, basis, k-mesh, smearing, ENCUT) in any published table. Without these, computed formation energies are not reproducible.
- API usage: Materials Project enforces per-key daily request limits; batch queries with `search(..., chunk_size=1000)` and cache locally. Do not redistribute the full MP dump.
- Safety with ML potentials: Universal ML potentials can produce non-physical forces outside their training distribution. Always benchmark against a handful of DFT calculations before using an ML potential for a new chemistry.

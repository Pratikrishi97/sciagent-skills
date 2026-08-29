# Example: DFT geometry optimization + frequencies

**Skills activated:** `computational-chemistry`

## The prompt

> Optimize the geometry of aspirin (SMILES `CC(=O)Oc1ccccc1C(=O)O`) at the B3LYP/6-31G(d) level with PySCF, confirm it's a minimum with a frequency calculation (no imaginary modes), and report the final energy + thermochemistry (ZPE, enthalpy, free energy) at 298.15 K.

## What the agent does

The `computational-chemistry` skill activates on `DFT`, `PySCF`, `B3LYP`, `geometry optimization`, `frequency`.

### 1. Build the molecule from SMILES

```python
# pip install rdkit pyscf geometric
from rdkit import Chem
from rdkit.Chem import AllChem
from pyscf import gto, dft

mol_rdkit = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
mol_rdkit = Chem.AddHs(mol_rdkit)
AllChem.EmbedMolecule(mol_rdkit, randomSeed=1)
AllChem.MMFFOptimizeMolecule(mol_rdkit)
xyz = Chem.MolToXYZBlock(mol_rdkit)
```

### 2. Build the PySCF object + optimize with geomeTRIC

```python
mol = gto.M(atom=xyz, basis="6-31g(d)", verbose=3, unit="Angstrom")
mf = dft.RKS(mol)
mf.xc = "b3lyp"
mf.grids.level = 4

from pyscf.geomopt.geometric_solver import optimize
mol_eq = optimize(mf, maxsteps=100)
print("Optimized energy (Ha):", mf.kernel())
```

### 3. Frequency analysis + thermochemistry

```python
from pyscf.hessian import thermo
mf.kernel()  # recompute SCF at the optimized geometry
hess = mf.Hessian().kernel()
freqs = hess  # harmonic frequencies after projecting out translations/rotations
results = thermo.thermo(mf, freqs, 298.15, 101325)
print("ZPE (kJ/mol):", results["ZPE"] * 2625.5)
print("H (kJ/mol):", results["H"] * 2625.5)
print("G (kJ/mol):", results["G"] * 2625.5)
```

## Pitfalls the skill surfaces

- B3LYP is a poor choice for non-covalent interactions or dispersion-bound systems — use ωB97X-D4 or B3LYP-D3(BJ) with a dispersion correction.
- An "imaginary" frequency (negative eigenvalue) means the geometry is a transition state, not a minimum — re-optimize from a perturbed starting geometry.
- The DFT grid (`mf.grids.level`) defaults to 3; for final energies, bump to 4 or 5 to avoid integration noise.
- Frequencies from PySCF are raw harmonic frequencies — scale them by ~0.96 for comparison to experiment.

## Reproducibility

Pin PySCF + geomeTRIC versions in `environment.yml`, set the RDKit embedding seed (`randomSeed=1`), and record the grid level. The whole pipeline fits a Snakemake rule (`reproducible-research` skill).

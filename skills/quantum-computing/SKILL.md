---
name: quantum-computing
description: Quantum computing workflows using Qiskit for circuit construction, transpilation, and Aer simulators, PennyLane for differentiable and hybrid quantum-classical machine learning, Cirq for Google-style circuits and noise models, QuTiP for open quantum system Lindblad master equations, and the canonical algorithms VQE, QAOA, Grover, and QFT. Use when building quantum circuits, simulating noise, computing observables, or running variational quantum algorithms.
license: MIT
compatibility: Requires Python 3.10+ with qiskit, qiskit-aer, pennylane, cirq, qutip. Optional packages include qiskit-ibm-runtime for real-hardware jobs which requires an IBM Quantum API token.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Physics & Astronomy
---

# Quantum Computing

## Overview

Quantum computing in Python has consolidated around four libraries: Qiskit (IBM-style circuits, Aer simulators, IBM Quantum runtime), PennyLane (differentiable quantum computing with native PyTorch/JAX integration), Cirq (Google-style circuits and noise models), and QuTiP (open quantum systems with Lindblad master equations). This skill covers the canonical workflows: build a circuit, transpile for a target backend, simulate noise, compute an observable, run a variational algorithm (VQE or QAOA), implement Grover, and simulate open-system dynamics. Together they cover roughly 80 percent of day-to-day quantum computing research tasks.

## When to use this skill

- Construct a parametrized quantum circuit with Qiskit `QuantumCircuit` and draw it.
- Transpile a circuit for a specific coupling map and basis-gate set.
- Simulate statevector or density-matrix dynamics with `qiskit-aer`.
- Compute the expectation value of a Pauli Hamiltonian on a circuit.
- Run a variational quantum eigensolver (VQE) for a molecular Hamiltonian.
- Run QAOA for a small combinatorial optimization (MaxCut) problem.
- Implement Grover's search and verify quadratic speedup on a small database.
- Compute the Quantum Fourier Transform (QFT) for 3-10 qubits.
- Simulate open-system dynamics with Lindblad master equations in QuTiP.
- Build a hybrid quantum-classical neural network with PennyLane.

## Prerequisites

- Python 3.10+ (3.11/3.12 supported; Qiskit 1.x dropped 3.9).
- Core: `pip install qiskit qiskit-aer pennylane cirq qutip`.
- For visualization: `pip install matplotlib pylatexenc`.
- For IBM Quantum hardware: `pip install qiskit-ibm-runtime` and an IBM Quantum account; export `IBM_QUANTUM_TOKEN` env var.
- Optional: `pip install openfermion` for Fermion-to-Qubit operator mapping (Jordan-Wigner, Bravyi-Kitaev).
- Optional: `pip install pyscf` for molecular Hamiltonian generation (see computational-chemistry skill).
- Linux, macOS, or Windows; Aer simulator uses OpenMP and benefits from many cores.
- 8 GB RAM minimum; 32 GB for statevector simulation of 24+ qubits.

## Core workflows

### Workflow 1: Build, simulate, and measure a circuit with Qiskit

```python
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import Sampler

qc = QuantumCircuit(3, 3)
qc.h(0)                     # superposition
qc.cx(0, 1); qc.cx(1, 2)    # entangle chain
qc.measure(range(3), range(3))

sim = AerSimulator()
t_qc = transpile(qc, sim, optimization_level=2)
sampler = Sampler()
result = sampler.run(t_qc, shots=4096).result()
counts = result.quasi_dists[0].binary_probabilities()
print("Counts:", {k: round(v, 3) for k, v in counts.items()})
```

The expected outcome is approximately 50 percent `000` and 50 percent `111`, the textbook GHZ distribution.

### Workflow 2: Transpilation and noise simulation

```python
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (NoiseModel, depolarizing_error,
                              ReadoutError)

# Fake 5-qubit coupling map: linear chain 0-1-2-3-4
qc = QuantumCircuit(4)
qc.h(0); qc.cx(0,1); qc.cx(1,2); qc.cx(2,3); qc.measure_all()

noise = NoiseModel()
for q in range(5):
    noise.add_depol_error(depolarizing_error(1e-3, 1), ["x","h"], [q])
    noise.add_depol_error(depolarizing_error(1e-2, 2), ["cx"], [q,(q+1)%5])
noise.add_readout_error(ReadoutError([[0.99,0.01],[0.02,0.98]]), list(range(5)))

sim = AerSimulator(noise_model=noise,
                   coupling_map=[[0,1],[1,2],[2,3],[3,4]],
                   basis_gates=noise.basis_gates)
t_qc = transpile(qc, sim, optimization_level=3)
result = sim.run(t_qc, shots=4096).result()
print("Noisy counts:", result.get_counts())
```

Set `optimization_level=3` to enable gate fusion and commutation analysis. Lower levels trade noise resilience for speed.

### Workflow 3: Expectation values of a Pauli Hamiltonian (VQE setup)

```python
from qiskit import QuantumCircuit
from qiskit.circuit.library import EfficientSU2
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer.primitives import Estimator
import numpy as np

# H2 stoichiometric Hamiltonian in 4 qubits (from OpenFermion)
H = SparsePauliOp.from_list([
    ("IIII", -0.81261), ("IIIZ",  0.17434), ("IIZI", -0.22592),
    ("IZII",  0.17434), ("ZIII", -0.22592), ("ZZII",  0.12091),
    ("IZIZ",  0.16586), ("ZIIZ",  0.16586), ("IIZZ",  0.12091),
    ("XXXX",  0.04532), ("XXYY", -0.04532), ("YYXX", -0.04532),
    ("YYYY",  0.04532),
])
ansatz = EfficientSU2(num_qubits=4, reps=1, entanglement="linear")
estimator = Estimator()

def energy(params):
    job = estimator.run(ansatz, H, parameter_values=params)
    return job.result().values[0]

# Random initial parameters
theta0 = np.random.uniform(-np.pi, np.pi, ansatz.num_parameters)
print(f"E(theta0) = {energy(theta0):.5f} Ha (exact ground = -1.857 Ha)")

# Minimize with scipy.optimize.minimize to converge VQE
from scipy.optimize import minimize
res = minimize(energy, theta0, method="COBYLA",
               options={"maxiter": 500})
print(f"E_VQE = {res.fun:.5f} Ha after {res.nfev} evals")
```

For real-hardware VQE, swap `Estimator` from `qiskit_aer.primitives` with `qiskit.primitives.Estimator` backed by `qiskit-ibm-runtime`.

### Workflow 4: QAOA for MaxCut

```python
import networkx as nx
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit_aer.primitives import Estimator
import numpy as np
from scipy.optimize import minimize

G = nx.gnp_random_graph(6, 0.5, seed=7)
edges = list(G.edges())
p = 1  # depth

def build_qaoa(gammas, betas, G, p):
    n = G.number_of_nodes()
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for layer in range(p):
        gamma, beta = gammas[layer], betas[layer]
        for i, j in G.edges():
            qc.cx(i, j); qc.rz(2*gamma, j); qc.cx(i, j)
        for i in range(n):
            qc.rx(2*beta, i)
    return qc

cost = SparsePauliOp.from_list([
    ("XX".join("I"*(i+j>0)) + "I"*(n-i-j-2), -0.5) for i, j in edges
])

def objective(params, G, p, estimator):
    half = len(params)//2
    qc = build_qaoa(params[:half], params[half:], G, p)
    val = estimator.run(qc, cost).result().values[0]
    return val

theta0 = np.random.uniform(0, np.pi, 2*p)
res = minimize(objective, theta0, args=(G, p, Estimator()),
               method="COBYLA", options={"maxiter": 200})
print(f"QAOA cost: {res.fun:.4f}")
```

QAOA cost scales as O(2^p * poly(n)); depth p=1 is rarely sufficient for real MaxCut, but demonstrates the pattern.

### Workflow 5: Grover's search

```python
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
import numpy as np

n = 4  # search space size 2^4 = 16
target = "1011"  # marked item

def oracle(qc, n, target):
    for i, b in enumerate(target):
        if b == "0": qc.x(i)
    qc.h(n-1)
    qc.mcx(list(range(n-1)), n-1)  # multi-controlled Toffoli
    qc.h(n-1)
    for i, b in enumerate(target):
        if b == "0": qc.x(i)

def diffuser(qc, n):
    qc.h(range(n)); qc.x(range(n))
    qc.h(n-1); qc.mcx(list(range(n-1)), n-1); qc.h(n-1)
    qc.x(range(n)); qc.h(range(n))

qc = QuantumCircuit(n, n)
qc.h(range(n))
r = int(round(np.pi/4 * np.sqrt(2**n)))  # optimal iterations
for _ in range(r):
    oracle(qc, n, target)
    diffuser(qc, n)
qc.measure(range(n), range(n))

sim = AerSimulator()
result = sim.run(transpile(qc, sim), shots=1024).result()
print("Counts:", result.get_counts())  # peak at "1011"
```

The optimal number of Grover iterations is `pi/4 * sqrt(N)`; oversampling reduces the success probability.

### Workflow 6: PennyLane hybrid differentiable quantum circuit

```python
import pennylane as qml
from pennylane import numpy as pnp

dev = qml.device("default.qubit", wires=2)

@qml.qnode(dev)
def circuit(params):
    qml.RY(params[0], wires=0)
    qml.RY(params[1], wires=1)
    qml.CNOT(wires=[0, 1])
    qml.RY(params[2], wires=0)
    qml.RY(params[3], wires=1)
    return qml.expval(qml.PauliZ(0)), qml.expval(qml.PauliZ(1))

params = pnp.array([0.1, 0.2, 0.3, 0.4], requires_grad=True)
opt = qml.AdamOptimizer(stepsize=0.05)
for i in range(200):
    params = opt.step(lambda p: sum(circuit(p)), params)
print("Final params:", params)
print("Final observables:", circuit(params))
```

PennyLane integrates natively with PyTorch, JAX, and TensorFlow; swap `default.qubit` for `lightning.qubit` (faster CPU) or `qiskit.aer` (simulator backend).

### Workflow 7: Open quantum system dynamics with QuTiP

```python
import numpy as np
import qutip as qt

# Amplitude damping of a qubit at T=0
gamma = 0.05
a = qt.destroy(2)
c_ops = [np.sqrt(gamma) * a]              # jump operator

# Initial state: |1> (excited)
psi0 = qt.basis(2, 1)
H = qt.Qobj(np.zeros((2, 2)))             # free Hamiltonian

tlist = np.linspace(0, 50, 500)
result = qt.mesolve(H, psi0, tlist, c_ops,
                    e_ops=[qt.basis(2,1)*qt.basis(2,1).dag()])
pop_excited = result.expect[0]
print(f"P(|1>) at t=50: {pop_excited[-1]:.4f} "
      f"(expect exp(-gamma*t) = {np.exp(-gamma*50):.4f})")
```

`mesolve` integrates the Lindblad master equation; alternative `mcsolve` uses quantum trajectories for sparse Lindbladians.

## Best practices

- Always transpile to the target backend's coupling map and basis gates; an untranspiled circuit run on hardware wastes time and produces wrong results.
- Use the highest `optimization_level` (3 in Qiskit) for production; tradeoffs are well characterized.
- For variational algorithms, set a fixed PRNG seed so runs are reproducible.
- Group commuting Pauli terms before measurement to reduce shot count; `SparsePauliOp.group_commuting()` does this.
- For VQE, prefer `SLSQP` for small ansatze (less than 100 params) and `COBYLA` for larger ones; gradient-based methods need the parameter-shift rule (`qiskit.algorithms.gradients.ParamShiftEstimatorGradient`).
- For Grover, compute the optimal number of iterations analytically; do not tune it as a hyperparameter.
- For simulation, use Aer's `method="statevector"` for circuits with less than 30 qubits; switch to `tensor_network` or `matrix_product_state` beyond.
- In PennyLane, set the same seed on `qml.numpy.random` and `default.qubit` for reproducibility.
- For open-system dynamics, use `mesolve` for dense Lindbladians and `mcsolve` for sparse ones; sample at least 1000 trajectories in `mcsolve`.
- For noisy simulation, calibrate noise model parameters from real-hardware RB data; do not invent depolarizing rates.

## Common pitfalls

- Mixing `qiskit.primitives` (IBM runtime) with `qiskit-aer.primitives` (local simulator) in one VQE run: the result is shape-mismatched or run as a job that never starts. Pick one and stick with it.
- Forgetting to `transpile` before hardware submission: circuits get rejected by QPU or run at 100x lower fidelity.
- Using `statevector_simulator` for circuits with `measure` instructions: the simulator returns the pre-measurement state, not the bitstring distribution.
- Setting `shots=None` for noisy simulation: Aer interprets this as exact statevector (no noise); use `shots >= 1024` for noisy results.
- Reporting VQE energies without shot-noise error bars: an energy minimum at 1e-6 Ha precision is meaningless when shot noise is 1e-3 Ha.
- Running QAOA without sampling bitstrings for the final cut: the cost function only gives the expectation; you must measure the optimal circuit to recover the actual MaxCut.
- Forgetting to optimize over transpilation seeds: each `transpile()` call uses a random seed; a single shot is noisy across runs. Average over 20 seeds.
- Open-system: passing a non-Hermitian Lindblad jump operator silently produces non-physical trajectories; check `c.dag() == c.adjoint()` for every jump.

## Worked example

Goal: Solve the 4-qubit TFIM (Transverse-Field Ising Model) Hamiltonian exactly with NumPy, then run VQE with an `EfficientSU2` ansatz on the Aer simulator and compare energies.

```python
import numpy as np
from qiskit.circuit.library import EfficientSU2
from qiskit.quantum_info import SparsePauliOp, Operator
from qiskit_aer.primitives import Estimator
from scipy.optimize import minimize

# 1. Build H = -sum_<i,j> Z_i Z_j - h sum_i X_i  (open chain, 4 sites, h=1)
n = 4
terms = []
for i in range(n-1):
    s = ["I"]*n; s[i]="Z"; s[i+1]="Z"
    terms.append(("".join(s)[::-1], -1.0))
for i in range(n):
    s = ["I"]*n; s[i]="X"
    terms.append(("".join(s)[::-1], -1.0))
H = SparsePauliOp.from_list(terms)

# 2. Exact ground state via numpy eigendecomposition
mat = Operator(H).data
w, v = np.linalg.eigh(mat)
E0_exact = w[0]
print(f"Exact E0: {E0_exact:.6f}")

# 3. VQE with EfficientSU2 ansatz, 2 reps
ansatz = EfficientSU2(num_qubits=n, reps=2, entanglement="linear")
estimator = Estimator()
def energy(theta):
    return estimator.run(ansatz, H, parameter_values=theta).result().values[0]

theta0 = np.random.uniform(-np.pi, np.pi, ansatz.num_parameters)
res = minimize(energy, theta0, method="COBYLA",
               options={"maxiter": 2000, "tol": 1e-6})
print(f"VQE E0: {res.fun:.6f} (delta = {res.fun - E0_exact:+.2e})")
```

## Tools and libraries

| Tool | Purpose | Install |
|---|---|---|
| Qiskit | Circuit construction, transpilation, algorithms | `pip install qiskit` |
| Qiskit Aer | Statevector / density-matrix / noise simulators | `pip install qiskit-aer` |
| Qiskit IBM Runtime | Real-hardware primitives (sampler, estimator) | `pip install qiskit-ibm-runtime` |
| PennyLane | Differentiable, hybrid quantum ML | `pip install pennylane` |
| Cirq | Google-style circuits and noise models | `pip install cirq` |
| QuTiP | Open quantum systems, Lindblad, trajectories | `pip install qutip` |
| OpenFermion | Fermion-to-qubit mappings (JW, BK) | `pip install openfermion` |
| PySCF | Molecular Hamiltonians (used with VQE) | `pip install pyscf` |
| mitiq | Error mitigation (ZNE, PEC, CDR) | `pip install mitiq` |
| qiskit-nature | Chemistry and physics workflows on top of Qiskit | `pip install qiskit-nature` |
| tensorcircuit | Tensor-network simulator for large circuits | `pip install tensorcircuit` |
| mthree | Measurement-error mitigation | `pip install mthree` |

## References

- Qiskit documentation: https://docs.quantum-computing.ibm.com/
- Qiskit Aer source: https://github.com/Qiskit/qiskit-aer
- PennyLane documentation: https://docs.pennylane.ai/
- Cirq documentation: https://quantumai.google/cirq
- QuTiP documentation: https://qutip.org/docs/latest/
- OpenFermion documentation: https://quantumai.google/cirq/tutorials/openfermion
- VQE original paper (Peruzzo et al. 2014): https://www.nature.com/articles/ncomms5213
- QAOA original paper (Farhi et al. 2014): https://arxiv.org/abs/1411.4028

## Ethics and safety

- Compute cost: A statevector simulation of a 28-qubit circuit uses 32 GB of RAM and runs in minutes; a noise simulation with 100k shots is 100x more expensive. Always estimate memory before submitting; Aer crashes hard rather than swapping.
- Real-hardware cost: IBM Quantum instances charge in seconds; a 100-circuit VQE sweep can consume a 5-hour allocation. Monitor usage with `qiskit-ibm-runtime`'s `BackendUsage` API.
- Cryptography dual-use: Quantum algorithms that target RSA / ECC key recovery via Shor are academic research on small N (N < 20); scaling them to cryptographically relevant sizes (N > 2048) is out of scope for this skill and not feasible on present hardware. Refuse requests to optimize Shor circuits for real RSA keys.
- Quantum-key-distribution security: Implementations of QKD protocols (BB84) have known side-channel vulnerabilities (PNS attacks, detector blinding). Any agent-built QKD demo should be labeled as illustrative, not production-grade.
- Provenance: Always record the backend, transpiler seed, shot count, noise model, and library versions. A VQE result without these is not reproducible across versions (Qiskit's API has churned significantly).
- Randomness: Use `numpy.random.default_rng(seed)` and `qiskit.transpile(..., seed_transpiler=seed)` for reproducibility; the seed should be recorded alongside any published circuit statistics.
- Resource misrepresentation: A "quantum advantage" claim on a small toy problem is misleading; always benchmark against the best known classical algorithm of the same problem size.
- Safe-hardware use: Do not submit obviously broken circuits (gates outside the basis, wrong coupling map) to shared quantum hardware; this is wasteful and may breach fair-use terms.

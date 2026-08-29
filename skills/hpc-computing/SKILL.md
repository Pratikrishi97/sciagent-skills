---
name: hpc-computing
description: Run jobs on SLURM clusters, parallelize with MPI via mpi4py, scale dask on SLURM with dask-jobqueue, request GPUs, checkpoint long-running work, and stage data across scratch and parallel filesystems. Use when submitting batch jobs, writing job arrays, or building distributed Python on a cluster.
license: MIT
compatibility: Requires Python 3.10+ with dask-jobqueue, mpi4py. Optional: apptainer, dask, distributed, zarr. Requires access to a SLURM-based HPC cluster.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Research Infrastructure
---

# HPC Computing

## Overview

High-performance computing clusters use SLURM (Simple Linux Resource for
Resource Management) as the scheduler. The workloads are batch jobs (`sbatch`),
interactive allocations (`salloc`), job arrays, MPI programs, and modern
Python parallel stacks like Dask. This skill covers SLURM batch scripts
(partitions, QoS, job arrays, GPUs), mpi4py for SPMD parallelism,
dask-jobqueue for scaling Python on a cluster, checkpoint/restart for
long runs, data staging across `$HOME`, `$SCRATCH`, and parallel filesystems
(beeGFS, Lustre, GPFS), and fair-share/accounting best practices. The
principle is: write jobs that are idempotent, restartable, and friendly
to other users.

## When to use this skill

- You are submitting batch jobs to a SLURM cluster.
- You need to run an array of similar jobs (parameter sweep).
- You are writing an MPI program in Python with mpi4py.
- You want to scale pandas/numpy workloads with Dask.
- You need to request GPUs and manage checkpoint/restart.

## Prerequisites

- Python 3.10+
- Core: `mpi4py`, `dask`, `distributed`, `dask-jobqueue`
- Optional: `apptainer`, `zarr`, `pandas`, `numpy`, `cupy` for GPU
- System: a SLURM cluster account; cluster-specific paths to `$SCRATCH`
  and modulefiles
- pip install:
  ```bash
  pip install mpi4py dask distributed dask-jobqueue
  pip install zarr pandas numpy cupy-cuda12  # cuda matches the cluster driver
  ```

## Core workflows

### 1. SLURM batch script template

`job.sbatch`:
```bash
#!/bin/bash
#SBATCH --job-name=experiment
#SBATCH --partition=compute
#SBATCH --qos=normal
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=32
#SBATCH --cpus-per-task=1
#SBATCH --mem=120G
#SBATCH --time=04:00:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=you@lab.org

set -euo pipefail
module purge
module load python/3.11 cuda/12.4
source /sw/etc/profile.d/conda.sh
conda activate sciproj

srun --cpu-bind=cores python -m src.compute --in $SCRATCH/data/run.h5
```

Submit: `sbatch job.sbatch`. Track: `squeue -u $USER`.

### 2. Job arrays for parameter sweeps

```bash
#SBATCH --array=1-100%20   # 100 jobs, max 20 running
#SBATCH --output=logs/array-%A_%a.out

# Inside the script:
python -m src.sweep --trial $SLURM_ARRAY_TASK_ID
```

Resume from a failed index: `sbatch --array=42-100 job.sbatch`.

### 3. MPI parallelism with mpi4py

```python
from mpi4py import MPI
import numpy as np

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

N = 1_000_000
chunk = N // size
local = np.random.default_rng(rank).normal(size=chunk)
local_sum = float(local.sum())
total = comm.reduce(local_sum, op=MPI.SUM, root=0)

if rank == 0:
    print(f"sum across {size} ranks = {total:.2f}")
```

Run: `mpirun -np 8 python reduce.py` or via `srun --mpi=pmix -n 128`.

### 4. Dask on SLURM with dask-jobqueue

```python
from dask_jobqueue import SLURMCluster
from dask.distributed import Client

cluster = SLURMCluster(
    queue="compute",
    cores=32,
    memory="120GB",
    processes=32,
    walltime="02:00:00",
    job_extra_directives=["--export=ALL"],
    log_directory="logs/",
)
cluster.scale(jobs=10)  # 10 nodes = 320 workers
client = Client(cluster)

import dask.array as da
x = da.random.normal(size=(10_000, 10_000), chunks=(1_000, 1_000))
print("mean:", x.mean().compute())
client.close(); cluster.close()
```

### 5. GPU jobs and checkpoint/restart

```bash
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a100:1
#SBATCH --gpus-per-node=1
```

Checkpoint Python with dask or a manual pickle:
```python
import pickle, json
from pathlib import Path

def checkpoint(state, path):
    Path(path).parent.mkdir(exist_ok=True, parents=True)
    with open(path, "wb") as f:
        pickle.dump(state, f)
    with open(path + ".json", "w") as f:
        json.dump({"step": state["step"], "timestamp": state["ts"]}, f)

def maybe_resume(path):
    if Path(path).exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return None
```

## Best practices

- Always specify `--time`, `--mem`, and `--partition` in `sbatch`; jobs
  without these defaults are killed at the cluster cap.
- Use job arrays (`--array=1-N%K`) for parameter sweeps instead of one
  huge job; arrays resume cleanly.
- Stage data in `$SCRATCH`, not `$HOME`; home is quota'd and slow on
  parallel filesystems.
- Pre-fetch input files locally before launching compute; reading over
  NFS during a 128-task job thrashes metadata.
- Write outputs as Zarr or chunked HDF5; per-task CSV files written in
  parallel fragment the filesystem.
- Checkpoint every wall-hour; SLURM pre-empts at the walltime.
- Use `--cpu-bind=cores` and `--gpu-bind=map_gpu` for hardware affinity.
- Set `MAIL_TYPE=END,FAIL,TIME_LIMIT_50` and check your email.
- Use Apptainer SIFs, not Docker, on HPC; admin policies forbid Docker.
- Read the cluster's documentation on fair-share; killing "queue hog"
  behaviour helps everyone.

## Common pitfalls

- Forgetting `--mem` defaults to the cluster minimum and OOMs large tasks.
- Job arrays running 100 at once against a small DB; rate-limit with `%K`.
- `mpi4py` installed without the matching MPI library; `mpirun` silently
  falls back to OpenMPI without CUDA support.
- `srun` inside an `sbatch` job double-counts ranks; pick one of
  `mpirun` or `srun --mpi=pmix`.
- Dask cluster running `--mem=120GB` while requesting `120GB` from
  SLURM underestimates the dashboard's overhead; leave 5-10% slack.
- Writing one CSV per rank to a shared NFS path saturates metadata
  servers; aggregate into Zarr or Parquet partitions instead.
- Forgetting to `cluster.close()` leaves jobs orphaned; users are
  charged until they hit the walltime.
- `$SCRATCH` purged after 30 days; copy outputs to project space.
- GPUs without `nvidia-smi` pre-check on the allocated node; bind with
  `CUDA_VISIBLE_DEVICES` from the SLURM allocation.

## Worked example

A complete parameter sweep: 50 trials of a Python function, each as a
SLURM array job, writing results into a Zarr store, with checkpoint/resume.

`sweep.sbatch`:
```bash
#!/bin/bash
#SBATCH --job-name=sweep
#SBATCH --partition=compute
#SBATCH --array=1-50%10
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/sweep-%A_%a.out

set -euo pipefail
module load python/3.11
source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate sciproj

export SCRATCH=$SCRATCH
python -m src.sweep --trial ${SLURM_ARRAY_TASK_ID} \
  --in  $SCRATCH/sweep/trial_${SLURM_ARRAY_TASK_ID}/input.zarr \
  --out $SCRATCH/sweep/trial_${SLURM_ARRAY_TASK_ID}/output.zarr \
  --seed ${SLURM_ARRAY_TASK_ID}
```

`src/sweep.py`:
```python
import argparse, numpy as np, zarr, pickle, os
from pathlib import Path

def run(trial: int, in_path: str, out_path: str, seed: int) -> None:
    rng = np.random.default_rng(seed)
    # checkpoint file
    ckpt = Path(out_path).with_suffix(".pkl")
    if ckpt.exists():
        state = pickle.loads(ckpt.read_bytes())
        n0 = state["step"]
    else:
        state = {"step": 0}; n0 = 0

    # load Zarr
    root = zarr.open(in_path, mode="r")
    x = root["signal"][:]   # full slice, pretend local

    out_root = zarr.open(out_path, mode="a")
    ds = out_root.create_array("result", shape=(10_000,), chunks=(1_000,),
                               dtype="f4", overwrite=True)
    for k in range(n0, 10_000):
        ds[k] = float(np.cos(x[k % len(x)]) + rng.normal(0, 0.01))
        state["step"] = k + 1
        if k % 1000 == 0:
            ckpt.write_bytes(pickle.dumps(state))
            os.fsync(ckpt.open("rb").fileno()) if False else None
    ckpt.unlink(missing_ok=True)  # clean up on success

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--trial", type=int, required=True)
    p.add_argument("--in", dest="in_path", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    run(a.trial, a.in_path, a.out, a.seed)
```

Submit and monitor:
```bash
sbatch sweep.sbatch
squeue -u $USER
# After all jobs complete, aggregate:
python - <<'PY'
import zarr, dask.array as da
root = zarr.open("$SCRATCH/sweep", mode="r")
chunks = [root[f"trial_{i:02d}/output.zarr/result"][:] for i in range(1, 51)]
out = da.stack(chunks).mean(axis=0).compute()
print("mean curve:", out[:5])
PY
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| SLURM (sbatch/srun) | Cluster scheduler | system provisioned |
| mpi4py | MPI for Python | `pip install mpi4py` |
| dask | Parallel arrays/dataframes | `pip install dask` |
| distributed | Dask scheduler + workers | `pip install distributed` |
| dask-jobqueue | SLURM/PBS deployment | `pip install dask-jobqueue` |
| apptainer | HPC containers | install Apptainer |
| zarr | Chunked parallel writes | `pip install zarr` |
| cupy | GPU arrays | `pip install cupy-cuda12` |
| strace | Debug filesystem contention | system tool |
| Mamba/conda | Module envs on HPC | install Miniforge |
| nvidia-smi | GPU introspection | NVIDIA driver |

## References

- SLURM docs: https://slurm.schedmd.com/documentation.html
- sbatch manual: https://slurm.schedmd.com/sbatch.html
- mpi4py tutorial: https://mpi4py.readthedocs.io/
- dask-jobqueue: https://jobqueue.dask.org/
- Dask best practices: https://docs.dask.org/en/stable/best-practices.html
- Apptainer user guide: https://apptainer.org/docs/user/main/
- Zarr parallel writes: https://zarr.readthedocs.io/
- NCAR HPC best practices: https://arc.ucar.edu/knowledge-base/

## Ethics & safety

- **Fair-share:** respect cluster fair-share policies; do not game QoS or
  over-allocate. Other labs share the cluster.
- **Cost transparency:** record core-hours and GPU-hours in your project
  reports; PI budgets depend on accurate accounting.
- **Energy:** prefer vectorized, GPU, or distributed runs over naive
  loops; cluster time is real carbon.
- **Reproducibility:** pin container image SHAs and module versions in
  job scripts; reviewers must be able to re-run the same SLURM script.
- **Safety:** test jobs at small scale (`salloc --time=00:30:00`) before
  firing an array; cluster admins notice badly behaved accounts.

# Example: SLURM job array for parameter sweeps

**Skills activated:** `hpc-computing`, `reproducible-environments`

## The prompt

> I have a parameter sweep: 64 configs of a PyTorch training script, each needs 1 GPU for ~2 hours. Write a SLURM job array that runs all 64 in parallel batches of 8, with checkpoint/resume, scratch staging, and a Singularity image for full reproducibility. Report a summary CSV of run times + final metrics.

## What the agent does

`hpc-computing` on `SLURM`, `sbatch`, `job array`, `gres=gpu`; `reproducible-environments` for the Singularity image + pinned env.

### 1. The SLURM batch script

```bash
#!/bin/bash
#SBATCH --job-name=sweep
#SBATCH --array=0-63%8              # 64 tasks, max 8 concurrent
#SBATCH --time=02:30:00
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --output=logs/%A_%a.out
#SBATCH --error=logs/%A_%a.err

set -euo pipefail
module load cuda/12.2
module load apptainer/1.2

# config index from the array task ID
CONFIGS=(configs/*.yaml)
CFG=${CONFIGS[$SLURM_ARRAY_TASK_ID]}
NAME=$(basename "$CFG" .yaml)

# stage to local scratch
SCRATCH=/localscratch/$SLURM_JOB_ID-$SLURM_ARRAY_TASK_ID
mkdir -p "$SCRATCH"
cp data/tiny.pt "$SCRATCH/"
cp "$CFG" "$SCRATCH/config.yaml"

# run inside the pinned container
apptainer exec --nv --bind "$SCRATCH:/work" envs/train.sif \
    python train.py --config /work/config.yaml \
                    --data /work/tiny.pt \
                    --ckpt /work/${NAME}.pt \
                    --resume /work/${NAME}.pt 2>/dev/null || true

# copy results back
cp "$SCRATCH/${NAME}.pt" results/
cp "$SCRATCH/metrics.json" "results/${NAME}.json"
rm -rf "$SCRATCH"
```

### 2. Build the Singularity image from a Dockerfile (hermetic)

```dockerfile
FROM nvidia/cuda:12.2.0-cudnn8-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y python3-pip
RUN pip3 install --no-cache-dir torch==2.2.0 pandas==2.2.0 pyyaml==6.0.1
ENTRYPOINT ["python3"]
```

```bash
docker build -t train:1.0 .
docker run --rm -v $(pwd):/work train:1.0 bash -c "cd /work && python train.py --config configs/c0.yaml --dry-run"
apptainer build envs/train.sif docker-daemon://train:1.0
```

### 3. Aggregate results

```python
# pip install pandas
import pandas as pd, json, pathlib
rows = []
for p in pathlib.Path("results").glob("*.json"):
    rows.append(json.loads(p.read_text()))
df = pd.DataFrame(rows)
df.to_csv("sweep_summary.csv", index=False)
print(df.sort_values("val_auc", ascending=False).head())
```

## Pitfalls the skill surfaces

- `%8` caps concurrency at 8 — without it, SLURM will try to start all 64 at once and queue most of them, but on a busy cluster you'll starve other users. Match the cap to your fair-share.
- `--resume` with a missing checkpoint silently does nothing; guard it (`2>/dev/null || true`) so a first run doesn't fail the array.
- `/localscratch` is per-node; copy results back to `$HOME` or a shared scratch before the job ends or they're gone.
- `--nv` exposes host GPUs inside Apptainer; without it the container sees no CUDA devices.
- Pin every library version in the Dockerfile. A "latest" tag makes the run unreproducible in 6 months.

## Reproducibility

Commit the SLURM script, the configs, and the Dockerfile + `.sif` SHA256 to the repo. Record `sacct -j <jobid> --format=...` for runtime stats. See the `reproducible-research` skill for the Snakemake + DVC wrap if the sweep is part of a larger pipeline.

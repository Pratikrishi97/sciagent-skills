---
name: reproducible-environments
description: Pin Python and system dependencies with conda/mamba, lockfiles (conda-lock, pip-tools, uv), multi-stage Dockerfiles, Apptainer/Singularity for HPC, and nix for hermetic builds. Use when building containers or lockfiles so collaborators and CI reproduce exact package versions and hashes.
license: MIT
compatibility: Requires Python 3.10+ with conda or mamba; optional Docker, Apptainer, nix, uv, pip-tools.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Research Infrastructure
---

# Reproducible Environments

## Overview

Reproducibility lives or dies at the environment layer. A pinned environment
that boots in 2026 must still install in 2030. The canonical stack: conda or
mamba for cross-platform binary packages; `conda-lock` for fully reproducible
multi-platform lockfiles; `pip-tools` for hash-pinned pip environments; `uv`
for blazing-fast installs and lock files; Docker multi-stage builds for full
runtime reproducibility; Apptainer/Singularity for HPC containerized runs;
and nix for hermetic, content-addressable builds. The principle is: every
artifact has a lockfile (or a container image hash) tied to a single
commit of your code.

## When to use this skill

- You need new collaborators to install the project in one command.
- You are shipping to HPC where users cannot `sudo docker`.
- You want CI to fail fast on a dependency change that breaks the build.
- You need bit-for-bit reproducibility for a published paper.
- You are migrating from conda to uv to speed up CI.

## Prerequisites

- Python 3.10+
- One of: `conda` (Anaconda or Miniforge), `mamba`, or `micromamba`
- For pip workflows: `pip`, `pip-tools`, `uv` (>=0.4)
- For containers: `docker`, or `apptainer`/`singularity` on HPC
- Optional: `nix` (>=2.18) for hermetic builds
- pip install:
  ```bash
  pip install --upgrade uv pip-tools conda-lock
  ```

## Core workflows

### 1. Conda/mamba environment.yml

```yaml
# environment.yml
name: sciproj
channels:
  - conda-forge
  - nodefaults
dependencies:
  - python=3.11
  - numpy=1.26.*
  - pandas=2.2.*
  - matplotlib=3.9.*
  - h5py=3.10.*
  - pyarrow=15.*
  - pip
  - pip:
    - opentrons==2.20.*
    - structlog==24.*
```

Create and lock:
```bash
mamba env create -f environment.yml
mamba env export --no-builds > environment.lock.yml
```

### 2. Cross-platform lockfile with conda-lock

```bash
conda-lock lock --file environment.yml \
  --platform linux-64 --platform osx-64 --platform osx-arm64 \
  --lockfile conda-linux.yml
# Re-create exactly:
conda-lock install -n sciproj conda-linux.yml
```

### 3. Hash-pinned pip requirements with uv

```bash
# pyproject.toml has dependencies; uv.lock is the hash-pinned lockfile
uv venv
uv pip compile pyproject.toml -o requirements.txt --generate-hashes
uv sync            # exact re-install from uv.lock
uv pip install -r requirements.txt --require-hashes
```

### 4. Multi-stage scientific Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache-dir -r pyproject.toml

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src ./src
RUN useradd -m -u 1000 scientist
USER scientist
ENTRYPOINT ["python", "-m", "src.cli"]
```

Build and pin:
```bash
docker build -t sciproj:$(git rev-parse --short HEAD) .
docker run --rm sciproj:abc1234 --version
```

### 5. Apptainer / Singularity for HPC

```bash
# Build a SIF from the Docker image above
apptainer build sciproj.sif docker-daemon://sciproj:abc1234
# Run on an HPC cluster login node
srun apptainer exec sciproj.sif python -m src.cli
```

A `def` (definition file) alternative for HPC build hosts that cannot run
docker:

```singularity
Bootstrap: docker
From: python:3.11-slim
%post
    pip install --no-cache-dir uv
    uv pip install --system numpy pandas matplotlib pyarrow
%runscript
    exec python "$@"
```

## Best practices

- Always provide a lockfile alongside the spec file; CI should build from
  the lockfile, not from loose version ranges.
- Pin Python itself (`python=3.11`) in `environment.yml`; `python>=3.10`
  is for development only.
- Use `conda-forge` as the first channel and `nodefaults`; mixing channels
  silently produces unsatisfiable solves.
- Hash-pinned pip files (`--generate-hashes`) detect supply-chain swaps.
- Multi-stage Dockerfiles keep the final image small (~200 MB vs 2 GB for
  a monolithic scientific image).
- In containers, set `WORKDIR`, create a non-root user, and fix the UID/GID
  to match HPC (`1000:1000` is the conventional default).
- For HPC: ship an Apptainer SIF; admins rarely allow Docker.
- Use `uv` for cache reuse across CI runs; pip's cache is slower and
  re-resolves every time.
- Re-lock on every PR via CI; require approval for changes to the lockfile.
- Tag container images with `git short SHA`, not `latest`; reviewers must
  know exactly what they ran.

## Common pitfalls

- `environment.yml` with `>=` constraints solved by latest package on the
  day of install; downstream CI gets a different env.
- Mixing conda and pip-installed packages in one environment breaks on
  pip upgrades (numpy ABI mismatch); pick one channel per env.
- Single-stage Dockerfiles install compilers in the final image,
  multiplying its size; always use multi-stage.
- Forgetting `--no-builds` in `conda env export` writes platform-specific
  build strings that don't transfer across Linux/macOS.
- `uv` lockfile and `requirements.txt` drift if both are committed; pick
  one as the source of truth.
- Apptainer build sandboxed from Dockerfile on a system without Docker;
  build SIFs on a host with Docker, then copy to HPC.
- Hardcoding `/home/you` paths in containers breaks at runtime where the
  user is different; use `${HOME}` or absolute `/app`.
- nix flakes that pin to a moving `nixpkgs` channel silently bump;
  use `github:NixOS/nixpkgs/<rev>` in the flake input.

## Worked example

Reproducible environment for a small scientific project end-to-end: conda
environment.yml, conda-lock lockfile, multi-stage Dockerfile, and an
Apptainer SIF for HPC.

```yaml
# environment.yml
name: sciproj
channels: [conda-forge, nodefaults]
dependencies:
  - python=3.11
  - numpy=1.26.*
  - pandas=2.2.*
  - matplotlib=3.9.*
  - h5py=3.10.*
  - pip
  - pip:
      - structlog==24.*
```

```bash
# 1. Solve and lock for linux-64 (one command)
conda-lock lock -f environment.yml -p linux-64 -p osx-arm64
# Result: conda-linux.yml, confa-osx-arm64.yml (fully hashed)

# 2. Build the container
docker build -t sciproj:$(git rev-parse --short HEAD) .

# 3. Convert to Apptainer SIF for HPC
apptainer build sciproj.sif docker-daemon://sciproj:$(git rev-parse --short HEAD)

# 4. Run on the cluster (with SLURM)
sbatch --wrap="apptainer exec sciproj.sif python -m src.cli --in data/run.h5"
```

Verify reproducibility by running the same SHA + lockfile in three places:
```bash
# Local Linux dev box
conda-lock install -n sciproj conda-linux.yml
# macOS laptop
conda-lock install -n sciproj conda-osx-arm64.yml
# CI (GitHub Actions ubuntu-latest)
conda-lock install -n sciproj conda-linux.yml
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| conda | Cross-platform binary packages | install Miniforge |
| mamba | Fast conda solver | `conda install mamba` |
| micromamba | Single-binary conda | install from GitHub |
| conda-lock | Multi-platform lockfiles | `pip install conda-lock` |
| pip | Standard Python installer | bundled with Python |
| pip-tools | Hash-pinned pip requirements | `pip install pip-tools` |
| uv | Ultra-fast installer + lock | `pip install uv` |
| docker | Container runtime | system install |
| apptainer | HPC containers | install Apptainer |
| nix | Hermetic builds | install nix |
| just | Recipe runner | `cargo install just` or prebuilt |

## References

- conda user guide: https://docs.conda.io/projects/conda/
- mamba: https://mamba.readthedocs.io/
- conda-lock: https://conda-incubator.github.io/conda-lock/
- pip-tools: https://pip-tools.readthedocs.io/
- uv docs: https://docs.astral.sh/uv/
- Dockerfile reference: https://docs.docker.com/engine/reference/builder/
- Apptainer docs: https://apptainer.org/docs/
- Nix Flakes: https://nixos.wiki/wiki/Flakes

## Ethics & safety

- **Supply chain:** hash-pinned lockfiles detect malicious swaps; never
  ship from a `latest` tag in production.
- **License compliance:** audit the dependency tree for copyleft (GPL)
  licenses when shipping commercial software; use `pip-licenses`.
- **Reproducibility:** pin and lock before publishing; reviewers cannot
  reproduce "works on my machine" claims.
- **Security:** scan images for known CVEs (`grype`, `trivy`); rebuild
  periodically even if the lockfile did not change.
- **Accessibility of compute:** prefer free and open-source runtimes
  (Apptainer over Docker on HPC) so environments run on shared,
  institutionally-funded resources.

---
name: deep-learning
description: Train and fine-tune neural networks for scientific research using PyTorch, including image classification, regression on spectroscopy, transfer learning on microscopy, mixed-precision training, distributed training with accelerate or DDP, gradient checkpointing, and JAX/Flax for research prototyping. Use when training models with nn.Module, DataLoader, optim, lr_scheduler, autocast, early stopping, or integrating Weights and Biases or MLflow for experiment tracking.
license: MIT
compatibility: Requires Python 3.10+ with PyTorch 2.1+ and CUDA-capable GPU recommended. Optional extras include accelerate, wandb, mlflow, jax, flax, tqdm.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Machine Learning & Statistics
---

# Deep Learning for Science

## Overview

Deep learning is the workhorse for high-dimensional scientific data — microscopy, crystallography, spectroscopy, genomics sequences, single-cell counts, climate fields, and remotely sensed imagery. PyTorch has become the dominant framework in scientific labs because of its eager execution, research-friendly API, and tight integration with the broader Python scientific stack (NumPy, xarray, scikit-image).

This skill covers the canonical PyTorch research loop: `nn.Module` design, `DataLoader` batching, an `optim` + `lr_scheduler` training loop with `tqdm` progress, mixed-precision training via `torch.autocast`, distributed training with `accelerate` or native DDP, gradient checkpointing for memory-bound models, transfer learning for fine-tuning pretrained backbones (torchvision, timm, torchgeo), experiment tracking with Weights & Biases and MLflow, and the early-stopping discipline that prevents overfitting on small scientific datasets.

## When to use this skill

- You are training a CNN, ViT, GNN, or transformer on scientific image/sequence/graph data.
- You need mixed-precision training to fit larger batches or larger models on a single GPU.
- You want to fine-tune a pretrained backbone (e.g., ImageNet, SatMAE, scVI) on a small scientific dataset.
- You are scaling beyond one GPU with `accelerate`, DDP, or FSDP.
- Your model is memory-bound and you need gradient checkpointing.
- You want to log metrics, hyperparameters, and model artifacts to W&B or MLflow.
- You want to prototype a custom architecture in JAX/Flax for research.
- You need early stopping and checkpoint resume for long training runs.

## Prerequisites

- Python 3.10+
- PyTorch >= 2.1 (CUDA 11.8 or 12.1 recommended)
- torchvision, tqdm, numpy

```bash
pip install torch torchvision tqdm numpy matplotlib
# Optional research-grade extras
pip install accelerate wandb mlflow timm torchmetrics jax flax optax
```

Verify GPU: `python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`.

## Core workflows

### Model definition (nn.Module) and DataLoader

```python
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

class SpectraDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.as_tensor(X, dtype=torch.float32)        # (N, L)
        self.y = torch.as_tensor(y, dtype=torch.float32).unsqueeze(-1)  # (N, 1)
    def __len__(self): return len(self.X)
    def __getitem__(self, i): return self.X[i], self.y[i]

class ConvReg(nn.Module):
    def __init__(self, L=512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(1, 32, 7, padding=3), nn.ReLU(), nn.MaxPool1d(2),
            nn.Conv1d(32, 64, 5, padding=2), nn.ReLU(), nn.MaxPool1d(2),
            nn.Flatten(),
            nn.Linear(64 * (L // 4), 128), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 1),
        )
    def forward(self, x):
        return self.net(x.unsqueeze(1))  # add channel dim

train_loader = DataLoader(SpectraDataset(X_tr, y_tr), batch_size=64,
                          shuffle=True, num_workers=4, pin_memory=True)
```

### Training loop with autocast (mixed precision) and tqdm

```python
from tqdm import tqdm
from torch import optim
from torch.optim.lr_scheduler import CosineAnnealingLR

device = "cuda" if torch.cuda.is_available() else "cpu"
model = ConvReg().to(device)
opt = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
sched = CosineAnnealingLR(opt, T_max=len(train_loader) * 50)
scaler = torch.cuda.amp.GradScaler()

for epoch in range(50):
    model.train()
    for X, y in tqdm(train_loader, desc=f"epoch {epoch}"):
        X, y = X.to(device, non_blocking=True), y.to(device, non_blocking=True)
        with torch.autocast(device_type="cuda", dtype=torch.float16):
            loss = nn.functional.mse_loss(model(X), y)
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.step(opt)
        scaler.update()
        sched.step()
```

### Early stopping + checkpointing

```python
class EarlyStop:
    def __init__(self, patience=5, min_delta=0.0):
        self.patience, self.min_delta = patience, min_delta
        self.best, self.wait = float("inf"), 0
    def step(self, val_loss) -> bool:
        if val_loss < self.best - self.min_delta:
            self.best, self.wait = val_loss, 0
            return True   # save checkpoint
        self.wait += 1
        return self.wait < self.patience

es = EarlyStop(patience=7)
for epoch in range(50):
    val_loss = evaluate(model, val_loader)
    save = es.step(val_loss)
    if save:
        torch.save({"model": model.state_dict(), "epoch": epoch}, "best.pt")
    if not save and es.wait >= es.patience:
        break
```

### Transfer learning with a frozen pretrained backbone

```python
import timm
import torch.nn as nn

backbone = timm.create_model("resnet50", pretrained=True, num_classes=0)
backbone.eval()
for p in backbone.parameters(): p.requires_grad = False

class TransferHead(nn.Module):
    def __init__(self, dim=2048, n_classes=8):
        super().__init__()
        self.backbone = backbone
        self.head = nn.Linear(dim, n_classes)
    def forward(self, x):
        with torch.no_grad():
            feats = self.backbone(x)
        return self.head(feats)

model = TransferHead().to(device)
opt = optim.AdamW(model.head.parameters(), lr=1e-3)  # train head only first
```

### Distributed training with accelerate

```python
# train.py
from accelerate import Accelerator
accel = Accelerator(mixed_precision="fp16")
model, opt, train_loader, sched = accel.prepare(model, opt, train_loader, sched)
for X, y in train_loader:
    with accel.autocast():
        loss = nn.functional.mse_loss(model(X), y)
    accel.backward(loss); opt.step(); opt.zero_grad()
# Run:  accelerate launch --multi_gpu --num_processes 4 train.py
```

For native DDP, use `torch.nn.parallel.DistributedDataParallel` and `torchrun --nproc_per_node=4 train.py`.

## Best practices

- Always seed everything: `torch.manual_seed(42)`, `np.random.seed(42)`, `random.seed(42)`, and set `torch.backends.cudnn.deterministic=True` when needed.
- Use `AdamW` (decoupled weight decay) over `Adam` for new projects; pair with a `CosineAnnealingLR` or `OneCycleLR` schedule.
- Enable mixed precision (`autocast` + `GradScaler`) by default — typically 1.5-2x speedup and 2x memory savings.
- Prefer `timm` for vision backbones over hand-rolled ResNet/ViT code.
- Use `torchmetrics` for correctness-checked metrics (AUROC, F1, etc.) accumulated across batches.
- Log everything (hyperparams, gradients, samples, metrics) to W&B or MLflow; reproduce from a single config artifact.
- Use gradient checkpointing (`model.gradient_checkpointing_enable()`) for transformers / large models that don't fit in memory.
- Validate on a fixed, time-stamped holdout — never on training-augmented batches.
- Save checkpoints as `{"model": state_dict, "epoch": epoch, "config": cfg}` and resume from `--resume best.pt`.
- Profile before optimizing: `torch.profiler.profile` reveals whether you are GPU-, CPU-, or IO-bound.

## Common pitfalls

- **Forgetting `model.train()` / `model.eval()`** — dropout and BN stats leak across train/eval, silently degrading results.
- **`shuffle=True` in test loader** — breaks reproducibility and any per-sample interpretation.
- **Not using `non_blocking=True` and `pin_memory=True`** — leaves 10-20% of GPU idle on data movement.
- **Vanilla Adam + flat LR** — typically 0.5x worse than AdamW + cosine schedule; common rookie mistake.
- **Log-softmax + NLLLoss** — works, but is slower than `cross_entropy` which is fused; the two are mathematically equivalent.
- **Unsynced `scaler` in distributed training** — each process must call `scaler.step(opt)` consistently or gradients desync.
- **Forgetting to freeze backbone** for transfer learning step 1 — the pretrained weights drift and the small new head cannot recover.
- **No early stopping** on small scientific datasets — the model memorizes the training set after a few epochs and val loss diverges.

## Worked example

Train a 1D-CNN regressor on synthetic spectra, with mixed precision, early stopping, and W&B logging.

```python
import numpy as np, torch, torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from torch import optim
from tqdm import tqdm

# Synthetic: 1D spectra (L=256), target = sum of two Gaussian peaks
N, L = 2000, 256
x = np.linspace(0, 10, L)
X = (np.exp(-(x - 3) ** 2 / 0.5) * np.random.uniform(0.5, 1.5, (N, 1))
     + np.exp(-(x - 7) ** 2 / 0.8) * np.random.uniform(0.3, 1.0, (N, 1))).astype(np.float32)
y = X.sum(axis=1).astype(np.float32)

ds = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
dl = DataLoader(ds, batch_size=64, shuffle=True, num_workers=2, pin_memory=True)

class CNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(1, 32, 7, padding=3), nn.ReLU(), nn.MaxPool1d(2),
            nn.Conv1d(32, 64, 5, padding=2), nn.ReLU(), nn.MaxPool1d(2),
            nn.Flatten(),
            nn.Linear(64 * (L // 4), 128), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, 1),
        )
    def forward(self, x): return self.net(x.unsqueeze(1)).squeeze(-1)

device = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(42)
model = CNN().to(device)
opt = optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
sched = optim.lr_scheduler.CosineAnnealingLR(opt, T_max=len(dl) * 30)
scaler = torch.cuda.amp.GradScaler()

best, wait = float("inf"), 0
for epoch in range(30):
    model.train()
    for Xb, yb in tqdm(dl, desc=f"epoch {epoch}"):
        Xb, yb = Xb.to(device, non_blocking=True), yb.to(device, non_blocking=True)
        with torch.autocast(device_type=device, dtype=torch.float16) if device == "cuda" else torch.cuda.amp.autocast(enabled=False):
            loss = nn.functional.mse_loss(model(Xb), yb)
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
    if loss.item() < best - 1e-4:
        best, wait = loss.item(), 0
        torch.save(model.state_dict(), "best.pt")
    else:
        wait += 1
        if wait >= 5: break
print(f"best train MSE = {best:.4f}")
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| PyTorch | Tensors, autograd, nn, optim | `pip install torch` |
| torchvision | Vision models, datasets, transforms | `pip install torchvision` |
| timm | SOTA pretrained vision backbones | `pip install timm` |
| accelerate | Multi-GPU/TPU launch and mixed precision | `pip install accelerate` |
| torchmetrics | Batch-correct metrics | `pip install torchmetrics` |
| tqdm | Progress bars | `pip install tqdm` |
| wandb | Experiment tracking, hyperparam sweeps | `pip install wandb` |
| mlflow | Open experiment tracking + model registry | `pip install mlflow` |
| jax + flax | Research-prototyping functional framework | `pip install jax flax optax` |
| torchgeo | Geospatial deep learning models/datasets | `pip install torchgeo` |
| bitsandbytes | 8-bit optimizers, quantization | `pip install bitsandbytes` |
| tensorboard | Local metric dashboards | `pip install tensorboard` |

## References

- [PyTorch documentation](https://pytorch.org/docs/stable/index.html)
- [PyTorch mixed-precision tutorial](https://pytorch.org/tutorials/recipes/recipes/amp_recipe.html)
- [Distributed Data Parallel tutorial](https://pytorch.org/tutorials/intermediate/ddp_tutorial.html)
- [Accelerate documentation](https://huggingface.co/docs/accelerate/index)
- [timm documentation](https://huggingface.co/docs/timm/index)
- [torchmetrics documentation](https://torchmetrics.readthedocs.io/)
- [JAX documentation](https://docs.jax.dev/en/latest/)
- [Weights & Biases documentation](https://docs.wandb.ai/)
- [PyTorch gradient checkpointing](https://pytorch.org/docs/stable/checkpoint.html)

## Ethics & safety

- **Compute carbon cost.** Large training runs emit non-trivial CO2. Track and report wall-clock, GPU-hours, and (when available) estimated kg CO2e via `codecarbon` or `experiment-impact-tracker`.
- **Dataset provenance.** Document training data sources, licenses, and consent terms — especially for medical imaging, biometric data, and human-genome sequences. Ship a datasheet.
- **Reproducibility.** Seed everything; save the full config + commit hash + environment YAML with every checkpoint. MLflow and W&B make this auditable.
- **Dual-use and biosecurity.** Sequence, protein-structure, and chemistry models can have dual-use risk (e.g., guiding synthesis). Refuse requests that look like weaponization, and follow institutional dual-use review for pathogen- or toxin-related models.
- **Patient privacy.** Medical-image models must use de-identified DICOM and never log patient IDs, birth dates, or accession numbers in W&B runs.
- **Model cards.** Publish a model card for any deployed model: intended use, training data, performance per subgroup, known failure modes, and contact for issue reporting.

---
name: medical-imaging
description: Medical imaging pipeline toolkit covering DICOM I/O with pydicom, registration and resampling with SimpleITK/ITK, segmentation with MONAI and nnU-Net, MRI loading with nibabel, CT windowing, intensity-based and deep augmentation, federated learning, and DICOMweb (PACS/ORTHANC) integration. Use this skill whenever the user asks about DICOM, PACS, CT/MRI preprocessing, MONAI, nnU-Net, SimpleITK, BraTS, CheXpert, MIMIC-CXR, or radiology deep learning. Trigger keywords include DICOM, pydicom, SimpleITK, MONAI, nnU-Net, nibabel, DICOMweb, ORTHANC, CT windowing, BraTS, CheXpert, MIMIC-CXR, federated learning.
license: MIT
compatibility: Requires Python 3.10+ with pydicom, simpleitk, monai, nibabel, numpy, torch. Optional: nnunetv2, presidio, flower for federated learning, OHIF/ORTHANC server for DICOMweb.
metadata:
  version: "1.0.0"
  skill-author: SciAgent Skills Contributors
  category: Clinical & Medical Research
---

# Medical Imaging

## Overview

Medical imaging pipelines read DICOM studies from a PACS or on-disk, de-identify
them, resample to a common voxel grid, register series, and feed segmentation or
detection models (MONAI networks, nnU-Net self-configuring pipelines, CheXpert
classifiers). Outputs are RT-Struct, NIfTI segmentation masks, or DICOM-SR
structured reports. The field is dominated by DICOM format conventions, voxel
spacing inconsistencies, contrast windowing (CT in Hounsfield units), and strict
de-identification requirements before any model touches the data.

This skill wires `pydicom` for DICOM I/O, `SimpleITK` for resampling and
registration, `MONAI` and `nnU-Net` for segmentation, `nibabel` for NIfTI/MRI
work, and the DICOMweb (`QIDO-RS`/`WADO-RS`/`STOW-RS`) protocol for ORTHANC and
enterprise PACS.

## When to use this skill

- User asks to **read**, **de-identify**, or **write** DICOM files.
- User needs to **resample** or **register** CT/MR volumes to a common grid.
- User asks to **segment** organs, lesions, or tumors (liver, brain, lung).
- User mentions **MONAI**, **nnU-Net**, **3D U-Net**, **DeepEdit**, **DeepGrow**.
- User asks for **CT windowing** (lung, bone, brain, abdomen) and HU conversion.
- User wants to query a **PACS** or **ORTHANC** via DICOMweb.
- User asks for **federated learning** across hospital sites.
- Skip for: general computer vision (use a generic CV skill), pathology
  whole-slide imaging (use a dedicated WSI skill), or clinical text
  de-identification (use `clinical-nlp`).

## Prerequisites

- Python 3.10+ (3.11 recommended; PyTorch 2.x with CUDA for GPU workflows).
- System tools: `dcm2niix` (DICOM -> NIfTI), `gdcm` (optional DICOM codec).
- Python packages:

```bash
pip install pydicom simpleitk nibabel numpy scipy pandas
pip install "monai[all]" torch torchvision
# Optional: nnunetv2 flower pynetdicom (DICOMweb client / DICOM SCP)
# Optional: platipy (registration helper), dcmstack
```

- Data access: TCIA (open), MIMIC-CXR (PhysioNet credentialed), BraTS (open),
  CheXpert (Stanford license), local IRB approval for clinical PACS extracts.

## Core workflows

### DICOM I/O with pydicom

Read a CT slice, convert pixel data to Hounsfield units, and apply a lung
window.

```python
import pydicom, numpy as np
ds = pydicom.dcmread("CT_001.dcm")
img = ds.pixel_array.astype(np.float32)
# Convert to Hounsfield units: HU = pixel * RescaleSlope + RescaleIntercept
img = img * float(ds.RescaleSlope) + float(ds.RescaleIntercept)

def window(img, center=-600, width=1500):
    lo, hi = center - width / 2, center + width / 2
    return np.clip(img, lo, hi)

lung = window(img, -600, 1500)
bone = window(img, 400, 1500)
brain = window(img, 40, 80)
```

### Resampling and registration with SimpleITK

Resample a CT to 1x1x1 mm isotropic and rigidly register two MR series.

```python
import SimpleITK as sitk
img = sitk.ReadImage("ct.nrrd")
spacing = img.GetSpacing()
new_spacing = (1.0, 1.0, 1.0)
resampled = sitk.Resample(
    img, sitk.Transform(3, sitk.sitkIdentity),
    sitk.sitkLinear, 0.0, img.GetPixelID(),
    img.GetOrigin(), new_spacing, img.GetDirection())

# Rigid registration of moving->fixed MR
fixed = sitk.ReadImage("mr_fixed.nrrd")
moving = sitk.ReadImage("mr_moving.nrrd")
reg = sitk.ImageRegistrationMethod()
reg.SetMetricAsMeanSquares()
reg.SetOptimizerAsRegularStepGradientDescent(0.1, 100, 1e-6, 10)
reg.SetInitialTransform(sitk.Euler3DTransform())
final_tx = reg.Execute(fixed, moving)
resampled_moving = sitk.Resample(
    moving, fixed, final_tx, sitk.sitkLinear, 0.0)
```

### Brain tumor segmentation with MONAI

Build a 3D U-Net training loop on BraTS-format NIfTI volumes.

```python
import torch, monai
from monai.networks.nets import UNet
from monai.data import CacheDataset, DataLoader, decollate_batch
from monai.transforms import (
    LoadImageD, EnsureChannelFirstD, SpacingD, OrientationD,
    ScaleIntensityD, RandFlipD, Compose)

keys = ("image", "label")
train_tf = Compose([
    LoadImageD(keys), EnsureChannelFirstD(keys),
    OrientationD(keys, "RAS"), SpacingD(keys, (1.5, 1.5, 1.5)),
    ScaleIntensityD("image"),
    RandFlipD(keys, prob=0.5, spatial_axis=0),
])
data = [{"image": f"brats/{i}/t1.nii.gz", "label": f"brats/{i}/seg.nii.gz"}
        for i in range(50)]
ds = CacheDataset(data, train_tf, cache_rate=0.5)
loader = DataLoader(ds, batch_size=2, shuffle=True)

net = UNet(
    spatial_dims=3, in_channels=1, out_channels=4,
    channels=(16, 32, 64, 128, 256), strides=(2, 2, 2, 2),
    num_res_units=2).cuda()
opt = torch.optim.AdamW(net.parameters(), 1e-4)
loss = monai.losses.DiceCELoss(to_onehot_y=True, softmax=True)
for epoch in range(10):
    for batch in loader:
        x, y = batch["image"].cuda(), batch["label"].cuda()
        opt.zero_grad(); l = loss(net(x), y); l.backward(); opt.step()
```

### nnU-Net v2 self-configured training

Run nnU-Net's planning and training on a custom dataset.

```bash
# Prepare dataset following nnU-Net raw format:
#   nnUNet_raw/Dataset001_MyTask/imagesTr/...nii.gz
#   nnUNet_raw/Dataset001_MyTask/labelsTr/...nii.gz
#   nnUNet_raw/Dataset001_MyTask/dataset.json
nnUNetv2_plan_and_preprocess -d 1 --verify_dataset_integrity
nnUNetv2_train DATASET_ID 1 3d_fullres --c   # 5-fold cross-val
nnUNetv2_predict -i input/ -o output/ -d 1 -c 3d_fullres
```

```python
import subprocess
subprocess.run(["nnUNetv2_plan_and_preprocess", "-d", "1",
                "--verify_dataset_integrity"], check=True)
subprocess.run(["nnUNetv2_train", "1", "1", "3d_fullres"], check=True)
```

### DICOMweb query and fetch (ORTHANC/PACS)

Query studies, series, and retrieve instances via DICOMweb QIDO-RS/WADO-RS.

```python
import requests
BASE = "https://orthanc.local/dicom-web"
headers = {"Authorization": "Bearer " + TOKEN}

# QIDO-RS: find studies
r = requests.get(f"{BASE}/studies?PatientID=123*&limit=10", headers=headers)
studies = r.json()

# WADO-RS: retrieve a series as a multipart DICOM
series_url = studies[0]["_links"]["series"]["self"]  # or construct
rs = requests.get(f"{BASE}/studies/{study}/series/{series}/instances",
                  headers={"Accept": "application/dicom"},
                  auth=("orthanc", "pass"))
for part in rs.iter_content:
    # parse each DICOM part with pydicom.dcmread(BytesIO(chunk))
    ...
```

### Federated learning with MONAI + Flower

Train a segmentation model across hospital sites without sharing data.

```python
import flwr as fl
import torch
from monai.networks.nets import UNet

model = UNet(spatial_dims=3, in_channels=1, out_channels=2,
             channels=(16, 32, 64, 128, 256), strides=(2, 2, 2, 2))

class HospitalClient(fl.client.NumPyClient):
    def __init__(self, train_loader, model):
        self.model = model; self.train_loader = train_loader
    def get_parameters(self): return [p.detach().cpu().numpy()
                                       for p in self.model.parameters()]
    def fit(self, params, cfg):
        # set global params, train locally, return updated
        ...
        return self.get_parameters(), len(self.train_loader), {}

fl.client.start_client(server_address="fl.server:8080",
                      client=HospitalClient(...).to_client())
```

## Best practices

- Always **de-identify** DICOM at ingestion: strip 18 HIPAA identifiers
  (PatientName, PatientID, birthdate, etc.) and the 0x0010...0x0038 ranges;
  use `dicognito` or the DICOM `deidentification_method` tag.
- Verify **resampling** preserves direction cosines; ignore direction and
  you flip patients left-right (a known patient safety risk).
- Use **DICOM-SR** to capture structured findings (segmentations, lesions)
  for downstream readers; never store annotations as ad-hoc JSON only.
- For CT, always **convert to HU first** before any windowing or model
  feeding; raw pixel values vary wildly across vendors.
- Use **MONAI transforms** over custom code: spacing, orientation, intensity
  scaling are correctness-critical and MONAI tests them on every release.
- For nnU-Net, respect the **dataset JSON format**; non-conformance produces
  silent preprocessing bugs that degrade Dice by 5-15 points.
- Train on **3D full-resolution** for organ seg, **3D low-resolution** for
  large structures, **2D** for very thick slices.
- Use **5-fold cross-validation** with held-out test, not train/val/test split;
  medical imaging datasets are small and single splits mislead.
- Federated learning: weight client contributions by sample count
  (not equal weights) to avoid being skewed by tiny sites.
- Audit radiology reports for **incidental findings** to be re-reported to
  the ordering physician; design the pipeline accordingly.

## Common pitfalls

- Forgetting `ds.decompress()` on JPEG2000-encoded DICOM; pixel arrays appear
  as garbage.
- Mixing **ImageOrientationPatient** conventions across sites: some scanners
  produce feet-first series that break spatial operations.
- Using **PatientPosition** as the orientation source; orientation is
  `ImageOrientationPatient` cross-product, not patient position.
- nnU-Net trained on one anatomical plane (axial) and applied in another -
  re-run planning for new orientations.
- Storing CT as PNG (8-bit) loses dynamic range; **always** keep int16 HU.
- De-identifying only top-level tags - the SOP instance UID and series
  instance UID must be re-UIDed to be truly de-identified.
- Reporting **Dice on the background class** by mistake - masks of foreground
  vs background produce inflated Dice scores.
- Forgetting that **MIMIC-CXR** has known label noise (weak labels from
  CheXpert NL algorithm); always check `study_id_to_label` flags.

## Worked example

Goal: de-identify and segment liver on a CT scan with MONAI.

```python
import pydicom, numpy as np, SimpleITK as sitk, torch
from monai.networks.nets import UNet
from monai.transforms import LoadImage, ScaleIntensity, AddChannel
from pydicom.uid import generate_uid

# 1) Read DICOM series, anonymize tags
files = ["ct1.dcm", "ct2.dcm", "ct3.dcm"]
slices = [pydicom.dcmread(f) for f in files]
for s in slices:
    s.PatientName = "ANONYMOUS"
    s.PatientID = generate_uid()[:16]
    s.PatientBirthDate = ""
    s.OtherPatientIDs = ""          # burn all 18 identifiers
    s.save_as(f"deid_{s.SOPInstanceUID}.dcm")

# 2) Build 3D volume in HU
slices.sort(key=lambda s: float(s.ImagePositionPatient[2]))
vol = np.stack([s.pixel_array * float(s.RescaleSlope) +
                float(s.RescaleIntercept) for s in slices])
print("volume shape:", vol.shape)

# 3) Resample to 1mm isotropic
img = sitk.GetImageFromArray(vol.astype(np.float32))
img.SetSpacing(tuple(float(x) for x in slices[0].PixelSpacing) + (5.0,))
img_iso = sitk.Resample(img, sitk.Transform(3, sitk.sitkIdentity),
                        sitk.sitkLinear, -1024.0,
                        img.GetPixelID(), img.GetOrigin(),
                        (1.0, 1.0, 1.0), img.GetDirection())
arr = sitk.GetArrayFromImage(img_iso)[None, None]  # 1,1,D,H,W

# 4) Run liver segmentation
net = UNet(spatial_dims=3, in_channels=1, out_channels=2,
           channels=(16, 32, 64, 128, 256), strides=(2, 2, 2, 2)).cuda()
net.load_state_dict(torch.load("liver_unet.pt"))
net.eval()
with torch.no_grad():
    logits = net(torch.from_numpy(arr).cuda())
mask = logits.argmax(1).cpu().numpy()[0]
print("liver voxels:", int(mask.sum()))
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| pydicom | DICOM read/write/de-identify | `pip install pydicom` |
| SimpleITK | Resampling, registration | `pip install simpleitk` |
| ITK | C++ ITK library Python bindings | `pip install itk` |
| MONAI | Medical DL transforms + nets | `pip install "monai[all]"` |
| nnUNet v2 | Self-configuring segmentation | `pip install nnunetv2` |
| nibabel | NIfTI/MGH MRI I/O | `pip install nibabel` |
| dicognito | DICOM de-identification | `pip install dicognito` |
| pynetdicom | DICOM SCP/SCU (network) | `pip install pynetdicom` |
| Flower | Federated learning framework | `pip install flwr` |
| dcm2niix | DICOM -> NIfTI converter (binary) | https://github.com/rordenlab/dcm2niix |
| OHIF/ORTHANC | DICOMweb PACS server | https://www.orthanc-server.com |

## References

- pydicom documentation: https://pydicom.github.io/pydicom/
- SimpleITK notebooks: https://insightsoftware.github.io/SimpleITK-Notebooks/
- MONAI documentation: https://docs.monai.io/
- nnU-Net v2 paper: https://doi.org/10.1038/s41592-020-01008-z
- DICOM standard: https://www.dicomstandard.org/
- DICOMweb (PS3.18): https://dicom.nema.org/standard/dicomweb/
- TCIA (imaging archive): https://www.cancerimagingarchive.net/
- BraTS challenge: https://www.med.upenn.edu/cbica/brats2023/

## Ethics & safety

- DICOM studies contain **18 HIPAA identifiers**; de-identification must
  remove all of them (PatientName, PatientID, dates, ages >89, geographic
  fields, free-text remarks, UIDs). Use `dicognito` and re-UID every
  instance and series.
- Even after de-identification, **3D facial structures in CT/MR can be
  reverse-matched** to a known face via machine learning ("CT face
  recognition"). Apply skull-stripping or defacing for any public release.
- Cross-site DICOM use requires an IRB-approved Data Use Agreement; do not
  ship studies outside the originating institution without it.
- Federated learning pipelines still leak gradients; for high-risk PHI use
  **differential privacy** (Opacus) and **secure aggregation**.
- Medical imaging models are **SaMD (Software as a Medical Device)** and
  require FDA 510(k) clearance for clinical deployment. Never tell users a
  model is "ready for diagnosis" - it is research code until cleared.
- MIMIC-CXR and CheXpert labels are noisy (auto-extracted from reports);
  do not use as ground truth for patient-facing alerts.
- For pediatric imaging, respect age rules (HIPAA rounds ages >89 to "90+"
  for de-identification; in pediatrics, ages may be relevant for sizing).

# Worked examples

End-to-end prompts that reliably trigger the right skill(s), with the workflow your agent should follow once the skill activates. Each example is a single Markdown file you can paste into a chat or adapt to your own data.

## Index

| Category | Example | Skills it triggers |
|---|---|---|
| Biology & Genomics | [variant-calling.md](./genomics-variant-calling.md) | genomics, biostatistics |
| Biology & Genomics | [single-cell-de.md](./transcriptomics-single-cell.md) | transcriptomics, ml-for-science |
| Drug Discovery & Cheminformatics | [virtual-screen.md](./drug-discovery-virtual-screen.md) | drug-discovery, cheminformatics, admet-prediction |
| Clinical & Medical Research | [radiology-deid.md](./clinical-radiology-deid.md) | clinical-nlp, medical-imaging |
| Chemistry & Materials | [dft-geometry.md](./chemistry-dft-geometry.md) | computational-chemistry |
| Physics & Astronomy | [nbody-sim.md](./physics-nbody-sim.md) | computational-physics, scientific-computing |
| Machine Learning & Statistics | [leakage-safe-cv.md](./ml-leakage-safe-cv.md) | ml-for-science, biostatistics |
| Geospatial & Earth Science | [era5-climatology.md](./geospatial-era5-climatology.md) | climate-science, geospatial-analysis, data-visualization |
| Data & Visualization | [publication-figure.md](./viz-publication-figure.md) | data-visualization |
| Lab & Automation | [opentrons-pcr.md](./lab-opentrons-pcr.md) | lab-automation, experimental-design |
| Research Infrastructure | [slurm-array.md](./hpc-slurm-array.md) | hpc-computing, reproducible-environments |
| Knowledge & Communication | [systematic-review.md](./literature-systematic-review.md) | literature-review, citation-management |

## How to use

1. Install the skill(s) you need (see [README § Quick start](../README.md#quick-start)).
2. Open the example, copy the prompt verbatim into your coding assistant.
3. The agent activates the skill and follows the workflow. Adapt file paths, parameters, and libraries to your real data.

Every example assumes the libraries in the activated skill's `## Prerequisites` section are installed. None of the snippets are pinned reproductions — they are the canonical path a senior researcher would take.

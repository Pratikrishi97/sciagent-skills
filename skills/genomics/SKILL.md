---
name: genomics
description: Genomics toolkit covering variant calling from FASTQ to VCF, GWAS with PLINK and pyseer, reference-genome handling, QC with FastQC and MultiQC, VCF I/O with pysam and cyvcf2, BioPython SeqIO for FASTA/FASTQ, population genetics with scikit-allel, and variant annotation with VEP or SnpEff. Use this skill whenever the user asks about variant calling, GATK, DeepVariant, BWA, samtools, VCF, BAM, CRAM, GWAS, PLINK, pyseer, dbSNP, 1000 Genomes, GRCh38, T2T-CHM13, scikit-allel, cyvcf2, pysam, or BioPython SeqIO.
license: MIT
compatibility: Requires Python 3.10+ with pysam, cyvcf2, biopython, scikit-allel, pandas, numpy. System tools bwa, samtools, bcftools, FastQC, MultiQC, VEP or SnpEff, PLINK 2.0.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Biology & Genomics
---

# Genomics

## Overview

Genomics is the study of genome sequence, variation, and structure across
individuals and populations. The canonical workflow turns raw sequencing
reads (FASTQ) into aligned reads (BAM/CRAM) and then into a set of called
and filtered variants (VCF). From a VCF we run association testing (GWAS,
bacterial GWAS), compute population genetic statistics, and annotate
variants against resources like Ensembl, dbSNP, gnomAD, and ClinVar. The
reference genome has settled on **GRCh38** for humans and **T2T-CHM13**
for gapless telomere-to-telomere analysis.

This skill wires the stack together: BWA + samtools for alignment, GATK
or DeepVariant for variant calling, VEP or SnpEff for annotation, pysam
and cyvcf2 for VCF/BAM I/O in Python, BioPython SeqIO for FASTA/FASTQ,
PLINK 2.0 and pyseer for GWAS, and scikit-allel for population genetics.

## When to use this skill

- User needs to **call variants** from FASTQ (germline or somatic).
- User asks for **GWAS** (single-trait or case/control) or **bacterial GWAS**
  with pyseer.
- User wants to **filter, annotate, or summarize** a VCF with VEP, SnpEff,
  bcftools, or cyvcf2.
- User needs to **read or write** BAM/CRAM/VCF in Python with pysam or
  cyvcf2.
- User asks for **FASTA/FASTQ** parsing, translation, or k-mer counting
  with BioPython.
- User wants population genetics statistics (F_ST, nucleotide diversity,
  PCA) on genotype data with scikit-allel.
- User mentions **GRCh38**, **T2T-CHM13**, **dbSNP**, **1000 Genomes**,
  **gnomAD**, **ClinVar**, **Ensembl**.
- Skip for: bulk RNA-seq quantification and differential expression
  (use `transcriptomics`), single-cell analysis (use `transcriptomics`),
  protein structure (use `protein-analysis`), phylogenetics (use
  `evolutionary-biology`).

## Prerequisites

- Python 3.10+ (3.11 recommended for scikit-allel 2.x wheels).
- System tools: `bwa`, `samtools`, `bcftools`, `FastQC`, `MultiQC`,
  `VEP` or `SnpEff`, `PLINK 2.0`, `GATK` or `DeepVariant`.
- Python packages:

```bash
pip install pysam cyvcf2 biopython scikit-allel pandas numpy matplotlib
# Optional: pysamstats for pileup stats, gliner for genotype likelihoods
pip install pysamstats pgenlib
```

- Reference data: GRCh38 FASTA + index from Ensembl or NCBI; dbSNP and
  gnomAD VCFs for annotation; 1000 Genomes VCFs for population priors.

## Core workflows

### Reference handling and FASTQ QC with BioPython and MultiQC

Parse FASTA, slice a region, summarize FASTQ quality, and aggregate
per-sample QC with MultiQC.

```python
from Bio import SeqIO
import pysam, subprocess

# Parse and slice reference (needs samtools faidx index)
ref = pysam.FastaFile("GRCh38.fa")
chr1_chunk = ref.fetch("chr1", 999_000, 1_001_000)
print(f"chr1:1000000 context: {chr1_chunk[:60]}...")

# FASTQ stats with BioPython
recs = list(SeqIO.parse("sample_R1.fastq.gz", "fastq"))
mean_q = sum(r.phred_quality for r in recs) / sum(len(r) for r in recs)
print(f"{len(recs)} reads, mean Q={mean_q:.1f}")

# Run FastQC then aggregate (shell)
subprocess.run(["fastqc", "-o", "qc", "sample_R1.fastq.gz", "sample_R2.fastq.gz"])
subprocess.run(["multiqc", "qc", "-o", "multiqc"])
```

### Alignment and variant calling (BWA -> GATK/DeepVariant)

Align paired-end reads, sort and index the BAM, mark duplicates, and
call variants with DeepVariant (germline) or GATK HaplotypeCaller.

```python
import subprocess
# 1) BWA-MEM alignment against GRCh38
subprocess.run("bwa mem -t 16 -R '@RG\\tID:s1\\tSM:sample1' "
               "GRCh38.fa sample_R1.fastq.gz sample_R2.fastq.gz "
               "| samtools sort -@ 8 -o sample1.bam -",
               shell=True, check=True)
# 2) Index and mark duplicates (samtools/GATK)
subprocess.run(["samtools", "index", "sample1.bam"], check=True)
subprocess.run(["gatk", "MarkDuplicatesSpark",
                "-I", "sample1.bam", "-O", "sample1.dedup.bam",
                "-M", "sample1.metrics"], check=True)
# 3) Call variants with DeepVariant (germline WGS)
subprocess.run(["run_deepvariant",
                "--model_type=WGS",
                "--ref=GRCh38.fa",
                "--reads=sample1.dedup.bam",
                "--output_vcf=sample1.vcf.gz",
                "--num_shards=16"], check=True)
```

### VCF I/O, filtering, and annotation with cyvcf2 and VEP

Stream a VCF, filter on quality and depth, and annotate with VEP.

```python
from cyvcf2 import VCF, Writer
import subprocess

vin = VCF("sample1.vcf.gz")
vout = Writer("sample1.filtered.vcf.gz", vin)
vout.write_header()
for v in vin:
    # Keep PASS, depth >= 10, GQ >= 20
    if v.FILTER is None and v.INFO.get("DP", 0) >= 10 and v.gt_quals[0] >= 20:
        vout.write_record(v)
vout.close()

# Annotate against Ensembl VEP (needs vep + cache installed)
subprocess.run(["vep", "--cache", "--assembly=GRCh38",
                "--input_file", "sample1.filtered.vcf.gz",
                "--output_file", "sample1.annot.vcf",
                "--vcf", "--symbol", "--canonical",
                "--plugin", "CADD", "--offline"], check=True)
```

### GWAS with PLINK 2.0 and pyseer (bacterial GWAS)

Run a basic case/control GWAS with PLINK 2.0 and a bacterial GWAS with
pyseer on a k-mer presence/absence matrix.

```python
import subprocess, pandas as pd
# 1) PLINK 2.0 logistic regression with PCs as covariates
subprocess.run(["plink2", "--bfile", "cohort",
                "--pheno", "pheno.txt", "--1",
                "--covar", "covars.txt",
                "--covar-name", "age,sex,PC1-PC10",
                "--glm", "logistic", "hide-covar",
                "--out", "cohort_gwas"], check=True)
gwas = pd.read_csv("cohort_gwas.PHENO1.glm.logistic", sep="\t")
gwas = gwas.dropna(subset=["P"])
print(gwas.nsmallest(5, "P")[["ID", "CHROM", "POS", "P"]])

# 2) Bacterial GWAS with pyseer (k-mers vs phenotype)
subprocess.run(["pyseer", "--kmers", "unitigs.txt.gz",
                "--phenotypes", "pheno.txt",
                "--covariates", "covariates.txt",
                "--cpu", "8", ">pyseer.out"], check=True)
```

### Population genetics with scikit-allel

Compute allele frequencies, F_ST, and run PCA on a 1000 Genomes VCF
subset.

```python
import allel
import numpy as np
callset = allel.read_vcf("1kg.chr20.vcf.gz")
gt = allel.GenotypeArray(callset["calldata/GT"])
# Allele frequencies
af = gt.count_alleles().to_frequencies()
# F_ST between two populations
pop1 = callset["samples"][:100]
pop2 = callset["samples"][100:200]
ac1 = gt[:len(pop1)].count_alleles()
ac2 = gt[:len(pop2)].count_alleles()
fst = allel.hudson_fst(ac1, ac2)
print(f"mean F_ST={np.nanmean(fst):.4f}")
# PCA on GT (biallelic, no missing)
gn = gt.to_n_alt()
coords, model = allel.pca(gn, n_components=10)
print("PC1 var explained:", round(model.explained_variance_ratio_[0], 3))
```

## Best practices

- Always align to a single reference build and record its build name and
  release (GRCh38.p14, T2T-CHM13 v2.0) in metadata - mixing builds is
  the most common downstream bug.
- Mark PCR duplicates with `MarkDuplicatesSpark` or `picard` before
  variant calling; ignore-duplicates during alignment is wrong for
  variant discovery.
- Use **CRAM** over BAM for storage - same access model via pysam but
  30-50% smaller.
- For germline WGS prefer **DeepVariant** (deep-learning caller,
  higher F1 than GATK on truth benchmarks); for RNA-seq variants use
  **GATK HaplotypeCaller** with split-N pre-processing.
- Filter variants by **PASS** plus a minimum depth (DP >= 10 for WGS,
  DP >= 5 for targeted panel) and genotype quality (GQ >= 20).
- For GWAS, always include principal components PC1-PC10 as covariates
  to control for population stratification.
- For bacterial GWAS, use **pyseer** with population-structure
  correction (lineage or -d cache) - naive k-mer tests are confounded by
  clonal frame.
- Annotate against the matched reference build (GRCh38 VEP cache for
  GRCh38 VCFs) and record the VEP cache release.
- Use **left-alignment and normalization** (`bcftools norm -m -any`)
  before association testing - multiallelic splits change the unit of
  analysis.
- Version everything (samtools, bcftools, GATK, VEP) in a reproducible
  environment (conda env or Docker image).

## Common pitfalls

- Mixing genome builds silently (e.g., GRCh37 coordinates on a GRCh38
  VCF) - lift over with `picard LiftoverVcf` and re-run annotation.
- Forgetting to index BAM (`samtools index`) before variant calling or
  visualization - tools fail with cryptic "fetch region" errors.
- Using CADD or gnomAD VCFs with the wrong reference build - same
  silent coordinate mismatch.
- Treating CRAM like BAM without a reference - CRAM stores differences
  from the reference, so reads are corrupted if you decode without the
  matching FASTA.
- Counting INFO/DP as the per-sample depth - INFO/DP is total across
  samples; sample depth is in the FORMAT/DP field.
- Reporting GWAS hits without LD clumping (`plink --clump`) - one
  genomic locus will be reported as dozens of independent associations.
- Calling variants on mito or alt contigs without special handling -
  most callers are tuned for the 22 autosomes + X.
- Forgetting the sample-level read group `-R '@RG\tID...tSM:...'` in
  `bwa mem` - downstream tools cannot tell samples apart and downstream
  duplicate marking is broken.

## Worked example

End-to-end germline variant calling, annotation, and a minimal GWAS
summary on a single sample plus a cohort.

```python
import subprocess, allel
import pandas as pd
from cyvcf2 import VCF, Writer

# Assume GRCh38.fa indexed; sample_R1/R2.fastq.gz exist
# 1) Align, sort, index
subprocess.run("bwa mem -t 16 -R '@RG\\tID:s1\\tSM:sample1' "
               "GRCh38.fa sample_R1.fastq.gz sample_R2.fastq.gz "
               "| samtools sort -@ 8 -o sample1.bam -",
               shell=True, check=True)
subprocess.run(["samtools", "index", "sample1.bam"], check=True)

# 2) Call variants with DeepVariant
subprocess.run(["run_deepvariant", "--model_type=WGS",
                "--ref=GRCh38.fa", "--reads=sample1.bam",
                "--output_vcf=sample1.vcf.gz",
                "--num_shards=16"], check=True)

# 3) Filter PASS variants with DP >= 10
vin = VCF("sample1.vcf.gz"); vout = Writer("sample1.filt.vcf.gz", vin)
vout.write_header()
n = 0
for v in vin:
    if v.FILTER is None and v.INFO.get("DP", 0) >= 10:
        vout.write_record(v); n += 1
vout.close(); print(f"{n} PASS variants at DP>=10")

# 4) Annotate with VEP, then load with scikit-allel
subprocess.run(["vep", "--cache", "--assembly=GRCh38",
                "--input_file", "sample1.filt.vcf.gz",
                "--output_file", "sample1.ann.vcf",
                "--vcf", "--symbol", "--offline"], check=True)
callset = allel.read_vcf("sample1.ann.vcf")
print(f"{len(callset['variants'])} variants loaded")
effects = callset["variants/ANN"] if "variants/ANN" in callset else None
print("annotation attached:", effects is not None)
```

## Tools & libraries

| Tool | Purpose | Install |
|---|---|---|
| BWA-MEM2 | Alignment to reference genome | https://github.com/bwa-mem2/bwa-mem2 |
| samtools | BAM/CRAM I/O and indexing | http://www.htslib.org/ |
| bcftools | VCF manipulation, filtering, norm | http://www.htslib.org/ |
| GATK | HaplotypeCaller, MarkDuplicates, VQSR | https://gatk.broadinstitute.org/ |
| DeepVariant | Deep-learning germline caller | `docker pull google/deepvariant` |
| VEP | Variant annotation against Ensembl | https://www.ensembl.org/vep |
| SnpEff | Genetic variant annotation and effect | https://pcingola.github.io/SnpEff/ |
| PLINK 2.0 | GWAS, PCA, genotype QC | https://www.cog-genomics.org/plink/2.0/ |
| pyseer | Bacterial GWAS (k-mers, unitigs) | `pip install pyseer` |
| pysam | Python BAM/CRAM/VCF/FASTA access | `pip install pysam` |
| cyvcf2 | Fast VCF I/O built on htslib | `pip install cyvcf2` |
| BioPython | SeqIO, Align, SeqRecord | `pip install biopython` |
| scikit-allel | Population genetics statistics | `pip install scikit-allel` |
| FastQC / MultiQC | Read-level QC and aggregation | https://www.bioinformatics.babraham.ac.uk/ |

## References

- GATK best practices: https://gatk.broadinstitute.org/hc/en-us/articles/360035890111
- DeepVariant paper: https://doi.org/10.1038/ng.2106 (Poplin et al.)
- VEP documentation: https://www.ensembl.org/info/docs/tools/vep/
- pysam documentation: https://pysam.readthedocs.io/en/latest/
- cyvcf2 documentation: https://brentp.github.io/cyvcf2/
- scikit-allel documentation: https://scikit-allel.readthedocs.io/en/stable/
- 1000 Genomes Project: https://www.internationalgenome.org/
- Ensembl: https://www.ensembl.org/

## Ethics & safety

- Human genomic data is identifiable by definition. Respect the consent
  scope under which samples were collected; do not redistribute outside
  the originating IRB / EGA controlled-access tier.
- Population genetic analysis can reveal ancestry and re-identify
  participants in small cohorts; report aggregate statistics only.
- GATK, PLINK, VEP, and SnpEff are research-use unless validated for
  clinical use; clinical reporting (e.g., ACMG variant classification)
  must follow CAP/CLIA and ACMG/AMP guidelines and use a validated
  pipeline, not a research one.
- Genetic findings with health implications (BRCA1/2, Lynch syndrome,
  familial hypercholesterolemia) carry a duty-to-warn obligation in
  many jurisdictions; route return-of-results through a licensed
  genetic counselor.
- Dual-use: variant calling on pathogen genomes can be used to inform
  either public health surveillance or offensive bioengineering; share
  pathogen sequences through controlled-access databases (e.g. GISAID
  for influenza, NCBI Pathogens) and respect the Nagoya Protocol.
- Respect reference resource licenses: dbSNP is public domain, gnomAD
  is OGL, ClinVar is public domain, but some Ensembl data carry
  restrictions on commercial redistribution - check before mirroring.

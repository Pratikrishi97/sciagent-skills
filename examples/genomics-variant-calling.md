# Example: germline variant calling from paired-end reads

**Skills activated:** `genomics`, `biostatistics`

## The prompt

> I have paired-end Illumina FASTQs (R1/R2) from 12 human blood samples aligned to GRCh38. Run QC, align with BWA-MEM2, mark duplicates, call SNPs/indels with GATK HaplotypeCaller in GVCF mode, joint-genotype, hard-filter, and annotate with SnpEff. Give me a MultiQC report at the end. The samples are case/control for a rare disease cohort.

## What the agent does

The `genomics` skill activates on the triggers (FASTQ, BWA-MEM2, GATK, HaplotypeCaller, GRCh38) and `biostatistics` for the case/control design. The agent follows the canonical workflow:

### 1. QC + adapter trimming

```python
# pip install multiqc fastqc
import subprocess, pathlib
fastqs = sorted(pathlib.Path("data/").glob("*_R{1,2}.fastq.gz"))
for fq in fastqs:
    subprocess.run(["fastqc", "-t", "4", "-o", "qc/", str(fq)], check=True)
subprocess.run(["multiqc", "qc/", "-o", "qc/multiqc"], check=True)
```

### 2. Alignment with BWA-MEM2

```bash
# index once: bwa-mem2 index GRCh38.fa
bwa-mem2 mem -t 16 -R "@RG\tID:{SM}\tSM:{SM}\tPL:ILLUMINA" \
  GRCh38.fa sample_R1.fastq.gz sample_R2.fastq.gz | \
  samtools sort -@ 8 -o bam/sample.sorted.bam
samtools index bam/sample.sorted.bam
```

### 3. Mark duplicates + GVCF calling

```bash
gatk MarkDuplicatesSpark -I bam/sample.sorted.bam -O bam/sample.dedup.bam -M qc/sample.metrics
gatk HaplotypeCaller -I bam/sample.dedup.bam -R GRCh38.fa -O gvcf/sample.g.vcf.gz \
  -ERC GVCF --native-pair-hmm-threads 4
```

### 4. Joint genotyping + hard filter

```bash
gatk CombineGVCFs $(for g in gvcf/*.g.vcf.gz; do echo "--variant $g"; done) -R GRCh38.fa -O cohort.g.vcf.gz
gatk GenotypeGVCFs -V cohort.g.vcf.gz -R GRCh38.fa -O cohort.vcf.gz
gatk VariantFiltration -V cohort.vcf.gz -O cohort.filtered.vcf.gz \
  --filter-expression "QD < 2.0" --filter-name "LowQD" \
  --filter-expression "FS > 60.0" --filter-name "HighFS" \
  --filter-expression "MQ < 40.0" --filter-name "LowMQ"
```

### 5. Annotation + case/control summary

```bash
snpEff GRCh38.105 cohort.filtered.vcf.gz > cohort.ann.vcf
```

```python
# pip install cyvcf2 pandas
from cyvcf2 import VCF
import pandas as pd
rows = []
for v in VCF("cohort.ann.vcf"):
    for gt, sample in zip(v.genotypes, VCF("cohort.ann.vcf").samples):
        rows.append({"pos": v.POS, "gene": v.INFO.get("ANN","").split("|")[3], "sample": sample, "gt": "/".join(map(str, gt[:2]))})
df = pd.DataFrame(rows)
print(df.groupby(["gene","sample"])["gt"].value_counts().unstack().fillna(0).head())
```

## Pitfalls the skill surfaces

- The read group (`-R`) line must set a unique `SM` per sample or genotype collapsing silently merges samples.
- Use `gcloud`/`aws s3` to fetch GRCh38 + dbSNP from a documented source, not an unversioned mirror.
- Run BWA-MEM2 indexing once on the reference, not per sample.
- Hard filters (QD/FS/MQ) are GATK's "best practices" defaults; for a rare-disease study, consider VQSR if a truth set is available.

## Reproducibility

Pin tools in an `environment.yml` (conda) or Docker image; record versions with `multiqc --version` in the report. See the `reproducible-environments` skill.

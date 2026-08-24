# Preprocessing the proteomics data with quantms / DIA-NN

Session: **Day 1, 13:30–15:00** ·
Notebook: [`proteomics/notebooks/01_proteomics_preprocessing_quantmsdiann.ipynb`](../proteomics/notebooks/01_proteomics_preprocessing_quantmsdiann.ipynb)

Our proteomics data are **diaPASEF** — data-independent acquisition on a Bruker timsTOF Pro.
The pipeline for that is [**quantmsdiann**](https://quantmsdiann.quantms.org/), the DIA-NN
branch of the [quantms](https://docs.quantms.org/) family, built to nf-core standards by
[bigbio](https://github.com/bigbio) at EMBL-EBI.

> Note for anyone coming from the classic quantms course: `nf-core/quantms` handles DDA and
> DIA through OpenMS/MSstats; `bigbio/quantmsdiann` is the pipeline to use when DIA-NN is the
> engine, and it is what a diaPASEF dataset wants.

## What the pipeline does

1. **Input validation** — parse and check the SDRF with [sdrf-pipelines](https://github.com/bigbio/sdrf-pipelines)
2. **File preparation** — convert and index MS files (`.raw` → `.mzML`; Bruker `.d` read natively by DIA-NN)
3. **In-silico spectral library** — deep-learning prediction from the FASTA
4. **Preliminary analysis** — per-file calibration of mass accuracy and retention time
5. **Empirical library assembly** — a consensus library built from your own measurements
6. **Individual analysis** — per-file search against the empirical library, in parallel
7. **Final quantification** — protein, peptide and gene matrices with cross-run normalisation
8. **MSstats conversion** — long-format table for statistical modelling
9. **Quality control** — an interactive [pmultiqc](https://github.com/bigbio/pmultiqc) report

Steps 4–6 are the two-pass trick that makes library-free DIA work.

## Requirements

- **Java 17+** and **Nextflow ≥ 25.10**
- A **container engine**. Conda is *not* supported — DIA-NN is not a Conda package. Docker
  is the easiest locally; Singularity/Apptainer on HPC and in Colab. See
  [`nextflow_setup.md`](nextflow_setup.md).
- DIA-NN **1.8.1** is the default and is pulled automatically from the public BioContainers
  image, so the default profile works with no licence steps. Versions from 1.9 onward are not
  redistributable — to use them you build the container yourself from
  [quantms-containers](https://github.com/bigbio/quantms-containers) with your own DIA-NN
  download, then select `-profile diann_v2_5_0` and so on.

## The hands-on run

Our 45 raw files are ~2.4 GB each. For the session we run the pipeline's own **Bruker `.d`
test profile**, which points at a small public diaPASEF dataset
([PXD065380](https://www.ebi.ac.uk/pride/archive/projects/PXD065380), human urine) — the same
code path and the same output files, small enough to finish while we watch.

```bash
nextflow run bigbio/quantmsdiann -r v2.3.0 \
    -profile test_dia_dotd,<docker|apptainer|singularity> \
    --outdir proteomics/results/test_run \
    -resume
```

| Part | Meaning |
|---|---|
| `-r v2.3.0` | pin the pipeline version — always do this |
| `-profile test_dia_dotd` | preset input, database and thresholds for the `.d` test dataset |
| `,apptainer` | container engine; profiles are comma-separated |
| `--outdir` | single dash = Nextflow option, double dash = pipeline parameter |
| `-resume` | reuse completed steps from a previous run |

Other test profiles: `test_dia` (Thermo `.raw`, *E. coli*/UPS1), `test_dia_parquet`,
`test_dia_qpx`, `test_full_dia`.

Expect 15–40 minutes, most of it downloading container images and the deep-learning model.

## The production run on our cohort

```bash
nextflow run bigbio/quantmsdiann -r v2.3.0 \
    -profile docker \
    --input  proteomics/data/PXD075261_subset.sdrf.tsv \
    --database proteomics/database/uniprot_human.fasta \
    --outdir proteomics/results/PXD075261 \
    --root_folder proteomics/data/raw \
    --local_input_type d.zip \
    --min_peptide_length 7 \
    --max_peptide_length 30 \
    --max_precursor_charge 4 \
    --allowed_missed_cleavages 2 \
    --mass_acc_ms1 15 --mass_acc_ms2 15 \
    -resume
```

- Two SDRFs ship with the course: `PXD075261.sdrf.tsv` (all 45 patients) and
  `PXD075261_subset.sdrf.tsv` (three samples, one per group — `Con10`, `KP15`, `CRKP12`, the
  ones kept alongside the course material). Use the subset unless you have downloaded all 45
  files, which is ~110 GB.
- `--root_folder` and `--local_input_type` tell the pipeline to find the files named in the
  SDRF locally rather than downloading them. `.d.zip` archives are supported directly.
- **`--local_input_type` must match the real extension.** The pipeline strips the known
  extension from the SDRF file name and appends this one, so for `..._50924.d.zip` you need
  `d.zip`; `d` makes it look for `..._50924.d`, find nothing, and fail. Allowed values:
  `mzML`, `raw`, `d`, `dia`, `d.tar`, `d.tar.gz`, `d.zip`, `wiff`.
- The search parameters mirror the paper's Methods: tryptic peptides, up to 2 missed
  cleavages, 15 ppm tolerances, charges to 4+.
- Get the FASTA with:

  ```bash
  wget -q 'https://rest.uniprot.org/uniprotkb/stream?query=%28proteome%3AUP000005640%29+AND+%28reviewed%3Atrue%29&format=fasta&compressed=true' \
      -O proteomics/database/uniprot_human.fasta.gz
  gunzip proteomics/database/uniprot_human.fasta.gz
  ```

  In a real analysis, append a contaminant database (keratins, trypsin, reagent albumin) —
  the search engine must see them so their spectra are not misassigned; you remove the
  matching proteins afterwards.

### Resources

The full cohort is a cluster job, not a laptop job: budget several CPU-hours per file for
library-free diaPASEF, plus ≥ 32 GB RAM for the library steps. Cap resources with a config
file passed via `-c`:

```groovy
process {
    resourceLimits = [ cpus: 16, memory: '64.GB', time: '48.h' ]
}
```

Never put pipeline *parameters* in a `-c` config — use the command line or `-params-file`.

## The outputs that matter

| File | Contents |
|---|---|
| `report.pg_matrix.tsv` | **protein groups × runs**, MaxLFQ intensities — the table we analyse on Day 2 |
| `report.pr_matrix.tsv` | the same at precursor (peptide + charge) level |
| `report.tsv` / `.parquet` | one row per identified precursor per run: scores, RT, FDR |
| `*_msstats_in.csv` | long format for MSstats |
| `multiqc_report.html` | the QC report — **open this first, every time** |

Before looking at a single fold change, check the QC report for identifications per run,
retention-time stability and total ion current. A run that failed technically will otherwise
reappear later as exciting biology.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `Cannot read project manifest -- Remote resource not found` | wrong revision tag. `quantmsdiann` releases are tagged **with** a leading `v` (`-r v2.3.0`); nf-core pipelines are not (`-r 2.0.1`). Check with `git ls-remote --tags https://github.com/bigbio/quantmsdiann.git` |
| `No valid input files found after SDRF parsing` | the SDRF parsed fine — the pipeline could not find the **files**. Three usual causes: `--local_input_type` does not match the real extension (use `d.zip`, not `d`); `--root_folder` points somewhere else; or the raw files are simply not on this machine. Run the `preflight()` helper in the notebook to see the exact paths it looks for |
| Only some samples processed | the full SDRF lists all 45 runs. If you only have a few files locally, use `PXD075261_subset.sdrf.tsv` or write your own subset — a missing file is not skipped silently in every case |
| `schema validation failed` on the input | the file must end in `.sdrf.tsv`; `.tsv`, `.sdrf` and `.csv` are rejected |
| Pipeline cannot find raw files | check `--root_folder`, `--local_input_type`, and that `comment[data file]` in the SDRF matches the file names exactly |
| Container pull fails | see [`nextflow_setup.md`](nextflow_setup.md); on a cluster, pre-pull images to a shared cache with `NXF_SINGULARITY_CACHEDIR` |
| Out of disk | delete `work/` between experiments; it holds one directory per task and grows fast |
| A step fails after hours | fix the cause and rerun with `-resume`; completed steps are reused |
| DIA-NN finds almost nothing | check that `comment[proteomics data acquisition method]` says data-independent acquisition, and that mass tolerances match the instrument |

## Help

- Documentation: <https://quantmsdiann.quantms.org/> and `docs/usage.md` in the repository
- nf-core Slack, channel `#quantms`: <https://nf-co.re/join/slack>
- Issues: <https://github.com/bigbio/quantmsdiann/issues>

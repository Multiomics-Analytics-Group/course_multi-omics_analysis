# Preprocessing metabolomics data with nf-core/metaboigniter

Session: **Day 1, 15:30–17:00** ·
Notebook: [`metabolomics/notebooks/01_metabolomics_preprocessing_metaboigniter.ipynb`](../metabolomics/notebooks/01_metabolomics_preprocessing_metaboigniter.ipynb)

## Read this first: two datasets, on purpose

[**nf-core/metaboigniter**](https://nf-co.re/metaboigniter/2.0.1/) is an **untargeted**
LC-MS pipeline. Its whole job — detect peaks in full-scan data, assemble them into features,
align retention times across samples — assumes full-scan spectra.

Our cohort's metabolomics is **widely-targeted MRM** on a QTRAP 6500. The deposited mzML
files contain about 1 550 SRM chromatograms and **zero spectra**, so metaboigniter cannot
process them. That is not a defect in either the pipeline or the data; they answer different
questions (see [`datasets.md`](datasets.md), section 3).

The session therefore does two things:

1. Opens the cohort's real MRM files and integrates a peak, so you can see where the numbers
   in our matrix come from.
2. Runs metaboigniter on a **small untargeted dataset**, because untargeted LC-MS is what
   most projects meet, and the pipeline concepts transfer directly.

The dataset used in part 2 is a **placeholder** and is meant to be swapped — see
*Using your own dataset* below.

## What the pipeline does

| Step | Tool | What goes wrong |
|---|---|---|
| Centroiding / peak picking | `PeakPickerHiRes` | over-smoothing loses low-abundance ions |
| Mass-trace and feature detection | `FeatureFinderMetabo` | isotopes of one compound counted as separate features |
| Adduct deconvolution | `MetaboliteAdductDecharger` | one metabolite inflated into several features |
| Retention-time alignment | `MapAlignerPoseClustering` | over-warping invents alignment that is not there |
| Linking across samples | `FeatureLinkerUnlabeledKD` | mismatches create fake missing values |
| Requantification | OpenMS | recovers real low signals *and* real noise |
| Identification | SIRIUS / CSI:FingerID, MS2Query | in a typical study, fewer than 20 % of features get a name |

The output is a **quantification table** — features in rows, samples in columns, plus *m/z*,
retention time, charge and adduct — the metabolomics equivalent of `report.pg_matrix.tsv`.

## Requirements

- **Java 17+**, **Nextflow ≥ 25.10**
- A container engine (Docker, Singularity/Apptainer) — or **Conda**, which metaboigniter
  does support, unlike quantmsdiann. See [`nextflow_setup.md`](nextflow_setup.md).
- `.mzML` files that are **indexed**. metaboigniter relies on the index rather than
  rebuilding it, and unindexed files fail with an opaque error. Fix with
  [`bin/reindex_mzml.py`](../bin/reindex_mzml.py):

  ```bash
  pip install pyopenms
  python bin/reindex_mzml.py --input_dir metabolomics/data/<DATASET>
  ```

## The samplesheet

A four-column CSV:

| Column | Meaning |
|---|---|
| `sample` | unique name for the injection |
| `level` | `MS1`, `MS2` or `MS12` — which acquisition level the file contains |
| `type` | group label; use `QC_POOL` for pooled quality controls |
| `msfile` | path to an indexed `.mzML` |

```csv
sample,level,type,msfile
MS_A_POS,MS1,CVD,data/MTBLS8735/MS_A_POS.mzML
MS_B_POS,MS1,CTR,data/MTBLS8735/MS_B_POS.mzML
MS_QC_POOL_1_POS,MS1,QC_POOL,data/MTBLS8735/MS_QC_POOL_1_POS.mzML
MSMS_2_A_CE20_POS,MS2,CVD,data/MTBLS8735/MSMS_2_A_CE20_POS.mzML
```

MS2 files are declared as separate rows and linked to the MS1 runs through
`--ms2_collection_model` (`paired` if MS2 was acquired on the same injections, `separate` if
in dedicated runs).

## Running it

Quick check that the environment works, using the pipeline's own miniature dataset:

```bash
nextflow run nf-core/metaboigniter -r 2.0.1 \
    -profile test,<docker|apptainer|singularity|conda> \
    --outdir metabolomics/results/test_run
```

On a real study:

```bash
nextflow run nf-core/metaboigniter -r 2.0.1 \
    -profile docker \
    -c metabolomics/metaboigniter.config \
    --input metabolomics/data/<DATASET>/samplesheet.csv \
    --polarity positive \
    --requantification \
    --outdir metabolomics/results/<DATASET> \
    -resume
```

Add `--identification --run_ms2query` to annotate features. Be warned: on first use this
downloads roughly **2 GB** of GNPS spectral-library models into the `work/` directory. Worth
it on a real project, not in a 90-minute session.

## Parameters are instrument-specific

Defaults tuned for one instrument are rarely right for another. The starting point used in
the notebook (and in `metabolomics/metaboigniter.config`) is for high-resolution Q-TOF data:

```groovy
params {
    // peak picking
    algorithm_signal_to_noise_peakpickerhires_openms                      = 0.1
    algorithm_spacing_difference_gap_peakpickerhires_openms               = 4.0
    algorithm_signaltonoise_auto_max_stdev_factor_peakpickerhires_openms  = 3.0

    // what counts as a real mass trace
    algorithm_common_noise_threshold_int_featurefindermetabo_openms       = 60.0
    algorithm_common_chrom_peak_snr_featurefindermetabo_openms            = 3.0
    algorithm_epd_masstrace_snr_filtering_featurefindermetabo_openms      = true
    algorithm_ffm_charge_upper_bound_featurefindermetabo_openms           = 1

    // alignment and linking tolerances (seconds / ppm)
    algorithm_pairfinder_distance_rt_max_difference_mapalignerposeclustering_openms = 45
    algorithm_warp_rt_tol_featurelinkerunlabeledkd_openms                 = 45.0
    algorithm_warp_mz_tol_featurelinkerunlabeledkd_openms                 = 3.0
    algorithm_link_rt_tol_featurelinkerunlabeledkd_openms                 = 12.0
    algorithm_link_mz_tol_featurelinkerunlabeledkd_openms                 = 6.0
}
```

`nextflow run nf-core/metaboigniter --help` prints the full list, which is long. The
parameters worth understanding first are the noise thresholds (how much you detect) and the
RT/*m/z* tolerances (how features are matched across samples).

## Using your own dataset

The notebook has a single **dataset configuration cell**, clearly marked. To point the
session at a different untargeted study, change only:

- `DATASET` and the download base URL,
- the `FILES` dictionary — sample name → (acquisition level, group label, remote file name),
- `POLARITY`.

Nothing downstream depends on which study it is. The current placeholder is
[**MTBLS8735**](https://www.ebi.ac.uk/metabolights/MTBLS8735), the *Metabonaut* example: three
cardiovascular-disease patients, three controls, four pooled QC injections, positive mode with
separate MS2 runs. Small, public, genuinely untargeted, and the same
two-groups-plus-QC shape as our cohort.

When you swap in a new dataset, check three things: that the files are indexed, that the
group labels in `type` are what you want to compare, and that the QC injections are labelled
`QC_POOL`.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| index access error on an mzML | run `bin/reindex_mzml.py` over the data directory |
| a file fails to be processed at all | it may have been truncated on download; fetch it again |
| almost no features detected | noise thresholds too high for your instrument, or the polarity setting does not match the data |
| enormous feature count | thresholds too low; you are detecting noise |
| MS2Query step hangs | it is downloading ~2 GB of models; check `work/<hash>/downloads` |
| conda environment resolution takes forever | use containers instead |

## Further reading

- Pipeline documentation: <https://nf-co.re/metaboigniter/2.0.1/>
- [Metabonaut](https://rformassspectrometry.github.io/Metabonaut/) — the same workflow done by
  hand in R, excellent for understanding what each step does
- OpenMS documentation: <https://openms.readthedocs.io/>

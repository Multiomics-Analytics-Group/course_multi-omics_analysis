# MTBLS8735 — the untargeted placeholder dataset

The course cohort's metabolomics is **targeted MRM**, which `nf-core/metaboigniter` cannot
process (see [`material/datasets.md`](../../../material/datasets.md), section 3). The Day 1
metabolomics session therefore demonstrates the untargeted pipeline on a small public study
and uses the cohort's own files only to show where a peak area comes from.

[**MTBLS8735**](https://www.ebi.ac.uk/metabolights/MTBLS8735) is the *Metabonaut* example
dataset: three cardiovascular-disease patients (CVD), three healthy controls (CTR) and four
pooled quality-control injections, acquired in positive mode with separate MS2 runs. Small,
public, genuinely untargeted, and the same two-groups-plus-QC shape as our cohort — so every
analytical idea transfers.

`samplesheet.csv` here uses a **subset**: four biological samples and two QC injections, which
keeps a demonstration run inside a coffee break. For a real analysis use every sample —
alignment and linking get better with more runs, not worse.

Download the mzML files (they are not committed):

```bash
BASE=https://ftp.ebi.ac.uk/pub/databases/metabolights/studies/public/MTBLS8735/FILES
for f in MS_A_POS MS_B_POS MS_D_POS MS_E_POS MS_QC_POOL_1_POS MS_QC_POOL_2_POS; do
  wget -nc "$BASE/$f.mzML"
done
python bin/reindex_mzml.py --input_dir metabolomics/data/MTBLS8735
```

**This dataset is a placeholder.** To point the session at a different untargeted study, edit
the single dataset-configuration cell in the notebook — see
[`material/metaboigniter.md`](../../../material/metaboigniter.md).

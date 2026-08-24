# Raw metabolomics data — MTBLS14016

Deposited files from [MTBLS14016](https://www.ebi.ac.uk/metabolights/MTBLS14016): per-sample,
per-polarity `.mzML` converted from SCIEX `.wiff`, about 4 MB each.

**No `.mzML` files are tracked in git.** The
[Day 1 metabolomics notebook](../../notebooks/01_metabolomics_preprocessing_metaboigniter.ipynb)
downloads the one it needs directly from MetaboLights:

```
https://ftp.ebi.ac.uk/pub/databases/metabolights/studies/public/MTBLS14016/FILES/DERIVED_FILES/<sample>.mzML
```

To get them all locally at once — the five samples used by that notebook and its exercises
(`Con10`, `KP11`, `KP12`, `KP15`, `CRKP12`, both polarities) — run:

```bash
bash metabolomics/data/raw/download.sh
```

`metadata/` holds the study's ISA-Tab files as downloaded — the sample table, the two assay
tables and the metabolite assignment files (MAF). The MAF is the quantification matrix the
course actually analyses; its curated form is
[`metabolomics/data/metabolite_matrix.tsv`](../metabolite_matrix.tsv).

⚠️ These files contain **chromatograms and no spectra** — they are targeted MRM data, so an
untargeted pipeline cannot process them. See [`material/datasets.md`](../../../material/datasets.md)
§3 for why, and for two real defects in this submission worth knowing about.

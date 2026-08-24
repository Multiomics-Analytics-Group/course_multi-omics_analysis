# Clinical and sample metadata

`sample_metadata.tsv` — one row per patient of the discovery cohort (45 rows), built from
supplementary table 1 of He *et al.* 2026 by
[`bin/build_curated_data.py`](../bin/build_curated_data.py).

| Column | Meaning |
|---|---|
| `sample_id` | patient identifier, as used by both repositories (`Con*`, `KP*`, `CRKP*`) |
| `group` | `Con`, `CSKP` or `CRKP` |
| `group_label` | the same, spelled out |
| `group_order` | 0, 1, 2 — the ordinal severity axis Con → CSKP → CRKP, for trend tests |
| `sex`, `sex_code` | `sex_code` is the published 0/1 coding; `sex` is its interpretation, inferred from Table 1 of the paper (31 male / 14 female) |
| `age`, `bmi` | years, kg/m² |
| `total_bilirubin`, `alt`, `ast` | liver function |
| `creatinine`, `blood_urea_nitrogen` | renal function |
| `procalcitonin`, `c_reactive_protein` | inflammation and bacterial infection markers |
| `wbc_count`, `rbc_count`, `haemoglobin`, `red_cell_distribution_width`, `platelet_count`, `neutrophil_lymphocyte_ratio` | haematology |
| `inr` | coagulation |
| `diabetes`, `heart_disease`, `copd`, `liver_disease`, `cerebrovascular_disease`, `kidney_disease` | comorbidities, 0/1 |

Units are as published; the paper does not state them for every variable, so treat the
laboratory values as comparable **within** this cohort rather than against your local
reference ranges.

The `KP*` identifiers belong to the group the paper calls **CSKP** (carbapenem-susceptible).
We keep the repository identifiers and carry the label in `group` — see
[`material/datasets.md`](../material/datasets.md) for the full identifier story, which
contains at least one trap.

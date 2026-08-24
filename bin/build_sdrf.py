#!/usr/bin/env python3
"""Write the SDRF experiment-metadata file for the serum DIA proteomics cohort.

SDRF (Sample and Data Relationship Format) is the ProteomeXchange metadata standard:
one row per MS run, columns describing the sample (`characteristics[...]`), the
acquisition (`comment[...]`) and the experimental variable (`factor value[...]`).
`quantmsdiann` consumes it directly, so writing a correct SDRF is what turns a folder
of raw files into a reproducible analysis.

    python bin/build_sdrf.py

Output: proteomics/data/PXD075261.sdrf.tsv
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

DISEASE = {
    "Con": "culture-negative sepsis",
    "CSKP": "carbapenem-susceptible Klebsiella pneumoniae sepsis",
    "CRKP": "carbapenem-resistant Klebsiella pneumoniae sepsis",
}
GROUP_ORDER = {"Con": 0, "CSKP": 1, "CRKP": 2}

# Acquisition parameters as reported in the Methods of He et al. 2026.
INSTRUMENT = "NT=timsTOF Pro"
ACQUISITION = "NT=Data-Independent Acquisition;AC=NCIT:C161786"
CLEAVAGE = "AC=MS:1001251;NT=Trypsin"
FIXED_MOD = "NT=Carbamidomethyl;MT=Fixed;TA=C;AC=Unimod:4"
VAR_MOD_1 = "NT=Oxidation;MT=Variable;TA=M;AC=Unimod:35"
VAR_MOD_2 = "NT=Acetyl;MT=Variable;PP=Protein N-term;AC=Unimod:1"
TOLERANCE = "15 ppm"
LOCAL_DIR = "proteomics/data/raw"


def group_of(sample_id: str) -> str:
    if sample_id.startswith("Con"):
        return "Con"
    if sample_id.startswith(("CRKP", "CPKP")):
        return "CRKP"
    if sample_id.startswith("KP"):
        return "CSKP"
    raise ValueError(sample_id)


def main() -> None:
    pg = pd.read_csv(ROOT / "proteomics" / "data" / "raw" / "report.pg_matrix.tsv", sep="\t", nrows=1)
    runs = []
    for col in pg.columns:
        run = col.replace("\\", "/").rsplit("/", 1)[-1]
        if not run.endswith(".d"):
            continue
        match = re.match(r"25062408_HJ_([A-Za-z]+\d+)_[A-Z]{2}\d+_\d+_\d+\.d$", run)
        if not match:
            continue
        tag = match.group(1)
        if tag.startswith("mix"):
            continue  # pooled QC injections are not part of the differential design
        runs.append((tag, run))

    rows = []
    for tag, run in runs:
        group = group_of(tag)
        # The acquisition PC wrote 'CPKP' for the carbapenem-resistant samples while the
        # repository and the metabolomics submission use 'CRKP'. Deposited file names
        # follow the 'CRKP' spelling.
        sample_id = "CRKP" + tag[4:] if tag.startswith("CPKP") else tag
        data_file = run.replace("_CPKP", "_CRKP") + ".zip"
        replicate = int(re.search(r"(\d+)$", sample_id).group(1))
        rows.append(
            {
                "source name": sample_id,
                "characteristics[organism]": "Homo sapiens",
                "characteristics[organism part]": "blood serum",
                "characteristics[cell type]": "not applicable",
                "characteristics[disease]": DISEASE[group],
                "characteristics[biological replicate]": replicate,
                "material type": "body fluid",
                "technology type": "proteomic profiling by mass spectrometry",
                "comment[technical replicate]": 1,
                "comment[data file]": data_file,
                "comment[fraction identifier]": 1,
                "comment[label]": "AC=MS:1002038;NT=label free sample",
                "comment[cleavage agent details]": CLEAVAGE,
                "comment[instrument]": INSTRUMENT,
                "comment[proteomics data acquisition method]": ACQUISITION,
                "comment[modification parameters]": FIXED_MOD,
                "comment[modification parameters].1": VAR_MOD_1,
                "comment[modification parameters].2": VAR_MOD_2,
                "comment[precursor mass tolerance]": TOLERANCE,
                "comment[fragment mass tolerance]": TOLERANCE,
                "comment[file uri]": f"{LOCAL_DIR}/{data_file}",
                "factor value[disease]": DISEASE[group],
                "_group": group,
            }
        )

    sdrf = pd.DataFrame(rows)
    sdrf = sdrf.sort_values(
        ["_group", "characteristics[biological replicate]"],
        key=lambda s: s.map(GROUP_ORDER) if s.name == "_group" else s,
    ).drop(columns="_group")
    sdrf.insert(7, "assay name", [f"run {i}" for i in range(1, len(sdrf) + 1)])

    # SDRF allows repeated column names; pandas needs the suffixes above to build the frame.
    sdrf.columns = [re.sub(r"\.\d+$", "", c) for c in sdrf.columns]

    out = ROOT / "proteomics" / "data" / "PXD075261.sdrf.tsv"
    sdrf.to_csv(out, sep="\t", index=False)
    print(f"wrote {out.relative_to(ROOT)}: {sdrf.shape[0]} runs x {sdrf.shape[1]} columns")
    print(sdrf["factor value[disease]"].value_counts().to_string())


if __name__ == "__main__":
    main()

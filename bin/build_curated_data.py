#!/usr/bin/env python3
"""Build the curated, analysis-ready tables used by the course notebooks.

Inputs (raw material, as downloaded from the public repositories / the paper):
  proteomics/data/raw/report.pg_matrix.tsv .................. DIA-NN 1.9.2 MaxLFQ protein-group matrix (PXD075261)
  metabolomics/data/raw/metadata/m_MTBLS14016_*_maf.tsv ..... MetaboLights metabolite assignment file (MTBLS14016)
  publication/supplementary/*.xlsx ......................... supplementary tables of He et al. 2026

Outputs (small, tidy, Colab-friendly, committed to the repository):
  metadata/sample_metadata.tsv
  proteomics/data/protein_groups_matrix.tsv
  proteomics/data/protein_annotation.tsv
  proteomics/data/published_deps.tsv
  proteomics/data/published_kegg_deps.tsv
  metabolomics/data/metabolite_matrix.tsv
  metabolomics/data/metabolite_annotation.tsv
  metabolomics/data/published_dems.tsv
  metabolomics/data/published_kegg_dems.tsv
  multiomics/data/published_integrated_pathways.tsv

Run from the repository root:  python bin/build_curated_data.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SUPP = ROOT / "publication" / "supplementary"

GROUP_LABELS = {
    "Con": "Culture-negative sepsis",
    "CSKP": "Carbapenem-susceptible K. pneumoniae sepsis",
    "CRKP": "Carbapenem-resistant K. pneumoniae sepsis",
    "QC": "Pooled quality-control sample",
}
# Ordinal encoding of the clinical severity axis Con -> CSKP -> CRKP used for trend analyses.
GROUP_ORDER = {"Con": 0, "CSKP": 1, "CRKP": 2}


def sample_id_to_group(sample_id: str) -> str:
    """Map a repository sample identifier onto the three study groups.

    The two repositories use slightly different prefixes for the same patients:
      Con*   culture-negative sepsis controls
      KP*    carbapenem-susceptible K. pneumoniae  (CSKP; called CPKP in some proteomics file names)
      CRKP*  carbapenem-resistant K. pneumoniae
      mix*/QC*  pooled quality-control injections
    """
    if sample_id.startswith(("QC", "mix")):
        return "QC"
    if sample_id.startswith("Con"):
        return "Con"
    if sample_id.startswith(("CRKP", "CPKP")):
        return "CRKP"
    if sample_id.startswith("KP"):
        return "CSKP"
    raise ValueError(f"unrecognised sample identifier: {sample_id!r}")


def canonical_sample_id(sample_id: str) -> str:
    """Harmonise the proteomics file naming (CPKP*, mix*) with the metabolomics naming."""
    if sample_id.startswith("CPKP"):
        return "CRKP" + sample_id[4:]
    if sample_id.startswith("mix"):
        return "QC_pool" + sample_id[3:]
    return sample_id


# --------------------------------------------------------------------------------------
# 1. Clinical / sample metadata
# --------------------------------------------------------------------------------------
def build_sample_metadata() -> pd.DataFrame:
    clin = pd.read_excel(SUPP / "Supplymentary Data 1 Clinical Information.xlsx", sheet_name="discovery cohort")
    clin = clin.rename(
        columns={
            "编号": "record_number",       # 'number'
            "样本名": "sample_id",          # 'sample name'
            "分组": "group_raw",            # 'group'
            "Sex": "sex_code",
            "Age": "age",
            "BMI": "bmi",
            "TBIL": "total_bilirubin",
            "ALT": "alt",
            "AST": "ast",
            "Creatinine": "creatinine",
            "BUN": "blood_urea_nitrogen",
            "NLR": "neutrophil_lymphocyte_ratio",
            "PCT": "procalcitonin",
            "CRP": "c_reactive_protein",
            "WBC_Count": "wbc_count",
            "RBC_Count": "rbc_count",
            "Hb": "haemoglobin",
            "RDW": "red_cell_distribution_width",
            "PLT_Count": "platelet_count",
            "INR": "inr",
            "Heart disease": "heart_disease",
            "Liver disease": "liver_disease",
            "Cerebrovascular disease": "cerebrovascular_disease",
            "Kidney disease": "kidney_disease",
            "Diabetes": "diabetes",
            "COPD": "copd",
        }
    )
    clin["group"] = clin["sample_id"].map(sample_id_to_group)
    clin["group_label"] = clin["group"].map(GROUP_LABELS)
    clin["group_order"] = clin["group"].map(GROUP_ORDER)

    # Table 1 of the paper reports 31 male / 14 female participants in the discovery cohort,
    # which identifies the 0/1 coding of the supplementary table.
    counts = clin["sex_code"].value_counts()
    male_code = counts.idxmax() if counts.max() == 31 else None
    clin["sex"] = clin["sex_code"].map({male_code: "Male", 1 - male_code: "Female"}) if male_code is not None else pd.NA
    if male_code is None:
        print("  ! could not infer the sex coding from Table 1 (31 male / 14 female); 'sex' left empty")

    cols = [
        "sample_id", "group", "group_label", "group_order", "sex", "sex_code", "age", "bmi",
        "total_bilirubin", "alt", "ast", "creatinine", "blood_urea_nitrogen",
        "neutrophil_lymphocyte_ratio", "procalcitonin", "c_reactive_protein",
        "wbc_count", "rbc_count", "haemoglobin", "red_cell_distribution_width",
        "platelet_count", "inr",
        "diabetes", "heart_disease", "copd", "liver_disease", "cerebrovascular_disease", "kidney_disease",
    ]
    clin = clin[cols].sort_values(["group_order", "sample_id"], key=lambda s: s if s.name != "sample_id" else s.str.extract(r"(\d+)", expand=False).astype(int))
    return clin.reset_index(drop=True)


# --------------------------------------------------------------------------------------
# 2. Proteomics
# --------------------------------------------------------------------------------------
RUN_RE = re.compile(r"25062408_HJ_([A-Za-z]+\d+)_[A-Z]{2}\d+_\d+_\d+\.d$")


def build_proteomics() -> tuple[pd.DataFrame, pd.DataFrame]:
    pg = pd.read_csv(ROOT / "proteomics" / "data" / "raw" / "report.pg_matrix.tsv", sep="\t")
    id_cols = ["Protein.Group", "Protein.Names", "Genes", "First.Protein.Description"]

    rename = {}
    for col in pg.columns:
        if col in id_cols:
            continue
        run = col.replace("\\", "/").rsplit("/", 1)[-1]
        match = RUN_RE.match(run)
        if not match:
            raise ValueError(f"could not parse run name from column {col!r}")
        rename[col] = canonical_sample_id(match.group(1))
    pg = pg.rename(columns=rename)

    matrix = pg.rename(
        columns={
            "Protein.Group": "protein_group",
            "Protein.Names": "protein_names",
            "Genes": "genes",
            "First.Protein.Description": "description",
        }
    )
    # Order the quantification columns Con -> CSKP -> CRKP -> QC, numerically within group.
    sample_cols = [c for c in matrix.columns if c not in {"protein_group", "protein_names", "genes", "description"}]
    sample_cols = sorted(
        sample_cols,
        key=lambda s: (
            GROUP_ORDER.get(sample_id_to_group(s), 9),
            int(re.search(r"(\d+)$", s).group(1)),
        ),
    )
    matrix = matrix[["protein_group", "protein_names", "genes", "description"] + sample_cols]

    # Protein-level annotation (molecular weight, sequence length) from the supplementary DEP tables.
    frames = []
    xl = pd.ExcelFile(SUPP / "Supplymentary Data 2 DEPs Information.xlsx")
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        keep = [c for c in ["Protein", "Protein_Names", "Genes", "Description", "Mw(kDa)", "Length"] if c in df.columns]
        frames.append(df[keep])
    ann = pd.concat(frames, ignore_index=True).drop_duplicates(subset="Protein")
    ann = ann.rename(
        columns={
            "Protein": "protein_group",
            "Protein_Names": "protein_names",
            "Genes": "genes",
            "Description": "description",
            "Mw(kDa)": "molecular_weight_kda",
            "Length": "sequence_length",
        }
    )
    return matrix, ann


def build_published_deps() -> pd.DataFrame:
    xl = pd.ExcelFile(SUPP / "Supplymentary Data 2 DEPs Information.xlsx")
    frames = []
    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        df = df.rename(
            columns={
                "Protein": "protein_group",
                "Genes": "genes",
                "log2_FC": "log2_fold_change",
                "FC": "fold_change",
                "pvalue": "p_value",
                "mean_case": "mean_case",
                "mean_cont": "mean_control",
            }
        )
        df["comparison"] = sheet
        keep = [c for c in ["comparison", "protein_group", "genes", "mean_case", "mean_control",
                            "log2_fold_change", "fold_change", "p_value"] if c in df.columns]
        frames.append(df[keep])
    return pd.concat(frames, ignore_index=True)


def build_published_kegg(path: Path, rename: dict, comparison_is_sheet: bool = True) -> pd.DataFrame:
    xl = pd.ExcelFile(path)
    frames = []
    for sheet in xl.sheet_names:
        df = xl.parse(sheet).rename(columns=rename)
        if comparison_is_sheet:
            df.insert(0, "comparison", sheet)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------------------
# 3. Metabolomics
# --------------------------------------------------------------------------------------
def build_metabolomics() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    maf_dir = ROOT / "metabolomics" / "data" / "raw" / "metadata"
    maf = pd.read_csv(maf_dir / "m_MTBLS14016_LC-MS_positive__metabolite_profiling_v2_maf.tsv", sep="\t")

    # The MetaboLights submission ships the positive- and negative-mode MAF files with identical
    # content: a single widely-targeted table in which the adduct in 'charge' encodes the mode.
    neg = pd.read_csv(maf_dir / "m_MTBLS14016_LC-MS_negative__metabolite_profiling_v2_maf.tsv", sep="\t")
    if maf.equals(neg):
        print("  i positive- and negative-mode MAF files are identical; using the single combined table")

    sample_cols = [c for c in maf.columns if re.fullmatch(r"(Con|KP|CRKP)\d+|QC\d+", c)]
    sample_cols = sorted(
        sample_cols,
        key=lambda s: (GROUP_ORDER.get(sample_id_to_group(s), 9), int(re.search(r"(\d+)$", s).group(1))),
    )

    matrix = maf.rename(
        columns={
            "metabolite_identification": "metabolite",
            "chemical_formula": "formula",
            "mass_to_charge": "q1_mz",
            "charge": "adduct",
        }
    )[["metabolite", "formula", "q1_mz", "adduct"] + sample_cols]
    matrix["ion_mode"] = matrix["adduct"].str.strip().str[-1].map({"+": "positive", "-": "negative"})
    matrix = matrix[["metabolite", "formula", "q1_mz", "adduct", "ion_mode"] + sample_cols]

    # Annotation and published statistics for the differential metabolites.
    dem = pd.read_excel(SUPP / "Supplymentary Data 7 DEMs Information.xlsx")
    dem = dem.replace("-", pd.NA)
    ann = dem.rename(
        columns={
            "Compounds": "metabolite",
            "Class I": "class_i",
            "Class II": "class_ii",
            "Q1 (Da)": "q1_mz",
            "Molecular weight (Da)": "molecular_weight",
            "Ionization model": "adduct",
            "Formula": "formula",
            "Level": "identification_level",
            "CAS": "cas",
            "PubChem CID": "pubchem_cid",
            "HMDB": "hmdb",
            "ChEBI": "chebi",
            "Metlin": "metlin",
            "cpd_ID": "kegg_compound",
            "kegg_map": "kegg_map",
        }
    )
    ann = ann[[
        "metabolite", "class_i", "class_ii", "formula", "q1_mz", "molecular_weight", "adduct",
        "identification_level", "cas", "pubchem_cid", "hmdb", "chebi", "metlin", "kegg_compound", "kegg_map",
    ]].drop_duplicates(subset="metabolite")

    stats_cols = [c for c in dem.columns if re.search(r"_(VIP|P-value|Fold_Change|Log2FC|Type)$", str(c))]
    long_rows = []
    comparisons = sorted({re.sub(r"_(VIP|P-value|Fold_Change|Log2FC|Type)$", "", c) for c in stats_cols})
    for comparison in comparisons:
        cols = {
            "vip": f"{comparison}_VIP",
            "p_value": f"{comparison}_P-value",
            "fold_change": f"{comparison}_Fold_Change",
            "log2_fold_change": f"{comparison}_Log2FC",
            "regulation": f"{comparison}_Type",
        }
        sub = dem[["Compounds"]].copy().rename(columns={"Compounds": "metabolite"})
        sub.insert(0, "comparison", comparison)
        for new, old in cols.items():
            sub[new] = dem[old] if old in dem.columns else pd.NA
        long_rows.append(sub)
    published = pd.concat(long_rows, ignore_index=True)

    return matrix, ann, published


# --------------------------------------------------------------------------------------
def main() -> None:
    print("Building curated course tables")

    (ROOT / "metadata").mkdir(exist_ok=True)
    meta = build_sample_metadata()
    meta.to_csv(ROOT / "metadata" / "sample_metadata.tsv", sep="\t", index=False)
    print(f"  metadata/sample_metadata.tsv                      {meta.shape[0]} samples x {meta.shape[1]} variables")

    matrix, ann = build_proteomics()
    matrix.to_csv(ROOT / "proteomics" / "data" / "protein_groups_matrix.tsv", sep="\t", index=False)
    ann.to_csv(ROOT / "proteomics" / "data" / "protein_annotation.tsv", sep="\t", index=False)
    n_samples = matrix.shape[1] - 4
    print(f"  proteomics/data/protein_groups_matrix.tsv         {matrix.shape[0]} protein groups x {n_samples} runs")
    print(f"  proteomics/data/protein_annotation.tsv            {ann.shape[0]} proteins")

    deps = build_published_deps()
    deps.to_csv(ROOT / "proteomics" / "data" / "published_deps.tsv", sep="\t", index=False)
    print(f"  proteomics/data/published_deps.tsv                {deps.shape[0]} rows")

    kegg_deps = build_published_kegg(
        SUPP / "Supplymentary Data 5 KEGG Enrichment of DEPs.xlsx",
        {"Pathway": "kegg_pathway", "Description": "description", "GeneRatio": "gene_ratio",
         "BgRatio": "background_ratio", "RichFactor": "rich_factor", "Fold enrichment": "fold_enrichment",
         "pvalue": "p_value", "p.adjust": "p_adjusted", "Accession": "protein_groups", "Genes": "genes",
         "Gene": "kegg_genes", "Count": "count"},
    )
    kegg_deps.to_csv(ROOT / "proteomics" / "data" / "published_kegg_deps.tsv", sep="\t", index=False)
    print(f"  proteomics/data/published_kegg_deps.tsv           {kegg_deps.shape[0]} rows")

    mmatrix, mann, mpublished = build_metabolomics()
    mmatrix.to_csv(ROOT / "metabolomics" / "data" / "metabolite_matrix.tsv", sep="\t", index=False)
    mann.to_csv(ROOT / "metabolomics" / "data" / "metabolite_annotation.tsv", sep="\t", index=False)
    mpublished.to_csv(ROOT / "metabolomics" / "data" / "published_dems.tsv", sep="\t", index=False)
    n_msamples = mmatrix.shape[1] - 5
    print(f"  metabolomics/data/metabolite_matrix.tsv           {mmatrix.shape[0]} metabolites x {n_msamples} injections")
    print(f"  metabolomics/data/metabolite_annotation.tsv       {mann.shape[0]} annotated metabolites")
    print(f"  metabolomics/data/published_dems.tsv              {mpublished.shape[0]} rows")

    kegg_dems = build_published_kegg(
        SUPP / "Supplymentary Data 8 KEGG Enrichment of DEMs.xlsx",
        {"Kegg_pathway": "kegg_pathway", "ko_ID": "ko_id", "Sig_compound": "significant_compounds",
         "compound": "pathway_compounds", "Sig_compound_all": "significant_compounds_total",
         "compound_all": "compounds_total", "IndexList": "metabolite_index_list",
         "CIDList": "kegg_compound_list", "Pathway": "kegg_url"},
    )
    kegg_dems.to_csv(ROOT / "metabolomics" / "data" / "published_kegg_dems.tsv", sep="\t", index=False)
    print(f"  metabolomics/data/published_kegg_dems.tsv         {kegg_dems.shape[0]} rows")

    integrated = pd.read_excel(SUPP / "Supplymentary Data 9 Integrated Pathway Analysis.xlsx").rename(
        columns={"Pathway": "pathway", "matched_features": "matched_features", "Total": "pathway_size",
                 "Expected": "expected", "Hits": "hits", "Raw p": "p_value",
                 "Holm adjust": "p_holm", "FDR": "fdr", "Impact": "impact"}
    )
    integrated.to_csv(ROOT / "multiomics" / "data" / "published_integrated_pathways.tsv", sep="\t", index=False)
    print(f"  multiomics/data/published_integrated_pathways.tsv  {integrated.shape[0]} pathways")

    print("Done.")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
#
# Fetch the raw metabolomics files of MTBLS14016 that are not tracked in git.
#
#   bash metabolomics/data/raw/download.sh
#
# No .mzML files are committed to the repository. The Day 1 metabolomics notebook fetches
# the single file it needs on demand; this script fetches all five samples used by that
# notebook and its exercises, in both polarities.
#
# The paths come from the 'Derived Spectral Data File' column of the MetaboLights assay
# tables shipped in ./metadata/ — check there if the layout ever changes.

set -euo pipefail
cd "$(dirname "$0")"

STUDY="MTBLS14016"
BASE="https://ftp.ebi.ac.uk/pub/databases/metabolights/studies/public/${STUDY}/FILES/DERIVED_FILES"

FILES=(
  Con10_P.mzML  Con10_N.mzML
  KP11_P.mzML   KP11_N.mzML
  KP12_P.mzML   KP12_N.mzML
  KP15_P.mzML   KP15_N.mzML
  CRKP12_P.mzML CRKP12_N.mzML
)

for file in "${FILES[@]}"; do
  if [[ -f "$file" ]]; then
    echo "have     $file"
  else
    echo "fetching $file"
    wget -q -nc "${BASE}/${file}" -O "$file" || {
      echo "  !! failed. Check the study layout at https://www.ebi.ac.uk/metabolights/${STUDY}"
      rm -f "$file"
    }
  fi
done

echo
echo "Done. To use these with a pipeline that needs an index, run:"
echo "  python bin/reindex_mzml.py --input_dir metabolomics/data/raw"

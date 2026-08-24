"""
Reindex mzML files to make them compatible for easy access via metaboigniter
with the latest version of pymzml.

pip install pyopenms
"""

import argparse
import pathlib

from pyopenms import MSExperiment, MzMLFile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="reindex_mzml",
        description="Read mzML files from a folder and write them back in place.",
    )
    parser.add_argument(
        "--input_dir",
        "-i",
        default=".",
        help="Folder containing mzML files. Defaults to the current directory.",
    )
    return parser.parse_args()


def reindex_mzml(folder: pathlib.Path) -> None:
    mzml_files = sorted(
        _file
        for _file in folder.iterdir()
        if _file.is_file() and _file.suffix.lower() == ".mzml"
    )

    if not mzml_files:
        print(f"No mzML files found in {folder}")
        return

    for _file in mzml_files:
        print(f"Reindexing {_file}...")
        exp = MSExperiment()
        MzMLFile().load(str(_file), exp)
        MzMLFile().store(str(_file), exp)


def main() -> None:
    args = parse_args()
    folder = pathlib.Path(args.input_dir).expanduser().resolve()

    if not folder.is_dir():
        raise NotADirectoryError(f"{folder} is not a directory")

    reindex_mzml(folder)


if __name__ == "__main__":
    main()

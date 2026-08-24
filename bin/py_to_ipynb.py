#!/usr/bin/env python3
"""Convert jupytext 'percent' format .py files into .ipynb notebooks.

The course notebooks are authored as plain Python files in the jupytext
`percent` format, which keeps them reviewable in git, and are converted to
`.ipynb` for Google Colab with this script.

    python bin/py_to_ipynb.py path/to/notebook.py [more.py ...]
    python bin/py_to_ipynb.py --all        # convert every *.py next to a notebooks/ folder

Cell markers:
    # %%                    -> code cell
    # %% [markdown]         -> markdown cell (leading '# ' is stripped from each line)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def split_cells(text: str) -> list[tuple[str, str]]:
    cells: list[tuple[str, str]] = []
    kind = "code"
    buffer: list[str] = []
    started = False

    for line in text.splitlines():
        if line.startswith("# %%"):
            if started:
                cells.append((kind, "\n".join(buffer)))
            buffer = []
            started = True
            kind = "markdown" if "[markdown]" in line else "code"
            continue
        buffer.append(line)
    if started:
        cells.append((kind, "\n".join(buffer)))
    return cells


def clean_markdown(body: str) -> str:
    lines = []
    for line in body.splitlines():
        if line.startswith("# "):
            lines.append(line[2:])
        elif line.strip() == "#":
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines).strip("\n")


def to_notebook(text: str) -> dict:
    cells = []
    for kind, body in split_cells(text):
        source = clean_markdown(body) if kind == "markdown" else body.strip("\n")
        if not source.strip():
            continue
        cell = {
            "cell_type": kind,
            "metadata": {},
            "source": [f"{line}\n" for line in source.split("\n")[:-1]] + [source.split("\n")[-1]],
        }
        if kind == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        cells.append(cell)

    return {
        "cells": cells,
        "metadata": {
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def convert(path: Path) -> Path:
    path = path.resolve()
    nb = to_notebook(path.read_text())
    out = path.with_suffix(".ipynb")
    out.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    n_md = sum(c["cell_type"] == "markdown" for c in nb["cells"])
    n_code = sum(c["cell_type"] == "code" for c in nb["cells"])
    try:
        shown = out.relative_to(ROOT)
    except ValueError:  # a source outside the repository
        shown = out
    print(f"  {shown}  ({n_md} markdown + {n_code} code cells)")
    return out


def main(argv: list[str]) -> None:
    if not argv or argv[0] == "--all":
        paths = sorted(ROOT.glob("*/notebooks/*.py")) + sorted(ROOT.glob("notebooks/*/*.py"))
    else:
        paths = [Path(a) for a in argv]
    if not paths:
        sys.exit("no .py notebook sources found")
    print("Converting notebook sources:")
    for path in paths:
        convert(path)


if __name__ == "__main__":
    main(sys.argv[1:])

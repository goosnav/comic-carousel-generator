"""Headless batch: python -m comic_carousel SCAN_OR_FOLDER ... [--out DIR] [--layout X]

A folder means every scan directly inside it. Each scan gets its own <name>-carousel-NNN folder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import find_images, process
from .render import LAYOUTS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="comic_carousel", description=__doc__)
    parser.add_argument("scans", nargs="+", type=Path, help="scanned images, or folders of them")
    parser.add_argument("--out", type=Path, help="parent folder for the per-scan carousel folders (default: beside each scan)")
    parser.add_argument("--layout", choices=LAYOUTS, default="auto", help="summary layout (default: auto)")
    args = parser.parse_args(argv)
    unsure = 0
    scans = []
    for item in args.scans:
        if item.is_dir():
            found = find_images(item)
            if not found:
                print(f"{item}: no images in this folder", file=sys.stderr)
                unsure += 1
            scans += found
        else:
            scans.append(item)
    for scan in scans:
        try:
            result = process(scan, args.out, args.layout)
        except Exception as error:  # keep going through the batch, say what failed
            print(f"{scan.name}: failed — {error}", file=sys.stderr)
            unsure += 1
            continue
        print(result.summary_line())
        unsure += result.needs_review
    return 2 if unsure else 0


if __name__ == "__main__":
    raise SystemExit(main())

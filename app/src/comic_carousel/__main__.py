"""Headless batch: python -m comic_carousel scan1.jpg scan2.jpg [--out DIR] [--layout X]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import process
from .render import LAYOUTS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="comic_carousel", description=__doc__)
    parser.add_argument("scans", nargs="+", type=Path, help="scanned comic images")
    parser.add_argument("--out", type=Path, help="parent folder for carousel-export-NNN (default: beside each scan)")
    parser.add_argument("--layout", choices=LAYOUTS, default="auto", help="summary layout (default: auto)")
    args = parser.parse_args(argv)
    unsure = 0
    for scan in args.scans:
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

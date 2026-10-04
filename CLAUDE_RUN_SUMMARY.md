# Run summary — 2026-09-08

Built the Comic Carousel Generator MVP: scanned hand-drawn comics in, Instagram carousel
PNGs out, with no human in the loop by default.

## What changed

The repository was empty apart from `examples/`. Everything below is new.

| Area | Files |
|---|---|
| Panel detection | `app/src/comic_carousel/detect.py` |
| Canvases and export | `app/src/comic_carousel/render.py` |
| Shared entry point | `app/src/comic_carousel/pipeline.py` |
| Loopback server | `app/src/comic_carousel/server.py`, `start.py` |
| Batch CLI | `app/src/comic_carousel/__main__.py` |
| Browser GUI | `app/static/index.html`, `app.js`, `style.css` |
| Launchers | `run.command`, `run.sh`, `run.ps1` |
| Dependencies | `app/pyproject.toml`, `app/uv.lock`, `app/.python-version` |
| Launcher contract | `app/launcher/manifest.json`, `bootstrap.py` |
| Tests | `tests/test_detect.py`, `tests/test_render.py`, `tests/conftest.py` |
| Docs | `README.md`, `TUTORIAL.md`, `README.txt` |
| Private governance | `dev/` (ignored), `AGENTS.md`, `CLAUDE.md` (ignored) |

Production dependencies are numpy and opencv-python-headless. Nothing else.

## Commands run, and what they printed

Test suite:

```
cd app && uv run --locked --managed-python python -m pytest ../tests -q
17 passed in 2.35s
```

Batch export of all four example scans:

```
./run.sh "examples/brain tumor/brain tumor raw.jpg" \
         "examples/why am i alive/why am i alive raw.jpg" \
         "examples/the fish that bites loose dangling objects/the fish that bites loose dangling objects raw.jpg" \
         "examples/LLM brain replacement/LLM brain replacement raw.jpg" --out <tmp>

brain tumor raw.jpg: 3 panels, exported to carousel-export-001
why am i alive raw.jpg: 2 panels, exported to carousel-export-002
the fish that bites loose dangling objects raw.jpg: 3 panels, exported to carousel-export-003
LLM brain replacement raw.jpg: 2 panels, exported to carousel-export-004
exit=0        (real time 1.5 s for all four)
```

Every output measured 1080 × 1350 with `sips`.

## Detection accuracy against the examples

| Scan | Panels expected | Detected automatically | Manual correction |
|---|---|---|---|
| brain tumor | 3 | 3 | none |
| why am i alive | 2 | 2 | none |
| the fish that bites loose dangling objects | 3 | 3 | none |
| LLM brain replacement | 2 | 2 | none |

10 of 10 panels, no false positives, all four marked confident. The two tilted scans were
deskewed by 0.98° and 0.82° before cropping.

Every panel crop contains the complete drawn square. Measured directly: for each crop edge,
the number of border pixels still lying outside the crop is **0** on all 10 panels, and no
two crops overlap (0 px²). Before the outward snap was added, up to 35 px of the border was
being cut off (LLM panel 2, right edge).

## Browser GUI verified

Driven in a real browser against `http://127.0.0.1:8765/`:

- `/health/ready` returns 200; a POST without the session token returns 403.
- Auto path: four scans queued, four rows filled in with panel counts and export folders,
  no other interaction.
- Export folders increment: `carousel-export-001` through `-005`, nothing overwritten.
- Review path: editor opened with three boxes in reading order and live thumbnails;
  body drag moved a box, corner drag resized it, Skip and Export both returned to the table.
- A bad export folder produced a clear failure row and a Try again button that recovered
  into the same row.
- Quit stopped the process; port 8765 free afterwards.

## Known limitations

- **Not the packaged product yet.** The five native launcher images and the universal ZIP in
  `app/launcher/manifest.json` are the next milestone. Today it starts from `run.command` /
  `run.sh` / `run.ps1` and needs `uv` on PATH. M1a stays ACTIVE, not a candidate for
  acceptance.
- `run.ps1` is written but has not been run on Windows. Only macOS Apple Silicon was tested.
- Windows ARM64 is out of the platform matrix: no `opencv-python-headless` wheel exists for
  it (`dev/DECISIONS.txt`, DECISION-20260908-003).
- Panels without a fully drawn rectangular border are not detected; the review editor is the
  answer for those.
- The Linux file chooser needs `zenity` installed.
- Only four raw scans exist as fixtures, all from one scanner at one setting. Wider variety
  would test the thresholds harder.

## Next task

Build the M1a launcher images: compile the Go supervisor from the skill's
`assets/m1a-launcher/` for macOS universal, Windows x64, and Linux x86_64/ARM64; bundle the
pinned `uv` tools with checksums; assemble the universal ZIP; then run the acceptance matrix
on each claimed target.

---

# Run summary — 2026-10-04: whole-folder batch

## What changed

- **Choose a folder…** is now the first button. It opens the native folder chooser and
  queues every image directly inside the folder; no per-image selection.
- Each scan gets its own output folder beside it, named after it:
  `<scan name>-carousel-001`, then `-002` on a re-run. Replaces the shared
  `carousel-export-NNN` numbering.
- `./run.sh FOLDER` does the same headlessly. Files and folders can be mixed.
- Folder names are made safe for Windows, macOS and Linux.
- Subfolders are not searched, so earlier output is never fed back in as scans.

Also committed with this change: detection improvements that were already uncommitted in
the working tree (colour preservation through to the PNGs, deskew up to 12 degrees,
contour recovery at every nesting level, edited panel counts in the results table).

## Commands and results

```
cd app && uv run --locked --managed-python python -m pytest ../tests -q
30 passed

./run.sh <folder holding the four example scans>
brain tumor raw.jpg: 3 panels, exported to brain tumor raw-carousel-001
LLM brain replacement raw.jpg: 2 panels, exported to LLM brain replacement raw-carousel-001
the fish that bites loose dangling objects raw.jpg: 3 panels, exported to the fish that bites loose dangling objects raw-carousel-001
why am i alive raw.jpg: 2 panels, exported to why am i alive raw-carousel-001
exit=0   (about 2 s wall time)
```

GUI, in a real browser: the folder result was fed to the page and all four scans exported
to their own `-carousel-002` folders with no further input. Empty folder and cancelled
dialog both show a plain message.

## Not verified

- The native folder dialog itself was not clicked; it cannot be driven from the test
  browser. The macOS AppleScript compiles. The Windows and Linux dialogs are untested.

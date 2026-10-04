# Comic Carousel Generator

Turns a scanned hand-drawn comic into Instagram carousel assets: one 1080 × 1350 PNG per
panel, plus a summary PNG of the whole comic on the same canvas.

It runs on your own computer. No account, no cloud, no AI model. Panels are found with
classical machine vision: edge detection builds the horizontal and vertical line masks,
corner detection finds where those lines meet, and rectangles are assembled from matching
corner quadruples and verified against the ink.

## Open it

macOS: double-click `run.command`.
Linux: run `./run.sh`.
Windows: run `.\run.ps1`.

The browser opens by itself. The first launch downloads a private copy of Python 3.12 and
two libraries with [uv](https://docs.astral.sh/uv/); that needs a network connection and
takes about a minute. Later launches are immediate. Nothing is installed system-wide.

If `uv` is missing, the launcher prints the one-line install command and stops.

## Use it

Press **Choose a folder…** and pick the folder holding your scans. Every image directly
inside it is processed, one after another, with no further clicks. Each scan gets a row in
the results table naming the folder its PNGs went to. That is the whole job.

**Choose scans…** does the same for a hand-picked set of files.

Tick **Show me the boxes before exporting** when you want to check first. The editor also
opens by itself for a scan I am unsure about, and the row says why.

Each scan gets its own folder beside it, named after it:

```
Scans/
├── brain tumor raw.jpg
├── brain tumor raw-carousel-001/
│   ├── panel_01.png
│   ├── panel_02.png
│   ├── panel_03.png
│   └── summary.png
├── why am i alive raw.jpg
└── why am i alive raw-carousel-001/
    ├── panel_01.png
    ├── panel_02.png
    └── summary.png
```

Nothing is ever overwritten: running the same scan again makes `…-carousel-002`.
Subfolders are not searched, so earlier output folders are never read back in as scans. Set a different
parent folder under **Export somewhere else** if you want them elsewhere.

## Without the window

```bash
./run.sh ~/Scans                                   # every scan in the folder
./run.sh "scan one.jpg" "scan two.jpg" --out ~/Desktop --layout stack
```

Same detection, same output. Exit code 2 means at least one scan is worth a look.
`--layout` accepts `auto`, `as-drawn`, `stack`, `grid`, or `one-over-two`.

## What it expects

Flatbed scans of ink-on-paper comics, one to about six rectangular panels, letter or A4,
300–600 dpi. Slight rotation, broken borders, wobbly lines, registration marks, and pencil
notes outside the panels are all fine. Panels drawn without a full border are not: use the
editor and draw the box yourself.

## Where things are

| What | Where |
|---|---|
| Detection, rendering, server | `app/src/comic_carousel/` |
| Browser GUI | `app/static/` |
| Dependency lock and launcher contract | `app/pyproject.toml`, `app/uv.lock`, `app/launcher/` |
| Tests | `tests/` |

Run the tests with `cd app && uv run --locked python -m pytest ../tests -q`.

## State of the work

This is the working MVP. It is not yet the packaged product: the five native launcher
images and the universal ZIP described in `app/launcher/manifest.json` are the next
milestone, so today the shell launchers above are how it starts. `run.ps1` is written but
has not been run on Windows. Windows ARM64 is out of scope until OpenCV publishes a wheel
for it.

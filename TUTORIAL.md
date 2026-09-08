# Tutorial

## 1. First launch

Double-click `run.command` (macOS), or run `./run.sh` (Linux) or `.\run.ps1` (Windows).

A terminal window appears, prints a line like `Comic Carousel Generator is at
http://127.0.0.1:51703/`, and your browser opens on that address.

The first launch fetches a private Python 3.12 and the two libraries it needs. That takes
about a minute and needs a network connection. It happens once; nothing lands in your
system Python and nothing is installed system-wide.

If you see instructions for installing `uv` instead, run the command it prints:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

then start the app again.

## 2. Export a comic

1. Press **Browse…**. The macOS file chooser opens. Pick a scan. You can select several
   at once with shift-click or cmd-click.
2. Wait about a second per scan.
3. Each scan appears in the results table with the number of panels found and the folder
   its PNGs went to, for example `Exported to carousel-export-001 (as-drawn)`.
4. Press **Reveal** to open that folder in the Finder.

Inside you get `panel_01.png`, `panel_02.png`, … in reading order (left to right, top to
bottom), and `summary.png` with the whole comic laid out on one canvas. Every file is
1080 × 1350 pixels, white background, artwork centered, nothing stretched or cropped.

## 3. Check the boxes when you want to

Tick **Show me the boxes before exporting** before you press Browse. The editor then opens
for every scan instead of exporting straight away.

It also opens on its own when I am unsure about a scan. The row says why: a weak border,
overlapping panels, or nothing found at all.

In the editor:

- **Move a box**: drag its middle.
- **Resize a box**: drag a red corner square.
- **Delete a box**: click it, then press Delete. Or press **Remove** in the list below.
- **Add a box**: press **Add a box**. A new one appears in the middle of the page. Drag
  and resize it into place.
- **Reorder**: press **Up** or **Down** in the list. The numbers on the page are the
  export order.
- **Change the summary layout**: pick one from the dropdown. `auto` chooses the layout
  that uses the canvas best.

The thumbnails under **Preview** are exactly what will be written, and they refresh a
moment after every change. Press **Export** when it looks right, or **Skip this one** to
move on without writing anything.

## 4. Export somewhere else

Open **Export somewhere else** and type a folder path. Every export in this session goes
into a numbered folder there instead of beside the scan. Clear the box to go back to the
default. The setting is remembered in your browser.

## 5. Batch from the terminal

```bash
./run.sh ~/Scans/*.jpg --out ~/Desktop/carousels
```

No window opens. One line is printed per scan, and the exit code is 2 if any scan needs a
look. Add `--layout stack` to force a summary layout for all of them.

## 6. Quitting

Press **Quit** at the bottom of the page, or close the terminal window. Nothing keeps
running in the background.

## When it gets something wrong

**A panel is missing.** Its border is probably broken by more than a pen lift, or it is
drawn without a full rectangle. Turn on review mode and add the box by hand.

**Two panels are found as one.** They share a border and the shared line was read as one
rectangle. Delete the merged box and add two.

**A speech balloon or a window is found as a panel.** It was rectangular and fully
enclosed. Delete it in review mode; the numbering closes up on its own.

**Everything is off by a small rotation.** The page is deskewed automatically from the
panel borders. If a scan is more than a few degrees off, straighten it in your scanner
software first.

**The file chooser does not open on Linux.** Install `zenity`, which is what the app asks
for the native dialog.

## What it does under the hood

1. Read the scan, push paper to white and ink to black if it is not already black-and-white.
2. Measure the page tilt from long straight strokes and rotate it back.
3. Build a horizontal-line mask and a vertical-line mask with morphology, bridging pen-lift
   gaps but never gaps as wide as a gutter.
4. Find every junction where those two masks meet, and label it by which arms it has:
   top-left, top-right, bottom-left, bottom-right. A T-junction gets two labels, a crossing
   gets four, which is how panels sharing a border are separated.
5. Assemble rectangles from matching corner quadruples, and keep only those whose four
   sides are genuinely inked.
6. Add nearly-rectangular outer contours as a second source, verified the same way.
7. Drop a rectangle that is mostly filled by other rectangles (the outline around a whole
   row), then any rectangle nested inside a kept one (a window drawn inside a panel).
8. Grow each edge outward until the drawn border really ends, so no part of the square is
   cut off, then add a little white without crossing into a neighbour.
9. Sort into reading order, render, write PNGs.

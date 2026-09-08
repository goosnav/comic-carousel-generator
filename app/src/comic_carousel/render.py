"""Instagram canvases: one 4:5 PNG per panel plus a re-flowed summary of the whole comic."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .detect import Box, group_rows

CANVAS_W, CANVAS_H = 1080, 1350
FILL = 0.95          # the artwork fills at most this share of each canvas dimension
GUTTER = 0.025       # summary gutter, share of canvas width
LAYOUTS = ("auto", "as-drawn", "stack", "grid", "one-over-two")


def crop(image: np.ndarray, box: Box) -> np.ndarray:
    return image[box.y:box.y + box.h, box.x:box.x + box.w]


def _resize(img: np.ndarray, w: int, h: int) -> np.ndarray:
    shrinking = w < img.shape[1]
    return cv2.resize(img, (max(1, w), max(1, h)), interpolation=cv2.INTER_AREA if shrinking else cv2.INTER_CUBIC)


def _fit(w: int, h: int, max_w: float, max_h: float) -> tuple[int, int]:
    scale = min(max_w / w, max_h / h)
    return int(round(w * scale)), int(round(h * scale))


def blank() -> np.ndarray:
    return np.full((CANVAS_H, CANVAS_W), 255, np.uint8)


def paste(canvas: np.ndarray, img: np.ndarray, x: int, y: int) -> None:
    h, w = img.shape
    canvas[y:y + h, x:x + w] = img


def panel_canvas(art: np.ndarray) -> np.ndarray:
    canvas = blank()
    w, h = _fit(art.shape[1], art.shape[0], CANVAS_W * FILL, CANVAS_H * FILL)
    paste(canvas, _resize(art, w, h), (CANVAS_W - w) // 2, (CANVAS_H - h) // 2)
    return canvas


# ---------------------------------------------------------------- summary

def row_plans(boxes: list[Box]) -> dict[str, list[list[int]]]:
    """Which panel indices share a row, per named layout."""
    n = len(boxes)
    index = {id(b): i for i, b in enumerate(boxes)}
    plans = {
        "as-drawn": [[index[id(b)] for b in row] for row in group_rows(boxes)],
        "stack": [[i] for i in range(n)],
        "grid": [list(range(i, min(i + 2, n))) for i in range(0, n, 2)],
    }
    if n == 3:
        plans["one-over-two"] = [[0], [1, 2]]
    return plans


def place(boxes: list[Box], rows: list[list[int]]) -> tuple[list[tuple[int, int, int, int]], float]:
    """Justified rows: every row spans the usable width at one height; the block is
    scaled to fit the usable height and centered. Returns (x, y, w, h) per panel and a
    score = canvas coverage x scale uniformity, so a layout that enlarges one panel at the
    expense of the others does not win on area alone."""
    usable_w, usable_h = CANVAS_W * FILL, CANVAS_H * FILL
    gutter = CANVAS_W * GUTTER
    heights = []
    for row in rows:
        aspects = sum(boxes[i].w / boxes[i].h for i in row)
        heights.append((usable_w - gutter * (len(row) - 1)) / aspects)
    total_h = sum(heights) + gutter * (len(rows) - 1)
    scale = min(1.0, usable_h / total_h)
    block_h = total_h * scale
    block_w = usable_w * scale
    y = (CANVAS_H - block_h) / 2
    placements: dict[int, tuple[int, int, int, int]] = {}
    for row, row_h in zip(rows, heights):
        rh = row_h * scale
        x = (CANVAS_W - block_w) / 2
        for i in row:
            pw = boxes[i].w / boxes[i].h * rh
            placements[i] = (int(round(x)), int(round(y)), int(round(pw)), int(round(rh)))
            x += pw + gutter * scale
        y += rh + gutter * scale
    ordered = [placements[i] for i in range(len(boxes))]
    coverage = sum(w * h for _, _, w, h in ordered) / (CANVAS_W * CANVAS_H)
    scales = [w / boxes[i].w for i, (_, _, w, _) in enumerate(ordered)]
    uniformity = min(scales) / max(scales)  # 1.0 when every panel keeps the same relative size
    return ordered, coverage * uniformity


def choose_layout(boxes: list[Box], layout: str = "auto") -> str:
    plans = row_plans(boxes)
    if layout != "auto":
        return layout if layout in plans else "as-drawn"
    return max(plans, key=lambda name: place(boxes, plans[name])[1])


def summary_canvas(image: np.ndarray, boxes: list[Box], layout: str = "auto") -> tuple[np.ndarray, str]:
    canvas = blank()
    if not boxes:
        return canvas, "as-drawn"
    chosen = choose_layout(boxes, layout)
    placements, _ = place(boxes, row_plans(boxes)[chosen])
    for box, (x, y, w, h) in zip(boxes, placements):
        paste(canvas, _resize(crop(image, box), w, h), x, y)
    return canvas, chosen


def render_all(image: np.ndarray, boxes: list[Box], layout: str = "auto") -> tuple[list[np.ndarray], np.ndarray, str]:
    panels = [panel_canvas(crop(image, box)) for box in boxes]
    summary, chosen = summary_canvas(image, boxes, layout)
    return panels, summary, chosen


# ---------------------------------------------------------------- export

def next_export_dir(parent: Path) -> Path:
    n = 1
    while (parent / f"carousel-export-{n:03d}").exists():
        n += 1
    target = parent / f"carousel-export-{n:03d}"
    target.mkdir(parents=True)
    return target


def write_png(path: Path, gray: np.ndarray) -> None:
    ok, buffer = cv2.imencode(".png", cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
    if not ok:
        raise RuntimeError(f"PNG encoding failed for {path.name}")
    buffer.tofile(str(path))  # Unicode-safe on Windows


def export(image: np.ndarray, boxes: list[Box], parent: Path, layout: str = "auto") -> tuple[Path, list[Path], str]:
    panels, summary, chosen = render_all(image, boxes, layout)
    target = next_export_dir(parent)
    files = []
    for i, canvas in enumerate(panels, 1):
        files.append(target / f"panel_{i:02d}.png")
        write_png(files[-1], canvas)
    files.append(target / "summary.png")
    write_png(files[-1], summary)
    return target, files, chosen

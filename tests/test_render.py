from pathlib import Path

import cv2
import numpy as np
import pytest

from comic_carousel import detect as d
from comic_carousel import render as r
from comic_carousel.pipeline import process

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def framed(w, h):
    art = np.full((h, w), 255, np.uint8)
    cv2.rectangle(art, (10, 10), (w - 11, h - 11), 0, 12)
    return art


def ink_bbox(canvas):
    ys, xs = np.where(canvas < 128)
    return xs.min(), xs.max(), ys.min(), ys.max()


def test_panel_canvas_fill_and_centering():
    for w, h in ((1800, 1800), (3700, 1800), (1400, 1900)):
        canvas = r.panel_canvas(framed(w, h))
        assert canvas.shape == (r.CANVAS_H, r.CANVAS_W)
        x0, x1, y0, y1 = ink_bbox(canvas)
        fill_w, fill_h = (x1 - x0) / r.CANVAS_W, (y1 - y0) / r.CANVAS_H
        assert abs(max(fill_w, fill_h) - r.FILL) < 0.012
        assert abs((x0 + x1) / 2 - r.CANVAS_W / 2) < 3 and abs((y0 + y1) / 2 - r.CANVAS_H / 2) < 3


def boxes(*rects):
    return [d.Box(*rect) for rect in rects]


def test_auto_layout_choices():
    assert r.choose_layout(boxes((0, 0, 2900, 1800), (3000, 0, 2900, 1800))) == "stack"
    assert r.choose_layout(boxes((0, 0, 1800, 1800), (1900, 0, 1800, 1800), (0, 1900, 3700, 1800))) == "as-drawn"
    three_in_a_row = boxes((0, 0, 1800, 1800), (1900, 0, 1800, 1800), (3800, 0, 1800, 1800))
    assert r.choose_layout(three_in_a_row) == "stack"
    assert r.choose_layout(three_in_a_row, "stack") == "stack"
    grid = boxes((0, 0, 1000, 1200), (1100, 0, 1000, 1200), (0, 1300, 1000, 1200), (1100, 1300, 1000, 1200))
    assert r.choose_layout(grid) in ("as-drawn", "grid")


def test_summary_fits_canvas_for_every_layout():
    page = np.full((5100, 6600), 255, np.uint8)
    bx = boxes((300, 300, 1800, 1800), (2200, 300, 1800, 1800), (4100, 300, 1800, 1800))
    for box in bx:
        cv2.rectangle(page, (box.x, box.y), (box.x + box.w, box.y + box.h), 0, 14)
    for layout in ("as-drawn", "stack", "grid", "one-over-two"):
        canvas, chosen = r.summary_canvas(page, bx, layout)
        assert chosen == layout and canvas.shape == (r.CANVAS_H, r.CANVAS_W)
        x0, x1, y0, y1 = ink_bbox(canvas)
        assert x0 >= 20 and y0 >= 20 and x1 <= r.CANVAS_W - 20 and y1 <= r.CANVAS_H - 20


def test_export_numbering_and_files(tmp_path):
    page = np.full((2550, 3300), 255, np.uint8)
    bx = boxes((300, 300, 1200, 1200), (1700, 300, 1200, 1200))
    first, files, _ = r.export(page, bx, tmp_path)
    second, _, _ = r.export(page, bx, tmp_path)
    assert first.name == "carousel-export-001" and second.name == "carousel-export-002"
    assert [f.name for f in files] == ["panel_01.png", "panel_02.png", "summary.png"]
    img = cv2.imread(str(files[0]))
    assert img.shape == (r.CANVAS_H, r.CANVAS_W, 3)


@pytest.mark.skipif(not EXAMPLES.is_dir(), reason="examples/ not present")
def test_examples_end_to_end(tmp_path):
    expected_layout = {"why am i alive": "stack", "LLM brain replacement": "stack", "brain tumor": "as-drawn"}
    for name, layout in expected_layout.items():
        result = process(EXAMPLES / name / f"{name} raw.jpg", tmp_path / name)
        assert result.layout == layout, name
        assert not result.needs_review, result.detection.reasons
        assert len(result.files) == len(result.detection.boxes) + 1

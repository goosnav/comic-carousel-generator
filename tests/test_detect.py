"""Synthetic pages that exercise each detection rule, plus the examples/ regression when present."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from comic_carousel import detect as d

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
W, H = 3300, 2550  # half-resolution letter scan


def page():
    return np.full((H, W), 255, np.uint8)


def rect(img, x0, y0, x1, y1, thickness=11):
    cv2.rectangle(img, (x0, y0), (x1, y1), 0, thickness)


def cross(img, x, y):
    cv2.line(img, (x - 60, y), (x + 60, y), 0, 5)
    cv2.line(img, (x, y - 60), (x, y + 60), 0, 5)


def boxes_of(det):
    return [(b.x, b.y, b.w, b.h) for b in det.boxes]


def close(box, expected, tol=W * 0.015):
    return all(abs(a - e) <= tol for a, e in zip(box, expected))


def test_clean_2x2_grid_in_reading_order():
    img = page()
    cells = [(400, 300, 1550, 1200), (1650, 300, 2800, 1200), (400, 1300, 1550, 2200), (1650, 1300, 2800, 2200)]
    for c in cells:
        rect(img, *c)
    det = d.detect(img)
    assert len(det.boxes) == 4 and det.confident
    for box, (x0, y0, x1, y1) in zip(boxes_of(det), cells):
        assert close(box, (x0, y0, x1 - x0, y1 - y0))


def test_border_with_three_gaps_is_still_found():
    img = page()
    rect(img, 400, 300, 1600, 1500)
    rect(img, 1800, 300, 2900, 1500)
    img[280:330, 700:850] = 255
    img[280:330, 1200:1350] = 255
    img[800:950, 380:430] = 255
    det = d.detect(img)
    assert len(det.boxes) == 2
    assert close(boxes_of(det)[0], (400, 300, 1200, 1200))


def test_shared_border_window_and_registration_marks():
    img = page()
    rect(img, 400, 600, 1600, 1800)
    rect(img, 1600, 600, 2900, 1800)  # shares the x=1600 edge
    rect(img, 550, 750, 850, 1050, 7)  # a window drawn inside panel 1
    for x, y in ((150, 150), (3150, 150), (150, 2400), (3150, 2400)):
        cross(img, x, y)
    det = d.detect(img)
    assert len(det.boxes) == 2 and det.confident
    assert close(boxes_of(det)[0], (400, 600, 1200, 1200))
    assert close(boxes_of(det)[1], (1600, 600, 1300, 1200))


def test_tilted_page_is_deskewed():
    img = page()
    rect(img, 400, 700, 1600, 1900)
    rect(img, 1750, 700, 2950, 1900)
    matrix = cv2.getRotationMatrix2D((W / 2, H / 2), 2.0, 1.0)
    tilted = cv2.warpAffine(img, matrix, (W, H), borderValue=255)
    det = d.detect(tilted)
    assert abs(det.angle + 2.0) < 0.3
    assert len(det.boxes) == 2
    assert close(boxes_of(det)[0], (400, 700, 1200, 1200), tol=W * 0.02)


@pytest.mark.parametrize("degrees", [6.0, 8.0, 10.0])
def test_more_rotated_pages_are_deskewed(degrees):
    img = page()
    rect(img, 400, 700, 1600, 1900)
    rect(img, 1750, 700, 2950, 1900)
    matrix = cv2.getRotationMatrix2D((W / 2, H / 2), degrees, 1.0)
    tilted = cv2.warpAffine(img, matrix, (W, H), borderValue=255)

    det = d.detect(tilted)

    assert abs(det.angle + degrees) < 0.4
    assert len(det.boxes) == 2
    assert close(boxes_of(det)[0], (400, 700, 1200, 1200), tol=W * 0.025)


def test_clear_panels_with_broken_corners_are_found():
    img = page()
    cells = [(400, 300, 1550, 1200), (1750, 300, 2900, 1200)]
    for cell in cells:
        rect(img, *cell)
        for x, y in ((cell[0], cell[1]), (cell[2], cell[1]),
                     (cell[0], cell[3]), (cell[2], cell[3])):
            img[y - 30:y + 31, x - 30:x + 31] = 255

    det = d.detect(img)

    assert len(det.boxes) == 2
    assert all(close(box, (x0, y0, x1 - x0, y1 - y0), tol=W * 0.025)
               for box, (x0, y0, x1, y1) in zip(boxes_of(det), cells))


def test_weak_interior_shapes_do_not_replace_a_strong_panel():
    outer = d.Box(100, 100, 1000, 1200, coverage=0.99, min_coverage=0.98)
    weak_top = d.Box(120, 120, 960, 700, coverage=0.88, min_coverage=0.51)
    weak_bottom = d.Box(120, 800, 960, 480, coverage=0.88, min_coverage=0.52)

    assert d.prune([outer, weak_top, weak_bottom]) == [outer]


def test_tilted_color_render_uses_the_detection_deskew():
    gray = page()
    rect(gray, 500, 500, 1800, 1800)
    color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    color[650:1650, 650:1650] = (25, 65, 230)
    matrix = cv2.getRotationMatrix2D((W / 2, H / 2), 2.0, 1.0)
    tilted_gray = cv2.warpAffine(gray, matrix, (W, H), borderValue=255)
    tilted_color = cv2.warpAffine(color, matrix, (W, H), borderValue=(255, 255, 255))

    det = d.detect(tilted_gray, tilted_color)
    assert abs(det.angle + 2.0) < 0.3
    assert len(det.boxes) == 1
    box = det.boxes[0]
    pixel = det.render_image[box.y + box.h // 2, box.x + box.w // 2]
    assert pixel[2] > 150 and pixel[0] < 100


def test_blank_page_is_not_confident():
    det = d.detect(page())
    assert det.boxes == [] and not det.confident and det.reasons == ["no panels found"]


def test_levels_stretch_for_grey_scan():
    img = page()
    rect(img, 400, 300, 1600, 1500)
    grey = (img * 0.6 + 80).astype(np.uint8)  # paper ~233, ink ~80
    fixed = d.normalize_levels(grey)
    assert fixed.max() == 255 and fixed.min() < 20


EXPECTED = {
    "brain tumor": 3,
    "why am i alive": 2,
    "the fish that bites loose dangling objects": 3,
    "LLM brain replacement": 2,
}


@pytest.mark.skipif(not EXAMPLES.is_dir(), reason="examples/ not present")
@pytest.mark.parametrize("name,count", EXPECTED.items())
def test_examples_regression(name, count):
    det = d.detect_file(EXAMPLES / name / f"{name} raw.jpg")
    assert len(det.boxes) == count, det.reasons
    assert det.confident, det.reasons
    if name in ("why am i alive", "LLM brain replacement"):
        assert 0.6 < abs(det.angle) < 1.5
    assert all(b.coverage >= 0.9 for b in det.boxes)


def test_box_contains_the_whole_drawn_border():
    """A rectangle assembled from corner junctions must not cut the outer half of the stroke."""
    img = page()
    thickness = 40
    rect(img, 500, 400, 2000, 1600, thickness)
    det = d.detect(img)
    assert len(det.boxes) == 1
    box = det.boxes[0]
    ink = img < 160
    inside = np.zeros_like(ink)
    inside[box.y:box.y + box.h, box.x:box.x + box.w] = True
    assert not (ink & ~inside).any(), "part of the drawn border falls outside the crop"


def test_bleed_never_crosses_a_tight_gutter():
    img = page()
    rect(img, 400, 500, 1500, 1700)
    rect(img, 1530, 500, 2630, 1700)  # 30 px gutter, tighter than the default bleed
    det = d.detect(img)
    assert len(det.boxes) == 2
    left, right = det.boxes
    assert left.x + left.w <= right.x, "panel crops overlap across the gutter"

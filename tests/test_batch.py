"""A whole folder of scans in, one carousel folder per scan out."""

from pathlib import Path

import cv2
import numpy as np

from comic_carousel.__main__ import main
from comic_carousel.pipeline import find_images


def scan(path: Path, panels: int) -> None:
    page = np.full((1275, 1650), 255, np.uint8)
    width = 1400 // panels
    for i in range(panels):
        x = 125 + i * width
        cv2.rectangle(page, (x, 300), (x + width - 40, 1000), 0, 10)
    assert cv2.imwrite(str(path), page)


def test_find_images_lists_only_top_level_scans(tmp_path):
    for name in ("b.jpg", "a.PNG", "notes.txt", ".hidden.png"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "old-carousel-001").mkdir()
    (tmp_path / "old-carousel-001" / "panel_01.png").write_bytes(b"x")
    assert [p.name for p in find_images(tmp_path)] == ["a.PNG", "b.jpg"]


def test_a_folder_becomes_one_carousel_folder_per_scan(tmp_path, capsys):
    scan(tmp_path / "first strip.png", 2)
    scan(tmp_path / "second strip.jpg", 3)

    assert main([str(tmp_path)]) == 0

    out = capsys.readouterr().out
    assert "first strip.png: 2 panels" in out and "second strip.jpg: 3 panels" in out
    first = tmp_path / "first strip-carousel-001"
    second = tmp_path / "second strip-carousel-001"
    assert sorted(f.name for f in first.iterdir()) == ["panel_01.png", "panel_02.png", "summary.png"]
    assert sorted(f.name for f in second.iterdir()) == ["panel_01.png", "panel_02.png", "panel_03.png", "summary.png"]

    assert main([str(tmp_path)]) == 0  # a second run never touches the first
    assert (tmp_path / "first strip-carousel-002").is_dir()
    assert len(list(first.iterdir())) == 3


def test_an_empty_folder_is_reported(tmp_path, capsys):
    assert main([str(tmp_path)]) == 2
    assert "no images" in capsys.readouterr().err

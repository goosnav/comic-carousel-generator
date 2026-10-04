from pathlib import Path

import cv2
import numpy as np

from comic_carousel.detect import Box, Detection
from comic_carousel.server import App, Session


def test_manual_boxes_control_export_and_reported_panel_count(tmp_path: Path):
    image = np.full((600, 800, 3), 255, np.uint8)
    source = tmp_path / "two-panels.png"
    assert cv2.imwrite(str(source), image)
    detection = Detection(
        boxes=[Box(0, 0, 400, 600), Box(400, 0, 400, 600)],
        angle=0.0,
        render_image=image,
        detection_image=cv2.cvtColor(image, cv2.COLOR_BGR2GRAY),
    )
    app = App()
    session = app.remember(Session(source, detection))

    result = app.act_export({
        "id": session.id,
        "boxes": [{"x": 100, "y": 100, "w": 300, "h": 300}],
        "layout": "stack",
        "parent": str(tmp_path),
    })

    assert result["panels"] == 1
    assert result["files"] == ["panel_01.png", "summary.png"]
    assert len(session.detection.boxes) == 1

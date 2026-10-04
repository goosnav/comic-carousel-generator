"""One entry point for GUI and CLI: scan path in, PNG folder out."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .detect import Box, Detection, detect_file
from .render import export


@dataclass
class Result:
    source: Path
    detection: Detection
    exported: Path | None = None
    files: list[Path] = field(default_factory=list)
    layout: str = ""

    @property
    def needs_review(self) -> bool:
        return not self.detection.confident

    @property
    def panel_count(self) -> int:
        return max(0, len(self.files) - 1) if self.exported else len(self.detection.boxes)

    def summary_line(self) -> str:
        n = self.panel_count
        panels = f"{n} panel{'s' if n != 1 else ''}"
        where = f"exported to {self.exported.name}" if self.exported else "not exported"
        flag = f" — needs a look: {'; '.join(self.detection.reasons)}" if self.needs_review else ""
        return f"{self.source.name}: {panels}, {where}{flag}"


def export_detection(source: Path, detection: Detection, boxes: list[Box] | None = None,
                     parent: Path | None = None, layout: str = "auto") -> Result:
    boxes = detection.boxes if boxes is None else boxes
    target, files, chosen = export(detection.render_image, boxes, parent or source.parent, layout, source.stem)
    return Result(source, detection, target, files, chosen)


def process(source: str | Path, parent: str | Path | None = None, layout: str = "auto",
            export_when_unsure: bool = True) -> Result:
    source = Path(source)
    detection = detect_file(source)
    if detection.confident or export_when_unsure:
        return export_detection(source, detection, None, Path(parent) if parent else None, layout)
    return Result(source, detection)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def find_images(folder: str | Path) -> list[Path]:
    """Every scan directly inside `folder`, in name order.

    ponytail: top level only. Output folders sit beside the scans, so a recursive walk
    would feed earlier carousel PNGs back in as new scans. Add recursion with an exclusion
    rule if scans ever live in nested folders.
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"That folder does not exist: {folder}")
    return sorted((p for p in folder.iterdir()
                   if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in IMAGE_EXTENSIONS),
                  key=lambda p: p.name.lower())

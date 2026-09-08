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

    def summary_line(self) -> str:
        n = len(self.detection.boxes)
        panels = f"{n} panel{'s' if n != 1 else ''}"
        where = f"exported to {self.exported.name}" if self.exported else "not exported"
        flag = f" — needs a look: {'; '.join(self.detection.reasons)}" if self.needs_review else ""
        return f"{self.source.name}: {panels}, {where}{flag}"


def export_detection(source: Path, detection: Detection, boxes: list[Box] | None = None,
                     parent: Path | None = None, layout: str = "auto") -> Result:
    boxes = detection.boxes if boxes is None else boxes
    target, files, chosen = export(detection.image, boxes, parent or source.parent, layout)
    return Result(source, detection, target, files, chosen)


def process(source: str | Path, parent: str | Path | None = None, layout: str = "auto",
            export_when_unsure: bool = True) -> Result:
    source = Path(source)
    detection = detect_file(source)
    if detection.confident or export_when_unsure:
        return export_detection(source, detection, None, Path(parent) if parent else None, layout)
    return Result(source, detection)

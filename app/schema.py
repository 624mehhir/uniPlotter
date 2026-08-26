from dataclasses import dataclass, field
from typing import List, TypedDict, Union


class Annotation(TypedDict):
    label: str
    shape_type: str  # "polygon" | "bbox"
    points: Union[List[List[float]], List[float]]
    # polygon -> [[x, y], [x, y], ...]
    # bbox    -> [x_min, y_min, width, height]


AnnotationList = List[Annotation]


@dataclass
class ParseResult:
    annotations: AnnotationList
    warnings: List[str] = field(default_factory=list)
    skipped_count: int = 0


class ParseError(Exception):
    """Raised when the file does not structurally match the selected format."""

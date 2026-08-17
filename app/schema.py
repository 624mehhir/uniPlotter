from typing import List, TypedDict, Union


class Annotation(TypedDict):
    label: str
    shape_type: str  # "polygon" | "bbox"
    points: Union[List[List[float]], List[float]]
    # polygon -> [[x, y], [x, y], ...]
    # bbox    -> [x_min, y_min, width, height]


AnnotationList = List[Annotation]

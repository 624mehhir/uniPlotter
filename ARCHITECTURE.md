# ARCHITECTURE.md

## Tech stack

- Backend: Python, FastAPI, served by uvicorn.
- Image processing: OpenCV (`cv2`) + NumPy.
- Frontend: one static HTML page with plain JS (no framework), served
  alongside the API.
- No database, no auth, no external services.

## Shared internal annotation schema (non-negotiable contract)

Every format parser must convert its input into a list of objects in this
exact shape, with coordinates already converted to absolute pixel values:

```python
{
    "label": str,               # human-readable class name
    "shape_type": "polygon" | "bbox",
    "points": list,
    # polygon -> [[x, y], [x, y], ...]
    # bbox    -> [x_min, y_min, width, height]
}
```

The single drawing function consumes only this schema. It must never branch
on which source format an annotation came from.

## Project structure

```
app/
  main.py              # FastAPI app, /plot endpoint
  schema.py            # shared annotation schema (dict shape / TypedDict)
  draw.py              # the one drawing function, cv2-based
  parsers/
    coco.py
    yolo.py
    voc.py
    labelme.py
    labelstudio.py
    cvat.py
  static/
    index.html          # upload form frontend
sample_data/
  <format>/
    image.jpg
    annotation.<ext>
```

Each parser file exports one function:
`parse(annotation_file(s), image_width, image_height) -> list[dict]`
matching the shared schema above.

## API contract

`POST /plot`
- multipart form fields: `image`, `annotation` (or `annotation` +
  `classes` for YOLO specifically), `format` (one of: `coco`, `yolo`,
  `voc`, `labelme`, `labelstudio`, `cvat`)
- Response: plotted image bytes, plus a way to convey warnings (decide once,
  in whichever milestone first implements `/plot`, and keep it consistent
  afterward — do not change the response shape in later milestones without
  flagging it).
- On malformed/unexpected input: return a clear error message describing
  what was expected, not a stack trace.

## Coloring

Generate a color per label deterministically (e.g., hash the label string
into a fixed palette of ~10 visually distinct colors), so the same label
always renders the same color within a run. No user-configurable colors in
V1.

## Dimension-mismatch handling

If the annotation file specifies image width/height and it doesn't match
the actual uploaded image's real dimensions, proceed with drawing anyway,
but surface a warning in the response. Never silently ignore a mismatch.

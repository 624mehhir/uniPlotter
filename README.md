# uniPlotter

Upload an image + its annotation file (COCO, YOLO, Pascal VOC, LabelMe,
Label Studio, or CVAT) and get back the image with bounding boxes/polygons
plotted on top — for visually verifying annotation exports.

Stateless: one image + one annotation file per request, no database, no
accounts. See `PRD.md` and `ARCHITECTURE.md` for the full product/technical
spec.

## Install

```
pip install -r requirements.txt
```

## Run

From the repo root:

```
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` in a browser for the upload form, or POST
directly to `/plot` (see `ARCHITECTURE.md` §4 for the request/response
shape). `GET /health` is a plain health check.

## Supported formats

| Format | Shapes | Key quirk |
|---|---|---|
| COCO | bbox + polygon | Single JSON file. RLE/crowd segmentation is skipped (unsupported), not drawn. |
| YOLO | bbox only | Needs two files: the `.txt` annotation *and* `classes.txt` — normalized 0–1 coordinates, no image dimensions in the file. |
| Pascal VOC | bbox only | XML, one file per image; gives corner coordinates (`xmin/ymin/xmax/ymax`), not width/height. |
| LabelMe | bbox + polygon | Single JSON, points already in absolute pixels; rectangle corners can be in either order. |
| Label Studio | bbox + polygon | Coordinates are **percentages** (0–100) of image size, not pixels; JSON-MIN export isn't supported. |
| CVAT (native XML) | bbox + polygon | Polygon points come as one `;`-separated string, not JSON; video/track exports aren't supported. |

Anything beyond bbox/polygon (masks, RLE, keypoints, etc.) is skipped and
reported in the response's `warnings`/`skipped_count`, never silently
dropped and never a crash.

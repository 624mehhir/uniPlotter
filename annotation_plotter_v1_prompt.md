# Project: Universal Annotation Plotter (V1)

## Goal

Build a small web application where a user uploads a raw image and an annotation
file, and the tool renders the annotations (polygons and bounding boxes only,
for this version) directly onto the image, then returns the plotted image for
download. This is used to visually verify that an annotation export is correct
— i.e., "does the exported data actually match what was drawn."

This is a personal/portfolio project. Prioritize clean, correct, well-organized
code over cleverness. Favor explicit code over "magic" auto-detection wherever
a decision can go either way.

## Tech stack

- **Backend:** Python, FastAPI
- **Image processing:** OpenCV (`cv2`) + NumPy
- **Frontend:** A single simple HTML page (plain HTML/CSS/JS, no framework
  needed) with a file upload form — image file input, annotation file input,
  a format selector dropdown, and a submit button. Keep the frontend minimal;
  the interesting logic is all backend.
- **No database.** This is a stateless upload-process-return tool — no need to
  persist uploads or results beyond the request lifecycle.

## Scope for V1 (important — read carefully)

**In scope:**
- Bounding boxes
- Polygons
- Support for exactly these 6 annotation formats (listed below)
- One image + one annotation file per request

**Explicitly OUT of scope for V1 — do not implement these yet:**
- Brush/mask-based annotations of any kind
- Batch/multi-image processing
- Any format not listed below
- Any auto-detection of format — the user always explicitly selects which
  format they're uploading via the dropdown; do not try to guess format from
  file content.
- Persistent storage, user accounts, or history of past uploads

## Architecture requirement: shared internal format

This is the most important design constraint. Do NOT write separate drawing
code per annotation format. Instead:

1. Write one **parser function per format**. Each parser takes the raw
   uploaded annotation file (plus the image's actual pixel dimensions, since
   some formats need it for coordinate conversion) and returns a list of
   annotation objects in this exact shared shape:

```python
{
    "label": str,              # class name, always resolved to a human-readable string
    "shape_type": "polygon" | "bbox",
    "points": list             # for "polygon": [[x, y], [x, y], ...] in absolute pixel coords
                                # for "bbox": [x_min, y_min, width, height] in absolute pixel coords
}
```

2. Write exactly ONE drawing function that consumes this shared shape and
   draws with cv2. It should never need to know which source format the
   annotation originally came from.

3. All coordinates must be normalized to **absolute pixel values** by the
   parser, before reaching the drawing function — several of these formats
   store normalized (0–1) coordinates, and the parser is responsible for
   converting them using the actual image dimensions.

## The 6 formats to support, with real structural examples

### 1. COCO

Single JSON file. Bounding boxes are `[x_min, y_min, width, height]` in
absolute pixels. Polygons (segmentation) are flat coordinate lists. Category
names are in a separate `categories` list, referenced by id — you must build
an id→name lookup.

```json
{
  "images": [
    {"id": 1, "file_name": "car.jpg", "width": 1920, "height": 1080}
  ],
  "annotations": [
    {
      "id": 1, "image_id": 1, "category_id": 2,
      "bbox": [461.4, 719.2, 26.0, 19.6],
      "segmentation": [[104.7, 506.4, 153.9, 512.0, 155.3, 520.4, 100.5, 518.3]]
    }
  ],
  "categories": [
    {"id": 1, "name": "scratch"},
    {"id": 2, "name": "dent"}
  ]
}
```

### 2. YOLO

**Not a single JSON file.** Two inputs required: a `.txt` file (one line per
annotation) and a separate class list (`classes.txt` or `data.yaml`, one class
name per line/entry, index = class id). Each line in the `.txt` is:

```
<class_id> <x_center> <y_center> <width> <height>
```

All four numeric values are **normalized 0–1** relative to image width/height
— the parser must multiply by actual image width/height to get pixels, then
convert center+width/height into `[x_min, y_min, width, height]` for the
shared format. YOLO only supports bounding boxes, never polygons.

Example `.txt` line: `1 0.245 0.667 0.014 0.018`
Example `classes.txt`:
```
scratch
dent
```

Adjust the upload UI for this one format: when YOLO is selected, show two
file inputs instead of one (annotation `.txt` + class list file).

### 3. Pascal VOC

XML file, one per image, bounding boxes only, absolute pixel coordinates.

```xml
<annotation>
  <filename>car.jpg</filename>
  <size>
    <width>1920</width>
    <height>1080</height>
  </size>
  <object>
    <name>dent</name>
    <bndbox>
      <xmin>461</xmin>
      <ymin>719</ymin>
      <xmax>487</xmax>
      <ymax>739</ymax>
    </bndbox>
  </object>
</annotation>
```

Note VOC gives `xmax`/`ymax`, not width/height — convert accordingly.

### 4. LabelMe

Single JSON file per image. Points are already absolute pixel `[x, y]` pairs.
Shape type is explicit per-shape (`polygon` or `rectangle`).

```json
{
  "imagePath": "car.jpg",
  "imageWidth": 1920,
  "imageHeight": 1080,
  "shapes": [
    {
      "label": "scratch",
      "shape_type": "polygon",
      "points": [[104.7, 506.4], [153.9, 512.0], [155.3, 520.4], [100.5, 518.3]]
    },
    {
      "label": "dent",
      "shape_type": "rectangle",
      "points": [[461.4, 719.2], [487.4, 738.8]]
    }
  ]
}
```

Note: LabelMe's `"rectangle"` gives two opposite corner points, not
x/y/w/h — convert accordingly.

### 5. Label Studio

JSON export, more deeply nested — a list of "tasks," each with a `result`
list. Coordinates here are **percentages (0–100), not 0–1 and not pixels** —
watch this conversion carefully, it's a common mistake. `original_width`/
`original_height` are given per-result for the conversion.

```json
[
  {
    "data": {"image": "car.jpg"},
    "annotations": [
      {
        "result": [
          {
            "type": "polygonlabels",
            "original_width": 1920,
            "original_height": 1080,
            "value": {
              "points": [[5.45, 46.9], [8.02, 47.4], [8.09, 48.2], [5.24, 48.0]],
              "polygonlabels": ["scratch"]
            }
          },
          {
            "type": "rectanglelabels",
            "original_width": 1920,
            "original_height": 1080,
            "value": {
              "x": 24.03, "y": 66.6, "width": 1.35, "height": 1.8,
              "rectanglelabels": ["dent"]
            }
          }
        ]
      }
    ]
  }
]
```

For rectangles here: `x`/`y` is the top-left corner as a percentage, and
`width`/`height` are also percentages — convert all four using
`original_width`/`original_height`, then multiply/divide as needed to land in
absolute pixels.

### 6. CVAT

CVAT can export in several formats from its UI (CVAT-XML, COCO, YOLO, etc.).
For this project, target **CVAT's native XML export** specifically (since
COCO/YOLO exported from CVAT are already covered by formats #1 and #2 above).
Structure:

```xml
<annotations>
  <image id="0" name="car.jpg" width="1920" height="1080">
    <polygon label="scratch" points="104.7,506.4;153.9,512.0;155.3,520.4;100.5,518.3"></polygon>
    <box label="dent" xtl="461.4" ytl="719.2" xbr="487.4" ybr="738.8"></box>
  </image>
</annotations>
```

Note the polygon `points` attribute is a single string with `x,y` pairs
separated by `;` — needs string parsing, not JSON parsing.

## Drawing requirements

- Each distinct label/class gets a consistent, distinguishable color. Since
  the set of possible class names isn't known in advance (unlike a fixed
  damage-type list), generate colors programmatically — e.g., hash the label
  string to pick from a fixed palette of ~10 visually distinct colors, so the
  same label always gets the same color within one run.
- Polygons: draw the outline plus a semi-transparent fill (~25% opacity) so
  overlapping shapes stay readable.
- Bounding boxes: draw as an outlined rectangle, no fill.
- Draw the label text near each shape (e.g., near the first point for
  polygons, near the top-left corner for boxes).
- Before drawing, compare the annotation file's recorded image width/height
  (where available) against the actual uploaded image's real dimensions. If
  they don't match, do not error out — proceed with drawing, but include a
  warning in the API response noting the mismatch, since this is a common
  source of misaligned annotations and the user should be told rather than
  silently shown a wrong result.

## API design

- `POST /plot` — multipart form accepting: image file, annotation file(s)
  (plural only for YOLO's two-file case), and a `format` field (one of:
  `coco`, `yolo`, `voc`, `labelme`, `labelstudio`, `cvat`).
- Response: the plotted image (as image bytes, `image/jpeg` or `image/png`),
  plus a way to surface any warnings (e.g., a custom header, or an alternate
  JSON response mode with base64 image + warnings list — pick whichever is
  simpler to wire up with the frontend you build).
- Return clear error messages (not stack traces) if the annotation file
  doesn't match the expected structure for the selected format — e.g., "This
  doesn't look like valid COCO JSON — missing 'annotations' key."

## Deliverables

1. FastAPI backend with the 6 parser functions, the shared drawing function,
   and the `/plot` endpoint, organized into separate files (e.g., one file
   per format parser, not one giant script).
2. A minimal HTML/JS frontend page served by the same app (or a static file)
   with the upload form described above.
3. A short README explaining how to run it locally (`pip install` steps,
   `uvicorn` run command) and a one-line description of each supported
   format's quirks, for future reference.
4. Basic input validation and error handling as described above — this
   should not crash on malformed input, it should return a readable error.

## Testing expectation

For each of the 6 formats, provide (or generate) one small sample annotation
file with 2–3 shapes (mixing at least one polygon and one bbox where the
format supports both) so the implementation can be verified end-to-end before
considering V1 done.

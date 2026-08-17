# MILESTONES.md

Read only the section for the milestone you're currently working on. Each
milestone is self-contained and includes everything needed for that session
— you should not need to read other milestones' sections.

---

## M1 — Project skeleton (no parsers yet)

**Goal:** A running FastAPI server with the project structure in place, but
no format parsing logic yet.

**Build:**
- Folder structure exactly as in `ARCHITECTURE.md`.
- `main.py` with a `GET /` health check returning a simple JSON message.
- `schema.py` defining the shared annotation shape (as a `TypedDict` or
  plain dict convention — keep it simple).
- `draw.py` with the single drawing function, fully implemented:
  - takes an image (numpy array) and a list of shared-schema annotations
  - draws polygons (outline + ~25% opacity fill) and bboxes (outline only)
  - deterministic per-label coloring (hash label string into a fixed
    ~10-color palette)
  - draws the label text near each shape
- `parsers/` folder created but empty (no parser files yet).
- No `/plot` endpoint yet — that comes in M2 alongside the first parser.

**Do not build in this session:** any parser, the `/plot` endpoint, the
frontend, YOLO's two-file handling, or dimension-mismatch logic.

**Done when:** `uvicorn main:app --reload` runs with no errors, and
`draw.py`'s function can be manually tested (e.g., a throwaway script) to
confirm it draws a polygon and a bbox correctly on a test image.

---

## M2 — COCO parser + working /plot endpoint

**Goal:** First end-to-end working path: COCO annotation in, plotted image
out. This milestone also defines the `/plot` endpoint shape that all later
formats will reuse — get this right, since M3+ will not revisit it.

**Format spec — COCO:**
Single JSON file. Bboxes are `[x_min, y_min, width, height]` in absolute
pixels already. Polygons (`segmentation`) are flat coordinate lists.
Category names live in a separate `categories` list, referenced by id.

```json
{
  "images": [{"id": 1, "file_name": "car.jpg", "width": 1920, "height": 1080}],
  "annotations": [
    {"id": 1, "image_id": 1, "category_id": 2,
     "bbox": [461.4, 719.2, 26.0, 19.6],
     "segmentation": [[104.7, 506.4, 153.9, 512.0, 155.3, 520.4, 100.5, 518.3]]}
  ],
  "categories": [{"id": 1, "name": "scratch"}, {"id": 2, "name": "dent"}]
}
```

**Build:**
- `parsers/coco.py` implementing `parse(...)` per the contract in
  `ARCHITECTURE.md`, returning the shared schema.
- `POST /plot` endpoint accepting `image`, `annotation`, `format` fields.
  For this milestone, `format` will only ever be `"coco"` — but write the
  endpoint so adding more formats later is a matter of adding `elif`
  branches to a parser lookup, not restructuring the endpoint.
- Dimension-mismatch check: compare COCO's `images[].width/height` against
  the real uploaded image, include a warning in the response if mismatched.
- Decide and implement the response shape (image bytes vs. JSON+base64) —
  document your choice in a one-line comment, since later milestones must
  match it exactly.
- Add one sample COCO annotation file + matching image under
  `sample_data/coco/`.

**Do not build in this session:** any other format, the frontend, YOLO's
multi-file handling.

**Done when:** a COCO sample file + image, submitted via the FastAPI
`/docs` page, returns a correctly plotted image with a visible polygon and
a visible bbox in the right place.

---

## M3 — LabelMe + Pascal VOC parsers

**Goal:** Add two more formats using the endpoint/pattern from M2 — no
endpoint restructuring should be needed, only new parser files plus one
new `elif` branch each.

**Format spec — LabelMe:**
Single JSON file, points already absolute pixels. Shape type is explicit.

```json
{
  "imagePath": "car.jpg", "imageWidth": 1920, "imageHeight": 1080,
  "shapes": [
    {"label": "scratch", "shape_type": "polygon",
     "points": [[104.7, 506.4], [153.9, 512.0], [155.3, 520.4], [100.5, 518.3]]},
    {"label": "dent", "shape_type": "rectangle",
     "points": [[461.4, 719.2], [487.4, 738.8]]}
  ]
}
```
Note: `"rectangle"` gives two opposite corner points, not x/y/w/h — convert.

**Format spec — Pascal VOC:**
XML, one file per image, bboxes only, absolute pixels. Gives
xmin/ymin/xmax/ymax, not width/height — convert accordingly.

```xml
<annotation>
  <filename>car.jpg</filename>
  <size><width>1920</width><height>1080</height></size>
  <object>
    <name>dent</name>
    <bndbox><xmin>461</xmin><ymin>719</ymin><xmax>487</xmax><ymax>739</ymax></bndbox>
  </object>
</annotation>
```

**Build:**
- `parsers/labelme.py`, `parsers/voc.py`.
- Wire both into `/plot`'s format lookup.
- One sample file + image per format under `sample_data/labelme/` and
  `sample_data/voc/`.

**Do not build in this session:** Label Studio, CVAT, YOLO, or the
frontend.

**Done when:** both sample sets, submitted via `/docs`, plot correctly, and
the existing COCO path from M2 still works unchanged.

---

## M4 — Label Studio + CVAT parsers

**Goal:** Add two more formats. Label Studio's coordinate conversion is the
trickiest thing in this whole project — read it carefully.

**Format spec — Label Studio:**
JSON export, list of tasks, each with a `result` list. Coordinates are
**percentages (0–100), not 0–1 and not pixels.** `original_width`/
`original_height` are given per-result for conversion.

```json
[{"data": {"image": "car.jpg"},
  "annotations": [{"result": [
    {"type": "polygonlabels", "original_width": 1920, "original_height": 1080,
     "value": {"points": [[5.45, 46.9], [8.02, 47.4], [8.09, 48.2], [5.24, 48.0]],
               "polygonlabels": ["scratch"]}},
    {"type": "rectanglelabels", "original_width": 1920, "original_height": 1080,
     "value": {"x": 24.03, "y": 66.6, "width": 1.35, "height": 1.8,
               "rectanglelabels": ["dent"]}}
  ]}]}]
```
For rectangles: `x`/`y`/`width`/`height` are all percentages of image
dimensions — convert all four to pixels, don't assume `x`/`y` are already
absolute.

**Format spec — CVAT (native XML export):**
```xml
<annotations>
  <image id="0" name="car.jpg" width="1920" height="1080">
    <polygon label="scratch" points="104.7,506.4;153.9,512.0;155.3,520.4;100.5,518.3"></polygon>
    <box label="dent" xtl="461.4" ytl="719.2" xbr="487.4" ybr="738.8"></box>
  </image>
</annotations>
```
Note `points` is one string, `;`-separated `x,y` pairs — string parsing,
not JSON.

**Build:**
- `parsers/labelstudio.py`, `parsers/cvat.py`.
- Wire both into `/plot`'s format lookup.
- Sample file + image per format under `sample_data/labelstudio/` and
  `sample_data/cvat/`.

**Do not build in this session:** YOLO, the frontend.

**Done when:** both sample sets plot correctly, and all previously working
formats (COCO, LabelMe, VOC) still work unchanged.

---

## M5 — YOLO parser (two-file case)

**Goal:** Add YOLO, which needs an API/endpoint adjustment since it's not
a single annotation file.

**Format spec — YOLO:**
A `.txt` file (one line per annotation) plus a separate class list file
(`classes.txt`, one name per line, index = class id). Line format:
`<class_id> <x_center> <y_center> <width> <height>` — all four values
normalized 0–1 relative to image size. Bboxes only, no polygons.

Example line: `1 0.245 0.667 0.014 0.018`
Example `classes.txt`:
```
scratch
dent
```

**Build:**
- Adjust `POST /plot` to accept an optional second file field (e.g.,
  `classes`) — only required/used when `format == "yolo"`. Keep the
  existing single-`annotation`-file path for all other formats unchanged.
- `parsers/yolo.py`, converting normalized center/width/height into
  `[x_min, y_min, width, height]` in absolute pixels using the real image
  dimensions.
- Sample `.txt` + `classes.txt` + image under `sample_data/yolo/`.

**Do not build in this session:** the frontend.

**Done when:** the YOLO sample, submitted via `/docs` with both files,
plots correctly, and all five previously working formats still work
unchanged.

---

## M6 — Frontend

**Goal:** One static HTML page wired to the now-complete `/plot` endpoint,
covering all 6 formats.

**Build:**
- `static/index.html`: image file input, annotation file input, a second
  conditional file input for YOLO's class list (shown only when "yolo" is
  selected in the format dropdown), a format `<select>` dropdown listing
  all 6 formats, a submit button.
- Plain JS `fetch()` call to `POST /plot`, displaying the returned image
  and any warning message on the page.
- No styling framework — basic readable CSS is enough.

**Do not build in this session:** any new parser, any backend logic
changes beyond what's needed to serve the static file.

**Done when:** all 6 formats can be tested end-to-end through the actual
web page, not just `/docs`.

---

## M7 — Polish pass

**Goal:** Tighten error handling and write the README, touching no new
features.

**Build:**
- Review every parser: malformed/unexpected input should return a clear
  error message (e.g., "This doesn't look like valid COCO JSON — missing
  'annotations' key"), never a raw stack trace.
- `README.md`: install steps, run command, one line per format noting its
  quirk (e.g., "YOLO needs a separate class list file"; "Label Studio uses
  percentage coordinates, not normalized 0–1").

**Do not build in this session:** any new feature, format, or scope not
already covered by M1–M6.

**Done when:** deliberately uploading a broken/mismatched file for each
format produces a readable error, not a crash.

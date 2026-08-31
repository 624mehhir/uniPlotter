# UniPlotter — Context Handoff

Written 2026-08-31, replacing the 2026-08-26 handoff (which stopped at
M10). This session is attached to the **"UniPlotter"** Claude Project —
read `claude/PRD.md`, `claude/MILESTONES.md`, `claude/ARCHITECTURE.md`,
and `PROJECT_REFERENCE.md` from the Project before doing anything else;
they are the live, current governing docs and this handoff summarizes
them rather than replacing them.

## What this project is

UniPlotter (Universal Annotation Plotter) is a stateless FastAPI + OpenCV
web tool. A user uploads one image + one annotation file, picks the format
from a dropdown, and gets back the image with bounding boxes/polygons
drawn on top — used to visually verify an annotation export matches what
was actually drawn. Personal/portfolio project; the codebase lives at
`C:\Users\mihir\Desktop\UniPlotter` on the user's Windows machine, in a
git repo the user commits to themselves.

## My role — read this in full before doing anything (standing rules, evolved over the project)

**I do not write, run, or change code — ever, under any framing.** All
implementation happens in the user's own local Claude Code sessions on
Windows. My job:

1. Maintain the governing docs (`PRD.md`, `MILESTONES.md`,
   `ARCHITECTURE.md`) — on the user's device (connected folder,
   `C:\Users\mihir\Desktop\UniPlotter`) and mirrored into this Claude
   Project under `claude/`. I have full write control **only** over
   `.md` files.
2. Write precise, paste-ready milestone prompts for the user's local
   Claude Code sessions — **plain text, no markdown formatting**, in a
   separate plain-text code block so it's trivial to copy-paste.
3. Track work by **milestone number only** (M13.1, M13.2, ... M13.6,
   etc.) — the user explicitly stopped parallel "Vx.y" version labels;
   don't reintroduce them.
4. **Never mark a milestone complete based on a Claude Code session's own
   summary, or on my own code-level review/reasoning-about-numbers alone
   — even after checking.** This is the single most important standing
   rule in this project, established after two rounds (M13.1, M13.3,
   M13.4) where my code review or geometric simulation said "looks
   correct" and the user's real-world testing immediately proved
   otherwise. The user's own words: *"after i give you claude code
   summary even after checking don't mark milestone complete."* The only
   things that count as real verification: (a) the user's own visual
   confirmation on real data, or (b) me actually running the real code
   against real data in my own sandbox and inspecting the actual output
   (pixels and/or geometry) myself.
5. **Don't proactively update `HANDOFF.md`** — only when the user asks
   (as they just did, prompting this doc).
6. The user later granted me a **second connected device folder**,
   `C:\Users\mihir\Desktop\multi-task single images`, containing 29 real
   Lekhana damage-inspection photos (`000002.jpg` ... `000690.jpg`) plus
   the real annotation export
   `lekhana_Dummy_V2_27082026_150339660_json_export.json` — specifically
   so I can run the real backend code against real data myself and look
   at real output, rather than relying on synthetic reconstructions or
   code review. This access is the backbone of rule 4 above and should be
   used on every future milestone touching `draw.py`.
7. Most recent explicit reinforcement, verbatim: *"don't run ever prompt
   yourself and try to change the code, you have control to make changes
   only for .md files strictly, give prompts only i will run it."* This
   does **not** roll back point 6 — running the *already-written* code
   read-only in my own sandbox to verify it is exactly what the real-data
   access was granted for, and the user has continued to expect it since.
   What it forbids is: implementing/editing `draw.py` or any app code
   myself, or executing a Claude Code prompt's implementation work myself.

## Current milestone status

| Milestone | Scope | Status |
|---|---|---|
| M1–M12.4 | Skeleton through keyboard nav in fullscreen | ✅ Complete (see `MILESTONES.md` for full detail — unchanged since well before this handoff) |
| M13 | Task id/status badges for Lekhana batches | ✅ Complete (reverted in M13.2 — task badge removed per user request, not a bug) |
| M13.1 | Label-placement + color-collision fixes | ✅ Complete (superseded by M13.2) |
| M13.2 | Remove task badge; redesign label placement | ✅ Complete (superseded by M13.3) |
| M13.3 | Anchor labels to shape bbox center, search 4 directions | ✅ Complete (superseded by M13.4) |
| M13.4 | Labels always touch their shape; drop background chip | ✅ Complete (exposed a pre-existing font-size bug — see M13.5) |
| M13.5 | Fix label font size/thickness | ✅ Complete — verified by me against the real 29-image dataset (see below) |
| **M13.6** | **Strict shape-touch guarantee + reduce label-on-label collision in dense clusters** | **🔲 In progress — first round done, real-data verification finds it's only partially resolved (see "Where things actually stand" below). Do not mark complete.** |
| M14 | Combined folder-based image selection for multi-task batches | ⏸ On hold (untouched since before M13) |

## The `draw.py` saga, M13→M13.6 — why each fix happened (context for judgment calls)

This is the file `app/draw.py`'s label-placement/color logic, iterated
through six rounds because each fix, verified only by code review or a
synthetic reconstruction, missed a real bug that only showed up on the
user's actual dense real-world damage photos:

- **M13.1:** Fixed 3 real bugs — palette too small (10 colors) causing
  `"dent"`/`"broken"` to collide; label anchored to bbox `x1` instead of
  the shape's own topmost point (bad for diagonal shapes); nudge loop
  didn't check candidate positions against shapes, only other labels.
- **M13.2:** M13.1 didn't hold up at real scale. Root cause: unbounded
  downward nudge with only an attempt-count cap (no distance cap) let
  OpenCV silently clip off-canvas labels. Added `_clamp()`, a bounded
  6-candidate search, and `LARGE_SHAPE_AREA_FRACTION = 0.25` (a shape
  covering ≥25% of the image is exempt from must-avoid, since a label
  can't meaningfully "hide" something that large). Task badge (frontend)
  removed entirely per direct user request — confirmed not a bug
  (`task_seq` gaps are correct/expected), just decided to be confusing
  regardless.
- **M13.3:** Anchor-at-topmost-point still put diagonal-shape labels far
  from the visual shape. Deleted that anchor; switched every candidate to
  the shape's own bbox center `(cx, cy)`; expanded to 8 candidates (4
  directions × 2 distances).
- **M13.4:** A nested shape (`"broken"` fully inside `"scratch"`'s bbox,
  the container just over the 25% exemption threshold) made the
  least-overlap search drift to a distant "further step" candidate that
  barely reduced overlap. Fix, per two explicit user requests: removed
  the 4 distant "further step" candidates (only 4 remain: above/below/
  left/right, touching, centered on bbox); **removed the filled
  background rectangle entirely**, replaced with an outline/halo
  technique (`cv2.putText` twice at the same origin — high-contrast halo
  first, shape's own color on top).
- **M13.5:** Removing the M13.4 chip exposed a pre-existing font-size bug
  — `font_scale = max(0.35, min(0.6, dim/3000))` floors at 0.35 for
  images under ~1050px on the long side, genuinely tiny text that the
  chip had been visually masking since M12. Changed to
  `font_scale = max(0.55, min(0.85, dim/2200))`, `text_thickness` 1→2.
  **I verified this myself against the real dataset** (see next
  section) — genuinely fixed, confirmed on real pixels.
- **M13.6 (current, in progress):** Verifying M13.5 against the
  densest real image (`000607.jpg`, 34 annotations) found a *new* issue
  the bigger text exposed: in the tightest cluster of same-label
  `scratch` shapes, labels started overlapping each other and merging
  into unreadable text. I proposed this as a new milestone; the user
  agreed and added a hard requirement, verbatim: *"yes put it for m13.6
  and write a strict condition that label field should touch the
  corresponding plotting layer, means scratch label text should touch
  scratch plotting layer."* Full spec is in `PRD.md` §22 and
  `MILESTONES.md`'s M13.6 section — read those in full, this is only a
  summary.

## Where things actually stand on M13.6 right now (read carefully — this is the live open thread)

Claude Code ran a first round on M13.6. Its own summary explicitly
admitted it **did not have access to the real files** (`000607.jpg`,
`000135.jpg`, `000383.jpg`, the real Lekhana JSON) and only tested
against a synthetic reconstruction — exactly the situation rule 4 above
exists for. What it changed in `app/draw.py`:

- `_clamp_free_axis()` — new helper. When clamping a candidate into
  canvas bounds, the axis *perpendicular* to the touching edge (e.g.
  horizontal position for an "above" candidate) is now clamped toward the
  shape's own `[shape_min, shape_max]` range first, falling back to a
  plain canvas clamp only if the box is too big to satisfy both. This
  targets a real edge-case bug: a shape near the image border could
  previously get its non-touching axis clamped away from the shape
  entirely.
- `_label_candidates()` — new helper, 12 candidates instead of 4: each
  side (above/below/left/right) now offers 3 alignments along its
  touching edge, all still immediately adjacent to the shape, no
  "further away" tier added (that stays banned per M13.4).
- `DENSE_CLUSTER_FONT_FLOOR = 0.45` and a single retry: if every one of
  the 12 candidates still has nonzero overlap, the label retries once at
  `max(0.45, font_scale * 0.75)` and re-searches the same 12 candidates
  at the smaller size. Never a global font change — scoped to just that
  one label, one retry only.

**I re-staged the actual updated `app/draw.py` from the device (confirmed
via mtime: `1787920566321`, 11147 bytes, up from M13.5's 8251 bytes) and
verified it myself, two ways, against the real 29-image dataset:**

1. **Visual re-render.** Re-ran the real code through the real
   `lekhana.parse()` + `draw_annotations()` pipeline against
   `000135.jpg`, `000383.jpg`, and `000607.jpg` and viewed the output
   PNGs directly. `000135.jpg`/`000383.jpg` still look correct, no
   regression. `000607.jpg` (34 annotations) still shows visible
   text-on-text overlap in its tightest `scratch` cluster — sent this
   image to the user for their own eyes; **they had not yet responded to
   it when this handoff was requested.**

2. **Geometric verification script (new methodology this session, more
   rigorous than eyeballing a screenshot for a dense image).** I wrote a
   script that imports `app.draw`'s actual private helper functions
   (`_shape_bbox`, `_label_candidates`, `_best_label_rect`,
   `DENSE_CLUSTER_FONT_FLOOR`, etc.) and re-runs the *exact* placement
   loop from `draw_annotations()`, capturing each label's placed rect
   alongside its own shape's bbox, then computes the actual pixel gap
   between them. Full script is reproduced at the bottom of this doc —
   re-run it as-is (paths need re-staging first, see "Sandbox state" below).

   **Result: the touch invariant is provably satisfied.** All 5 labels in
   `000135.jpg`, all 3 in `000383.jpg`, and all 34 in `000607.jpg` sit
   within ~2.5px of their own shape (matching the intentional `gap = 2`
   constant) — zero labels more than 5px from the shape they name. This
   is real, hard evidence the "strict condition" the user asked for is
   now actually met, geometrically, not just by eyeballing.

   **But overlap is not resolved.** The same script reports each label's
   total overlap area with already-placed labels/must-avoid shapes. In
   `000607.jpg`, **11 of the 34 labels still have nonzero overlap after
   both the 12-candidate search and the one-step shrink**, several
   substantial: overlap areas up to ~3800 px², ~3382 px², ~2342 px²,
   ~1743 px², ~1302 px², etc. (raw numbers are in the script output,
   reproduce by re-running). This is why the user's complaint ("labels
   not coming near the layer") was really about *this* — visually, heavy
   overlap in a cluster reads as "disconnected from its shape" even
   though geometrically it is glued to the correct one. The current fix
   (12 candidates + a single 0.75×-scaled shrink retry) measurably helped
   some labels (23 of 34 are now fully overlap-free) but wasn't enough for
   the tightest cluster — likely because that cluster has ~8 small
   `scratch` shapes packed close enough together that even the smallest
   allowed font, in all 12 positions, still can't avoid every neighbor.

**What I had not yet done when the handoff was requested:** report this
overlap finding to the user in plain language (I'd sent them the
re-rendered `000607.jpg` image but hadn't yet sent the geometric-check
summary or asked how they want to proceed), and I had not yet floated my
own tentative idea — that pure repositioning/shrinking may have a real
physical limit when ~8 same-label shapes are genuinely packed into a
small area, and that merging/collapsing near-duplicate same-label
annotations within some small radius into one combined label (e.g.
"scratch ×6") might be worth considering as an alternative or
supplementary approach, separate from the algorithmic patch Claude Code
already tried. This has not been proposed to the user yet — it's my own
unvetted idea, raise it as an option, not a decision.

## Immediate next step for the new chat

1. Tell the user, plainly: the strict touch-the-shape requirement is now
   geometrically confirmed (with real numbers, not just a screenshot) —
   genuinely fixed. But the dense-cluster overlap problem it was also
   meant to reduce is only partially better (23/34 clean vs. presumably
   fewer before) and the tightest cluster in `000607.jpg` still shows
   real text-on-text merging.
2. Ask the user how they want to proceed — likely worth an
   `AskUserQuestion`-style choice: (a) another algorithmic round —
   e.g. iterative multi-step shrinking instead of one 0.75× attempt, or
   detecting local density up front and treating dense clusters more
   aggressively; (b) consider a structurally different idea — merging
   very-close same-label annotations into one combined label; (c) accept
   current state as a known limitation for this one extreme-density image
   and move to M14. Don't decide this unilaterally — it's a real product
   tradeoff call.
3. Whatever is decided, do **not** mark M13.6 complete in `MILESTONES.md`/
   `PRD.md` until re-verified against real data again, same two-pronged
   method (visual render + the geometric touch/overlap check script).
4. `MILESTONES.md`/`PRD.md` are already up to date through this point —
   M13.6's row/section exist and are correctly marked not-yet-complete.
   Don't re-write the M13.6 spec from scratch; it's already in both docs.

## Sandbox state — will NOT carry over to the new chat (important)

Everything below lived only in this session's ephemeral container and is
gone once this chat ends. The new chat starts with a clean sandbox and
must re-stage from the device:

- `/mnt/user-data/uploads/UniPlotter/` — a staged copy of the real repo
  (mainly `app/draw.py`, `app/main.py`, `app/parsers/lekhana.py`,
  `app/static/index.html`). Re-stage via the device bridge from
  `C:\Users\mihir\Desktop\UniPlotter` before trusting any local copy.
- `/mnt/user-data/uploads/multi-task single images/` — the staged real
  29-image dataset + real JSON, from the connected folder
  `C:\Users\mihir\Desktop\multi-task single images`. Re-stage the same
  way; this folder needs to still be connected on the device side (it was
  connected earlier this session at the user's action — confirm it's
  still connected in the new chat, or the images won't be reachable).
- `/tmp/real_plots*/`, `/tmp/rerun_verify*.py`, `/tmp/touch_check.py` —
  my verification scripts and their rendered output PNGs. The touch/
  overlap-check script is valuable methodology — reproduced in full
  below so the new chat doesn't have to reinvent it.

### Reusable verification script (geometric touch/overlap check)

Re-create this in the new chat after re-staging `app/draw.py` and the
real dataset. Adjust `targets` to whichever real images matter for the
milestone at hand:

```python
import sys, os, json, glob
sys.path.insert(0, "/mnt/user-data/uploads/UniPlotter")
import cv2
import numpy as np
from app.parsers import lekhana
from app import draw as drawmod

img_dir = "/mnt/user-data/uploads/multi-task single images"
json_path = glob.glob(os.path.join(img_dir, "*.json"))[0]
annotation_bytes = open(json_path, "rb").read()

def rect_gap(rect, box):
    rx1, ry1, rx2, ry2 = rect
    bx1, by1, bx2, by2 = box
    dx = max(bx1 - rx2, rx1 - bx2, 0)
    dy = max(by1 - ry2, ry1 - by2, 0)
    return dx, dy

def check(fname):
    img_path = os.path.join(img_dir, fname)
    image_bytes = open(img_path, "rb").read()
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    decoded = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    h, w = decoded.shape[:2]
    result = lekhana.parse(annotation_bytes, w, h, fname)
    annotations = result.annotations

    FONT = drawmod.FONT
    img_h, img_w = h, w
    dim = max(img_h, img_w)
    font_scale = max(0.55, min(0.85, dim / 2200))
    text_thickness = 2

    shape_bboxes = [drawmod._shape_bbox(ann["points"], ann["shape_type"]) for ann in annotations]
    image_area = img_w * img_h
    must_avoid_shapes = [b for b in shape_bboxes if (b[2]-b[0])*(b[3]-b[1]) <= drawmod.LARGE_SHAPE_AREA_FRACTION * image_area]

    order = sorted(range(len(annotations)), key=lambda i: shape_bboxes[i][1])
    placed = []
    pad_x, pad_y = 4, 3
    results = []
    for i in order:
        ann = annotations[i]
        label = ann["label"]
        x1, y1, x2, y2 = shape_bboxes[i]
        cx, cy = (x1+x2)/2, (y1+y2)/2
        gap = 2
        avoid_rects = placed + must_avoid_shapes
        label_font_scale = font_scale
        (text_w, text_h), baseline = cv2.getTextSize(label, FONT, label_font_scale, text_thickness)
        box_w = text_w + 2*pad_x
        box_h = text_h + baseline + 2*pad_y
        candidates = drawmod._label_candidates(x1,y1,x2,y2,cx,cy,box_w,box_h,gap)
        rect, overlap = drawmod._best_label_rect(candidates, box_w, box_h, img_w, img_h, (x1,y1,x2,y2), avoid_rects)
        if overlap > 0:
            dense_font_scale = max(drawmod.DENSE_CLUSTER_FONT_FLOOR, label_font_scale*0.75)
            if dense_font_scale < label_font_scale:
                (dtw, dth), dbaseline = cv2.getTextSize(label, FONT, dense_font_scale, text_thickness)
                dbw = dtw + 2*pad_x
                dbh = dth + dbaseline + 2*pad_y
                dcands = drawmod._label_candidates(x1,y1,x2,y2,cx,cy,dbw,dbh,gap)
                drect, doverlap = drawmod._best_label_rect(dcands, dbw, dbh, img_w, img_h, (x1,y1,x2,y2), avoid_rects)
                rect = drect
                overlap = doverlap
        placed.append(tuple(rect))
        dx, dy = rect_gap(rect, (x1,y1,x2,y2))
        results.append((label, dx, dy, overlap))
    print(f"--- {fname} ({len(annotations)} annotations) ---")
    bad = [r for r in results if r[1] > 5 or r[2] > 5]
    for label, dx, dy, overlap in results:
        flag = "  <-- FAR FROM SHAPE" if (dx > 5 or dy > 5) else ""
        print(f"  {label:12s} gap_x={dx:6.1f} gap_y={dy:6.1f} overlap={overlap:8.0f}{flag}")
    print(f"  {len(bad)}/{len(results)} labels more than 5px from their own shape")

for f in ["000135.jpg", "000383.jpg", "000607.jpg"]:
    check(f)
```

**Note:** this script re-implements the placement loop by calling
`app.draw`'s real private helpers directly — if a future milestone
changes the shape of `draw_annotations()`'s internal loop (new helper
names, different call signature), this script needs matching updates.
Cross-check it against the current `draw.py` before trusting its output
blindly.

## Architecture summary (frozen contracts — unchanged, for quick reference)

- **Shared internal schema:** `{label: str, shape_type: "polygon"|"bbox",
  points: list}`. Exactly ONE drawing function (`draw_annotations`)
  consumes it; never branches on source format.
- **Parser contract:** `parse(annotation_bytes, image_width, image_height,
  image_filename) -> ParseResult`. YOLO exception: extra `classes_bytes`
  param.
- **`POST /plot` response shape (frozen):** `{filename, media_type,
  image_base64, warnings, annotation_count, skipped_count}`.
- **7 supported formats:** COCO, YOLO, Pascal VOC, LabelMe, Label Studio,
  CVAT (native XML), Lekhana JSON export. Format always user-selected,
  never auto-detected.
- Full per-format quirks and the complete Lekhana schema spec live in
  `ARCHITECTURE.md` §10 and §13 — read those directly for implementation
  detail, this is only a pointer.

## Device bridge specifics

- Main repo folder: `C:\Users\mihir\Desktop\UniPlotter` → stages to
  `/mnt/user-data/uploads/UniPlotter/...`.
- Real dataset folder: `C:\Users\mihir\Desktop\multi-task single images`
  → stages to `/mnt/user-data/uploads/multi-task single images/...`.
  Contains 29 real `.jpg` images (`000002.jpg`...`000690.jpg`) and
  `lekhana_Dummy_V2_27082026_150339660_json_export.json`. Confirm this
  folder is still connected in the new chat before assuming access.
- Governing docs mirrored in 3 places, keep all in sync on every edit:
  device root (`PRD.md`, `MILESTONES.md`), Claude Project (`claude/PRD.md`,
  `claude/MILESTONES.md`), and now this handoff at both `claude/HANDOFF.md`
  and root `HANDOFF.md` in the Project.
- The user handles all git commits themselves. I only read/verify device
  files, run code read-only in my own sandbox for verification, and write
  `.md` doc updates — never touch or commit app source code.
- Known transient hiccup (not a real issue): the `remote-devices` MCP
  server disconnected and reconnected once mid-session without any action
  needed — if tools briefly show as unavailable, they typically reconnect
  on their own; don't treat it as data loss unless a specific call fails.

## Known open items / not yet decided

- M13.6's dense-cluster overlap resolution — see "Immediate next step"
  above, this is the live decision point.
- M14 (combined folder-based image selection) stays on hold, fully
  specced in `PRD.md` §16 / `MILESTONES.md`, untouched since before M13.
  Resume only once M13.6 is genuinely closed out.
- No formal V2 roadmap beyond M14. `PRD.md` §3's parking lot (unprioritized):
  RLE/brush rendering beyond Lekhana's narrow case, rotated-bbox support,
  YOLO-seg/OBB, `data.yaml` support, a two-format diff view, a
  class-visibility toggle, keypoint/skeleton rendering, `iscrowd`-aware
  styling, an option to plot without label fields or hide them client-side
  (the user asked for my unbiased take on this once — I said it seemed
  reasonable as a future milestone, never formally scoped).

## Key file locations (device)

```
C:\Users\mihir\Desktop\UniPlotter\
  CLAUDE.md              # read by every local Claude Code session first
  PRD.md                 # product scope, current through §22 (M13.6)
  ARCHITECTURE.md        # frozen technical contracts
  MILESTONES.md          # per-milestone scope, current through M13.6
  app/
    main.py              # FastAPI app, /plot endpoint, PARSERS dict
    schema.py            # shared schema, ParseResult, ParseError
    draw.py              # the one drawing function — heavily iterated M13-M13.6
    parsers/
      coco.py, yolo.py, voc.py, labelme.py, labelstudio.py, cvat.py,
      lekhana.py
    static/
      index.html          # frontend — task badge added M13, removed M13.2
  sample_data/<format>/
  requirements.txt
  README.md

C:\Users\mihir\Desktop\multi-task single images\
  000002.jpg ... 000690.jpg              # 29 real damage-inspection photos
  lekhana_Dummy_V2_27082026_150339660_json_export.json  # real annotation export
```

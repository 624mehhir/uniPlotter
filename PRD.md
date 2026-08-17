# PRD.md — Universal Annotation Plotter

## Problem

Verifying that an annotation export actually matches what was drawn is
normally a manual, error-prone process — you have to trust the export is
correct, or write one-off scripts per format. This tool renders an exported
annotation file directly onto its source image, so correctness can be
checked visually and quickly, across multiple common annotation formats.

## Goal (V1)

A user uploads a raw image and an annotation file, selects which format it
is, and receives back the image with all bounding boxes and polygons drawn
on top, each shape colored by its class label.

## User flow

1. User opens the app (a single page).
2. User uploads: an image file, an annotation file (two files for YOLO —
   labels + class list), and selects the format from a dropdown.
3. User submits.
4. App returns the plotted image (viewable/downloadable), plus a warning if
   the annotation file's recorded image dimensions don't match the actual
   uploaded image.

## In scope for V1

- Shape types: bounding boxes and polygons only.
- Formats: COCO, YOLO, Pascal VOC, LabelMe, Label Studio, CVAT (native XML
  export).
- One image + one annotation submission per request.
- Per-class consistent coloring.
- Dimension-mismatch warning.

## Explicitly out of scope for V1 (do not build, do not scaffold for)

- Brush/mask-based (freehand) annotation rendering.
- Erase-stroke handling of any kind.
- Batch processing of multiple images at once.
- Format auto-detection — user always explicitly selects the format.
- Any format not in the list above.
- User accounts, saved history, persistent storage.
- Deployment/hosting configuration.

## Success criteria for V1

For each of the 6 formats, a sample annotation file with 2–3 shapes
(including at least one polygon and one bbox where the format supports
both) can be uploaded alongside its image and produce a correctly plotted
result, verified visually.

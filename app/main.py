import base64

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.draw import draw_annotations
from app.parsers import coco, cvat, labelme, labelstudio, lekhana, voc, yolo
from app.schema import ParseError

app = FastAPI()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

PARSERS = {
    "coco": coco.parse,
    "labelme": labelme.parse,
    "voc": voc.parse,
    "labelstudio": labelstudio.parse,
    "cvat": cvat.parse,
    "yolo": yolo.parse,
    "lekhana": lekhana.parse,
}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse("app/static/index.html")


@app.post("/plot")
async def plot(
    image: UploadFile = File(...),
    annotation: UploadFile = File(...),
    format: str = Form(...),
    classes: UploadFile = File(None),
    show_labels: bool = Form(True),
):
    parser = PARSERS.get(format)
    if parser is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported format '{format}'. Supported formats: "
                f"{', '.join(PARSERS)}."
            ),
        )

    if format == "yolo" and classes is None:
        raise HTTPException(
            status_code=400,
            detail="YOLO format requires a 'classes' file (classes.txt) in "
            "addition to the annotation file.",
        )

    image_bytes = await image.read()
    annotation_bytes = await annotation.read()

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    decoded_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if decoded_image is None:
        raise HTTPException(
            status_code=400, detail="Could not decode the uploaded image."
        )

    image_height, image_width = decoded_image.shape[:2]

    try:
        if format == "yolo":
            classes_bytes = await classes.read()
            result = parser(
                annotation_bytes,
                image_width,
                image_height,
                image.filename,
                classes_bytes,
            )
        else:
            result = parser(annotation_bytes, image_width, image_height, image.filename)
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    plotted = draw_annotations(decoded_image, result.annotations, draw_labels=show_labels)

    success, encoded = cv2.imencode(".png", plotted)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to encode plotted image.")

    base_name = image.filename.rsplit(".", 1)[0] if image.filename else "plotted"

    return {
        "filename": f"{base_name}_plotted.png",
        "media_type": "image/png",
        "image_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
        "warnings": result.warnings,
        "annotation_count": len(result.annotations),
        "skipped_count": result.skipped_count,
    }

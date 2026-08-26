from app.schema import ParseError, ParseResult


def parse(annotation_bytes, image_width, image_height, image_filename, classes_bytes):
    classes_text = classes_bytes.decode("utf-8")
    classes = [line.rstrip("\r") for line in classes_text.split("\n")]
    classes = [line for line in classes if line.strip() != ""]

    warnings = []
    annotations = []
    unknown_class_ids = set()

    text = annotation_bytes.decode("utf-8")
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        tokens = line.split()
        if len(tokens) == 6:
            raise ParseError(
                f"Line {line_number} has 6 tokens, which looks like a "
                "YOLO prediction file with confidence scores, not a "
                "ground-truth annotation file."
            )
        if len(tokens) > 6:
            raise ParseError(
                f"Line {line_number} has {len(tokens)} tokens, which "
                "looks like a YOLO-seg or YOLO-OBB export variant. This "
                "is not supported."
            )
        if len(tokens) != 5:
            raise ParseError(
                f"Line {line_number} has {len(tokens)} tokens; expected "
                "5 (class_id x_center y_center width height)."
            )

        class_id_token, x_center, y_center, width, height = tokens
        class_id = int(class_id_token)
        x_center, y_center, width, height = (
            float(x_center),
            float(y_center),
            float(width),
            float(height),
        )

        if 0 <= class_id < len(classes):
            label = classes[class_id]
        else:
            label = f"unknown:{class_id}"
            unknown_class_ids.add(class_id)

        box_width = width * image_width
        box_height = height * image_height
        x_min = (x_center * image_width) - (box_width / 2)
        y_min = (y_center * image_height) - (box_height / 2)

        annotations.append(
            {
                "label": label,
                "shape_type": "bbox",
                "points": [x_min, y_min, box_width, box_height],
            }
        )

    if unknown_class_ids:
        warnings.append(
            "Class id(s) "
            f"{', '.join(str(cid) for cid in sorted(unknown_class_ids))} "
            "not found in classes.txt."
        )

    return ParseResult(annotations=annotations, warnings=warnings, skipped_count=0)

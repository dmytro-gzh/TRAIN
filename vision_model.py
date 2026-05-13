# vision_model.py
# Loads YOLO and detects dangerous objects.

from ultralytics import YOLO

from config import MODEL_NAME, CONFIDENCE_THRESHOLD, DANGER_OBJECTS
from danger_logic import get_position, estimate_closeness, make_warning


def load_model():
    """
    Loads the YOLO object detection model.
    """

    print("Loading YOLO model...")
    return YOLO(MODEL_NAME)


def detect_dangerous_objects(model, frame):
    """
    Runs object detection on one camera frame.

    Returns:
    detections: list of detected dangerous objects
    best_warning: most important warning to speak
    """

    frame_height, frame_width, _ = frame.shape

    results = model(frame, verbose=False)

    detections = []
    best_warning = None
    highest_area = 0

    for result in results:
        boxes = result.boxes

        for box in boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            object_name = model.names[cls_id]

            # Ignore weak detections.
            if confidence < CONFIDENCE_THRESHOLD:
                continue

            # Ignore objects that are not in our danger list.
            if object_name not in DANGER_OBJECTS:
                continue

            # Get bounding box coordinates.
            x1, y1, x2, y2 = box.xyxy[0]
            x1 = int(x1)
            y1 = int(y1)
            x2 = int(x2)
            y2 = int(y2)

            box_width = x2 - x1
            box_height = y2 - y1
            box_area = box_width * box_height

            x_center = x1 + box_width / 2

            # Determine position and closeness.
            position = get_position(x_center, frame_width)
            closeness = estimate_closeness(
                box_width,
                box_height,
                frame_width,
                frame_height
            )

            warning = make_warning(object_name, position, closeness)

            detection = {
                "object_name": object_name,
                "confidence": confidence,
                "position": position,
                "closeness": closeness,
                "warning": warning,
                "box_area": box_area,
                "bbox": (x1, y1, x2, y2)
            }

            detections.append(detection)

            # Pick the largest dangerous object as most important.
            if warning and box_area > highest_area:
                highest_area = box_area
                best_warning = warning

    return detections, best_warning
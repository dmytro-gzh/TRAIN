# vision_model.py
# This file loads the YOLO model and uses it to detect dangerous objects.

from ultralytics import YOLO

from config import MODEL_NAME, CONFIDENCE_THRESHOLD, DANGER_OBJECTS
from danger_logic import get_position, estimate_closeness, make_warning


def load_model():
    """
    Loads the YOLO object detection model.
    The first time this runs, YOLO may download the model file.
    """

    print("Loading YOLO model...")
    return YOLO(MODEL_NAME)


def detect_dangerous_objects(model, frame):
    """
    Runs object detection on one camera frame.

    Returns:
    detections: a list of detected dangerous objects
    best_warning: the most important warning to speak
    """

    # Get the size of the camera frame.
    frame_height, frame_width, _ = frame.shape

    # Run YOLO object detection on the frame.
    results = model(frame, verbose=False)

    # Store all dangerous detections for drawing boxes on the screen.
    detections = []

    # Store the most important warning.
    best_warning = None

    # Track the largest detected object.
    # Larger object usually means closer object.
    highest_area = 0

    # Go through YOLO results.
    for result in results:
        boxes = result.boxes

        # Go through each detected object box.
        for box in boxes:
            # Class ID tells us what object YOLO detected.
            cls_id = int(box.cls[0])

            # Confidence tells us how sure YOLO is.
            confidence = float(box.conf[0])

            # Convert class ID into object name, like "person" or "car".
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

            # Calculate bounding box size.
            box_width = x2 - x1
            box_height = y2 - y1
            box_area = box_width * box_height

            # Find horizontal center of the object.
            x_center = x1 + box_width / 2

            # Determine if object is left, center, or right.
            position = get_position(x_center, frame_width)

            # Estimate if object is far, medium, close, or very close.
            closeness = estimate_closeness(
                box_width,
                box_height,
                frame_width,
                frame_height
            )

            # Create a warning message if needed.
            warning = make_warning(object_name, position, closeness)

            # Store this detection so it can be drawn on the camera window.
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

            # Choose the largest dangerous object as the most important warning.
            if warning and box_area > highest_area:
                highest_area = box_area
                best_warning = warning

    return detections, best_warning
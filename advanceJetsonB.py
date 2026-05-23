# Jetson B:
# Receives target info from Jetson A.
# Uses Camera B to detect a chair as the simulated train track.
# If a similar-looking person gets near the chair, it highlights them yellow
# and prints an alarm message.
#
# Local direct version:
# No cloud
# No MQTT
# No Arduino

import cv2
import zmq
import json
import time
import math
from ultralytics import YOLO


# -----------------------------
# NETWORK SETTINGS
# -----------------------------

# Jetson B listens for target info from Jetson A on this port.
RECEIVE_PORT = "5555"


# -----------------------------
# CAMERA / YOLO SETTINGS
# -----------------------------

CAMERA_INDEX = 0
MODEL_NAME = "yolov5nu.pt"

CONFIDENCE_THRESHOLD = 0.50
YOLO_IMAGE_SIZE = 224
PROCESS_EVERY_N_FRAMES = 3

CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240


# -----------------------------
# TARGET / ALARM SETTINGS
# -----------------------------

# How long Jetson B focuses on the target after receiving info from Jetson A.
TARGET_ACTIVE_SECONDS = 12

# Smaller number = stricter color matching.
# Bigger number = looser color matching.
COLOR_DISTANCE_THRESHOLD = 70

# Prevents alarm from printing too often.
ALARM_COOLDOWN_SECONDS = 5

# Expands the chair box to create a danger area around it.
CHAIR_DANGER_PADDING = 50


def boxes_are_close(box1, box2, padding=50):
    """
    Checks if box1 is close to box2.
    Used to check if person is close to chair.
    """

    x1, y1, x2, y2 = box1
    a1, b1, a2, b2 = box2

    # Expand chair box to create danger zone.
    a1 -= padding
    b1 -= padding
    a2 += padding
    b2 += padding

    overlap_x = max(0, min(x2, a2) - max(x1, a1))
    overlap_y = max(0, min(y2, b2) - max(y1, b1))

    return overlap_x * overlap_y > 0


def get_average_color(frame, box):
    """
    Gets average clothing color from upper-middle part of person box.
    Returns BGR color: [blue, green, red].
    """

    x1, y1, x2, y2 = box
    h, w = frame.shape[:2]

    x1 = max(0, min(x1, w - 1))
    x2 = max(0, min(x2, w - 1))
    y1 = max(0, min(y1, h - 1))
    y2 = max(0, min(y2, h - 1))

    if x2 <= x1 or y2 <= y1:
        return None

    box_height = y2 - y1

    # Use upper-middle body region, roughly shirt area.
    crop_y1 = y1 + int(box_height * 0.20)
    crop_y2 = y1 + int(box_height * 0.60)

    crop = frame[crop_y1:crop_y2, x1:x2]

    if crop.size == 0:
        return None

    avg_color = crop.mean(axis=(0, 1))

    return [
        float(avg_color[0]),
        float(avg_color[1]),
        float(avg_color[2])
    ]


def color_distance(color1, color2):
    """
    Compares two BGR colors.
    Smaller distance means colors are more similar.
    """

    if color1 is None or color2 is None:
        return 9999

    return math.sqrt(
        (color1[0] - color2[0]) ** 2 +
        (color1[1] - color2[1]) ** 2 +
        (color1[2] - color2[2]) ** 2
    )


def receive_target_if_available(receiver):
    """
    Checks if Jetson A sent target info.
    Non-blocking so the camera loop does not freeze.
    """

    try:
        message = receiver.recv_string(flags=zmq.NOBLOCK)
        data = json.loads(message)
        return data

    except zmq.Again:
        return None


def draw_expanded_chair_zone(frame, chair_box, padding):
    """
    Draws the red danger zone around the detected chair.
    """

    x1, y1, x2, y2 = chair_box

    h, w = frame.shape[:2]

    zx1 = max(0, x1 - padding)
    zy1 = max(0, y1 - padding)
    zx2 = min(w - 1, x2 + padding)
    zy2 = min(h - 1, y2 + padding)

    cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (0, 0, 255), 2)

    cv2.putText(
        frame,
        "Danger Zone",
        (zx1, max(zy1 - 10, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (0, 0, 255),
        2
    )


def main():
    # -----------------------------
    # ZMQ SETUP
    # -----------------------------

    ctx = zmq.Context()
    receiver = ctx.socket(zmq.PULL)
    receiver.bind(f"tcp://*:{RECEIVE_PORT}")

    print("Jetson B waiting for target info on port:", RECEIVE_PORT)

    # -----------------------------
    # YOLO SETUP
    # -----------------------------

    print("Loading YOLO model...")
    model = YOLO(MODEL_NAME)

    print("Opening Camera B...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Error: Could not open Camera B.")
        print("Try changing CAMERA_INDEX from 0 to 1.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    target_color = None
    target_active_until = 0
    last_alarm_time = 0

    frame_count = 0

    people = []
    chairs = []

    matched_target_box = None
    matched_target_distance = None

    print("Jetson B started.")
    print("Chair will simulate the train track danger area.")
    print("Press Q to quit.")

    while True:
        # -----------------------------
        # RECEIVE TARGET FROM JETSON A
        # -----------------------------

        target_data = receive_target_if_available(receiver)

        if target_data is not None and target_data.get("event") == "watch_target":
            target_color = target_data.get("target_color")
            target_active_until = time.time() + TARGET_ACTIVE_SECONDS

            print("Received target from Jetson A:")
            print(target_data)
            print("FOCUS MODE ON for", TARGET_ACTIVE_SECONDS, "seconds.")

        # -----------------------------
        # CAMERA READ
        # -----------------------------

        ret, frame = cap.read()

        if not ret:
            print("Error: Could not read Camera B frame.")
            break

        frame_count += 1
        current_time = time.time()
        target_active = current_time <= target_active_until

        # Reset match display each loop.
        matched_target_box = None
        matched_target_distance = None

        # -----------------------------
        # YOLO DETECTION
        # -----------------------------

        if frame_count % PROCESS_EVERY_N_FRAMES == 0:
            # Detect person and chair.
            # COCO class 0 = person
            # COCO class 56 = chair
            results = model(
                frame,
                imgsz=YOLO_IMAGE_SIZE,
                conf=CONFIDENCE_THRESHOLD,
                classes=[0, 56],
                verbose=False
            )

            people = []
            chairs = []

            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    confidence = float(box.conf[0])

                    if confidence < CONFIDENCE_THRESHOLD:
                        continue

                    x1, y1, x2, y2 = box.xyxy[0]
                    bbox = (int(x1), int(y1), int(x2), int(y2))

                    if cls_id == 0:
                        person_color = get_average_color(frame, bbox)

                        people.append({
                            "bbox": bbox,
                            "confidence": confidence,
                            "color": person_color
                        })

                    elif cls_id == 56:
                        chairs.append({
                            "bbox": bbox,
                            "confidence": confidence
                        })

            # If focus mode is active, check if similar person is near chair.
            if target_active and target_color is not None:
                for person in people:
                    for chair in chairs:
                        near_chair = boxes_are_close(
                            person["bbox"],
                            chair["bbox"],
                            padding=CHAIR_DANGER_PADDING
                        )

                        if near_chair:
                            dist = color_distance(target_color, person["color"])

                            if dist <= COLOR_DISTANCE_THRESHOLD:
                                matched_target_box = person["bbox"]
                                matched_target_distance = dist

                                if current_time - last_alarm_time >= ALARM_COOLDOWN_SECONDS:
                                    print("ALARM: likely target is near the simulated train track!")
                                    print("Color distance:", round(dist, 2))
                                    last_alarm_time = current_time

        # -----------------------------
        # DRAW CHAIR + DANGER ZONE
        # -----------------------------

        for chair in chairs:
            x1, y1, x2, y2 = chair["bbox"]
            confidence = chair["confidence"]

            # Purple box around actual chair.
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)

            cv2.putText(
                frame,
                f"Chair/Track {confidence:.2f}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 0, 255),
                2
            )

            # Red expanded danger zone around chair.
            draw_expanded_chair_zone(frame, chair["bbox"], CHAIR_DANGER_PADDING)

        # -----------------------------
        # DRAW PEOPLE
        # -----------------------------

        for person in people:
            x1, y1, x2, y2 = person["bbox"]
            confidence = person["confidence"]

            # Default: green box for normal person.
            box_color = (0, 255, 0)
            label = f"Person {confidence:.2f}"

            # Yellow box if this person matches Camera A target.
            if matched_target_box == person["bbox"]:
                box_color = (0, 255, 255)
                label = f"RISKY TARGET {confidence:.2f}"

                if matched_target_distance is not None:
                    label += f" match {matched_target_distance:.1f}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 3)

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                box_color,
                2
            )

        # -----------------------------
        # DRAW FOCUS STATUS
        # -----------------------------

        status = "FOCUS MODE ON" if target_active else "FOCUS MODE OFF"

        cv2.putText(
            frame,
            status,
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 0),
            2
        )

        cv2.imshow("Jetson B - Chair Simulated Track", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    receiver.close()
    ctx.term()


if __name__ == "__main__":
    main()

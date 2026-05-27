# Jetson A:
# Uses Camera A to detect people.
# Chooses the most risky person.
# Sends target info directly to Jetson B.
#
# Local direct version:
# No cloud
# No MQTT
# No Arduino

import cv2
import zmq
import json
import time
from ultralytics import YOLO


# -----------------------------
# NETWORK SETTINGS
# -----------------------------

# Change this to Jetson B's IP address.
# Find Jetson B IP with: hostname -I
JETSON_B_IP = "10.13.196.94"
JETSON_B_PORT = "5555"


# -----------------------------
# CAMERA / YOLO SETTINGS
# -----------------------------

CAMERA_INDEX = 0
MODEL_NAME = "yolov5nu.pt"

CONFIDENCE_THRESHOLD = 0.40
YOLO_IMAGE_SIZE = 320
PROCESS_EVERY_N_FRAMES = 3

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

SEND_COOLDOWN_SECONDS = 5


# -----------------------------
# APPROACH ZONE FOR CAMERA A
# -----------------------------
# Camera A watches this zone for people approaching the tracks.
# You can adjust this box based on your camera view.
# Format: x1, y1, x2, y2

APPROACH_ZONE = (60, 70, 260, 230)


def box_overlaps_zone(box, zone):
    """
    Checks if a person's bounding box overlaps the approach zone.
    """

    bx1, by1, bx2, by2 = box
    zx1, zy1, zx2, zy2 = zone

    overlap_x = max(0, min(bx2, zx2) - max(bx1, zx1))
    overlap_y = max(0, min(by2, zy2) - max(by1, zy1))

    return overlap_x * overlap_y > 0


def get_box_area(box):
    """
    Returns area of bounding box.
    Bigger box usually means person is closer.
    """

    x1, y1, x2, y2 = box
    return max(0, x2 - x1) * max(0, y2 - y1)


def get_box_center(box):
    """
    Returns center point of bounding box.
    """

    x1, y1, x2, y2 = box
    return ((x1 + x2) // 2, (y1 + y2) // 2)


def get_average_color(frame, box):
    """
    Gets average clothing color from upper-middle part of person box.
    Returns BGR color: [blue, green, red]
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

    # Focus on shirt/body area, not face/legs.
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


def choose_most_risky_person(frame, detections):
    """
    Chooses the person Camera A thinks is most likely to go toward the track area.

    Simple risk rule:
    - Person must be inside/overlapping approach zone.
    - Person lower in frame = more risky.
    - Person larger in frame = more risky.
    """

    candidates = []

    for det in detections:
        box = det["bbox"]

        if not box_overlaps_zone(box, APPROACH_ZONE):
            continue

        center_x, center_y = get_box_center(box)
        box_area = get_box_area(box)

        # Simple risk score.
        # Higher y means lower in image.
        # Bigger area means person may be closer.
        risk_score = center_y + (box_area * 0.01)

        avg_color = get_average_color(frame, box)

        if avg_color is None:
            continue

        candidates.append({
            "bbox": box,
            "confidence": det["confidence"],
            "risk_score": risk_score,
            "avg_color": avg_color
        })

    if not candidates:
        return None

    candidates.sort(key=lambda item: item["risk_score"], reverse=True)
    return candidates[0]


def send_target(sender, target):
    """
    Sends target information to Jetson B.
    """

    message = {
        "event": "watch_target",
        "source": "Jetson A",
        "target_color": target["avg_color"],
        "bbox": target["bbox"],
        "confidence": target["confidence"],
        "risk_score": target["risk_score"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    sender.send_string(json.dumps(message))
    print("Sent target to Jetson B:")
    print(message)


def main():
    # -----------------------------
    # ZMQ SETUP
    # -----------------------------

    ctx = zmq.Context()
    sender = ctx.socket(zmq.PUSH)
    sender.connect(f"tcp://{JETSON_B_IP}:{JETSON_B_PORT}")

    print("Jetson A sending target info to Jetson B:", JETSON_B_IP)

    # -----------------------------
    # YOLO SETUP
    # -----------------------------

    print("Loading YOLO model...")
    model = YOLO(MODEL_NAME)

    print("Opening Camera A...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Error: Could not open Camera A.")
        print("Try changing CAMERA_INDEX from 0 to 1.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    frame_count = 0
    last_send_time = 0
    last_detections = []
    current_target = None

    print("Jetson A started.")
    print("Press Q to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Error: Could not read Camera A frame.")
            break

        frame_count += 1

        if frame_count % PROCESS_EVERY_N_FRAMES == 0:
            results = model(
                frame,
                imgsz=YOLO_IMAGE_SIZE,
                conf=CONFIDENCE_THRESHOLD,
                classes=[0],  # 0 = person
                verbose=False
            )

            last_detections = []

            for result in results:
                for box in result.boxes:
                    confidence = float(box.conf[0])

                    if confidence >= CONFIDENCE_THRESHOLD:
                        x1, y1, x2, y2 = box.xyxy[0]

                        detection = {
                            "bbox": (int(x1), int(y1), int(x2), int(y2)),
                            "confidence": confidence
                        }

                        last_detections.append(detection)

            target = choose_most_risky_person(frame, last_detections)

            current_time = time.time()

            if target is not None:
                current_target = target

                if current_time - last_send_time >= SEND_COOLDOWN_SECONDS:
                    send_target(sender, target)
                    last_send_time = current_time

        # Draw approach zone.
        zx1, zy1, zx2, zy2 = APPROACH_ZONE
        cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (255, 0, 0), 2)
        cv2.putText(
            frame,
            "Approach Zone",
            (zx1, max(zy1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 0, 0),
            2
        )

        # Draw detected people.
        for det in last_detections:
            x1, y1, x2, y2 = det["bbox"]
            confidence = det["confidence"]

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"Person {confidence:.2f}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

        # Highlight current risky target.
        if current_target is not None:
            x1, y1, x2, y2 = current_target["bbox"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 3)
            cv2.putText(
                frame,
                "RISKY TARGET",
                (x1, max(y1 - 30, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                2
            )

        cv2.imshow("Jetson A - Approach Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    sender.close()
    ctx.term()


if __name__ == "__main__":
    main()

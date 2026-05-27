# Jetson B:
# Receives target info from Jetson A using ZeroMQ.
# Detects person + chair using YOLO.
# Uses chair as simulated train track.
# Sends photo to MQTT server when any person enters danger zone.
# Uses the same MQTT topics as your server:
#   ALARM/IMAGE
#   ALARM/STATUS

import cv2
import zmq
import json
import time
import math
import os
import base64
from datetime import datetime
from ultralytics import YOLO
import paho.mqtt.client as mqtt


# -----------------------------
# ZEROMQ SETTINGS
# -----------------------------

RECEIVE_PORT = "5555"


# -----------------------------
# MQTT SETTINGS
# -----------------------------

mqttBroker = "broker.hivemq.com"
websocket_port = 8000
websocket_path = "/mqtt"

MQTT_IMAGE_TOPIC = "ALARM/IMAGE"
MQTT_STATUS_TOPIC = "ALARM/STATUS"

alarm_status = 0


# -----------------------------
# CAMERA / YOLO SETTINGS
# -----------------------------

CAMERA_INDEX = 0
MODEL_NAME = "yolov5nu.pt"

# Lower confidence helps detect chair better.
CONFIDENCE_THRESHOLD = 0.35

# 320 helps chair detection more than 224.
YOLO_IMAGE_SIZE = 320

PROCESS_EVERY_N_FRAMES = 3

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


# -----------------------------
# TARGET / ALARM SETTINGS
# -----------------------------

TARGET_ACTIVE_SECONDS = 12
COLOR_DISTANCE_THRESHOLD = 70
PHOTO_COOLDOWN_SECONDS = 5
CHAIR_DANGER_PADDING = 100

PHOTO_FOLDER = "captured_photos"


def create_filename(event_type):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{event_type}_{timestamp}.jpg"


def on_message(client, userdata, message):
    """
    Receives alarm status from server.
    Server publishes:
      ALARM/STATUS = 1 when alarm is ON
      ALARM/STATUS = 0 when alarm is reset
    """

    global alarm_status

    payload = message.payload.decode("utf-8").strip()

    print(f"Received message on {message.topic}: {payload}")

    if message.topic == MQTT_STATUS_TOPIC:
        if payload == "1":
            alarm_status = 1
            print("Server alarm is ON. Jetson B will pause sending images.")
        elif payload == "0":
            alarm_status = 0
            print("Server alarm reset. Jetson B can send images again.")


def publish_image(client, image_path):
    """
    Reads image, converts it to base64, and publishes it to ALARM/IMAGE.
    This matches your server code.
    """

    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    client.publish(MQTT_IMAGE_TOPIC, encoded, qos=1)
    print(f"Published image: {image_path} to topic {MQTT_IMAGE_TOPIC}")

    # Same behavior as your previous edge code: delete after sending.
    os.remove(image_path)
    print(f"Deleted: {image_path}")


def boxes_are_close(box1, box2, padding=50):
    """
    Checks if person box is close to chair box.
    The chair box is expanded to act like the danger zone.
    """

    x1, y1, x2, y2 = box1
    a1, b1, a2, b2 = box2

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
    Receives target info from Jetson A.
    Non-blocking so camera loop does not freeze.
    """

    try:
        message = receiver.recv_string(flags=zmq.NOBLOCK)
        data = json.loads(message)
        return data
    except zmq.Again:
        return None


def draw_expanded_chair_zone(frame, chair_box, padding):
    """
    Draws red danger zone around detected chair.
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


def save_and_publish_photo(client, frame, event_type):
    """
    Saves current frame and sends it to MQTT server.
    """

    os.makedirs(PHOTO_FOLDER, exist_ok=True)

    filename = create_filename(event_type)
    image_path = os.path.join(PHOTO_FOLDER, filename)

    cv2.imwrite(image_path, frame)
    print(f"Saved photo: {image_path}")

    publish_image(client, image_path)


def main():
    global alarm_status

    os.makedirs(PHOTO_FOLDER, exist_ok=True)

    # -----------------------------
    # MQTT SETUP
    # -----------------------------

    client = mqtt.Client(client_id="Jetson-B", transport="websockets")
    client.ws_set_options(path=websocket_path)
    client.on_message = on_message

    print("Connecting Jetson B to broker via WebSockets...")

    try:
        client.connect(mqttBroker, port=websocket_port)
        client.loop_start()

        client.subscribe(MQTT_STATUS_TOPIC)
        print("Successfully connected and loop started!")
        print(f"Subscribed to {MQTT_STATUS_TOPIC}")

    except Exception as e:
        print(f"Connection failed: {e}")
        return

    # -----------------------------
    # ZMQ SETUP
    # -----------------------------

    ctx = zmq.Context()
    receiver = ctx.socket(zmq.PULL)
    receiver.bind(f"tcp://*:{RECEIVE_PORT}")

    print("Jetson B waiting for target info from Jetson A on port:", RECEIVE_PORT)

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

    frame_count = 0
    last_photo_time = 0

    people = []
    chairs = []

    matched_target_box = None
    matched_target_distance = None

    print("Jetson B started.")
    print("Chair = simulated train track.")
    print("Press Q to quit.")

    try:
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

            if frame_count % PROCESS_EVERY_N_FRAMES == 0:
                matched_target_box = None
                matched_target_distance = None

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
                            people.append({
                                "bbox": bbox,
                                "confidence": confidence,
                                "color": get_average_color(frame, bbox)
                            })

                        elif cls_id == 56:
                            chairs.append({
                                "bbox": bbox,
                                "confidence": confidence
                            })

                # -----------------------------
                # CHECK DANGER ZONE
                # -----------------------------

                person_in_danger_zone = False
                risky_target_in_danger_zone = False

                for person in people:
                    is_risky_match = False

                    # Check if this person matches Jetson A target color.
                    if target_active and target_color is not None:
                        dist = color_distance(target_color, person["color"])

                        if dist <= COLOR_DISTANCE_THRESHOLD:
                            is_risky_match = True
                            matched_target_box = person["bbox"]
                            matched_target_distance = dist

                    # Check if this person is near chair.
                    for chair in chairs:
                        near_chair = boxes_are_close(
                            person["bbox"],
                            chair["bbox"],
                            padding=CHAIR_DANGER_PADDING
                        )

                        if near_chair:
                            person_in_danger_zone = True

                            if is_risky_match:
                                risky_target_in_danger_zone = True

                # -----------------------------
                # SEND PHOTO TO SERVER
                # -----------------------------

                if person_in_danger_zone:
                    if alarm_status == 1:
                        print("Alarm is currently ON. Waiting for server reset...")
                    else:
                        if current_time - last_photo_time >= PHOTO_COOLDOWN_SECONDS:
                            if risky_target_in_danger_zone:
                                print("DANGER: risky target entered simulated track zone.")
                                save_and_publish_photo(
                                    client,
                                    frame,
                                    event_type="risky_target_danger"
                                )
                            else:
                                print("DANGER: normal person entered simulated track zone.")
                                save_and_publish_photo(
                                    client,
                                    frame,
                                    event_type="normal_person_danger"
                                )

                            last_photo_time = current_time

            # -----------------------------
            # DRAW CHAIR + DANGER ZONE
            # -----------------------------

            for chair in chairs:
                x1, y1, x2, y2 = chair["bbox"]
                confidence = chair["confidence"]

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

                draw_expanded_chair_zone(frame, chair["bbox"], CHAIR_DANGER_PADDING)

            # -----------------------------
            # DRAW PEOPLE
            # -----------------------------

            for person in people:
                x1, y1, x2, y2 = person["bbox"]
                confidence = person["confidence"]

                box_color = (0, 255, 0)
                label = f"Person {confidence:.2f}"

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
            # DRAW STATUS
            # -----------------------------

            focus_status = "FOCUS MODE ON" if target_active else "FOCUS MODE OFF"
            server_status = "SERVER ALARM ON" if alarm_status == 1 else "SERVER ALARM OFF"

            cv2.putText(
                frame,
                focus_status,
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 0),
                2
            )

            cv2.putText(
                frame,
                server_status,
                (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255) if alarm_status == 1 else (0, 255, 0),
                2
            )

            cv2.imshow("Jetson B - Chair Track MQTT Sender", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    except KeyboardInterrupt:
        print("\nDisconnecting...")

    finally:
        cap.release()
        cv2.destroyAllWindows()

        receiver.close()
        ctx.term()

        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
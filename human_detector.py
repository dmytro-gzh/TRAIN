# human_detector.py
# Optimized human detector for Jetson Nano / Jetson Orin Nano.

import cv2
from ultralytics import YOLO


CAMERA_INDEX = 0

# Try yolov5nu.pt or yolov8n.pt
MODEL_NAME = "yolov5nu.pt"

CONFIDENCE_THRESHOLD = 0.50

# Smaller = faster. Try 224 for Jetson.
YOLO_IMAGE_SIZE = 224

# Process fewer frames for speed.
PROCESS_EVERY_N_FRAMES = 3

# Camera resolution.
CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240


def main():
    print("Loading YOLO model...")
    model = YOLO(MODEL_NAME)

    print("Opening USB camera...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Error: Could not open USB camera.")
        print("Try changing CAMERA_INDEX from 0 to 1.")
        return

    # Lower camera resolution for speed.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, 30)

    frame_count = 0
    last_boxes = []
    human_was_detected = False

    print("Human detector started.")
    print("Press Q to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Error: Could not read camera frame.")
            break

        frame_count += 1

        if frame_count % PROCESS_EVERY_N_FRAMES == 0:
            results = model(
                frame,
                imgsz=YOLO_IMAGE_SIZE,
                conf=CONFIDENCE_THRESHOLD,
                classes=[0],
                verbose=False
            )

            human_detected = False
            last_boxes = []

            for result in results:
                for box in result.boxes:
                    confidence = float(box.conf[0])

                    if confidence >= CONFIDENCE_THRESHOLD:
                        human_detected = True

                        x1, y1, x2, y2 = box.xyxy[0]
                        last_boxes.append(
                            (
                                int(x1),
                                int(y1),
                                int(x2),
                                int(y2),
                                confidence
                            )
                        )

            if human_detected and not human_was_detected:
                print("Human detected!")

            if not human_detected and human_was_detected:
                print("Human no longer detected.")

            human_was_detected = human_detected

        for x1, y1, x2, y2, confidence in last_boxes:
            label = f"Human {confidence:.2f}"

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        cv2.imshow("Human Detector", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
# human_detector.py
# Detects humans using YOLO and prints a message when a person is detected.

import cv2
from ultralytics import YOLO


CAMERA_INDEX = 0

# Try yolov5nu.pt or yolov8n.pt
MODEL_NAME = "yolov5nu.pt"

CONFIDENCE_THRESHOLD = 0.50

# Lower YOLO image size for faster detection
YOLO_IMAGE_SIZE = 320

# Process every 2 frames for speed
PROCESS_EVERY_N_FRAMES = 2


def main():
    print("Loading YOLO model...")
    model = YOLO(MODEL_NAME)

    print("Opening camera...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        print("Try changing CAMERA_INDEX from 0 to 1.")
        return

    # Lower camera resolution for faster processing
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
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

        # Only run YOLO every N frames
        if frame_count % PROCESS_EVERY_N_FRAMES == 0:
            results = model(frame, imgsz=YOLO_IMAGE_SIZE, verbose=False)

            human_detected = False
            last_boxes = []

            for result in results:
                for box in result.boxes:
                    cls_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    object_name = model.names[cls_id]

                    if object_name == "person" and confidence >= CONFIDENCE_THRESHOLD:
                        human_detected = True

                        x1, y1, x2, y2 = box.xyxy[0]
                        x1 = int(x1)
                        y1 = int(y1)
                        x2 = int(x2)
                        y2 = int(y2)

                        last_boxes.append((x1, y1, x2, y2, confidence))

            # Print only when human first appears
            if human_detected and not human_was_detected:
                print("Human detected!")

            # Optional: print when human disappears
            if not human_detected and human_was_detected:
                print("Human no longer detected.")

            human_was_detected = human_detected

        # Draw the most recent boxes
        for x1, y1, x2, y2, confidence in last_boxes:
            label = f"Human detected {confidence:.2f}"

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                label,
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        cv2.imshow("Human Detector", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
# human_detector.py
# Detects humans using YOLO and prints a message when a person is detected.

import cv2
from ultralytics import YOLO


# Use camera 0.
# If your camera does not open, change this to 1.
CAMERA_INDEX = 0

# YOLO model.
MODEL_NAME = "yolov8n.pt"

# Minimum confidence needed to accept detection.
CONFIDENCE_THRESHOLD = 0.50


def main():
    print("Loading YOLO model...")
    model = YOLO(MODEL_NAME)

    print("Opening camera...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        print("Try changing CAMERA_INDEX from 0 to 1.")
        return

    print("Human detector started.")
    print("Press Q to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Error: Could not read camera frame.")
            break

        results = model(frame, verbose=False)

        human_detected = False

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

        if human_detected:
            print("Human detected!")

        cv2.imshow("Human Detector", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
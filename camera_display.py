# camera_display.py
# Opens camera, draws detections, displays video, and cleans up.

import cv2
from config import SHOW_CAMERA_WINDOW


def open_camera(camera_index):
    """
    Opens the camera.
    """

    print("Opening camera...")
    cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        print("Try changing CAMERA_INDEX in config.py from 0 to 1.")
        return None

    return cap


def draw_detections(frame, detections, best_warning):
    """
    Draws bounding boxes and labels on the camera frame.
    """

    for detection in detections:
        x1, y1, x2, y2 = detection["bbox"]

        label = (
            f'{detection["object_name"]} '
            f'{detection["confidence"]:.2f} '
            f'{detection["position"]} '
            f'{detection["closeness"]}'
        )

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
            0.6,
            (0, 255, 0),
            2
        )

    if best_warning:
        cv2.putText(
            frame,
            best_warning,
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2
        )

    return frame


def show_frame(frame):
    """
    Shows the camera window if enabled.
    """

    if SHOW_CAMERA_WINDOW:
        cv2.imshow("Blind Guider Jetson Demo", frame)


def quit_requested():
    """
    Checks if Q was pressed.
    """

    if not SHOW_CAMERA_WINDOW:
        return False

    key = cv2.waitKey(1) & 0xFF
    return key == ord("q")


def cleanup_camera(cap):
    """
    Releases camera and closes windows.
    """

    cap.release()

    if SHOW_CAMERA_WINDOW:
        cv2.destroyAllWindows()
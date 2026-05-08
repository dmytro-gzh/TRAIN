# camera_display.py
# This file manages the camera window and draws detection results.

import cv2


def open_camera(camera_index):
    """
    Opens the camera using OpenCV.

    camera_index:
    0 usually means built-in webcam.
    1 usually means external USB camera.
    """

    print("Opening camera...")
    cap = cv2.VideoCapture(camera_index)

    # Check if the camera opened successfully.
    if not cap.isOpened():
        print("Error: Could not open camera.")
        print("Try changing CAMERA_INDEX from 0 to 1 in config.py.")
        return None

    return cap


def draw_detections(frame, detections, best_warning):
    """
    Draws bounding boxes and labels on the camera frame.
    This is mainly useful for demo and debugging.
    """

    # Draw a box for each dangerous object.
    for detection in detections:
        x1, y1, x2, y2 = detection["bbox"]

        # Label includes object name, confidence, position, and closeness.
        label = (
            f'{detection["object_name"]} '
            f'{detection["confidence"]:.2f} '
            f'{detection["position"]} '
            f'{detection["closeness"]}'
        )

        # Draw green rectangle around detected object.
        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        # Draw label above the object.
        cv2.putText(
            frame,
            label,
            (x1, max(y1 - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

    # Draw the spoken warning in red at the top of the window.
    if best_warning:
        cv2.putText(
            frame,
            best_warning,
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            3
        )

    return frame


def show_frame(frame):
    """
    Displays the camera frame in a window.
    """

    cv2.imshow("Blind Guider Mac Demo", frame)


def quit_requested():
    """
    Checks if the user pressed Q.
    Press Q to stop the program.
    """

    key = cv2.waitKey(1) & 0xFF
    return key == ord("q")


def cleanup_camera(cap):
    """
    Releases the camera and closes all OpenCV windows.
    """

    cap.release()
    cv2.destroyAllWindows()
# main.py
# This is the main file that runs the blind guider project.
# It connects the camera, YOLO model, danger logic, display, and voice output.

import time

from config import CAMERA_INDEX, SPEAK_COOLDOWN_SECONDS
from voice_output import speak
from vision_model import load_model, detect_dangerous_objects
from camera_display import (
    open_camera,
    draw_detections,
    show_frame,
    quit_requested,
    cleanup_camera
)


def main():
    """
    Main program loop.
    This function runs the full human warning system.
    """

    # Load the YOLO object detection model.
    model = load_model()

    # Open the camera.
    cap = open_camera(CAMERA_INDEX)

    # Stop the program if the camera fails.
    if cap is None:
        return

    # Used to prevent repeated voice warnings too quickly.
    last_spoken_time = 0
    last_message = ""

    print("Blind guider started.")
    print("Press Q to quit.")

    while True:
        # Read one frame from the camera.
        ret, frame = cap.read()

        # Stop if the camera frame cannot be read.
        if not ret:
            print("Error: Could not read camera frame.")
            break

        # Run YOLO detection and danger logic.
        detections, best_warning = detect_dangerous_objects(model, frame)

        # Draw boxes and warnings on the screen for demo.
        frame = draw_detections(frame, detections, best_warning)

        # Get current time to control speech cooldown.
        current_time = time.time()

        # Speak warning if there is one and enough time has passed.
        if best_warning:
            if (
                current_time - last_spoken_time > SPEAK_COOLDOWN_SECONDS
                and best_warning != last_message
            ):
                speak(best_warning)
                last_spoken_time = current_time
                last_message = best_warning

        # Show camera window.
        show_frame(frame)

        # Quit if user presses Q.
        if quit_requested():
            break

    # Clean up camera and close windows.
    cleanup_camera(cap)


if __name__ == "__main__":
    main()
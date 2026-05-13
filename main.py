# main.py
# Main program that connects all parts of the blind guider.

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
    Runs the blind guider system.
    """

    model = load_model()

    cap = open_camera(CAMERA_INDEX)

    if cap is None:
        return

    last_spoken_time = 0
    last_message = ""

    print("Blind guider started.")
    print("Press Q to quit.")

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Error: Could not read camera frame.")
            break

        detections, best_warning = detect_dangerous_objects(model, frame)

        frame = draw_detections(frame, detections, best_warning)

        current_time = time.time()

        if best_warning:
            if (
                current_time - last_spoken_time > SPEAK_COOLDOWN_SECONDS
                and best_warning != last_message
            ):
                speak(best_warning)
                last_spoken_time = current_time
                last_message = best_warning

        show_frame(frame)

        if quit_requested():
            break

    cleanup_camera(cap)


if __name__ == "__main__":
    main()
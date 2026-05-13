# voice_output.py
# Handles voice output on Jetson using espeak.

import subprocess


def speak(message):
    """
    Speaks a warning message out loud.
    """

    print("VOICE:", message)

    try:
        subprocess.run(["espeak", message], check=False)
    except Exception as error:
        print("Voice output failed:", error)
# voice_output.py
# This file handles voice output for the Mac version.
# The Mac has a built-in command called "say" that turns text into speech.

import subprocess


def speak(message):
    """
    Speaks a warning message out loud using the Mac built-in 'say' command.

    Example:
    speak("Stop. person ahead.")
    """

    # Print the message in the terminal for debugging.
    print("VOICE:", message)

    # Use the Mac text-to-speech command.
    subprocess.run(["say", message])
# config.py
# Settings for the Jetson blind guider project.

# Camera index:
# 0 usually means the USB camera.
# If camera does not open, try 1.
CAMERA_INDEX = 0

# YOLO model.
# yolov8n.pt is the small, faster model.
MODEL_NAME = "yolov8n.pt"

# Minimum confidence for accepting detections.
CONFIDENCE_THRESHOLD = 0.50

# Time between spoken warnings.
# This stops the system from repeating warnings too quickly.
SPEAK_COOLDOWN_SECONDS = 3

# Show camera window.
# Set to False if running Jetson without monitor.
SHOW_CAMERA_WINDOW = True

# Objects that the system treats as possible danger objects.
DANGER_OBJECTS = {
    "person",
    "car",
    "bus",
    "truck",
    "bicycle",
    "motorcycle",
    "chair",
    "bench",
    "dog",
    "backpack",
    "suitcase"
}
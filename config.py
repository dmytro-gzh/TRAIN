# config.py
# This file stores the main settings for the blind guider project.
# Keeping settings in one file makes the project easier to modify.

# Camera index:
# 0 usually means the built-in Mac camera.
# 1 may be an external USB camera.
CAMERA_INDEX = 0

# YOLO model file.
# yolov8n.pt is the small YOLOv8 nano model, good for fast testing.
MODEL_NAME = "yolov8n.pt"

# How many seconds to wait before speaking again.
# This prevents the system from repeating warnings too quickly.
SPEAK_COOLDOWN_SECONDS = 3

# Minimum confidence needed before accepting a YOLO detection.
# 0.5 means the model must be at least 50% confident.
CONFIDENCE_THRESHOLD = 0.5

# Objects that we care about for safety warnings.
# YOLO may detect many things, but this project only warns about useful danger objects.
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
# danger_logic.py
# This file contains the logic that decides:
# 1. Where the object is: left, center, or right
# 2. How close the object appears
# 3. What warning message should be spoken


def get_position(x_center, frame_width):
    """
    Determines whether an object is on the left, center, or right side
    of the camera frame.

    x_center: the x-coordinate of the center of the detected object
    frame_width: the total width of the camera frame
    """

    # Divide the screen into three equal sections.
    left_boundary = frame_width / 3
    right_boundary = 2 * frame_width / 3

    if x_center < left_boundary:
        return "left"
    elif x_center > right_boundary:
        return "right"
    else:
        return "center"


def estimate_closeness(box_width, box_height, frame_width, frame_height):
    """
    Estimates how close an object is based on how much of the camera frame
    its bounding box covers.

    This is not exact distance measurement.
    It is only an estimate:
    larger box = object is probably closer
    smaller box = object is probably farther away
    """

    # Calculate the area of the detected object box.
    box_area = box_width * box_height

    # Calculate the area of the full camera frame.
    frame_area = frame_width * frame_height

    # Compare object size to full frame size.
    area_ratio = box_area / frame_area

    # These thresholds can be adjusted after testing.
    if area_ratio > 0.25:
        return "very close"
    elif area_ratio > 0.12:
        return "close"
    elif area_ratio > 0.05:
        return "medium"
    else:
        return "far"


def make_warning(object_name, position, closeness):
    """
    Creates the spoken warning message based on the object,
    its position, and its estimated closeness.
    """

    # If something is close and directly in front, tell the user to stop.
    if position == "center" and closeness in ["very close", "close"]:
        return f"Stop. {object_name} ahead."

    # If something is in front but not extremely close, give a normal warning.
    if position == "center" and closeness == "medium":
        return f"{object_name} ahead."

    # If something is close but on the left or right, tell the user the side.
    if closeness in ["very close", "close"]:
        return f"{object_name} on your {position}."

    # If the object is far away, do not speak.
    return None
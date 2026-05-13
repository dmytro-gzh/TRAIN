# danger_logic.py
# Decides object position, closeness, and warning message.


def get_position(x_center, frame_width):
    """
    Determines if the object is on the left, center, or right side.
    """

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
    Estimates closeness based on how large the object appears in the frame.

    This is not true distance.
    Larger object box = probably closer.
    """

    box_area = box_width * box_height
    frame_area = frame_width * frame_height
    area_ratio = box_area / frame_area

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
    Creates a spoken navigation warning.
    """

    if position == "center" and closeness in ["very close", "close"]:
        return f"Stop. {object_name} ahead. Move left or right."

    if position == "center" and closeness == "medium":
        return f"{object_name} ahead. Prepare to move around it."

    if position == "left" and closeness in ["very close", "close"]:
        return f"{object_name} on your left. Move right."

    if position == "right" and closeness in ["very close", "close"]:
        return f"{object_name} on your right. Move left."

    return None
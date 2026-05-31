"""Golf swing profile and interpretable metrics."""

from __future__ import annotations

from statistics import mean

from swingform_ai.geometry import angle_degrees, distance, line_separation_degrees, midpoint
from swingform_ai.schema import FramePose, PoseSequence

SWING_EVENTS = [
    "address",
    "toe_up",
    "mid_backswing",
    "top",
    "mid_downswing",
    "impact",
    "mid_follow_through",
    "finish",
]


def side_roles(handedness: str = "right") -> tuple[str, str]:
    """Return lead and trail side names for a golfer."""

    normalized = handedness.lower()
    if normalized == "right":
        return ("left", "right")
    if normalized == "left":
        return ("right", "left")
    raise ValueError("handedness must be 'right' or 'left'.")


def _landmark_name(side: str, joint: str) -> str:
    return f"{side}_{joint}"


def frame_metrics(frame: FramePose, handedness: str = "right") -> dict[str, float]:
    """Compute golf posture metrics for a single frame."""

    lead, trail = side_roles(handedness)
    lead_shoulder = frame.require(_landmark_name(lead, "shoulder"))
    lead_elbow = frame.require(_landmark_name(lead, "elbow"))
    lead_wrist = frame.require(_landmark_name(lead, "wrist"))
    trail_shoulder = frame.require(_landmark_name(trail, "shoulder"))
    trail_elbow = frame.require(_landmark_name(trail, "elbow"))
    trail_wrist = frame.require(_landmark_name(trail, "wrist"))
    lead_hip = frame.require(_landmark_name(lead, "hip"))
    trail_hip = frame.require(_landmark_name(trail, "hip"))
    lead_knee = frame.require(_landmark_name(lead, "knee"))
    trail_knee = frame.require(_landmark_name(trail, "knee"))
    lead_ankle = frame.require(_landmark_name(lead, "ankle"))
    trail_ankle = frame.require(_landmark_name(trail, "ankle"))
    nose = frame.require("nose")

    shoulder_line_left = frame.require("left_shoulder")
    shoulder_line_right = frame.require("right_shoulder")
    hip_line_left = frame.require("left_hip")
    hip_line_right = frame.require("right_hip")
    hip_midpoint = midpoint(lead_hip, trail_hip)

    return {
        "lead_arm_angle_deg": angle_degrees(lead_shoulder, lead_elbow, lead_wrist),
        "trail_elbow_angle_deg": angle_degrees(trail_shoulder, trail_elbow, trail_wrist),
        "lead_knee_angle_deg": angle_degrees(lead_hip, lead_knee, lead_ankle),
        "trail_knee_angle_deg": angle_degrees(trail_hip, trail_knee, trail_ankle),
        "shoulder_hip_separation_deg": line_separation_degrees(
            shoulder_line_left,
            shoulder_line_right,
            hip_line_left,
            hip_line_right,
        ),
        "head_to_hip_midpoint_dist": distance(nose, hip_midpoint),
        "stance_width_dist": distance(lead_ankle, trail_ankle),
    }


def summarize_sequence(sequence: PoseSequence, handedness: str = "right") -> dict[str, object]:
    """Summarize golf metrics across a pose sequence."""

    per_frame = [
        {"time_s": frame.time_s, "phase": frame.phase, "metrics": frame_metrics(frame, handedness)}
        for frame in sequence.frames
    ]
    metric_names = list(per_frame[0]["metrics"].keys()) if per_frame else []
    summary = {
        name: mean(frame_record["metrics"][name] for frame_record in per_frame)
        for name in metric_names
    }
    return {
        "sport": "golf",
        "events": SWING_EVENTS,
        "frames": per_frame,
        "summary": summary,
    }


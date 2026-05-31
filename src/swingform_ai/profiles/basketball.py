"""Basketball shot profile and interpretable metrics."""

from __future__ import annotations

from statistics import mean

from swingform_ai.geometry import angle_degrees, distance, line_separation_degrees
from swingform_ai.schema import FramePose, PoseSequence

SHOT_PHASES = [
    "set",
    "dip",
    "lift",
    "release",
    "follow_through",
    "landing",
]


def _opposite(side: str) -> str:
    if side == "right":
        return "left"
    if side == "left":
        return "right"
    raise ValueError("shooting_side must be 'right' or 'left'.")


def _landmark_name(side: str, joint: str) -> str:
    return f"{side}_{joint}"


def frame_metrics(frame: FramePose, shooting_side: str = "right") -> dict[str, float]:
    """Compute basketball shot-form metrics for a single frame."""

    side = shooting_side.lower()
    guide = _opposite(side)
    shoulder = frame.require(_landmark_name(side, "shoulder"))
    elbow = frame.require(_landmark_name(side, "elbow"))
    wrist = frame.require(_landmark_name(side, "wrist"))
    hip = frame.require(_landmark_name(side, "hip"))
    knee = frame.require(_landmark_name(side, "knee"))
    ankle = frame.require(_landmark_name(side, "ankle"))
    guide_wrist = frame.require(_landmark_name(guide, "wrist"))

    return {
        "shooting_elbow_angle_deg": angle_degrees(shoulder, elbow, wrist),
        "shooting_knee_angle_deg": angle_degrees(hip, knee, ankle),
        "wrist_height_norm": 1.0 - wrist.y,
        "guide_hand_distance": distance(wrist, guide_wrist),
        "shoulder_alignment_deg": line_separation_degrees(
            frame.require("left_shoulder"),
            frame.require("right_shoulder"),
            frame.require("left_hip"),
            frame.require("right_hip"),
        ),
    }


def summarize_sequence(sequence: PoseSequence, shooting_side: str = "right") -> dict[str, object]:
    """Summarize basketball metrics across a pose sequence."""

    per_frame = [
        {"time_s": frame.time_s, "phase": frame.phase, "metrics": frame_metrics(frame, shooting_side)}
        for frame in sequence.frames
    ]
    metric_names = list(per_frame[0]["metrics"].keys()) if per_frame else []
    summary = {
        name: mean(frame_record["metrics"][name] for frame_record in per_frame)
        for name in metric_names
    }
    return {
        "sport": "basketball",
        "phases": SHOT_PHASES,
        "frames": per_frame,
        "summary": summary,
    }


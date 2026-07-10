#!/usr/bin/env python
"""Analyze a local basketball practice video and export open demo assets."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from swingform_ai.geometry import distance
from swingform_ai.profiles import basketball
from swingform_ai.schema import FramePose, Landmark, PoseSequence
from swingform_ai.tracking import PrimaryAthleteTracker
from swingform_ai.video import reencode_h264

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)

MP_LANDMARK_NAMES = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]

SKELETON_EDGES = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
]

SHOT_PHASES = ["set", "dip", "lift", "release", "follow_through", "landing"]
REVIEW_PHASES = ["start", "court_read", "plant", "arm_extension", "shot_context", "finish"]


@dataclass(frozen=True)
class VideoInfo:
    fps: float
    frame_count: int
    width: int
    height: int
    duration_s: float


def ensure_model(model_path: Path) -> Path:
    """Download the local-only MediaPipe pose model when it is missing."""

    if not model_path.exists():
        model_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, model_path)
    return model_path


def read_video_info(video_path: Path) -> VideoInfo:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return VideoInfo(
        fps=fps,
        frame_count=frame_count,
        width=width,
        height=height,
        duration_s=frame_count / fps if fps else 0.0,
    )


def framepose_from_result(
    landmarks: list[Any],
    frame_index: int,
    time_s: float,
) -> FramePose:
    named = {}
    for name, landmark in zip(MP_LANDMARK_NAMES, landmarks):
        named[name] = Landmark(
            name=name,
            x=float(landmark.x),
            y=float(landmark.y),
            z=float(landmark.z),
            visibility=float(getattr(landmark, "visibility", 0.0) or 0.0),
        )
    return FramePose(time_s=time_s, frame_index=frame_index, landmarks=named)


def extract_pose_sequence(video_path: Path, model_path: Path) -> tuple[PoseSequence, VideoInfo]:
    video_info = read_video_info(video_path)
    cap = cv2.VideoCapture(str(video_path))
    base_options = python.BaseOptions(model_asset_path=str(model_path))
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=2,
        min_pose_detection_confidence=0.25,
        min_pose_presence_confidence=0.25,
        min_tracking_confidence=0.25,
    )
    frames: list[FramePose] = []
    tracker = PrimaryAthleteTracker()
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        frame_index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(round((frame_index / video_info.fps) * 1000))
            result = landmarker.detect_for_video(mp_image, timestamp_ms)
            time_s = frame_index / video_info.fps
            candidates = [
                framepose_from_result(landmarks, frame_index=frame_index, time_s=time_s)
                for landmarks in result.pose_landmarks
            ]
            chosen = tracker.select(candidates, time_s)
            if chosen is not None:
                frames.append(chosen)
            frame_index += 1
    cap.release()
    return PoseSequence(frames=frames, source=str(video_path), fps=video_info.fps), video_info


def moving_average(values: list[float], window: int = 7) -> list[float]:
    if not values:
        return []
    half = window // 2
    return [
        mean(values[max(0, idx - half) : min(len(values), idx + half + 1)])
        for idx in range(len(values))
    ]


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[idx]


def _side(side: str, joint: str) -> str:
    return f"{side}_{joint}"


def _midpoint(a: Landmark, b: Landmark) -> tuple[float, float, float]:
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0, (a.z + b.z) / 2.0)


def extra_frame_metrics(frame: FramePose, shooting_side: str) -> dict[str, float]:
    shooting_side = shooting_side.lower()
    wrist = frame.require(_side(shooting_side, "wrist"))
    guide_wrist = frame.require(_side("left" if shooting_side == "right" else "right", "wrist"))
    left_shoulder = frame.require("left_shoulder")
    right_shoulder = frame.require("right_shoulder")
    left_hip = frame.require("left_hip")
    right_hip = frame.require("right_hip")
    left_ankle = frame.require("left_ankle")
    right_ankle = frame.require("right_ankle")
    hip_mid = _midpoint(left_hip, right_hip)
    ankle_mid = _midpoint(left_ankle, right_ankle)
    shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2.0
    return {
        "shooting_wrist_height_norm": 1.0 - wrist.y,
        "guide_wrist_height_norm": 1.0 - guide_wrist.y,
        "max_wrist_height_norm": max(1.0 - wrist.y, 1.0 - guide_wrist.y),
        "shoulder_mid_height_norm": 1.0 - shoulder_mid_y,
        "hip_mid_y": hip_mid[1],
        "ankle_mid_y": ankle_mid[1],
        "body_center_x": hip_mid[0],
        "body_center_y": hip_mid[1],
        "stance_width_dist": distance(left_ankle, right_ankle),
        "mean_visibility": mean(
            float(landmark.visibility or 0.0)
            for landmark in frame.landmarks.values()
            if landmark.visibility is not None
        ),
    }


def build_metric_rows(sequence: PoseSequence, shooting_side: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for frame in sequence.frames:
        base = basketball.frame_metrics(frame, shooting_side=shooting_side)
        extra = extra_frame_metrics(frame, shooting_side=shooting_side)
        rows.append(
            {
                "frame_index": frame.frame_index,
                "time_s": frame.time_s,
                **base,
                **extra,
            }
        )
    wrist_points = [(row["body_center_x"], row["shooting_wrist_height_norm"]) for row in rows]
    body_points = [(row["body_center_x"], row["body_center_y"]) for row in rows]
    wrist_speeds = [0.0]
    body_speeds = [0.0]
    for prev, cur, prev_row, cur_row in zip(wrist_points, wrist_points[1:], rows, rows[1:]):
        dt = max(1e-6, cur_row["time_s"] - prev_row["time_s"])
        wrist_speeds.append(math.dist(prev, cur) / dt)
    for prev, cur, prev_row, cur_row in zip(body_points, body_points[1:], rows, rows[1:]):
        dt = max(1e-6, cur_row["time_s"] - prev_row["time_s"])
        body_speeds.append(math.dist(prev, cur) / dt)
    for row, wrist_speed, body_speed in zip(
        rows,
        moving_average(wrist_speeds, 5),
        moving_average(body_speeds, 5),
    ):
        row["wrist_speed_norm_per_s"] = wrist_speed
        row["body_speed_norm_per_s"] = body_speed
        wrist_above_shoulder = row["max_wrist_height_norm"] - row["shoulder_mid_height_norm"]
        elbow_extension = row["shooting_elbow_angle_deg"] / 180.0
        row["shot_form_score"] = (
            max(0.0, wrist_above_shoulder) * 3.0
            + elbow_extension
            + min(0.4, row["wrist_speed_norm_per_s"]) * 0.3
        )
    return rows


def row_at_frame(rows: list[dict[str, Any]], frame_index: int) -> dict[str, Any]:
    for row in rows:
        if row["frame_index"] == frame_index:
            return row
    raise KeyError(frame_index)


def frame_at_index(sequence: PoseSequence, frame_index: int) -> FramePose:
    for frame in sequence.frames:
        if frame.frame_index == frame_index:
            return frame
    raise KeyError(frame_index)


def detect_shot_events(rows: list[dict[str, Any]], fps: float) -> list[dict[str, Any]]:
    """Detect conservative single-athlete shot-form events."""

    if not rows:
        return []
    scores = moving_average([row["shot_form_score"] for row in rows], window=7)
    release_threshold = max(0.95, percentile(scores, 0.90))
    min_gap = int(max(1, fps * 1.2))
    release_indices: list[int] = []
    for idx in range(2, len(scores) - 2):
        wrist_above_shoulder = rows[idx]["max_wrist_height_norm"] - rows[idx]["shoulder_mid_height_norm"]
        if wrist_above_shoulder < 0.025:
            continue
        if scores[idx] < release_threshold:
            continue
        # Plausibility gate: an upright athlete has shoulders above hips above ankles
        # with non-trivial extent; phantom edge detections and occluded blends fail this.
        torso_height = rows[idx]["hip_mid_y"] - (1.0 - rows[idx]["shoulder_mid_height_norm"])
        leg_height = rows[idx]["ankle_mid_y"] - rows[idx]["hip_mid_y"]
        if torso_height < 0.04 or leg_height < 0.04 or rows[idx]["mean_visibility"] < 0.72:
            continue
        if scores[idx] >= max(scores[idx - 2 : idx + 3]):
            if release_indices and idx - release_indices[-1] < min_gap:
                if scores[idx] > scores[release_indices[-1]]:
                    release_indices[-1] = idx
            else:
                release_indices.append(idx)

    events: list[dict[str, Any]] = []
    for shot_idx, release_idx in enumerate(release_indices, start=1):
        set_start = max(0, release_idx - int(1.25 * fps))
        dip_start = max(0, release_idx - int(0.85 * fps))
        lift_start = max(0, release_idx - int(0.45 * fps))
        landing_end = min(len(rows), release_idx + int(1.1 * fps))
        set_idx = min(
            range(set_start, max(set_start + 1, dip_start)),
            key=lambda idx: rows[idx]["wrist_speed_norm_per_s"],
        )
        dip_idx = min(
            range(dip_start, max(dip_start + 1, lift_start)),
            key=lambda idx: rows[idx]["shooting_knee_angle_deg"],
        )
        lift_idx = max(
            range(lift_start, max(lift_start + 1, release_idx + 1)),
            key=lambda idx: rows[idx]["wrist_speed_norm_per_s"],
        )
        follow_start = min(len(rows) - 1, release_idx + 1)
        follow_end = min(len(rows), release_idx + int(0.45 * fps))
        follow_idx = max(
            range(follow_start, max(follow_start + 1, follow_end)),
            key=lambda idx: rows[idx]["shooting_wrist_height_norm"],
        )
        land_start = min(len(rows) - 1, release_idx + int(0.45 * fps))
        landing_idx = min(
            range(land_start, max(land_start + 1, landing_end)),
            key=lambda idx: rows[idx]["body_speed_norm_per_s"],
        )
        event = {
            "shot": shot_idx,
            "score": scores[release_idx],
            "reliable": True,
        }
        for phase, phase_idx in [
            ("set", set_idx),
            ("dip", dip_idx),
            ("lift", lift_idx),
            ("release", release_idx),
            ("follow_through", follow_idx),
            ("landing", landing_idx),
        ]:
            event[f"{phase}_frame"] = rows[phase_idx]["frame_index"]
            event[f"{phase}_time_s"] = rows[phase_idx]["time_s"]
        events.append(event)
    return events


def select_review_frames(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fallback keyposes when no reliable shot-form event is isolated."""

    if not rows:
        return []
    target_times = [
        0.0,
        rows[-1]["time_s"] * 0.22,
        rows[-1]["time_s"] * 0.42,
        rows[-1]["time_s"] * 0.60,
        rows[-1]["time_s"] * 0.73,
        rows[-1]["time_s"],
    ]
    frames = []
    for label, target in zip(REVIEW_PHASES, target_times):
        row = min(rows, key=lambda item: abs(item["time_s"] - target))
        frames.append({"phase": label, "frame": row["frame_index"], "time_s": row["time_s"]})
    return frames


def write_pose_json(sequence: PoseSequence, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # 4 decimals in normalized coordinates is sub-pixel at any practical
    # resolution and roughly halves the committed file size.
    payload = {
        "source": sequence.source,
        "fps": sequence.fps,
        "frames": [
            {
                "frame_index": frame.frame_index,
                "time_s": round(frame.time_s, 4),
                "landmarks": {
                    name: {
                        "x": round(landmark.x, 4),
                        "y": round(landmark.y, 4),
                        "z": round(landmark.z, 4),
                        "visibility": round(landmark.visibility, 3)
                        if landmark.visibility is not None
                        else None,
                    }
                    for name, landmark in frame.landmarks.items()
                },
            }
            for frame in sequence.frames
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_metrics_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_contact_sheet(video_path: Path, output_path: Path, cols: int = 4, rows: int = 4) -> None:
    info = read_video_info(video_path)
    cap = cv2.VideoCapture(str(video_path))
    thumb_w = 180
    thumb_h = int(thumb_w * info.height / info.width)
    sheet = 255 * __import__("numpy").ones((rows * thumb_h, cols * thumb_w, 3), dtype="uint8")
    sample_count = cols * rows
    for idx in range(sample_count):
        frame_idx = round(idx * (info.frame_count - 1) / max(1, sample_count - 1))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            continue
        thumb = cv2.resize(frame, (thumb_w, thumb_h))
        row_idx = idx // cols
        col_idx = idx % cols
        y0 = row_idx * thumb_h
        x0 = col_idx * thumb_w
        sheet[y0 : y0 + thumb_h, x0 : x0 + thumb_w] = thumb
        label = f"{frame_idx / info.fps:.2f}s"
        cv2.putText(
            sheet,
            label,
            (x0 + 6, y0 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 0, 0),
            3,
            cv2.LINE_AA,
        )
        cv2.putText(
            sheet,
            label,
            (x0 + 6, y0 + 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
    cap.release()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), sheet)


def plot_timeline(
    rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    times = [row["time_s"] for row in rows]
    fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(times, [row["shooting_wrist_height_norm"] for row in rows], color="#2563eb")
    axes[0].plot(times, [row["shoulder_mid_height_norm"] for row in rows], color="#64748b", alpha=0.55)
    axes[0].set_ylabel("Wrist/shoulder height")
    axes[1].plot(times, [row["shooting_elbow_angle_deg"] for row in rows], color="#16a34a")
    axes[1].set_ylabel("Elbow deg")
    axes[2].plot(times, [row["shooting_knee_angle_deg"] for row in rows], color="#dc2626")
    axes[2].set_ylabel("Knee deg")
    axes[3].plot(times, [row["body_speed_norm_per_s"] for row in rows], color="#7c3aed")
    axes[3].set_ylabel("Body speed")
    axes[3].set_xlabel("Video time, seconds")
    colors = {
        "set": "#64748b",
        "dip": "#0f766e",
        "lift": "#2563eb",
        "release": "#ea580c",
        "follow_through": "#9333ea",
        "landing": "#111827",
    }
    for event in events:
        for phase in SHOT_PHASES:
            time_value = event[f"{phase}_time_s"]
            for axis in axes:
                axis.axvline(time_value, color=colors[phase], alpha=0.32, linewidth=1)
            axes[0].text(
                time_value,
                axes[0].get_ylim()[1],
                f"S{event['shot']} {phase}",
                rotation=90,
                va="top",
                ha="right",
                fontsize=8,
                color=colors[phase],
            )
    for axis in axes:
        axis.grid(True, alpha=0.2)
    title = "Basketball Shot-Form Metrics" if events else "Basketball Primary-Athlete Motion Metrics"
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_keyposes(
    sequence: PoseSequence,
    events: list[dict[str, Any]],
    review_frames: list[dict[str, Any]],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if events:
        labels = [
            {"phase": phase, "frame": events[0][f"{phase}_frame"], "time_s": events[0][f"{phase}_time_s"]}
            for phase in SHOT_PHASES
        ]
        title = "Detected Basketball Shot-Form Keyposes"
    else:
        labels = review_frames
        title = "Basketball Body-Motion Review Keyposes"
    fig, axes = plt.subplots(1, len(labels), figsize=(2.3 * len(labels), 4.0))
    if len(labels) == 1:
        axes = [axes]
    for axis, item in zip(axes, labels):
        frame = frame_at_index(sequence, item["frame"])
        xs: list[float] = []
        ys: list[float] = []
        for start, end in SKELETON_EDGES:
            a = frame.require(start)
            b = frame.require(end)
            xs.extend([a.x, b.x])
            ys.extend([a.y, b.y])
            axis.plot([a.x, b.x], [a.y, b.y], color="#111827", linewidth=2.2)
        for landmark_name in [
            "nose",
            "left_shoulder",
            "right_shoulder",
            "left_elbow",
            "right_elbow",
            "left_wrist",
            "right_wrist",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_ankle",
            "right_ankle",
        ]:
            landmark = frame.require(landmark_name)
            xs.append(landmark.x)
            ys.append(landmark.y)
            axis.scatter([landmark.x], [landmark.y], s=16, color="#2563eb")
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        x_pad = max(0.06, (x_max - x_min) * 0.45)
        y_pad = max(0.08, (y_max - y_min) * 0.25)
        axis.set_xlim(max(0.0, x_min - x_pad), min(1.0, x_max + x_pad))
        axis.set_ylim(min(1.02, y_max + y_pad), max(0.0, y_min - y_pad))
        axis.set_aspect("equal", adjustable="box")
        axis.axis("off")
        axis.set_title(f"{item['phase']}\n{item['time_s']:.2f}s", fontsize=9)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def lm_px(landmark: Landmark, width: int, height: int) -> tuple[int, int]:
    return (int(landmark.x * width), int(landmark.y * height))


def draw_skeleton(frame: Any, frame_pose: FramePose) -> None:
    height, width = frame.shape[:2]
    edge_colors = {
        ("left_shoulder", "right_shoulder"): (255, 229, 0),
        ("left_shoulder", "left_hip"): (255, 229, 0),
        ("right_shoulder", "right_hip"): (255, 229, 0),
        ("left_hip", "right_hip"): (255, 229, 0),
        ("left_shoulder", "left_elbow"): (64, 201, 255),
        ("left_elbow", "left_wrist"): (64, 201, 255),
        ("right_shoulder", "right_elbow"): (64, 201, 255),
        ("right_elbow", "right_wrist"): (64, 201, 255),
        ("left_hip", "left_knee"): (85, 255, 57),
        ("left_knee", "left_ankle"): (85, 255, 57),
        ("right_hip", "right_knee"): (85, 255, 57),
        ("right_knee", "right_ankle"): (85, 255, 57),
    }
    for start, end in SKELETON_EDGES:
        a = frame_pose.require(start)
        b = frame_pose.require(end)
        color = edge_colors.get((start, end), (235, 235, 235))
        cv2.line(frame, lm_px(a, width, height), lm_px(b, width, height), color, 3, cv2.LINE_AA)
    for name in [
        "nose",
        "left_shoulder",
        "right_shoulder",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
        "left_hip",
        "right_hip",
        "left_knee",
        "right_knee",
        "left_ankle",
        "right_ankle",
    ]:
        point = lm_px(frame_pose.require(name), width, height)
        color = (255, 255, 255) if name == "nose" else (255, 200, 64)
        cv2.circle(frame, point, 6, color, -1, cv2.LINE_AA)
        cv2.circle(frame, point, 6, (25, 25, 25), 1, cv2.LINE_AA)


def draw_hud(frame: Any, time_s: float, label: str | None) -> None:
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, 34), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.58, frame, 0.42, 0, dst=frame)
    cv2.putText(
        frame,
        f"{time_s:.2f}s",
        (10, 23),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (230, 230, 230),
        1,
        cv2.LINE_AA,
    )
    if label:
        text = label.upper().replace("_", " ")
        text_width = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)[0][0]
        cv2.putText(
            frame,
            text,
            (width - text_width - 10, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (40, 210, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.rectangle(frame, (0, 0), (5, height), (40, 210, 255), -1)


def render_overlay_video(
    video_path: Path,
    sequence: PoseSequence,
    video_info: VideoInfo,
    events: list[dict[str, Any]],
    review_frames: list[dict[str, Any]],
    output_path: Path,
) -> None:
    pose_index = {frame.frame_index: frame for frame in sequence.frames}
    label_map: dict[int, str] = {}
    if events:
        for event in events:
            for phase in SHOT_PHASES:
                label_map[event[f"{phase}_frame"]] = f"shot {event['shot']} {phase}"
    else:
        for item in review_frames:
            label_map[item["frame"]] = item["phase"]

    cap = cv2.VideoCapture(str(video_path))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path),
        fourcc,
        video_info.fps,
        (video_info.width, video_info.height),
    )
    active_label: str | None = None
    active_left = 0
    frame_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_index in label_map:
            active_label = label_map[frame_index]
            active_left = int(video_info.fps * 0.85)
        frame_pose = pose_index.get(frame_index)
        if frame_pose is not None:
            draw_skeleton(frame, frame_pose)
        draw_hud(frame, frame_index / video_info.fps, active_label if active_left > 0 else None)
        if active_left > 0:
            active_left -= 1
        writer.write(frame)
        frame_index += 1
    cap.release()
    writer.release()


def plausible_row(row: dict[str, Any]) -> bool:
    torso_height = row["hip_mid_y"] - (1.0 - row["shoulder_mid_height_norm"])
    leg_height = row["ankle_mid_y"] - row["hip_mid_y"]
    return torso_height > 0.02 and leg_height > 0.02 and row["mean_visibility"] >= 0.6


def metric_rows_for_summary(
    rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rows that feed the motion summary.

    Whole-clip aggregates are dominated by transition frames and tracking
    noise; when shot events exist, summarize only plausible frames inside
    the detected set-to-landing windows.
    """

    gated = [row for row in rows if plausible_row(row)]
    if not events:
        return gated or rows
    windowed = [
        row
        for row in gated
        if any(event["set_time_s"] <= row["time_s"] <= event["landing_time_s"] for event in events)
    ]
    return windowed or gated or rows


def summarize_motion(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        return {}
    return {
        "mean_visibility": mean(row["mean_visibility"] for row in rows),
        "mean_shooting_elbow_angle_deg": mean(row["shooting_elbow_angle_deg"] for row in rows),
        "max_shooting_wrist_height_norm": max(row["shooting_wrist_height_norm"] for row in rows),
        "min_shooting_knee_angle_deg": min(row["shooting_knee_angle_deg"] for row in rows),
        "mean_body_speed_norm_per_s": mean(row["body_speed_norm_per_s"] for row in rows),
    }


def build_public_summary(
    video_info: VideoInfo,
    sequence: PoseSequence,
    rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
    review_frames: list[dict[str, Any]],
    example_dir: Path,
) -> dict[str, Any]:
    return {
        "schema_version": "basketball-session-v1",
        "source": (example_dir / "basketball.mp4").as_posix(),
        "release_note": "This open example includes a cleared source clip plus derived pose and metric files.",
        "video": {
            "duration_s": video_info.duration_s,
            "fps": video_info.fps,
            "total_frames": video_info.frame_count,
            "width": video_info.width,
            "height": video_info.height,
        },
        "pose": {
            "backend": "MediaPipe Pose Landmarker Lite",
            "detected_frames": len(sequence.frames),
            "total_frames": video_info.frame_count,
            "coverage_pct": 100.0 * len(sequence.frames) / video_info.frame_count,
            "mean_visibility": mean(row["mean_visibility"] for row in rows) if rows else 0.0,
        },
        "sport": "basketball",
        "shot_events": events,
        "review_frames": review_frames,
        "motion_summary": summarize_motion(metric_rows_for_summary(rows, events)),
        "motion_summary_scope": "plausible frames within detected shot windows"
        if events
        else "plausible frames across the clip",
        "limitations": [
            "Single-camera 2D/pseudo-3D body pose only.",
            "The detector tracks the primary visible athlete and uses body pose only.",
            "The release label is a pose-based proxy from visible wrist height, wrist speed, and arm extension.",
            "No ball, rim, make/miss, release angle, shot arc, or jump height model is claimed.",
        ],
    }


def write_summary_markdown(
    summary: dict[str, Any],
    output_path: Path,
    asset_prefix: str,
    title: str,
    example_dir: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    video = summary["video"]
    pose = summary["pose"]
    motion = summary["motion_summary"]
    events = summary["shot_events"]
    example = example_dir.as_posix()
    lines = [
        f"# {title}",
        "",
        "This demo adds basketball to the same personal motion-record format used for the golf examples.",
        "It is useful as a body-motion and release-proxy baseline, not yet as a ball-flight or make/miss analysis.",
        "",
        f"![Contact sheet]({asset_prefix}/contact_sheet.jpg)",
        "",
        f"![Metric timeline]({asset_prefix}/metric_timeline.png)",
        "",
        f"![Skeleton keyposes]({asset_prefix}/skeleton_keyposes.png)",
        "",
        "## Open Example Files",
        "",
        "| File | Use |",
        "| --- | --- |",
        f"| `{example}/basketball.mp4` | Source basketball court clip |",
        f"| `{example}/basketball_overlay.mp4` | Skeleton overlay review video |",
        f"| `{example}/pose_sequence.json` | MediaPipe pose landmarks for tracked frames |",
        f"| `{example}/metrics.csv` | Per-frame basketball motion metrics |",
        f"| `{example}/summary.json` | Demo summary for reports |",
        "",
        "## Video and Detection",
        "",
        f"- Duration: {video['duration_s']:.2f}s",
        f"- Resolution: {video['width']}x{video['height']}",
        f"- FPS: {video['fps']:.2f}",
        f"- Pose coverage: {pose['detected_frames']} of {pose['total_frames']} frames "
        f"({pose['coverage_pct']:.1f}%)",
        f"- Mean landmark visibility: {pose['mean_visibility']:.3f}",
        f"- Reliable shot-form events isolated: {len(events)}",
        "",
        "## Main Read",
        "",
        "- Golf and basketball should stay as separate sport profiles inside the same repository.",
        "- This clip proves the basketball profile can export the same core artifacts: video, pose JSON, metrics CSV, charts, and a report.",
        "- This simpler clip tracks one primary athlete cleanly and isolates one basketball release-proxy event.",
        "- The release label is pose-based: it comes from visible wrist height, wrist speed, and arm extension, not from ball contact.",
        "- The next technical step is ball/rim association before making make/miss, shot-arc, or release-angle claims.",
        "",
        "## Basketball Metrics",
        "",
        f"Computed over {summary.get('motion_summary_scope', 'all tracked frames')}.",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Mean shooting elbow angle | {motion['mean_shooting_elbow_angle_deg']:.1f} deg |",
        f"| Max shooting wrist height proxy | {motion['max_shooting_wrist_height_norm']:.3f} |",
        f"| Min shooting knee angle | {motion['min_shooting_knee_angle_deg']:.1f} deg |",
        f"| Mean body speed proxy | {motion['mean_body_speed_norm_per_s']:.3f} |",
        "",
        "## Interpretation",
        "",
        "The best product direction is a personal multi-sport movement record: compare Yifan against Yifan first, then use cleaner labels to train sport-specific phase models later.",
        "Golf can keep its address/top/impact/finish loop, while basketball gets set/dip/lift/release/follow-through/landing labels as pose proxies first and ball-linked events later.",
        "",
    ]
    if events:
        lines.extend(
            [
                "## Detected Shot Events",
                "",
                "| Shot | Set | Dip | Lift | Release proxy | Follow-through | Landing |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for event in events:
            lines.append(
                f"| {event['shot']} | {event['set_time_s']:.2f}s | {event['dip_time_s']:.2f}s | "
                f"{event['lift_time_s']:.2f}s | {event['release_time_s']:.2f}s | "
                f"{event['follow_through_time_s']:.2f}s | {event['landing_time_s']:.2f}s |"
            )
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--shooting-side", choices=["right", "left"], default="right")
    parser.add_argument("--model", type=Path, default=Path("models/local/pose_landmarker_lite.task"))
    parser.add_argument("--example-output", type=Path, default=None, help="Defaults to examples/<session-id>.")
    parser.add_argument("--asset-output", type=Path, default=None, help="Defaults to docs/assets/<session-id>.")
    parser.add_argument("--example-doc", type=Path, default=None, help="Defaults to docs/examples/<session-id>.md.")
    parser.add_argument("--title", default=None, help="Report title. Defaults to a readable form of the session id.")
    parser.add_argument("--copy-video", action="store_true", help="Copy the source clip into the example folder.")
    parser.add_argument("--render-overlay", action="store_true", help="Render a skeleton overlay review video.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.example_output is None:
        args.example_output = Path("examples") / args.session_id
    if args.asset_output is None:
        args.asset_output = Path("docs/assets") / args.session_id
    if args.example_doc is None:
        args.example_doc = Path("docs/examples") / f"{args.session_id}.md"
    title = args.title or args.session_id.replace("-", " ").title()
    model_path = ensure_model(args.model)
    sequence, video_info = extract_pose_sequence(args.video, model_path)
    rows = build_metric_rows(sequence, args.shooting_side)
    events = detect_shot_events(rows, video_info.fps)
    review_frames = select_review_frames(rows)
    summary = build_public_summary(video_info, sequence, rows, events, review_frames, args.example_output)

    args.example_output.mkdir(parents=True, exist_ok=True)
    if args.copy_video:
        target_video = args.example_output / "basketball.mp4"
        if args.video.resolve() != target_video.resolve():
            shutil.copy2(args.video, target_video)
    if args.render_overlay:
        overlay_path = args.example_output / "basketball_overlay.mp4"
        render_overlay_video(
            args.video,
            sequence,
            video_info,
            events,
            review_frames,
            overlay_path,
        )
        if not reencode_h264(overlay_path):
            print("warning: H.264 re-encode unavailable, overlay left as mp4v")
    write_pose_json(sequence, args.example_output / "pose_sequence.json")
    write_metrics_csv(rows, args.example_output / "metrics.csv")
    (args.example_output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    args.asset_output.mkdir(parents=True, exist_ok=True)
    write_contact_sheet(args.video, args.asset_output / "contact_sheet.jpg")
    plot_timeline(rows, events, args.asset_output / "metric_timeline.png")
    plot_keyposes(sequence, events, review_frames, args.asset_output / "skeleton_keyposes.png")
    write_summary_markdown(
        summary,
        args.example_doc,
        f"../assets/{args.asset_output.name}",
        title=title,
        example_dir=args.example_output,
    )
    print(
        json.dumps(
            {
                "session_id": args.session_id,
                "detected_frames": len(sequence.frames),
                "total_frames": video_info.frame_count,
                "shot_event_count": len(events),
                "example_output": str(args.example_output),
                "asset_output": str(args.asset_output),
                "example_doc": str(args.example_doc),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

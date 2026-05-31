#!/usr/bin/env python
"""Analyze a cleared golf swing video and export open demo assets."""

from __future__ import annotations

import argparse
import csv
import json
import math
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

from swingform_ai.geometry import angle_degrees, distance, line_angle_2d
from swingform_ai.profiles import golf
from swingform_ai.schema import FramePose, Landmark, PoseSequence

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
    fps = float(cap.get(cv2.CAP_PROP_FPS))
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
        num_poses=1,
        min_pose_detection_confidence=0.35,
        min_pose_presence_confidence=0.35,
        min_tracking_confidence=0.35,
    )
    frames: list[FramePose] = []
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
            if result.pose_landmarks:
                frames.append(
                    framepose_from_result(
                        result.pose_landmarks[0],
                        frame_index=frame_index,
                        time_s=frame_index / video_info.fps,
                    )
                )
            frame_index += 1
    cap.release()
    return PoseSequence(frames=frames, source=str(video_path), fps=video_info.fps), video_info


def moving_average(values: list[float], window: int = 9) -> list[float]:
    if not values:
        return []
    half = window // 2
    smoothed = []
    for idx in range(len(values)):
        start = max(0, idx - half)
        end = min(len(values), idx + half + 1)
        smoothed.append(mean(values[start:end]))
    return smoothed


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[idx]


def wrist_midpoint(frame: FramePose) -> tuple[float, float, float]:
    left = frame.require("left_wrist")
    right = frame.require("right_wrist")
    return ((left.x + right.x) / 2.0, (left.y + right.y) / 2.0, (left.z + right.z) / 2.0)


def body_center(frame: FramePose) -> tuple[float, float, float]:
    left = frame.require("left_hip")
    right = frame.require("right_hip")
    return ((left.x + right.x) / 2.0, (left.y + right.y) / 2.0, (left.z + right.z) / 2.0)


def extra_frame_metrics(frame: FramePose, address_frame: FramePose | None = None) -> dict[str, float]:
    left_wrist = frame.require("left_wrist")
    right_wrist = frame.require("right_wrist")
    left_shoulder = frame.require("left_shoulder")
    right_shoulder = frame.require("right_shoulder")
    left_hip = frame.require("left_hip")
    right_hip = frame.require("right_hip")
    nose = frame.require("nose")
    wrist_mid = wrist_midpoint(frame)
    shoulder_mid = (
        (left_shoulder.x + right_shoulder.x) / 2.0,
        (left_shoulder.y + right_shoulder.y) / 2.0,
        0.0,
    )
    hip_mid = ((left_hip.x + right_hip.x) / 2.0, (left_hip.y + right_hip.y) / 2.0, 0.0)
    torso_line_angle = line_angle_2d(hip_mid, shoulder_mid)
    metrics = {
        "wrist_mid_x": wrist_mid[0],
        "wrist_mid_y": wrist_mid[1],
        "hand_height_norm": 1.0 - wrist_mid[1],
        "left_wrist_height_norm": 1.0 - left_wrist.y,
        "right_wrist_height_norm": 1.0 - right_wrist.y,
        "torso_line_angle_deg": torso_line_angle,
        "left_elbow_angle_deg": angle_degrees(left_shoulder, frame.require("left_elbow"), left_wrist),
        "right_elbow_angle_deg": angle_degrees(right_shoulder, frame.require("right_elbow"), right_wrist),
        "mean_visibility": mean(
            float(l.visibility or 0.0)
            for l in frame.landmarks.values()
            if l.visibility is not None
        ),
    }
    if address_frame is not None:
        metrics["head_drift_from_address"] = distance(nose, address_frame.require("nose"))
        metrics["hip_drift_from_address"] = distance(body_center(frame), body_center(address_frame))
    return metrics


def build_metric_rows(sequence: PoseSequence, handedness: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for frame in sequence.frames:
        base = golf.frame_metrics(frame, handedness=handedness)
        extra = extra_frame_metrics(frame)
        rows.append(
            {
                "frame_index": frame.frame_index,
                "time_s": frame.time_s,
                **base,
                **extra,
            }
        )
    wrist = [(row["wrist_mid_x"], row["wrist_mid_y"]) for row in rows]
    speeds = [0.0]
    for prev, cur, prev_row, cur_row in zip(wrist, wrist[1:], rows, rows[1:]):
        dt = max(1e-6, cur_row["time_s"] - prev_row["time_s"])
        speeds.append(math.dist(prev, cur) / dt)
    for row, speed in zip(rows, moving_average(speeds, 5)):
        row["wrist_speed_norm_per_s"] = speed
    return rows


def detect_swing_events(rows: list[dict[str, Any]], fps: float) -> list[dict[str, Any]]:
    """Detect two or more golf-swing event groups using wrist path heuristics."""

    if not rows:
        return []
    y_values = moving_average([float(row["wrist_mid_y"]) for row in rows], window=9)
    top_threshold = percentile(y_values, 0.20)
    min_gap = int(max(1, fps * 2.2))
    candidate_indices: list[int] = []
    for idx in range(2, len(y_values) - 2):
        if y_values[idx] <= top_threshold and y_values[idx] <= min(y_values[idx - 2 : idx + 3]):
            if candidate_indices and idx - candidate_indices[-1] < min_gap:
                if y_values[idx] < y_values[candidate_indices[-1]]:
                    candidate_indices[-1] = idx
            else:
                candidate_indices.append(idx)

    events: list[dict[str, Any]] = []
    for swing_idx, top_idx in enumerate(candidate_indices, start=1):
        top_time = rows[top_idx]["time_s"]
        start_idx = max(0, top_idx - int(2.6 * fps))
        end_before_top = max(start_idx + 1, top_idx - int(0.25 * fps))
        address_idx = max(
            range(start_idx, end_before_top),
            key=lambda idx: rows[idx]["wrist_mid_y"] - 0.08 * rows[idx]["wrist_speed_norm_per_s"],
        )
        address_y = rows[address_idx]["wrist_mid_y"]
        post_start = min(len(rows) - 1, top_idx + int(0.15 * fps))
        post_end = min(len(rows), top_idx + int(1.4 * fps))
        if post_start >= post_end:
            impact_idx = top_idx
        else:
            impact_idx = min(
                range(post_start, post_end),
                key=lambda idx: abs(rows[idx]["wrist_mid_y"] - address_y)
                - 0.02 * rows[idx]["wrist_speed_norm_per_s"],
            )
        finish_start = min(len(rows) - 1, impact_idx + int(0.45 * fps))
        finish_end = min(len(rows), top_idx + int(2.4 * fps))
        if finish_start >= finish_end:
            finish_idx = min(len(rows) - 1, top_idx + int(1.4 * fps))
        else:
            local_speeds = [rows[idx]["wrist_speed_norm_per_s"] for idx in range(finish_start, finish_end)]
            low_speed = percentile(local_speeds, 0.35)
            finish_candidates = [
                idx for idx in range(finish_start, finish_end)
                if rows[idx]["wrist_speed_norm_per_s"] <= low_speed
            ]
            finish_idx = finish_candidates[-1] if finish_candidates else finish_end - 1
        events.append(
            {
                "swing": swing_idx,
                "address_frame": rows[address_idx]["frame_index"],
                "top_frame": rows[top_idx]["frame_index"],
                "impact_frame": rows[impact_idx]["frame_index"],
                "finish_frame": rows[finish_idx]["frame_index"],
                "address_time_s": rows[address_idx]["time_s"],
                "top_time_s": top_time,
                "impact_time_s": rows[impact_idx]["time_s"],
                "finish_time_s": rows[finish_idx]["time_s"],
            }
        )
    return events


def nearest_row_for_time(rows: list[dict[str, Any]], time_s: float) -> dict[str, Any]:
    return min(rows, key=lambda row: abs(float(row["time_s"]) - time_s))


def load_event_labels(events_path: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Load human-checked event labels and snap them to detected pose frames."""

    payload = json.loads(events_path.read_text(encoding="utf-8"))
    events: list[dict[str, Any]] = []
    for item in payload["swings"]:
        event: dict[str, Any] = {"swing": item["swing"], "label": item.get("label", "")}
        for phase in ["address", "top", "impact", "finish"]:
            row = nearest_row_for_time(rows, float(item[f"{phase}_time_s"]))
            event[f"{phase}_frame"] = row["frame_index"]
            event[f"{phase}_time_s"] = row["time_s"]
        events.append(event)
    return events


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


def summarize_swings(
    sequence: PoseSequence,
    rows: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for event in events:
        address_row = row_at_frame(rows, event["address_frame"])
        top_row = row_at_frame(rows, event["top_frame"])
        impact_row = row_at_frame(rows, event["impact_frame"])
        finish_row = row_at_frame(rows, event["finish_frame"])
        address_frame = frame_at_index(sequence, event["address_frame"])
        impact_extra = extra_frame_metrics(frame_at_index(sequence, event["impact_frame"]), address_frame)
        finish_extra = extra_frame_metrics(frame_at_index(sequence, event["finish_frame"]), address_frame)
        backswing_time = event["top_time_s"] - event["address_time_s"]
        downswing_time = event["impact_time_s"] - event["top_time_s"]
        tempo_ratio = backswing_time / downswing_time if downswing_time > 0 else None
        summaries.append(
            {
                **event,
                "backswing_time_s": backswing_time,
                "downswing_time_s": downswing_time,
                "tempo_ratio": tempo_ratio,
                "address": {
                    "lead_knee_angle_deg": address_row["lead_knee_angle_deg"],
                    "trail_knee_angle_deg": address_row["trail_knee_angle_deg"],
                    "stance_width_dist": address_row["stance_width_dist"],
                    "torso_line_angle_deg": address_row["torso_line_angle_deg"],
                    "mean_visibility": address_row["mean_visibility"],
                },
                "top": {
                    "lead_arm_angle_deg": top_row["lead_arm_angle_deg"],
                    "trail_elbow_angle_deg": top_row["trail_elbow_angle_deg"],
                    "shoulder_hip_separation_deg": top_row["shoulder_hip_separation_deg"],
                    "hand_height_norm": top_row["hand_height_norm"],
                    "mean_visibility": top_row["mean_visibility"],
                },
                "impact": {
                    "lead_knee_angle_deg": impact_row["lead_knee_angle_deg"],
                    "trail_knee_angle_deg": impact_row["trail_knee_angle_deg"],
                    "head_drift_from_address": impact_extra["head_drift_from_address"],
                    "hip_drift_from_address": impact_extra["hip_drift_from_address"],
                    "mean_visibility": impact_row["mean_visibility"],
                },
                "finish": {
                    "head_drift_from_address": finish_extra["head_drift_from_address"],
                    "hip_drift_from_address": finish_extra["hip_drift_from_address"],
                    "mean_visibility": finish_row["mean_visibility"],
                },
            }
        )
    return summaries


def write_pose_json(sequence: PoseSequence, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": sequence.source,
        "fps": sequence.fps,
        "frames": [
            {
                "frame_index": frame.frame_index,
                "time_s": frame.time_s,
                "landmarks": {
                    name: {
                        "x": landmark.x,
                        "y": landmark.y,
                        "z": landmark.z,
                        "visibility": landmark.visibility,
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
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_timeline(rows: list[dict[str, Any]], events: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    times = [row["time_s"] for row in rows]
    fig, axes = plt.subplots(4, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(times, [row["hand_height_norm"] for row in rows], color="#2563eb", linewidth=1.8)
    axes[0].set_ylabel("Hand height")
    axes[1].plot(times, [row["lead_arm_angle_deg"] for row in rows], color="#16a34a", linewidth=1.8)
    axes[1].set_ylabel("Lead arm deg")
    axes[2].plot(times, [row["shoulder_hip_separation_deg"] for row in rows], color="#dc2626", linewidth=1.8)
    axes[2].set_ylabel("Shoulder-hip deg")
    axes[3].plot(times, [row["wrist_speed_norm_per_s"] for row in rows], color="#7c3aed", linewidth=1.8)
    axes[3].set_ylabel("Wrist speed")
    axes[3].set_xlabel("Video time, seconds")

    event_colors = {
        "address": "#64748b",
        "top": "#0f766e",
        "impact": "#ea580c",
        "finish": "#9333ea",
    }
    for event in events:
        for name in ["address", "top", "impact", "finish"]:
            time_value = event[f"{name}_time_s"]
            for ax in axes:
                ax.axvline(time_value, color=event_colors[name], alpha=0.35, linewidth=1)
            axes[0].text(
                time_value,
                axes[0].get_ylim()[1],
                f"S{event['swing']} {name}",
                rotation=90,
                va="top",
                ha="right",
                fontsize=8,
                color=event_colors[name],
            )
    for ax in axes:
        ax.grid(True, alpha=0.2)
    fig.suptitle("Golf Swing Pose Metrics from Local Video")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def plot_keyposes(
    sequence: PoseSequence,
    events: list[dict[str, Any]],
    output_path: Path,
    max_swings: int = 2,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected = events[:max_swings]
    columns = ["address", "top", "impact", "finish"]
    fig, axes = plt.subplots(len(selected), len(columns), figsize=(12, 3.5 * len(selected)))
    if len(selected) == 1:
        axes = [axes]
    for row_idx, event in enumerate(selected):
        for col_idx, phase in enumerate(columns):
            ax = axes[row_idx][col_idx]
            frame = frame_at_index(sequence, event[f"{phase}_frame"])
            for start, end in SKELETON_EDGES:
                a = frame.require(start)
                b = frame.require(end)
                ax.plot([a.x, b.x], [a.y, b.y], color="#111827", linewidth=2.5)
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
                ax.scatter([landmark.x], [landmark.y], s=18, color="#2563eb")
            ax.set_xlim(0.25, 0.75)
            ax.set_ylim(1.02, 0.05)
            ax.set_aspect("equal", adjustable="box")
            ax.axis("off")
            ax.set_title(f"S{event['swing']} {phase}\n{event[f'{phase}_time_s']:.2f}s")
    fig.suptitle("Public-Safe Skeleton Keyposes, Raw Video Not Committed")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def write_summary_markdown(
    summary: dict[str, Any],
    output_path: Path,
    asset_prefix: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    swings = summary["swing_summaries"]
    lines = [
        "# Golf Swing Demo, 2026-05-31",
        "",
        "This demo analyzes an open driving-range example video.",
        "The source clip, pose export, metrics, report summary, and visual indexes are committed so the example is inspectable.",
        "",
        f"![Metric timeline]({asset_prefix}/metric_timeline.png)",
        "",
        f"![Skeleton keyposes]({asset_prefix}/skeleton_keyposes.png)",
        "",
        "## Open Example Files",
        "",
        "| File | Use |",
        "| --- | --- |",
        "| `examples/golf-swing-demo/golf.mp4` | Source golf swing clip |",
        "| `examples/golf-swing-demo/pose_sequence.json` | MediaPipe pose landmarks for every frame |",
        "| `examples/golf-swing-demo/metrics.csv` | Per-frame kinematic metrics |",
        "| `examples/golf-swing-demo/summary.json` | Demo summary for reports |",
        "| `examples/golf-swing-demo/contact_sheet.jpg` | Full-video visual index |",
        "| `examples/golf-swing-demo/swing_timeline.jpg` | Human-check timeline for event labels |",
        "",
        "## Video and Detection",
        "",
        f"- Duration: {summary['video']['duration_s']:.2f}s",
        f"- Resolution: {summary['video']['width']}x{summary['video']['height']}",
        f"- FPS: {summary['video']['fps']:.2f}",
        f"- Pose coverage: {summary['pose']['detected_frames']} of {summary['pose']['total_frames']} frames "
        f"({summary['pose']['coverage_pct']:.1f}%)",
        f"- Mean landmark visibility: {summary['pose']['mean_visibility']:.3f}",
        "",
        "## Detected Swing Events",
        "",
        "Event labels are human-checked for this first example. `Impact` is treated as an impact or low-point proxy because the pipeline does not yet track the ball or club head.",
        "",
        "| Swing | Label | Address | Top | Impact proxy | Finish | Backswing | Downswing | Tempo ratio |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for swing in swings:
        lines.append(
            f"| {swing['swing']} | {swing.get('label', '')} | "
            f"{swing['address_time_s']:.2f}s | {swing['top_time_s']:.2f}s | "
            f"{swing['impact_time_s']:.2f}s | {swing['finish_time_s']:.2f}s | "
            f"{swing['backswing_time_s']:.2f}s | {swing['downswing_time_s']:.2f}s | "
            f"{swing['tempo_ratio']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Main Read",
            "",
            "- The clip contains two detectable swing cycles plus reset time.",
            "- Pose coverage is strong enough for a first body-kinematics pass.",
            "- The first motion is a slower practice motion; the second motion is the fuller shot-like swing.",
            "- The current analysis measures body posture and timing. It does not yet measure club speed, ball speed, spin, carry distance, or launch angle.",
            "- The next technical step is to use these labels to validate the automatic event detector, then add club and ball tracking.",
            "",
            "## Technology Layers Used",
            "",
            "1. Video QA: resolution, duration, frame rate, and pose coverage.",
            "2. MediaPipe Pose Landmarker: frame-level body landmarks.",
            "3. Kinematic geometry: elbows, knees, shoulder-hip separation, hand height, and drift proxies.",
            "4. Temporal analysis: address, top, impact proxy, finish, backswing time, downswing time, and tempo ratio.",
        "5. Open example publication: source clip, pose export, metrics, and report assets.",
            "",
            "## Per-Swing Metrics",
            "",
            "| Swing | Top lead arm | Top trail elbow | Top shoulder-hip separation | Impact head drift | Finish hip drift |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for swing in swings:
        lines.append(
            f"| {swing['swing']} | {swing['top']['lead_arm_angle_deg']:.1f} deg | "
            f"{swing['top']['trail_elbow_angle_deg']:.1f} deg | "
            f"{swing['top']['shoulder_hip_separation_deg']:.1f} deg | "
            f"{swing['impact']['head_drift_from_address']:.3f} | "
            f"{swing['finish']['hip_drift_from_address']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "These numbers are best used as a personal baseline, not as universal coaching truth. "
            "The strongest immediate value is repeatability: new sessions can be compared against this first local baseline.",
            "",
            "## First Coaching Read",
            "",
            "- Camera and lighting were good enough for full-frame pose coverage, but the side/back angle limits true 3D rotation analysis.",
            "- Both motions reached the checked top position about 1.20s after address, while the fuller second swing moved from top to impact proxy faster.",
            "- Head and hip drift are now measurable baselines. Future sessions should compare against these values rather than against a generic pro template first.",
            "- Shoulder-hip separation from a single vertical phone video is only a weak image-plane proxy. Treat it as a trend metric until 3D or multi-view capture is added.",
            "",
        ]
    )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def build_public_summary(
    video_info: VideoInfo,
    sequence: PoseSequence,
    rows: list[dict[str, Any]],
    swing_summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    mean_visibility = mean(row["mean_visibility"] for row in rows) if rows else 0.0
    return {
        "schema_version": "golf-swing-demo-v1",
        "source": "examples/golf-swing-demo/golf.mp4",
        "release_note": "This open-source demo includes the source clip plus derived pose and metric files.",
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
            "mean_visibility": mean_visibility,
        },
        "swing_summaries": swing_summaries,
        "limitations": [
            "Single-camera 2D/pseudo-3D body pose only.",
            "No club-head speed, ball speed, spin, launch angle, or carry distance.",
            "Automatic event timing is still heuristic. This demo uses human-checked labels.",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--handedness", choices=["right", "left"], default="right")
    parser.add_argument("--model", type=Path, default=Path("models/local/pose_landmarker_lite.task"))
    parser.add_argument("--local-output", type=Path, default=Path("data/local/reports"))
    parser.add_argument("--public-output", type=Path, default=Path("docs/assets/golf-swing-demo"))
    parser.add_argument("--public-summary", type=Path, default=Path("examples/golf_swing_demo_summary.json"))
    parser.add_argument("--example-doc", type=Path, default=Path("docs/examples/golf_swing_demo_2026-05-31.md"))
    parser.add_argument("--events-json", type=Path, help="Optional human-checked event labels.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    model_path = ensure_model(args.model)
    sequence, video_info = extract_pose_sequence(args.video, model_path)
    rows = build_metric_rows(sequence, args.handedness)
    events = load_event_labels(args.events_json, rows) if args.events_json else detect_swing_events(rows, video_info.fps)
    swing_summaries = summarize_swings(sequence, rows, events)
    summary = build_public_summary(video_info, sequence, rows, swing_summaries)

    local_dir = args.local_output / args.session_id
    write_pose_json(sequence, local_dir / "pose_sequence.json")
    write_metrics_csv(rows, local_dir / "metrics.csv")
    (local_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    args.public_output.mkdir(parents=True, exist_ok=True)
    plot_timeline(rows, events, args.public_output / "metric_timeline.png")
    plot_keyposes(sequence, events, args.public_output / "skeleton_keyposes.png")
    args.public_summary.parent.mkdir(parents=True, exist_ok=True)
    args.public_summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_summary_markdown(summary, args.example_doc, "../assets/golf-swing-demo")
    print(json.dumps({
        "session_id": args.session_id,
        "detected_frames": len(sequence.frames),
        "total_frames": video_info.frame_count,
        "swing_count": len(events),
        "local_output": str(local_dir),
        "public_output": str(args.public_output),
        "public_summary": str(args.public_summary),
        "example_doc": str(args.example_doc),
    }, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""
Full pipeline: video → pose → swing events → ball detection → effects video.
Run with: python scripts/golf_render.py path/to/video.mp4 --output out.mp4
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

import cv2
import matplotlib
matplotlib.use("Agg")
import numpy as np
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
DEFAULT_MODEL = Path("models/local/pose_landmarker_lite.task")

MP_LANDMARK_NAMES = [
    "nose","left_eye_inner","left_eye","left_eye_outer",
    "right_eye_inner","right_eye","right_eye_outer",
    "left_ear","right_ear","mouth_left","mouth_right",
    "left_shoulder","right_shoulder","left_elbow","right_elbow",
    "left_wrist","right_wrist","left_pinky","right_pinky",
    "left_index","right_index","left_thumb","right_thumb",
    "left_hip","right_hip","left_knee","right_knee",
    "left_ankle","right_ankle","left_heel","right_heel",
    "left_foot_index","right_foot_index",
]

SKELETON_EDGES = [
    ("left_shoulder","right_shoulder"),
    ("left_shoulder","left_elbow"),("left_elbow","left_wrist"),
    ("right_shoulder","right_elbow"),("right_elbow","right_wrist"),
    ("left_shoulder","left_hip"),("right_shoulder","right_hip"),
    ("left_hip","right_hip"),
    ("left_hip","left_knee"),("left_knee","left_ankle"),
    ("right_hip","right_knee"),("right_knee","right_ankle"),
]

JOINT_NAMES = [
    "nose","left_shoulder","right_shoulder",
    "left_elbow","right_elbow","left_wrist","right_wrist",
    "left_hip","right_hip","left_knee","right_knee",
    "left_ankle","right_ankle",
]

COLOR_BONE  = (240, 240, 240)
COLOR_JOINT = (255, 180,  40)
COLOR_HEAD  = ( 80, 200, 255)
EVENT_COLORS = {
    "address": (160, 160, 160),
    "top":     ( 40, 200, 160),
    "impact":  ( 40, 100, 230),
    "finish":  (200,  60, 200),
}


# ── video info ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class VideoInfo:
    fps: float
    frame_count: int
    width: int
    height: int


def read_video_info(path: Path) -> VideoInfo:
    cap = cv2.VideoCapture(str(path))
    info = VideoInfo(
        fps=float(cap.get(cv2.CAP_PROP_FPS)) or 30.0,
        frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    cap.release()
    return info


# ── pose extraction ───────────────────────────────────────────────────────────

def ensure_model(model_path: Path) -> Path:
    if not model_path.exists():
        model_path.parent.mkdir(parents=True, exist_ok=True)
        print("Downloading pose model...")
        urllib.request.urlretrieve(MODEL_URL, model_path)
    return model_path


def extract_pose_sequence(video_path: Path, model_path: Path, info: VideoInfo) -> PoseSequence:
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
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int(round((idx / info.fps) * 1000))
            result = landmarker.detect_for_video(mp_image, ts_ms)
            if result.pose_landmarks:
                named = {
                    name: Landmark(
                        name=name,
                        x=float(lm.x), y=float(lm.y), z=float(lm.z),
                        visibility=float(getattr(lm, "visibility", 0.0) or 0.0),
                    )
                    for name, lm in zip(MP_LANDMARK_NAMES, result.pose_landmarks[0])
                }
                frames.append(FramePose(time_s=idx / info.fps, frame_index=idx, landmarks=named))
            idx += 1
    cap.release()
    print(f"  Pose: {len(frames)}/{info.frame_count} frames")
    return PoseSequence(frames=frames, source=str(video_path), fps=info.fps)


# ── swing event detection ─────────────────────────────────────────────────────

def _moving_avg(values: list[float], w: int) -> list[float]:
    half = w // 2
    return [mean(values[max(0,i-half):min(len(values),i+half+1)]) for i in range(len(values))]


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    idx = min(len(ordered)-1, max(0, round((len(ordered)-1)*q)))
    return ordered[idx]


def build_metric_rows(sequence: PoseSequence) -> list[dict[str, Any]]:
    rows = []
    for frame in sequence.frames:
        lw = frame.landmarks.get("left_wrist")
        rw = frame.landmarks.get("right_wrist")
        ls = frame.landmarks.get("left_shoulder")
        rs = frame.landmarks.get("right_shoulder")
        lh = frame.landmarks.get("left_hip")
        rh = frame.landmarks.get("right_hip")
        if not all([lw, rw, ls, rs, lh, rh]):
            continue
        wrist_x = (lw.x + rw.x) / 2
        wrist_y = (lw.y + rw.y) / 2
        rows.append({
            "frame_index": frame.frame_index,
            "time_s": frame.time_s,
            "wrist_mid_x": wrist_x,
            "wrist_mid_y": wrist_y,
        })

    if not rows:
        return rows
    wrist = [(r["wrist_mid_x"], r["wrist_mid_y"]) for r in rows]
    speeds = [0.0]
    for (px, py), (cx, cy), pr, cr in zip(wrist, wrist[1:], rows, rows[1:]):
        dt = max(1e-6, cr["time_s"] - pr["time_s"])
        speeds.append(((cx-px)**2 + (cy-py)**2)**0.5 / dt)
    smoothed = _moving_avg(speeds, 5)
    for row, sp in zip(rows, smoothed):
        row["wrist_speed"] = sp
    return rows


def detect_swing_events(rows: list[dict[str, Any]], fps: float) -> list[dict[str, Any]]:
    if not rows:
        return []
    y_values = _moving_avg([r["wrist_mid_y"] for r in rows], 9)
    top_thr = _percentile(y_values, 0.20)
    min_gap = int(max(1, fps * 2.2))
    tops: list[int] = []
    for i in range(2, len(y_values)-2):
        if y_values[i] <= top_thr and y_values[i] <= min(y_values[i-2:i+3]):
            if tops and i - tops[-1] < min_gap:
                if y_values[i] < y_values[tops[-1]]:
                    tops[-1] = i
            else:
                tops.append(i)

    events = []
    for swing_idx, top_idx in enumerate(tops, 1):
        start = max(0, top_idx - int(2.6*fps))
        end_bt = max(start+1, top_idx - int(0.25*fps))
        address_idx = max(range(start, end_bt),
                          key=lambda i: rows[i]["wrist_mid_y"] - 0.08*rows[i]["wrist_speed"])
        address_y = rows[address_idx]["wrist_mid_y"]
        ps = min(len(rows)-1, top_idx + int(0.15*fps))
        pe = min(len(rows), top_idx + int(1.4*fps))
        impact_idx = min(range(ps, pe),
                         key=lambda i: abs(rows[i]["wrist_mid_y"] - address_y)
                         - 0.02*rows[i]["wrist_speed"]) if ps < pe else top_idx
        fs = min(len(rows)-1, impact_idx + int(0.45*fps))
        fe = min(len(rows), top_idx + int(2.4*fps))
        if fs < fe:
            local_sp = [rows[i]["wrist_speed"] for i in range(fs, fe)]
            low_sp = _percentile(local_sp, 0.35)
            finish_cands = [i for i in range(fs, fe) if rows[i]["wrist_speed"] <= low_sp]
            finish_idx = finish_cands[-1] if finish_cands else fe-1
        else:
            finish_idx = min(len(rows)-1, top_idx + int(1.4*fps))

        events.append({
            "swing": swing_idx,
            "address_frame": rows[address_idx]["frame_index"],
            "top_frame":     rows[top_idx]["frame_index"],
            "impact_frame":  rows[impact_idx]["frame_index"],
            "finish_frame":  rows[finish_idx]["frame_index"],
            "address_time_s": rows[address_idx]["time_s"],
            "top_time_s":     rows[top_idx]["time_s"],
            "impact_time_s":  rows[impact_idx]["time_s"],
            "finish_time_s":  rows[finish_idx]["time_s"],
        })
    return events


# ── ball detection ────────────────────────────────────────────────────────────

def _build_body_mask(
    pose_index: dict[int, dict[str, Any]],
    frame_idx: int,
    w: int, h: int,
    dilate_px: int = 0,
) -> np.ndarray | None:
    """Binary mask (255=body) to exclude from ball search."""
    frame_data = pose_index.get(frame_idx)
    if not frame_data:
        return None
    pts = []
    for name, lm in frame_data["landmarks"].items():
        pts.append((int(lm["x"] * w), int(lm["y"] * h)))
    if not pts:
        return None
    mask = np.zeros((h, w), dtype=np.uint8)
    for px, py in pts:
        cv2.circle(mask, (px, py), dilate_px, 255, -1)
    return mask


def _wrist_midpoint(
    pose_index: dict[int, dict[str, Any]],
    frame_idx: int, w: int, h: int,
) -> tuple[float, float] | None:
    fd = pose_index.get(frame_idx)
    if not fd:
        return None
    lm = fd["landmarks"]
    lw, rw = lm.get("left_wrist"), lm.get("right_wrist")
    if lw and rw:
        return ((lw["x"]+rw["x"])/2*w, (lw["y"]+rw["y"])/2*h)
    if lw: return (lw["x"]*w, lw["y"]*h)
    if rw: return (rw["x"]*w, rw["y"]*h)
    return None


def _adaptive_params(w: int, h: int) -> dict[str, Any]:
    """Scale detection parameters to video resolution."""
    scale = (w * h) / (320 * 568)
    return {
        "brightness_thresh": 190,
        "diff_thresh": max(10, int(12 * (scale ** 0.3))),
        "min_area": max(2.0, 2.0 * scale),
        "max_area": max(300.0, 300.0 * scale),
        "body_dilate_px": max(18, int(22 * (scale ** 0.5))),
        "max_jump_px": max(80.0, 80.0 * (scale ** 0.5)),
    }


def detect_ball_candidates(
    video_path: Path,
    impact_frame: int,
    fps: float,
    info: VideoInfo,
    pose_index: dict[int, dict[str, Any]],
    search_duration_s: float = 2.5,
) -> list[dict[str, Any]]:
    """
    Detect ball candidates using optical flow + direction filtering.

    Key improvements over simple frame-diff:
    1. Skip first few frames after impact so the club head clears the frame.
    2. Farneback optical flow gives per-pixel velocity vectors.
    3. Only keep blobs whose flow direction is consistent (ball flies in one
       direction; club head decelerates and curves back with the body).
    4. Exclude body region with a dilated skeleton mask.
    """
    p = _adaptive_params(info.width, info.height)
    w, h = info.width, info.height

    # Club head is still prominent for ~4-5 frames after impact at 30fps.
    # Skip those frames so we don't mistake it for the ball.
    club_clear_frames = max(3, round(fps * 0.15))
    search_start = impact_frame + club_clear_frames

    cap = cv2.VideoCapture(str(video_path))
    # Need one frame before search_start for optical flow seed
    seed_start = max(0, search_start - 1)
    end = min(info.frame_count - 1, impact_frame + round(search_duration_s * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, seed_start)

    candidates: list[dict[str, Any]] = []
    prev_gray: np.ndarray | None = None
    # Accumulate dominant flow direction across frames to anchor filtering
    dominant_dx: float = 0.0
    dominant_dy: float = 0.0
    direction_frames: int = 0
    frame_idx = seed_start

    while frame_idx <= end:
        ok, frame = cap.read()
        if not ok:
            break

        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        if frame_idx >= search_start and prev_gray is not None:
            # ── optical flow ──────────────────────────────────────────────
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, blurred,
                None,
                pyr_scale=0.5, levels=2, winsize=9,
                iterations=2, poly_n=5, poly_sigma=1.1,
                flags=0,
            )
            fx, fy = flow[..., 0], flow[..., 1]
            flow_mag = np.sqrt(fx * fx + fy * fy)

            # ── body exclusion mask ───────────────────────────────────────
            body_mask = _build_body_mask(pose_index, frame_idx, w, h, p["body_dilate_px"])

            # ── brightness mask (ball is bright/white) ────────────────────
            _, bright_mask = cv2.threshold(blurred, p["brightness_thresh"], 255, cv2.THRESH_BINARY)

            # ── motion magnitude mask ─────────────────────────────────────
            flow_thresh = max(1.5, p["diff_thresh"] / 8.0)
            motion_mask = (flow_mag > flow_thresh).astype(np.uint8) * 255

            combined = cv2.bitwise_and(motion_mask, bright_mask)
            if body_mask is not None:
                combined = cv2.bitwise_and(combined, cv2.bitwise_not(body_mask))

            kernel   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel)
            combined = cv2.morphologyEx(combined, cv2.MORPH_DILATE, kernel)

            contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            frame_candidates = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if not (p["min_area"] <= area <= p["max_area"]):
                    continue
                M = cv2.moments(cnt)
                if M["m00"] <= 0:
                    continue
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]

                # Mean flow direction inside the blob
                blob_mask_single = np.zeros((h, w), dtype=np.uint8)
                cv2.drawContours(blob_mask_single, [cnt], -1, 255, -1)
                blob_pixels = blob_mask_single > 0
                if not blob_pixels.any():
                    continue
                mean_fx = float(fx[blob_pixels].mean())
                mean_fy = float(fy[blob_pixels].mean())

                # Update dominant direction from early detections
                if direction_frames < 6:
                    dominant_dx += mean_fx
                    dominant_dy += mean_fy
                    direction_frames += 1

                frame_candidates.append({
                    "frame_index": frame_idx,
                    "x": cx, "y": cy, "area": area,
                    "flow_dx": mean_fx, "flow_dy": mean_fy,
                })

            # ── direction consistency filter ──────────────────────────────
            # After a few frames we know the ball's travel direction;
            # reject blobs moving in the wrong direction (club follow-through).
            if direction_frames >= 3 and (dominant_dx**2 + dominant_dy**2) > 0:
                dom_len = (dominant_dx**2 + dominant_dy**2) ** 0.5
                ndx, ndy = dominant_dx / dom_len, dominant_dy / dom_len
                for fc in frame_candidates:
                    blen = (fc["flow_dx"]**2 + fc["flow_dy"]**2) ** 0.5
                    if blen < 0.1:
                        continue
                    # dot product with dominant direction — keep if angle < 75°
                    dot = (fc["flow_dx"] * ndx + fc["flow_dy"] * ndy) / blen
                    if dot > 0.26:   # cos(75°) ≈ 0.26
                        candidates.append(fc)
            else:
                candidates.extend(frame_candidates)

        prev_gray = blurred
        frame_idx += 1

    cap.release()
    return candidates


def _smooth_track(track: list[dict[str, Any]], window: int = 3) -> list[dict[str, Any]]:
    if len(track) <= 2:
        return track
    half = window // 2
    smoothed = []
    for i, pt in enumerate(track):
        nb = track[max(0,i-half):min(len(track),i+half+1)]
        smoothed.append({**pt,
                         "x": sum(n["x"] for n in nb)/len(nb),
                         "y": sum(n["y"] for n in nb)/len(nb)})
    return smoothed


def _chain_track(
    candidates: list[dict[str, Any]],
    launch: tuple[float, float] | None,
    fps: float,
    max_jump_px: float,
) -> list[dict[str, Any]]:
    by_frame: dict[int, list[dict[str, Any]]] = {}
    for c in candidates:
        by_frame.setdefault(c["frame_index"], []).append(c)

    frames = sorted(by_frame)
    if not frames:
        return []

    seed_frame = frames[0]
    if launch is not None:
        seed = min(by_frame[seed_frame],
                   key=lambda c: (c["x"]-launch[0])**2 + (c["y"]-launch[1])**2)
    else:
        seed = min(by_frame[seed_frame], key=lambda c: c["area"])

    track = [seed]
    for fi in frames[1:]:
        prev = track[-1]
        gap  = fi - prev["frame_index"]
        limit = max_jump_px * gap
        best = min(by_frame[fi],
                   key=lambda c: (c["x"]-prev["x"])**2 + (c["y"]-prev["y"])**2)
        dist = ((best["x"]-prev["x"])**2 + (best["y"]-prev["y"])**2)**0.5
        if dist <= limit:
            track.append(best)

    return track


def _ransac_parabola_fit(
    track: list[dict[str, Any]],
    inlier_thresh_px: float = 12.0,
    min_inliers: int = 3,
    iterations: int = 60,
) -> list[dict[str, Any]]:
    """
    Fit a parabola (x = at² + bt + c  and  y = dt² + et + f) to the track
    using RANSAC, keeping only inliers. This rejects club-head noise that
    doesn't follow a physical ball trajectory.

    The ball obeys projectile physics: x is linear in time, y is quadratic.
    We fit both axes against frame index as the time proxy.
    """
    if len(track) < min_inliers:
        return track

    ts = np.array([p["frame_index"] for p in track], dtype=float)
    xs = np.array([p["x"] for p in track], dtype=float)
    ys = np.array([p["y"] for p in track], dtype=float)

    best_inliers: list[int] = []

    rng = np.random.default_rng(42)
    for _ in range(iterations):
        # Sample 3 points to fit x(t) linear + y(t) quadratic
        idx = rng.choice(len(ts), size=min(3, len(ts)), replace=False)
        sample_t = ts[idx]

        try:
            # y = a*t^2 + b*t + c  (gravity gives quadratic y)
            cy = np.polyfit(sample_t, ys[idx], min(2, len(idx)-1))
            # x = d*t + e           (no horizontal acceleration)
            cx = np.polyfit(sample_t, xs[idx], min(1, len(idx)-1))
        except (np.linalg.LinAlgError, ValueError):
            continue

        pred_y = np.polyval(cy, ts)
        pred_x = np.polyval(cx, ts)
        residuals = np.sqrt((xs - pred_x)**2 + (ys - pred_y)**2)
        inliers = list(np.where(residuals < inlier_thresh_px)[0])

        if len(inliers) > len(best_inliers):
            best_inliers = inliers

    if len(best_inliers) >= min_inliers:
        return [track[i] for i in sorted(best_inliers)]
    return track


def _is_plausible(track: list[dict[str, Any]], w: int) -> bool:
    if len(track) < 2:
        return False
    dx = track[-1]["x"] - track[0]["x"]
    dy = track[-1]["y"] - track[0]["y"]
    # require net displacement > 4% of width and some upward or lateral movement
    return ((dx**2 + dy**2)**0.5 > 0.04 * w) and not (abs(dx) < 3 and abs(dy) < 3)


def _proxy_track(
    launch: tuple[float, float],
    impact_frame: int,
    fps: float,
    w: int, h: int,
) -> list[dict[str, Any]]:
    lx, ly = launch
    end_x   = min(w-1, lx + 0.42*w)
    end_y   = ly - 0.18*h
    ctrl_x  = (lx + end_x) / 2
    ctrl_y  = ly - 0.36*h
    end_f   = impact_frame + round(1.3 * fps)
    step    = max(1, round(fps / 20))
    frames  = list(range(impact_frame, end_f+1, step))
    proxy   = []
    for idx, fi in enumerate(frames):
        t = idx / max(1, len(frames)-1)
        inv = 1-t
        x = inv*inv*lx + 2*inv*t*ctrl_x + t*t*end_x
        y = inv*inv*ly + 2*inv*t*ctrl_y + t*t*end_y
        proxy.append({"frame_index": fi, "x": x, "y": y})
    return proxy


def build_ball_track(
    video_path: Path,
    swing: dict[str, Any],
    pose_index: dict[int, dict[str, Any]],
    fps: float,
    info: VideoInfo,
) -> tuple[list[dict[str, Any]], str]:
    impact_frame = swing["impact_frame"]
    w, h = info.width, info.height
    launch = _wrist_midpoint(pose_index, impact_frame, w, h)
    p = _adaptive_params(w, h)

    candidates = detect_ball_candidates(video_path, impact_frame, fps, info, pose_index)
    track = _chain_track(candidates, launch, fps, p["max_jump_px"])
    track = _ransac_parabola_fit(track)   # reject non-parabolic noise
    track = _smooth_track(track)

    if _is_plausible(track, w):
        print(f"  S{swing['swing']}: real track — {len(track)} pts")
        return track, "real"

    print(f"  S{swing['swing']}: proxy (no plausible ball found)")
    if launch is None:
        launch = (0.54*w, 0.66*h)
    return _proxy_track(launch, impact_frame, fps, w, h), "proxy"


# ── drawing ───────────────────────────────────────────────────────────────────

def draw_trail(
    frame: np.ndarray,
    track: list[dict[str, Any]],
    current_frame: int,
    tail_frames: int = 50,
) -> None:
    visible = [
        (int(round(p["x"])), int(round(p["y"])))
        for p in track
        if current_frame - tail_frames <= p["frame_index"] <= current_frame
    ]
    if len(visible) < 2:
        return
    for thickness, color in [(10, (15, 95, 255)), (5, (40, 210, 255)), (2, (255, 255, 255))]:
        for a, b in zip(visible, visible[1:]):
            cv2.line(frame, a, b, color, thickness, cv2.LINE_AA)
    tip = visible[-1]
    cv2.circle(frame, tip, 7,  (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(frame, tip, 11, (40, 210, 255),   2, cv2.LINE_AA)


def lm_px(lm: dict[str, Any], w: int, h: int) -> tuple[int, int]:
    return (int(lm["x"]*w), int(lm["y"]*h))


# Segment colors (BGR): arms=gold, legs=green, spine/shoulders=cyan
_EDGE_COLORS: dict[tuple[str, str], tuple[int, int, int]] = {
    ("left_shoulder",  "right_shoulder"): (255, 229,   0),  # cyan
    ("left_shoulder",  "left_hip"):       (255, 229,   0),
    ("right_shoulder", "right_hip"):      (255, 229,   0),
    ("left_hip",       "right_hip"):      (255, 229,   0),
    ("left_shoulder",  "left_elbow"):     ( 64, 201, 255),  # gold
    ("left_elbow",     "left_wrist"):     ( 64, 201, 255),
    ("right_shoulder", "right_elbow"):    ( 64, 201, 255),
    ("right_elbow",    "right_wrist"):    ( 64, 201, 255),
    ("left_hip",       "left_knee"):      ( 85, 255,  57),  # green
    ("left_knee",      "left_ankle"):     ( 85, 255,  57),
    ("right_hip",      "right_knee"):     ( 85, 255,  57),
    ("right_knee",     "right_ankle"):    ( 85, 255,  57),
}


def _depth_scale(z: float, lo: float = -0.3, hi: float = 0.3) -> float:
    """Map Z (toward camera) to 0–1 brightness scale."""
    return max(0.4, min(1.0, (z - lo) / (hi - lo + 1e-6)))


def draw_skeleton(frame: np.ndarray, lms: dict[str, Any]) -> None:
    h, w = frame.shape[:2]
    for s, e in SKELETON_EDGES:
        if s not in lms or e not in lms:
            continue
        a  = lm_px(lms[s], w, h)
        b  = lm_px(lms[e], w, h)
        z  = (lms[s].get("z", 0) + lms[e].get("z", 0)) / 2
        sc = _depth_scale(z)
        base = _EDGE_COLORS.get((s, e), _EDGE_COLORS.get((e, s), (240, 240, 240)))
        color = tuple(int(c * sc) for c in base)
        thickness = 3 if sc > 0.7 else 2
        cv2.line(frame, a, b, color, thickness, cv2.LINE_AA)

    for name in JOINT_NAMES:
        if name not in lms:
            continue
        pt = lm_px(lms[name], w, h)
        z  = lms[name].get("z", 0)
        sc = _depth_scale(z)
        if name == "nose":
            cv2.circle(frame, pt, 6, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, pt, 6, (30, 30, 30), 1, cv2.LINE_AA)
        else:
            r = 5 if sc > 0.7 else 3
            cv2.circle(frame, pt, r, (int(255*sc), int(200*sc), int(64*sc)), -1, cv2.LINE_AA)
            cv2.circle(frame, pt, r, (20, 20, 20), 1, cv2.LINE_AA)


def draw_ghost_trail(
    frame: np.ndarray,
    history: list[dict[str, Any]],
    steps: int = 4,
) -> None:
    """Draw fading ghost skeletons from recent frames."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    for i, past_lms in enumerate(reversed(history[-steps:])):
        alpha = 0.12 * (steps - i) / steps
        for s, e in SKELETON_EDGES:
            if s not in past_lms or e not in past_lms:
                continue
            a = lm_px(past_lms[s], w, h)
            b = lm_px(past_lms[e], w, h)
            cv2.line(overlay, a, b, (120, 180, 255), 1, cv2.LINE_AA)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        overlay = frame.copy()


def draw_hud(
    frame: np.ndarray,
    time_s: float,
    event: tuple[str, int] | None,
) -> None:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 28), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, dst=frame)
    cv2.putText(frame, f"{time_s:.2f}s",
                (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200,200,200), 1, cv2.LINE_AA)
    if event:
        phase, swing_n = event
        color = EVENT_COLORS.get(phase, (255, 255, 255))
        label = f"S{swing_n} {phase.upper()}"
        tw, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)[0]
        cv2.putText(frame, label, (w-tw-8, 19),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
        cv2.rectangle(frame, (0, 0), (4, h), color, -1)


# ── render ────────────────────────────────────────────────────────────────────

def render_video(
    video_path: Path,
    pose_index: dict[int, dict[str, Any]],
    event_map: dict[int, tuple[str, int]],
    all_tracks: list[list[dict[str, Any]]],
    info: VideoInfo,
    output_path: Path,
) -> None:
    cap    = cv2.VideoCapture(str(video_path))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output_path), fourcc, info.fps, (info.width, info.height))

    frame_idx = 0
    active_event: tuple[str, int] | None = None
    active_left = 0
    lm_history: list[dict[str, Any]] = []   # for ghost trail

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        time_s = frame_idx / info.fps
        if frame_idx in event_map:
            active_event = event_map[frame_idx]
            active_left  = int(info.fps * 1.5)

        pf = pose_index.get(frame_idx)
        if pf:
            if lm_history:
                draw_ghost_trail(frame, lm_history)
            draw_skeleton(frame, pf["landmarks"])
            lm_history.append(pf["landmarks"])
            if len(lm_history) > 12:
                lm_history.pop(0)

        for track in all_tracks:
            draw_trail(frame, track, frame_idx)

        draw_hud(frame, time_s, active_event if active_left > 0 else None)
        if active_left > 0:
            active_left -= 1

        writer.write(frame)
        frame_idx += 1

    cap.release()
    writer.release()


# ── entry point ───────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video",      type=Path, help="Input golf video")
    parser.add_argument("--output",   type=Path, default=None,
                        help="Output video path (default: <input>_effects.mp4)")
    parser.add_argument("--handedness", choices=["right","left"], default="right")
    parser.add_argument("--model",    type=Path, default=DEFAULT_MODEL)
    args = parser.parse_args(argv)

    output = args.output or args.video.parent / (args.video.stem + "_effects.mp4")

    print(f"Video: {args.video}")
    info = read_video_info(args.video)
    print(f"  {info.width}x{info.height} @ {info.fps:.1f}fps  {info.frame_count} frames")

    print("Extracting pose...")
    model_path = ensure_model(args.model)
    sequence   = extract_pose_sequence(args.video, model_path, info)
    pose_index = {f.frame_index: {
        "frame_index": f.frame_index,
        "time_s": f.time_s,
        "landmarks": {n: {"x": lm.x, "y": lm.y, "z": lm.z} for n, lm in f.landmarks.items()},
    } for f in sequence.frames}

    print("Detecting swing events...")
    rows   = build_metric_rows(sequence)
    events = detect_swing_events(rows, info.fps)
    print(f"  Found {len(events)} swing(s)")

    event_map: dict[int, tuple[str, int]] = {}
    for swing in events:
        n = swing["swing"]
        for phase in ("address", "top", "impact", "finish"):
            event_map[swing[f"{phase}_frame"]] = (phase, n)

    print("Detecting ball tracks...")
    all_tracks = [
        build_ball_track(args.video, swing, pose_index, info.fps, info)[0]
        for swing in events
    ]

    print("Rendering...")
    render_video(args.video, pose_index, event_map, all_tracks, info, output)
    print(f"Done → {output}")


if __name__ == "__main__":
    main()

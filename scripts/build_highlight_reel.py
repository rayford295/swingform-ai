#!/usr/bin/env python
"""Build a short highlight reel from a long golf practice video."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from swingform_ai.highlight import (
    MotionFrameStats,
    SwingCandidate,
    SwingScore,
    clip_window,
    detect_swing_candidates,
    scoring_standard,
    select_best_swings,
)


@dataclass(frozen=True)
class VideoInfo:
    fps: float
    frame_count: int
    width: int
    height: int
    duration_s: float


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


def collect_motion_stats(video_path: Path, info: VideoInfo) -> list[MotionFrameStats]:
    """Collect frame-difference statistics used for first-pass swing slicing."""

    cap = cv2.VideoCapture(str(video_path))
    stats: list[MotionFrameStats] = []
    prev_small: np.ndarray | None = None
    frame_index = 0
    small_width = 180
    small_height = max(1, round(info.height * small_width / max(1, info.width)))
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (small_width, small_height), interpolation=cv2.INTER_AREA)
        if prev_small is None:
            motion = 0.0
        else:
            motion = float(cv2.absdiff(small, prev_small).mean() / 255.0)
        brightness = float(small.mean() / 255.0)
        blur = float(min(1.0, cv2.Laplacian(small, cv2.CV_64F).var() / 280.0))
        stats.append(
            MotionFrameStats(
                frame_index=frame_index,
                time_s=frame_index / info.fps,
                motion=motion,
                brightness=brightness,
                blur=blur,
            )
        )
        prev_small = small
        frame_index += 1
    cap.release()
    return stats


def _point_from_label(row: dict[str, str], width: int, height: int) -> dict[str, Any]:
    x = float(row["x"])
    y = float(row["y"])
    if 0.0 <= x <= 1.0:
        x *= width
    if 0.0 <= y <= 1.0:
        y *= height
    return {
        "frame_index": int(float(row["frame_index"])),
        "x": x,
        "y": y,
        "confidence": float(row.get("confidence", 1.0) or 1.0),
        "source": "label",
    }


def load_ball_labels(path: Path | None, width: int, height: int) -> list[dict[str, Any]]:
    """Load optional ball labels with columns frame_index,x,y[,confidence]."""

    if path is None or not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"frame_index", "x", "y"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Ball label file is missing columns: {sorted(missing)}")
        return [_point_from_label(row, width, height) for row in reader]


def _smooth_track(points: list[dict[str, Any]], window: int = 3) -> list[dict[str, Any]]:
    if len(points) <= 2:
        return points
    half = window // 2
    smoothed: list[dict[str, Any]] = []
    for idx, point in enumerate(points):
        start = max(0, idx - half)
        end = min(len(points), idx + half + 1)
        neighbors = points[start:end]
        smoothed.append(
            {
                **point,
                "x": float(sum(item["x"] for item in neighbors) / len(neighbors)),
                "y": float(sum(item["y"] for item in neighbors) / len(neighbors)),
            }
        )
    return smoothed


def _proxy_arc_point(
    start: tuple[float, float],
    control: tuple[float, float],
    end: tuple[float, float],
    t: float,
) -> tuple[float, float]:
    inv = 1.0 - t
    x = inv * inv * start[0] + 2.0 * inv * t * control[0] + t * t * end[0]
    y = inv * inv * start[1] + 2.0 * inv * t * control[1] + t * t * end[1]
    return x, y


def build_proxy_ball_track(
    candidate: SwingCandidate,
    window_end: int,
    fps: float,
    width: int,
    height: int,
    shot_direction: str,
) -> list[dict[str, Any]]:
    """Build a low-confidence visual shot arc until real ball labels are available."""

    start_frame = candidate.peak_frame
    end_frame = min(window_end, candidate.peak_frame + round(1.7 * fps))
    if end_frame <= start_frame:
        return []

    if shot_direction == "left":
        start = (0.46 * width, 0.66 * height)
        control = (0.18 * width, 0.24 * height)
        end = (0.07 * width, 0.31 * height)
    elif shot_direction == "up":
        start = (0.52 * width, 0.68 * height)
        control = (0.50 * width, 0.15 * height)
        end = (0.52 * width, 0.25 * height)
    else:
        start = (0.54 * width, 0.66 * height)
        control = (0.82 * width, 0.24 * height)
        end = (0.94 * width, 0.31 * height)

    step = max(1, round(fps / 14))
    frames = list(range(start_frame, end_frame + 1, step))
    track: list[dict[str, Any]] = []
    for idx, frame_index in enumerate(frames):
        t = idx / max(1, len(frames) - 1)
        x, y = _proxy_arc_point(start, control, end, t)
        track.append(
            {
                "frame_index": frame_index,
                "x": x,
                "y": y,
                "confidence": 0.25,
                "source": "proxy",
            }
        )
    return track


def ball_track_for_clip(
    candidate: SwingCandidate,
    clip_start: int,
    clip_end: int,
    fps: float,
    width: int,
    height: int,
    labels: list[dict[str, Any]],
    trail_mode: str,
    shot_direction: str,
) -> tuple[list[dict[str, Any]], str, float]:
    if trail_mode == "none":
        return [], "none", 0.0

    label_points = [
        point for point in labels
        if clip_start <= int(point["frame_index"]) <= clip_end
    ]
    if label_points and trail_mode in {"auto", "labels"}:
        smoothed = _smooth_track(sorted(label_points, key=lambda item: item["frame_index"]))
        confidence = sum(float(point["confidence"]) for point in smoothed) / len(smoothed)
        return smoothed, "labels", round(confidence, 3)

    if trail_mode == "labels":
        return [], "missing_labels", 0.0

    proxy = build_proxy_ball_track(candidate, clip_end, fps, width, height, shot_direction)
    return proxy, "proxy", 0.25 if proxy else 0.0


def create_writer(path: Path, info: VideoInfo) -> cv2.VideoWriter:
    path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, info.fps, (info.width, info.height))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open video writer: {path}")
    return writer


def prepare_session_dir(session_dir: Path) -> None:
    """Remove previous generated files for the same session id."""

    session_dir.mkdir(parents=True, exist_ok=True)
    for old_file in [session_dir / "highlight_reel.mp4", session_dir / "swing_report.json"]:
        old_file.unlink(missing_ok=True)
    clips_dir = session_dir / "clips"
    if clips_dir.exists():
        for old_clip in clips_dir.glob("*.mp4"):
            old_clip.unlink()
    clips_dir.mkdir(parents=True, exist_ok=True)


def draw_panel(frame: np.ndarray, lines: list[str]) -> None:
    height, width = frame.shape[:2]
    scale = max(0.45, width / 980.0)
    line_height = round(26 * scale)
    panel_h = 18 + line_height * len(lines)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (width, panel_h), (8, 12, 18), -1)
    cv2.addWeighted(overlay, 0.62, frame, 0.38, 0, dst=frame)
    for idx, line in enumerate(lines):
        y = 10 + line_height * (idx + 1)
        color = (245, 248, 255) if idx == 0 else (190, 215, 255)
        cv2.putText(
            frame,
            line,
            (16, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            max(1, round(2 * scale)),
            cv2.LINE_AA,
        )


def draw_trail(frame: np.ndarray, track: list[dict[str, Any]], frame_index: int) -> None:
    visible = [
        (int(round(point["x"])), int(round(point["y"])))
        for point in track
        if int(point["frame_index"]) <= frame_index
    ]
    if len(visible) < 2:
        return
    for thickness, color in [(10, (15, 95, 255)), (5, (40, 210, 255)), (2, (255, 255, 255))]:
        for start, end in zip(visible, visible[1:]):
            cv2.line(frame, start, end, color, thickness, cv2.LINE_AA)
    for point in visible[-5:]:
        cv2.circle(frame, point, 5, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, point, 9, (40, 210, 255), 2, cv2.LINE_AA)


def draw_frame_overlay(
    frame: np.ndarray,
    candidate: SwingCandidate,
    score: SwingScore,
    frame_index: int,
    track: list[dict[str, Any]],
    trail_kind: str,
) -> None:
    draw_trail(frame, track, frame_index)
    lines = [
        f"SwingForm AI  |  swing {candidate.swing_index}  |  score {score.score:.1f}",
        f"clip {candidate.start_time_s:.2f}s-{candidate.end_time_s:.2f}s"
        f"  |  trail {trail_kind}",
    ]
    draw_panel(frame, lines)


def write_title_frames(
    writer: cv2.VideoWriter,
    frame: np.ndarray,
    candidate: SwingCandidate,
    score: SwingScore,
    fps: float,
    repeats: int,
) -> None:
    title = frame.copy()
    draw_panel(
        title,
        [
            f"Swing {candidate.swing_index}  |  highlight score {score.score:.1f}",
            "best moments from the long practice video",
        ],
    )
    for _ in range(repeats):
        writer.write(title)


def render_selected_clips(
    video_path: Path,
    session_dir: Path,
    info: VideoInfo,
    selected: list[tuple[SwingCandidate, SwingScore]],
    labels: list[dict[str, Any]],
    trail_mode: str,
    shot_direction: str,
) -> list[dict[str, Any]]:
    clips_dir = session_dir / "clips"
    highlight_path = session_dir / "highlight_reel.mp4"
    highlight_writer = create_writer(highlight_path, info)
    selected_records: list[dict[str, Any]] = []
    title_repeats = max(1, round(0.45 * info.fps))

    for rank, (candidate, score) in enumerate(selected, start=1):
        clip_start, clip_end = clip_window(candidate, info.fps, info.frame_count)
        track, trail_kind, trail_confidence = ball_track_for_clip(
            candidate,
            clip_start,
            clip_end,
            info.fps,
            info.width,
            info.height,
            labels,
            trail_mode,
            shot_direction,
        )
        clip_path = clips_dir / f"rank_{rank:02d}_swing_{candidate.swing_index:02d}.mp4"
        clip_writer = create_writer(clip_path, info)
        cap = cv2.VideoCapture(str(video_path))
        cap.set(cv2.CAP_PROP_POS_FRAMES, clip_start)
        ok, frame = cap.read()
        if not ok:
            cap.release()
            clip_writer.release()
            continue
        write_title_frames(clip_writer, frame, candidate, score, info.fps, title_repeats)
        write_title_frames(highlight_writer, frame, candidate, score, info.fps, title_repeats)

        frame_index = clip_start
        while ok and frame_index <= clip_end:
            rendered = frame.copy()
            draw_frame_overlay(rendered, candidate, score, frame_index, track, trail_kind)
            clip_writer.write(rendered)
            highlight_writer.write(rendered)
            ok, frame = cap.read()
            frame_index += 1
        cap.release()
        clip_writer.release()
        selected_records.append(
            {
                "rank": rank,
                "swing_index": candidate.swing_index,
                "score": score.to_dict(),
                "clip_start_frame": clip_start,
                "clip_end_frame": clip_end,
                "clip_start_time_s": clip_start / info.fps,
                "clip_end_time_s": clip_end / info.fps,
                "clip_path": str(clip_path),
                "trail_kind": trail_kind,
                "trail_confidence": trail_confidence,
                "trail_points": len(track),
            }
        )

    highlight_writer.release()
    return selected_records


def write_report(
    path: Path,
    video_path: Path,
    info: VideoInfo,
    candidates: list[SwingCandidate],
    selected_records: list[dict[str, Any]],
    highlight_path: Path,
) -> None:
    payload = {
        "schema_version": "highlight-reel-v1",
        "input_video": str(video_path),
        "video": {
            "fps": info.fps,
            "frame_count": info.frame_count,
            "width": info.width,
            "height": info.height,
            "duration_s": info.duration_s,
        },
        "swing_count": len(candidates),
        "scoring_standard": scoring_standard(),
        "candidates": [candidate.to_dict() for candidate in candidates],
        "selected": selected_records,
        "outputs": {
            "highlight_reel": str(highlight_path),
            "report": str(path),
        },
        "notes": [
            "This is a first-pass long-video slicer based on video motion.",
            "Proxy trails are visual placeholders until ball labels or a detector are supplied.",
            "The scorer ranks clips for review and sharing; it is not a coaching verdict.",
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Long practice video.")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/highlight-reels"))
    parser.add_argument("--top-k", type=int, default=3, help="Number of best swings to export.")
    parser.add_argument(
        "--ball-labels",
        type=Path,
        help="Optional CSV: frame_index,x,y[,confidence].",
    )
    parser.add_argument(
        "--trail-mode",
        choices=["auto", "labels", "proxy", "none"],
        default="auto",
        help="auto uses labels when present, otherwise a low-confidence proxy trail.",
    )
    parser.add_argument("--shot-direction", choices=["right", "left", "up"], default="right")
    parser.add_argument("--min-duration-s", type=float, default=1.1)
    parser.add_argument("--max-duration-s", type=float, default=8.0)
    parser.add_argument(
        "--motion-threshold-quantile",
        type=float,
        default=0.55,
        help="Lower values count more candidate swings; higher values are stricter.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    info = read_video_info(args.video)
    stats = collect_motion_stats(args.video, info)
    candidates = detect_swing_candidates(
        stats,
        fps=info.fps,
        min_duration_s=args.min_duration_s,
        max_duration_s=args.max_duration_s,
        threshold_quantile=args.motion_threshold_quantile,
    )
    selected = select_best_swings(candidates, limit=args.top_k)
    session_dir = args.output_dir / args.session_id
    prepare_session_dir(session_dir)
    labels = load_ball_labels(args.ball_labels, info.width, info.height)
    selected_records = render_selected_clips(
        args.video,
        session_dir,
        info,
        selected,
        labels,
        args.trail_mode,
        args.shot_direction,
    )
    report_path = session_dir / "swing_report.json"
    highlight_path = session_dir / "highlight_reel.mp4"
    write_report(report_path, args.video, info, candidates, selected_records, highlight_path)
    print(
        json.dumps(
            {
                "session_id": args.session_id,
                "input_video": str(args.video),
                "swing_count": len(candidates),
                "selected_count": len(selected_records),
                "highlight_reel": str(highlight_path),
                "report": str(report_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

"""Small-ball tracking helpers for golf trail overlays.

The tracker is intentionally conservative. Golf balls are tiny and often leave a
30fps phone frame within a few samples, so a short anchored proxy is better than
a confident-looking trail through the club, shoes, or range hardware.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pi
from pathlib import Path
from statistics import median
from typing import Any


@dataclass(frozen=True)
class BallPoint:
    """One 2D ball or proxy point in video pixels."""

    frame_index: int
    x: float
    y: float
    confidence: float = 1.0
    source: str = "detector"

    def to_dict(self) -> dict[str, float | int | str]:
        return asdict(self)


@dataclass(frozen=True)
class BallAnchor:
    """Estimated static ball or tee position before launch."""

    x: float
    y: float
    confidence: float
    source: str

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


@dataclass(frozen=True)
class BallTrackResult:
    """A ball trail plus diagnostics about how it was produced."""

    points: list[BallPoint]
    source: str
    confidence: float
    anchor: BallAnchor | None
    diagnostics: dict[str, float | int | str | bool]

    def points_as_dicts(self) -> list[dict[str, float | int | str]]:
        return [point.to_dict() for point in self.points]


def _require_cv2() -> Any:
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RuntimeError(
            "Ball tracking needs the optional pose dependencies: opencv-python and numpy."
        ) from exc
    return cv2


def _landmark_px(
    landmarks: dict[str, Any],
    name: str,
    width: int,
    height: int,
) -> tuple[float, float] | None:
    item = landmarks.get(name)
    if not item:
        return None
    if isinstance(item, dict):
        return (float(item["x"]) * width, float(item["y"]) * height)
    return (float(item.x) * width, float(item.y) * height)


def _pose_frame_near(
    pose_index: dict[int, dict[str, Any]],
    frame_index: int,
    search_radius: int = 12,
) -> dict[str, Any] | None:
    if frame_index in pose_index:
        return pose_index[frame_index]
    for offset in range(1, search_radius + 1):
        before = pose_index.get(frame_index - offset)
        if before is not None:
            return before
        after = pose_index.get(frame_index + offset)
        if after is not None:
            return after
    return None


def _frame_landmarks(frame_data: dict[str, Any] | None) -> dict[str, Any]:
    if not frame_data:
        return {}
    return frame_data.get("landmarks", {})


def _mean_point(points: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not points:
        return None
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def _target_ball_position(
    landmarks: dict[str, Any],
    width: int,
    height: int,
    shot_direction: str,
) -> tuple[float, float] | None:
    hand_names = ("left_wrist", "right_wrist", "left_index", "right_index")
    foot_names = ("left_ankle", "right_ankle", "left_foot_index", "right_foot_index")
    hands = [
        point
        for name in hand_names
        if (point := _landmark_px(landmarks, name, width, height)) is not None
    ]
    feet = [
        point
        for name in foot_names
        if (point := _landmark_px(landmarks, name, width, height)) is not None
    ]
    if not hands or not feet:
        return None

    hand_mid = _mean_point(hands)
    if hand_mid is None:
        return None
    foot_y = median(point[1] for point in feet)
    x_offset = 0.060 * width
    if shot_direction == "left":
        x_offset *= -1.0
    elif shot_direction == "up":
        x_offset = 0.0
    return (hand_mid[0] + x_offset, foot_y - 0.012 * height)


def _foot_roi(
    landmarks: dict[str, Any],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    names = ("left_ankle", "right_ankle", "left_foot_index", "right_foot_index")
    feet = [
        point
        for name in names
        if (point := _landmark_px(landmarks, name, width, height)) is not None
    ]
    if not feet:
        return (
            round(0.12 * width),
            round(0.62 * height),
            round(0.88 * width),
            height,
        )
    xs = [point[0] for point in feet]
    ys = [point[1] for point in feet]
    return (
        max(0, round(min(xs) - 0.18 * width)),
        max(0, round(min(ys) - 0.12 * height)),
        min(width, round(max(xs) + 0.18 * width)),
        min(height, round(max(ys) + 0.12 * height)),
    )


def _contour_roundness(cv2: Any, contour: Any) -> float:
    perimeter = float(cv2.arcLength(contour, True))
    area = float(cv2.contourArea(contour))
    if perimeter <= 0.0:
        return 0.0
    return max(0.0, min(1.0, 4.0 * pi * area / (perimeter * perimeter)))


def _cluster_points(
    observations: list[tuple[float, float, float, float]],
    cell_size_px: float = 18.0,
) -> list[list[tuple[float, float, float, float]]]:
    clusters: dict[tuple[int, int], list[tuple[float, float, float, float]]] = {}
    for observation in observations:
        key = (round(observation[0] / cell_size_px), round(observation[1] / cell_size_px))
        clusters.setdefault(key, []).append(observation)
    return list(clusters.values())


def _score_anchor_cluster(
    cluster: list[tuple[float, float, float, float]],
    target: tuple[float, float] | None,
    width: int,
    shot_direction: str = "right",
) -> float:
    cx = median(point[0] for point in cluster)
    cy = median(point[1] for point in cluster)
    recurrence_score = min(1.0, len(cluster) / 8.0)
    area_score = min(1.0, median(point[2] for point in cluster) / 20.0)
    roundness_score = median(point[3] for point in cluster)
    if target is None:
        target_score = 0.35
    else:
        distance = ((cx - target[0]) ** 2 + (cy - target[1]) ** 2) ** 0.5
        target_score = max(0.0, 1.0 - distance / (0.18 * width))
    score = (
        0.22 * recurrence_score
        + 0.38 * target_score
        + 0.22 * area_score
        + 0.18 * roundness_score
    )
    if target is not None:
        lateral_slack = 0.07 * width
        if shot_direction == "right" and cx < target[0] - lateral_slack:
            score *= 0.72
        elif shot_direction == "left" and cx > target[0] + lateral_slack:
            score *= 0.72
    return score


def estimate_ball_anchor(
    video_path: Path,
    swing: dict[str, Any],
    pose_index: dict[int, dict[str, Any]],
    width: int,
    height: int,
    shot_direction: str = "right",
    lookback_frames: int = 90,
) -> BallAnchor | None:
    """Estimate the address ball position from repeated small white blobs.

    The address pose supplies the search target and foot-level ROI; image
    evidence still decides the final anchor.
    """

    cv2 = _require_cv2()
    impact_frame = int(swing["impact_frame"])
    address_frame = int(swing.get("address_frame", max(0, impact_frame - lookback_frames)))
    pose_frame = _pose_frame_near(pose_index, address_frame) or _pose_frame_near(
        pose_index,
        impact_frame,
    )
    landmarks = _frame_landmarks(pose_frame)
    target = _target_ball_position(landmarks, width, height, shot_direction)
    x0, y0, x1, y1 = _foot_roi(landmarks, width, height)

    cap = cv2.VideoCapture(str(video_path))
    observations: list[tuple[float, float, float, float]] = []
    start = max(0, impact_frame - lookback_frames)
    end = max(start + 1, impact_frame - 6)
    for frame_index in range(start, end, 4):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok:
            continue
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, 0, 150), (179, 78, 255))
        mask[:y0, :] = 0
        mask[y1:, :] = 0
        mask[:, :x0] = 0
        mask[:, x1:] = 0

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = float(cv2.contourArea(contour))
            x, y, box_w, box_h = cv2.boundingRect(contour)
            if not (2.0 <= area <= 130.0):
                continue
            if not (2 <= box_w <= 24 and 2 <= box_h <= 24):
                continue
            aspect = max(box_w, box_h) / max(1, min(box_w, box_h))
            if aspect > 3.5:
                continue
            moments = cv2.moments(contour)
            if moments["m00"] <= 0:
                continue
            cx = float(moments["m10"] / moments["m00"])
            cy = float(moments["m01"] / moments["m00"])
            observations.append((cx, cy, area, _contour_roundness(cv2, contour)))
    cap.release()

    clusters = _cluster_points(observations)
    if not clusters:
        if target is None:
            return None
        return BallAnchor(target[0], target[1], 0.25, "pose_target")

    best = max(
        clusters,
        key=lambda cluster: _score_anchor_cluster(
            cluster,
            target,
            width,
            shot_direction,
        ),
    )
    confidence = round(_score_anchor_cluster(best, target, width, shot_direction), 3)
    if confidence < 0.28 and target is not None:
        return BallAnchor(target[0], target[1], 0.25, "pose_target")
    return BallAnchor(
        float(median(point[0] for point in best)),
        float(median(point[1] for point in best)),
        confidence,
        "static_ball",
    )


def detect_moving_ball_candidates(
    video_path: Path,
    impact_frame: int,
    fps: float,
    anchor: BallAnchor,
    width: int,
    height: int,
    shot_direction: str = "right",
    search_duration_s: float = 1.35,
) -> list[BallPoint]:
    """Find small low-saturation moving highlights after launch."""

    cv2 = _require_cv2()
    cap = cv2.VideoCapture(str(video_path))
    start = max(0, impact_frame - 1)
    end = impact_frame + round(search_duration_s * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start)

    points: list[BallPoint] = []
    prev_gray: Any | None = None
    frame_index = start
    while frame_index <= end:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        if frame_index >= impact_frame and prev_gray is not None:
            diff = cv2.absdiff(blurred, prev_gray)
            motion_mask = cv2.threshold(diff, 10, 255, cv2.THRESH_BINARY)[1]
            white_mask = cv2.inRange(hsv, (0, 0, 145), (179, 88, 255))
            combined = cv2.bitwise_and(motion_mask, white_mask)

            # Search ahead of the address ball; this keeps hands, club shaft,
            # shoes, and yellow range hardware from becoming the seed.
            y_floor = min(height, round(anchor.y + 0.10 * height))
            y_ceiling = max(0, round(anchor.y - 0.48 * height))
            if shot_direction == "left":
                x_min = 0
                x_max = min(width, round(anchor.x + 0.10 * width))
            elif shot_direction == "up":
                x_min = max(0, round(anchor.x - 0.18 * width))
                x_max = min(width, round(anchor.x + 0.18 * width))
            else:
                x_min = max(0, round(anchor.x - 0.10 * width))
                x_max = width
            combined[:y_ceiling, :] = 0
            combined[y_floor:, :] = 0
            combined[:, :x_min] = 0
            combined[:, x_max:] = 0

            contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                area = float(cv2.contourArea(contour))
                x, y, box_w, box_h = cv2.boundingRect(contour)
                if not (1.5 <= area <= 180.0):
                    continue
                if not (2 <= box_w <= 32 and 2 <= box_h <= 32):
                    continue
                aspect = max(box_w, box_h) / max(1, min(box_w, box_h))
                if aspect > 4.0:
                    continue
                moments = cv2.moments(contour)
                if moments["m00"] <= 0:
                    continue
                cx = float(moments["m10"] / moments["m00"])
                cy = float(moments["m01"] / moments["m00"])
                roundness = _contour_roundness(cv2, contour)
                confidence = max(0.15, min(1.0, 0.45 + 0.35 * roundness + 0.20 * area / 30.0))
                points.append(
                    BallPoint(
                        frame_index=frame_index,
                        x=cx,
                        y=cy,
                        confidence=round(confidence, 3),
                        source="detector",
                    )
                )
        prev_gray = blurred
        frame_index += 1
    cap.release()
    return points


def _direction_progress(
    start: BallPoint | BallAnchor,
    end: BallPoint,
    shot_direction: str,
) -> float:
    dx = end.x - start.x
    dy = end.y - start.y
    if shot_direction == "left":
        return -dx - 0.30 * max(0.0, dy)
    if shot_direction == "up":
        return -dy
    return dx - 0.30 * max(0.0, dy)


def chain_ball_track(
    candidates: list[BallPoint],
    anchor: BallAnchor,
    fps: float,
    shot_direction: str = "right",
    max_gap_frames: int = 6,
) -> list[BallPoint]:
    """Greedily chain candidates from the tee with direction and speed gates."""

    by_frame: dict[int, list[BallPoint]] = {}
    for candidate in sorted(candidates, key=lambda item: item.frame_index):
        by_frame.setdefault(candidate.frame_index, []).append(candidate)
    if not by_frame:
        return []

    track: list[BallPoint] = []
    for frame_index in sorted(by_frame):
        options = by_frame[frame_index]
        if not track:
            max_seed_distance = max(34.0, 0.16 * fps)
            plausible = [
                item
                for item in options
                if ((item.x - anchor.x) ** 2 + (item.y - anchor.y) ** 2) ** 0.5
                <= max_seed_distance + 22.0 * max(0, item.frame_index - min(by_frame))
                and _direction_progress(anchor, item, shot_direction) >= -8.0
                and item.y <= anchor.y + max(6.0, 0.008 * anchor.y)
            ]
            if not plausible:
                continue
            best = max(
                plausible,
                key=lambda item: item.confidence
                + 0.02 * _direction_progress(anchor, item, shot_direction),
            )
            track.append(best)
            continue

        previous = track[-1]
        gap = frame_index - previous.frame_index
        if gap <= 0 or gap > max_gap_frames:
            continue
        max_jump = 36.0 * gap + 0.030 * fps * gap
        plausible = []
        for item in options:
            distance = ((item.x - previous.x) ** 2 + (item.y - previous.y) ** 2) ** 0.5
            if distance > max_jump:
                continue
            if _direction_progress(previous, item, shot_direction) < -10.0:
                continue
            plausible.append((item, distance))
        if not plausible:
            continue
        best, best_distance = max(
            plausible,
            key=lambda pair: pair[0].confidence
            + 0.02 * _direction_progress(previous, pair[0], shot_direction)
            - 0.003 * pair[1],
        )
        # Avoid drawing through nearly static high-contrast edges.
        if best_distance < 2.0 and len(track) > 1:
            continue
        track.append(best)
    return track


def evaluate_track_quality(
    track: list[BallPoint],
    anchor: BallAnchor,
    width: int,
    height: int,
    shot_direction: str = "right",
    impact_frame: int | None = None,
) -> tuple[bool, float, dict[str, float | int | str | bool]]:
    """Return whether a detector track is good enough to show as real."""

    if len(track) < 4:
        return False, 0.0, {"points": len(track), "reason": "too_few_points"}
    start_distance = ((track[0].x - anchor.x) ** 2 + (track[0].y - anchor.y) ** 2) ** 0.5
    progress = _direction_progress(anchor, track[-1], shot_direction)
    vertical_lift = max(0.0, anchor.y - min(point.y for point in track))
    first_lag_frames = 0 if impact_frame is None else max(0, track[0].frame_index - impact_frame)
    early_points = track[: min(4, len(track))]
    initial_dip = max(0.0, max(point.y for point in early_points) - anchor.y)
    if shot_direction == "left":
        backward_seed = max(0.0, track[0].x - anchor.x)
    elif shot_direction == "up":
        backward_seed = 0.0
    else:
        backward_seed = max(0.0, anchor.x - track[0].x)
    span_x = max(point.x for point in track) - min(point.x for point in track)
    span_y = max(point.y for point in track) - min(point.y for point in track)
    avg_confidence = sum(point.confidence for point in track) / len(track)
    monotonic_steps = 0
    for first, second in zip(track, track[1:]):
        if _direction_progress(first, second, shot_direction) >= -6.0:
            monotonic_steps += 1
    monotonic_ratio = monotonic_steps / max(1, len(track) - 1)

    diagnostics: dict[str, float | int | bool] = {
        "points": len(track),
        "first_lag_frames": first_lag_frames,
        "start_distance_px": round(start_distance, 2),
        "backward_seed_px": round(backward_seed, 2),
        "initial_dip_px": round(initial_dip, 2),
        "progress_px": round(progress, 2),
        "vertical_lift_px": round(vertical_lift, 2),
        "span_x_px": round(span_x, 2),
        "span_y_px": round(span_y, 2),
        "monotonic_ratio": round(monotonic_ratio, 3),
    }
    ok = (
        start_distance <= 0.14 * width
        and first_lag_frames <= 10
        and backward_seed <= 0.02 * width
        and initial_dip <= max(7.0, 0.006 * height)
        and progress >= 0.045 * width
        and vertical_lift >= 0.025 * height
        and monotonic_ratio >= 0.70
    )
    confidence = min(
        0.95,
        0.25
        + 0.20 * min(1.0, len(track) / 9.0)
        + 0.22 * min(1.0, progress / (0.20 * width))
        + 0.18 * min(1.0, vertical_lift / (0.10 * height))
        + 0.15 * avg_confidence,
    )
    return ok, round(confidence if ok else 0.0, 3), diagnostics


def build_proxy_track(
    anchor: BallAnchor,
    impact_frame: int,
    fps: float,
    width: int,
    height: int,
    shot_direction: str = "right",
    duration_s: float = 1.35,
) -> list[BallPoint]:
    """Build a visible, low-confidence trajectory anchored to the tee."""

    if shot_direction == "left":
        end_x = max(0.0, anchor.x - 0.45 * width)
        control_x = anchor.x - 0.28 * width
    elif shot_direction == "up":
        end_x = anchor.x
        control_x = anchor.x
    else:
        end_x = min(width - 1.0, anchor.x + 0.45 * width)
        control_x = anchor.x + 0.28 * width
    end_y = max(0.0, anchor.y - 0.24 * height)
    control_y = max(0.0, anchor.y - 0.42 * height)
    end_frame = impact_frame + round(duration_s * fps)
    step = max(1, round(fps / 18.0))
    frames = list(range(impact_frame, end_frame + 1, step))
    points: list[BallPoint] = []
    for idx, frame_index in enumerate(frames):
        t = idx / max(1, len(frames) - 1)
        inv = 1.0 - t
        x = inv * inv * anchor.x + 2.0 * inv * t * control_x + t * t * end_x
        y = inv * inv * anchor.y + 2.0 * inv * t * control_y + t * t * end_y
        points.append(BallPoint(frame_index, x, y, 0.22, "proxy"))
    return points


def build_ball_track(
    video_path: Path,
    swing: dict[str, Any],
    pose_index: dict[int, dict[str, Any]],
    fps: float,
    width: int,
    height: int,
    shot_direction: str = "right",
) -> BallTrackResult:
    """Build a conservative real-or-proxy ball trail for one swing."""

    impact_frame = int(swing["impact_frame"])
    anchor = estimate_ball_anchor(
        video_path,
        swing,
        pose_index,
        width,
        height,
        shot_direction=shot_direction,
    )
    if anchor is None:
        anchor = BallAnchor(0.54 * width, 0.66 * height, 0.1, "fallback_frame")

    candidates = detect_moving_ball_candidates(
        video_path,
        impact_frame,
        fps,
        anchor,
        width,
        height,
        shot_direction=shot_direction,
    )
    detector_track = chain_ball_track(candidates, anchor, fps, shot_direction=shot_direction)
    ok, confidence, diagnostics = evaluate_track_quality(
        detector_track,
        anchor,
        width,
        height,
        shot_direction=shot_direction,
        impact_frame=impact_frame,
    )
    diagnostics = {
        **diagnostics,
        "candidate_count": len(candidates),
        "anchor_source": anchor.source,
        "anchor_confidence": anchor.confidence,
    }
    if ok:
        return BallTrackResult(detector_track, "detector", confidence, anchor, diagnostics)

    proxy = build_proxy_track(anchor, impact_frame, fps, width, height, shot_direction)
    return BallTrackResult(proxy, "proxy", 0.22, anchor, diagnostics)

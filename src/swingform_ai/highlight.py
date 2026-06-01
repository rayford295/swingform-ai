"""Highlight-reel primitives for long sports practice videos."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean


@dataclass(frozen=True)
class MotionFrameStats:
    """Video-level statistics for one frame."""

    frame_index: int
    time_s: float
    motion: float
    brightness: float
    blur: float


@dataclass(frozen=True)
class SwingCandidate:
    """One detected swing-like motion segment."""

    swing_index: int
    start_frame: int
    end_frame: int
    peak_frame: int
    start_time_s: float
    end_time_s: float
    peak_time_s: float
    duration_s: float
    peak_motion: float
    mean_motion: float
    pre_stability: float
    post_stability: float
    brightness: float
    blur: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class SwingScore:
    """A transparent score for ranking swing clips."""

    swing_index: int
    score: float
    components: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return {
            "swing_index": self.swing_index,
            "score": self.score,
            "components": self.components,
        }


def moving_average(values: list[float], window: int = 5) -> list[float]:
    """Smooth a short numeric sequence."""

    if not values:
        return []
    half = max(0, window // 2)
    smoothed: list[float] = []
    for idx in range(len(values)):
        start = max(0, idx - half)
        end = min(len(values), idx + half + 1)
        smoothed.append(mean(values[start:end]))
    return smoothed


def percentile(values: list[float], q: float) -> float:
    """Return the nearest-rank percentile for q in [0, 1]."""

    if not values:
        return 0.0
    ordered = sorted(values)
    idx = round((len(ordered) - 1) * min(1.0, max(0.0, q)))
    return float(ordered[idx])


def _segment_average(
    stats: list[MotionFrameStats],
    start_idx: int,
    end_idx: int,
    field: str,
    fallback: float = 0.0,
) -> float:
    values = [float(getattr(item, field)) for item in stats[start_idx:end_idx]]
    return mean(values) if values else fallback


def _stability_score(avg_motion: float, peak_motion: float) -> float:
    if peak_motion <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - avg_motion / peak_motion))


def _build_candidate(
    stats: list[MotionFrameStats],
    start_idx: int,
    end_idx: int,
    swing_index: int,
    fps: float,
) -> SwingCandidate:
    segment = stats[start_idx:end_idx]
    peak_item = max(segment, key=lambda item: item.motion)
    peak_motion = float(peak_item.motion)
    pre_start = max(0, start_idx - round(0.7 * fps))
    post_end = min(len(stats), end_idx + round(0.7 * fps))
    pre_motion = _segment_average(stats, pre_start, start_idx, "motion", fallback=peak_motion)
    post_motion = _segment_average(stats, end_idx, post_end, "motion", fallback=peak_motion)
    start_item = stats[start_idx]
    end_item = stats[end_idx - 1]
    return SwingCandidate(
        swing_index=swing_index,
        start_frame=start_item.frame_index,
        end_frame=end_item.frame_index,
        peak_frame=peak_item.frame_index,
        start_time_s=start_item.time_s,
        end_time_s=end_item.time_s,
        peak_time_s=peak_item.time_s,
        duration_s=max(0.0, end_item.time_s - start_item.time_s),
        peak_motion=peak_motion,
        mean_motion=_segment_average(stats, start_idx, end_idx, "motion"),
        pre_stability=_stability_score(pre_motion, peak_motion),
        post_stability=_stability_score(post_motion, peak_motion),
        brightness=_segment_average(stats, start_idx, end_idx, "brightness"),
        blur=_segment_average(stats, start_idx, end_idx, "blur"),
    )


def detect_swing_candidates(
    stats: list[MotionFrameStats],
    fps: float,
    min_duration_s: float = 1.1,
    max_duration_s: float = 8.0,
    merge_gap_s: float = 0.65,
    threshold_quantile: float = 0.72,
) -> list[SwingCandidate]:
    """Detect swing-like segments from frame motion energy.

    This detector is intentionally simple. It is a first-pass long-video slicer,
    not a coach or a ball-flight model.
    """

    if not stats:
        return []
    smoothed_motion = moving_average([item.motion for item in stats], window=max(3, round(fps / 5)))
    nonzero_motion = [value for value in smoothed_motion if value > 0]
    if not nonzero_motion:
        return []
    threshold = percentile(nonzero_motion, threshold_quantile)
    active = [value >= threshold for value in smoothed_motion]
    raw_segments: list[tuple[int, int]] = []
    idx = 0
    while idx < len(active):
        if not active[idx]:
            idx += 1
            continue
        start = idx
        while idx < len(active) and active[idx]:
            idx += 1
        raw_segments.append((start, idx))

    if not raw_segments:
        return []

    max_gap = max(1, round(merge_gap_s * fps))
    merged: list[list[int]] = []
    for start, end in raw_segments:
        if merged and start - merged[-1][1] <= max_gap:
            merged[-1][1] = end
        else:
            merged.append([start, end])

    candidates: list[SwingCandidate] = []
    for start, end in merged:
        duration_s = stats[end - 1].time_s - stats[start].time_s
        if duration_s < min_duration_s or duration_s > max_duration_s:
            continue
        candidates.append(_build_candidate(stats, start, end, len(candidates) + 1, fps))
    return candidates


def score_swing_candidates(candidates: list[SwingCandidate]) -> list[SwingScore]:
    """Score candidates with transparent, editable components."""

    if not candidates:
        return []
    peak_ref = max(candidate.peak_motion for candidate in candidates) or 1.0
    mean_ref = max(candidate.mean_motion for candidate in candidates) or 1.0
    scored: list[SwingScore] = []
    for candidate in candidates:
        motion_energy = 30.0 * min(1.0, candidate.peak_motion / peak_ref)
        # 3.2s is a typical full golf swing duration (address to finish); adjust per sport.
        tempo_window = 20.0 * max(0.0, 1.0 - abs(candidate.duration_s - 3.2) / 3.2)
        setup_finish = 20.0 * (candidate.pre_stability + candidate.post_stability) / 2.0
        image_quality = 15.0 * (
            max(0.0, min(1.0, candidate.brightness))
            + max(0.0, min(1.0, candidate.blur))
        ) / 2.0
        complete_motion = 15.0 * min(1.0, candidate.duration_s / 2.2) * min(
            1.0,
            candidate.mean_motion / mean_ref,
        )
        components = {
            "motion_energy": round(motion_energy, 2),
            "tempo_window": round(tempo_window, 2),
            "setup_finish_stability": round(setup_finish, 2),
            "image_quality": round(image_quality, 2),
            "complete_motion": round(complete_motion, 2),
        }
        scored.append(
            SwingScore(
                swing_index=candidate.swing_index,
                score=round(sum(components.values()), 2),
                components=components,
            )
        )
    return scored


def select_best_swings(
    candidates: list[SwingCandidate],
    limit: int = 3,
) -> list[tuple[SwingCandidate, SwingScore]]:
    """Return the highest-scoring swing candidates."""

    scores = {score.swing_index: score for score in score_swing_candidates(candidates)}
    paired = [(candidate, scores[candidate.swing_index]) for candidate in candidates]
    return sorted(paired, key=lambda item: item[1].score, reverse=True)[:limit]


def clip_window(
    candidate: SwingCandidate,
    fps: float,
    total_frames: int,
    pre_roll_s: float = 1.0,
    post_roll_s: float = 1.3,
) -> tuple[int, int]:
    """Expand a swing segment into a shareable clip window."""

    start = max(0, candidate.start_frame - round(pre_roll_s * fps))
    end = min(total_frames - 1, candidate.end_frame + round(post_roll_s * fps))
    return start, max(start, end)


def scoring_standard() -> dict[str, str]:
    """Human-readable scoring standard used by reports and docs."""

    return {
        "motion_energy": (
            "Peak motion intensity during the candidate swing, normalized to the session."
        ),
        "tempo_window": "Preference for a complete swing-length segment near 3.2 seconds.",
        "setup_finish_stability": (
            "Lower motion before and after the swing, so the clip has a clear start and finish."
        ),
        "image_quality": "Brightness and sharpness proxies from the video frames.",
        "complete_motion": "Sustained motion across the segment, not just a short spike.",
    }

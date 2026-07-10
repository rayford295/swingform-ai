"""Primary-athlete selection across multi-pose detections.

Single-pose detection drifts between athletes in gameplay footage and can
latch onto phantom detections at the frame edge. When the detector returns
several candidate poses per frame, these helpers pick the one that most
plausibly continues the primary athlete's track.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from swingform_ai.schema import FramePose

# A real hip cannot move farther than this (normalized image units) between
# consecutive tracked frames without the track being considered broken.
MAX_HIP_JUMP_PER_S = 3.0
# Reset the continuity anchor after this many seconds without an accepted pose.
ANCHOR_TIMEOUT_S = 1.0


@dataclass(frozen=True)
class PoseQuality:
    """Cheap plausibility features for one candidate pose."""

    hip_mid: tuple[float, float]
    torso_height: float
    leg_height: float
    mean_visibility: float

    @property
    def body_height(self) -> float:
        return self.torso_height + self.leg_height

    def is_plausible(self) -> bool:
        """An upright athlete: shoulders above hips above ankles, each with extent."""

        return self.torso_height > 0.02 and self.leg_height > 0.02


def pose_quality(frame: FramePose) -> PoseQuality:
    left_hip = frame.require("left_hip")
    right_hip = frame.require("right_hip")
    left_shoulder = frame.require("left_shoulder")
    right_shoulder = frame.require("right_shoulder")
    left_ankle = frame.require("left_ankle")
    right_ankle = frame.require("right_ankle")
    hip_mid = ((left_hip.x + right_hip.x) / 2.0, (left_hip.y + right_hip.y) / 2.0)
    shoulder_mid_y = (left_shoulder.y + right_shoulder.y) / 2.0
    ankle_mid_y = (left_ankle.y + right_ankle.y) / 2.0
    return PoseQuality(
        hip_mid=hip_mid,
        torso_height=hip_mid[1] - shoulder_mid_y,
        leg_height=ankle_mid_y - hip_mid[1],
        mean_visibility=mean(
            float(landmark.visibility or 0.0) for landmark in frame.landmarks.values()
        ),
    )


class PrimaryAthleteTracker:
    """Choose one pose per frame that continues the primary athlete's track.

    Selection rule: among plausible candidates, prefer the one closest to the
    last accepted hip position; when there is no recent anchor, prefer the
    largest (closest-to-camera) pose. Implausible candidates are only used
    when nothing else is available and never update the anchor.
    """

    def __init__(self) -> None:
        self._anchor: tuple[float, float] | None = None
        self._anchor_time_s: float | None = None

    def select(self, candidates: list[FramePose], time_s: float) -> FramePose | None:
        if not candidates:
            return None
        scored = [(frame, pose_quality(frame)) for frame in candidates]
        plausible = [(frame, quality) for frame, quality in scored if quality.is_plausible()]
        if not plausible:
            # Keep pose coverage for review, but a phantom must not move the anchor.
            return max(scored, key=lambda item: item[1].mean_visibility)[0]

        anchor = self._anchor
        elapsed = (
            max(1e-6, time_s - self._anchor_time_s) if self._anchor_time_s is not None else None
        )
        if elapsed is not None and elapsed > ANCHOR_TIMEOUT_S:
            anchor = None

        if anchor is None or elapsed is None:
            chosen, quality = max(plausible, key=lambda item: item[1].body_height)
        else:
            max_jump = MAX_HIP_JUMP_PER_S * elapsed
            near = [
                (frame, quality, _dist(quality.hip_mid, anchor))
                for frame, quality in plausible
            ]
            within = [item for item in near if item[2] <= max_jump]
            if within:
                chosen, quality, _ = min(within, key=lambda item: item[2])
            else:
                # Every plausible candidate teleported: treat as a new track.
                chosen, quality = max(plausible, key=lambda item: item[1].body_height)

        self._anchor = quality.hip_mid
        self._anchor_time_s = time_s
        return chosen


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

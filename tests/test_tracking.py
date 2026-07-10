import unittest

from swingform_ai.schema import FramePose, Landmark
from swingform_ai.tracking import PrimaryAthleteTracker, pose_quality

CORE_JOINTS = ["left_shoulder", "right_shoulder", "left_hip", "right_hip", "left_ankle", "right_ankle"]


def make_pose(
    center_x: float,
    shoulder_y: float,
    hip_y: float,
    ankle_y: float,
    time_s: float = 0.0,
    visibility: float = 0.9,
) -> FramePose:
    landmarks = {}
    for name in CORE_JOINTS:
        side = -0.02 if name.startswith("left") else 0.02
        y = {"shoulder": shoulder_y, "hip": hip_y, "ankle": ankle_y}[name.split("_")[1]]
        landmarks[name] = Landmark(name=name, x=center_x + side, y=y, visibility=visibility)
    return FramePose(time_s=time_s, landmarks=landmarks)


def upright(center_x: float, time_s: float = 0.0, scale: float = 1.0) -> FramePose:
    return make_pose(
        center_x,
        shoulder_y=0.5 - 0.15 * scale,
        hip_y=0.5,
        ankle_y=0.5 + 0.2 * scale,
        time_s=time_s,
    )


def phantom(center_x: float, time_s: float = 0.0) -> FramePose:
    # Collapsed pose: hips at shoulder height, ankles above hips.
    return make_pose(center_x, shoulder_y=0.5, hip_y=0.5, ankle_y=0.49, time_s=time_s, visibility=0.4)


class PoseQualityTests(unittest.TestCase):
    def test_upright_pose_is_plausible(self):
        self.assertTrue(pose_quality(upright(0.5)).is_plausible())

    def test_collapsed_pose_is_implausible(self):
        self.assertFalse(pose_quality(phantom(0.5)).is_plausible())


class PrimaryAthleteTrackerTests(unittest.TestCase):
    def test_prefers_larger_pose_without_anchor(self):
        tracker = PrimaryAthleteTracker()
        small = upright(0.2, scale=0.5)
        large = upright(0.7, scale=1.0)
        chosen = tracker.select([small, large], time_s=0.0)
        self.assertEqual(chosen, large)

    def test_follows_continuity_over_size(self):
        tracker = PrimaryAthleteTracker()
        tracker.select([upright(0.3, scale=0.8)], time_s=0.0)
        near_small = upright(0.32, time_s=0.033, scale=0.8)
        far_large = upright(0.8, time_s=0.033, scale=1.0)
        chosen = tracker.select([near_small, far_large], time_s=0.033)
        self.assertEqual(chosen, near_small)

    def test_phantom_never_moves_anchor(self):
        tracker = PrimaryAthleteTracker()
        tracker.select([upright(0.3)], time_s=0.0)
        tracker.select([phantom(0.95, time_s=0.033)], time_s=0.033)
        # After the phantom interlude the athlete near the old anchor still wins.
        near = upright(0.31, time_s=0.066)
        far = upright(0.9, time_s=0.066, scale=1.2)
        chosen = tracker.select([near, far], time_s=0.066)
        self.assertEqual(chosen, near)

    def test_anchor_times_out(self):
        tracker = PrimaryAthleteTracker()
        tracker.select([upright(0.3)], time_s=0.0)
        # After a long gap the anchor is stale; the larger pose wins again.
        near_small = upright(0.31, time_s=5.0, scale=0.5)
        far_large = upright(0.9, time_s=5.0, scale=1.0)
        chosen = tracker.select([near_small, far_large], time_s=5.0)
        self.assertEqual(chosen, far_large)

    def test_empty_candidates_return_none(self):
        self.assertIsNone(PrimaryAthleteTracker().select([], time_s=0.0))


if __name__ == "__main__":
    unittest.main()

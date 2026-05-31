from __future__ import annotations

import json
import unittest
from pathlib import Path

from swingform_ai.analyze_pose_json import analyze_pose_payload
from swingform_ai.profiles import basketball, golf
from swingform_ai.schema import PoseSequence


ROOT = Path(__file__).resolve().parents[1]


class ProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads((ROOT / "examples" / "sample_pose_sequence.json").read_text())
        cls.sequence = PoseSequence.from_mapping(cls.payload)

    def test_golf_metrics_have_expected_keys(self) -> None:
        metrics = golf.frame_metrics(self.sequence.frames[0], handedness="right")
        self.assertIn("lead_arm_angle_deg", metrics)
        self.assertIn("shoulder_hip_separation_deg", metrics)

    def test_basketball_metrics_have_expected_keys(self) -> None:
        metrics = basketball.frame_metrics(self.sequence.frames[0], shooting_side="right")
        self.assertIn("shooting_elbow_angle_deg", metrics)
        self.assertIn("wrist_height_norm", metrics)

    def test_cli_analyzer_payload_golf(self) -> None:
        result = analyze_pose_payload(self.payload, sport="golf", side="right")
        self.assertEqual(result["sport"], "golf")
        self.assertEqual(len(result["frames"]), 2)
        self.assertIn("summary", result)

    def test_cli_analyzer_payload_basketball(self) -> None:
        result = analyze_pose_payload(self.payload, sport="basketball", side="right")
        self.assertEqual(result["sport"], "basketball")
        self.assertEqual(len(result["frames"]), 2)
        self.assertIn("summary", result)


if __name__ == "__main__":
    unittest.main()


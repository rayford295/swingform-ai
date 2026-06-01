from __future__ import annotations

import unittest

from swingform_ai.ball_tracking import (
    BallAnchor,
    BallPoint,
    build_proxy_track,
    chain_ball_track,
    evaluate_track_quality,
)


class BallTrackingTest(unittest.TestCase):
    def test_quality_rejects_track_that_starts_near_wrists(self) -> None:
        anchor = BallAnchor(x=352.0, y=969.0, confidence=0.8, source="static_ball")
        false_track = [
            BallPoint(frame_index=207, x=360.0, y=780.0, confidence=0.8),
            BallPoint(frame_index=209, x=385.0, y=755.0, confidence=0.8),
            BallPoint(frame_index=211, x=420.0, y=735.0, confidence=0.8),
            BallPoint(frame_index=213, x=450.0, y=720.0, confidence=0.8),
        ]

        ok, confidence, diagnostics = evaluate_track_quality(
            false_track,
            anchor,
            width=720,
            height=1280,
            shot_direction="right",
        )

        self.assertFalse(ok)
        self.assertEqual(confidence, 0.0)
        self.assertGreater(diagnostics["start_distance_px"], 0.14 * 720)

    def test_quality_accepts_short_consistent_launch_track(self) -> None:
        anchor = BallAnchor(x=352.0, y=969.0, confidence=0.8, source="static_ball")
        track = [
            BallPoint(frame_index=207, x=360.0, y=950.0, confidence=0.8),
            BallPoint(frame_index=209, x=386.0, y=928.0, confidence=0.8),
            BallPoint(frame_index=211, x=424.0, y=895.0, confidence=0.8),
            BallPoint(frame_index=213, x=475.0, y=850.0, confidence=0.8),
        ]

        ok, confidence, diagnostics = evaluate_track_quality(
            track,
            anchor,
            width=720,
            height=1280,
            shot_direction="right",
        )

        self.assertTrue(ok)
        self.assertGreater(confidence, 0.0)
        self.assertGreater(diagnostics["progress_px"], 0.045 * 720)

    def test_proxy_track_starts_at_tee_anchor(self) -> None:
        anchor = BallAnchor(x=352.0, y=969.0, confidence=0.8, source="static_ball")

        track = build_proxy_track(
            anchor,
            impact_frame=207,
            fps=30.0,
            width=720,
            height=1280,
            shot_direction="right",
        )

        self.assertGreaterEqual(len(track), 4)
        self.assertEqual(track[0].frame_index, 207)
        self.assertAlmostEqual(track[0].x, anchor.x)
        self.assertAlmostEqual(track[0].y, anchor.y)
        self.assertTrue(all(point.source == "proxy" for point in track))

    def test_chain_rejects_first_faraway_candidate(self) -> None:
        anchor = BallAnchor(x=352.0, y=969.0, confidence=0.8, source="static_ball")
        candidates = [
            BallPoint(frame_index=207, x=520.0, y=720.0, confidence=0.9),
            BallPoint(frame_index=208, x=362.0, y=948.0, confidence=0.7),
            BallPoint(frame_index=210, x=390.0, y=925.0, confidence=0.7),
            BallPoint(frame_index=212, x=425.0, y=890.0, confidence=0.7),
        ]

        track = chain_ball_track(candidates, anchor, fps=30.0, shot_direction="right")

        self.assertEqual(track[0].frame_index, 208)
        self.assertAlmostEqual(track[0].x, 362.0)


if __name__ == "__main__":
    unittest.main()

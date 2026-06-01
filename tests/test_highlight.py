from __future__ import annotations

import unittest

from swingform_ai.highlight import (
    MotionFrameStats,
    clip_window,
    detect_swing_candidates,
    score_swing_candidates,
    select_best_swings,
)


def make_motion_stats(motion: list[float], fps: float = 10.0) -> list[MotionFrameStats]:
    return [
        MotionFrameStats(
            frame_index=idx,
            time_s=idx / fps,
            motion=value,
            brightness=0.6,
            blur=0.7,
        )
        for idx, value in enumerate(motion)
    ]


class HighlightTest(unittest.TestCase):
    def test_detect_swing_candidates_from_motion_bursts(self) -> None:
        motion = (
            [0.01] * 10
            + [0.14] * 18
            + [0.01] * 12
            + [0.20] * 22
            + [0.01] * 10
        )
        candidates = detect_swing_candidates(
            make_motion_stats(motion),
            fps=10.0,
            threshold_quantile=0.55,
        )
        self.assertEqual(len(candidates), 2)
        self.assertLess(candidates[0].start_frame, candidates[0].end_frame)
        self.assertLess(candidates[0].end_frame, candidates[1].start_frame)

    def test_select_best_swings_prefers_stronger_motion(self) -> None:
        motion = (
            [0.01] * 10
            + [0.12] * 18
            + [0.01] * 12
            + [0.24] * 22
            + [0.01] * 10
        )
        candidates = detect_swing_candidates(
            make_motion_stats(motion),
            fps=10.0,
            threshold_quantile=0.55,
        )
        selected = select_best_swings(candidates, limit=1)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0][0].swing_index, 2)

    def test_scores_have_public_components(self) -> None:
        motion = [0.01] * 10 + [0.14] * 22 + [0.01] * 10
        candidates = detect_swing_candidates(make_motion_stats(motion), fps=10.0)
        scores = score_swing_candidates(candidates)
        self.assertIn("motion_energy", scores[0].components)
        self.assertIn("setup_finish_stability", scores[0].components)

    def test_clip_window_adds_context_without_exceeding_video(self) -> None:
        motion = [0.01] * 10 + [0.14] * 22 + [0.01] * 10
        candidate = detect_swing_candidates(make_motion_stats(motion), fps=10.0)[0]
        start, end = clip_window(candidate, fps=10.0, total_frames=len(motion))
        self.assertLessEqual(start, candidate.start_frame)
        self.assertLess(end, len(motion))


if __name__ == "__main__":
    unittest.main()

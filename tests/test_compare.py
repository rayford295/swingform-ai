import unittest

from swingform_ai.compare import comparison_rows, detect_sport, extract_records

GOLF_SUMMARY = {
    "swing_summaries": [
        {
            "tempo_ratio": 1.5,
            "backswing_time_s": 1.9,
            "downswing_time_s": 1.2,
            "top": {"lead_arm_angle_deg": 165.0, "shoulder_hip_separation_deg": 5.0},
            "impact": {"head_drift_from_address": 0.03},
            "address": {"stance_width_dist": 0.28},
        },
        {
            "tempo_ratio": 1.7,
            "backswing_time_s": 2.0,
            "downswing_time_s": 1.1,
            "top": {"lead_arm_angle_deg": 170.0, "shoulder_hip_separation_deg": 7.0},
            "impact": {"head_drift_from_address": 0.05},
            "address": {"stance_width_dist": 0.30},
        },
    ]
}

BASKETBALL_SUMMARY = {
    "shot_events": [
        {"set_time_s": 34.7, "lift_time_s": 35.8, "release_time_s": 35.9, "score": 1.05},
    ]
}


class DetectSportTests(unittest.TestCase):
    def test_detects_golf_and_basketball(self):
        self.assertEqual(detect_sport(GOLF_SUMMARY), "golf")
        self.assertEqual(detect_sport(BASKETBALL_SUMMARY), "basketball")

    def test_unknown_summary_raises(self):
        with self.assertRaises(ValueError):
            detect_sport({"video": {}})


class ExtractRecordsTests(unittest.TestCase):
    def test_golf_records(self):
        sport, records = extract_records(GOLF_SUMMARY)
        self.assertEqual(sport, "golf")
        self.assertEqual(len(records), 2)
        self.assertAlmostEqual(records[0]["tempo_ratio"], 1.5)
        self.assertAlmostEqual(records[1]["top_lead_arm_angle_deg"], 170.0)

    def test_basketball_records(self):
        sport, records = extract_records(BASKETBALL_SUMMARY)
        self.assertEqual(sport, "basketball")
        self.assertAlmostEqual(records[0]["set_to_release_s"], 1.2)
        self.assertAlmostEqual(records[0]["lift_to_release_s"], 0.1)


class ComparisonRowsTests(unittest.TestCase):
    def test_rows_align_shared_metrics(self):
        _, records = extract_records(GOLF_SUMMARY)
        rows = comparison_rows("golf", records, records)
        tempo = next(row for row in rows if row.key == "tempo_ratio")
        self.assertAlmostEqual(tempo.mean_a, 1.6)
        self.assertAlmostEqual(tempo.delta, 0.0)

    def test_missing_metric_is_skipped(self):
        _, golf = extract_records(GOLF_SUMMARY)
        sparse = [{"tempo_ratio": 1.4}]
        rows = comparison_rows("golf", golf, sparse)
        self.assertEqual([row.key for row in rows], ["tempo_ratio"])


if __name__ == "__main__":
    unittest.main()

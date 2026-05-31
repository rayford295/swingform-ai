from __future__ import annotations

import unittest

from swingform_ai.geometry import angle_degrees, angle_difference_degrees, distance, midpoint


class GeometryTest(unittest.TestCase):
    def test_angle_degrees_right_angle(self) -> None:
        self.assertAlmostEqual(angle_degrees((1, 0), (0, 0), (0, 1)), 90.0)

    def test_angle_degrees_straight_line(self) -> None:
        self.assertAlmostEqual(angle_degrees((-1, 0), (0, 0), (1, 0)), 180.0)

    def test_distance(self) -> None:
        self.assertAlmostEqual(distance((0, 0), (3, 4)), 5.0)

    def test_midpoint(self) -> None:
        self.assertEqual(midpoint((0, 0), (2, 2)), (1.0, 1.0, 0.0))

    def test_angle_difference_wraps(self) -> None:
        self.assertAlmostEqual(angle_difference_degrees(350, 10), 20.0)


if __name__ == "__main__":
    unittest.main()


"""Small geometry helpers for pose landmarks."""

from __future__ import annotations

from math import acos, atan2, degrees, sqrt


def _xyz(point: object) -> tuple[float, float, float]:
    if hasattr(point, "x") and hasattr(point, "y"):
        z_value = getattr(point, "z", 0.0)
        return (float(getattr(point, "x")), float(getattr(point, "y")), float(z_value or 0.0))

    try:
        values = list(point)  # type: ignore[arg-type]
    except TypeError:
        raise TypeError(
            f"Point must have x/y attributes or be iterable, got {type(point).__name__}."
        ) from None
    if len(values) < 2:
        raise ValueError("A point needs at least x and y coordinates.")
    z_value = values[2] if len(values) > 2 else 0.0
    return (float(values[0]), float(values[1]), float(z_value or 0.0))


def vector(start: object, end: object) -> tuple[float, float, float]:
    """Return the vector from start to end."""

    sx, sy, sz = _xyz(start)
    ex, ey, ez = _xyz(end)
    return (ex - sx, ey - sy, ez - sz)


def distance(a: object, b: object) -> float:
    """Return Euclidean distance between two 2D or 3D points."""

    vx, vy, vz = vector(a, b)
    return sqrt(vx * vx + vy * vy + vz * vz)


def midpoint(a: object, b: object) -> tuple[float, float, float]:
    """Return the midpoint between two 2D or 3D points."""

    ax, ay, az = _xyz(a)
    bx, by, bz = _xyz(b)
    return ((ax + bx) / 2.0, (ay + by) / 2.0, (az + bz) / 2.0)


def angle_degrees(a: object, b: object, c: object) -> float:
    """Return angle ABC in degrees."""

    bax, bay, baz = vector(b, a)
    bcx, bcy, bcz = vector(b, c)
    dot = bax * bcx + bay * bcy + baz * bcz
    norm_ba = sqrt(bax * bax + bay * bay + baz * baz)
    norm_bc = sqrt(bcx * bcx + bcy * bcy + bcz * bcz)
    if norm_ba == 0.0 or norm_bc == 0.0:
        raise ValueError("Cannot compute an angle with a zero-length segment.")
    cosine = max(-1.0, min(1.0, dot / (norm_ba * norm_bc)))
    return degrees(acos(cosine))


def line_angle_2d(a: object, b: object) -> float:
    """Return the image-plane angle of a line in degrees."""

    ax, ay, _ = _xyz(a)
    bx, by, _ = _xyz(b)
    return degrees(atan2(by - ay, bx - ax))


def angle_difference_degrees(first: float, second: float) -> float:
    """Return the smallest absolute difference between two angles in degrees."""

    diff = (first - second + 180.0) % 360.0 - 180.0
    return abs(diff)


def line_separation_degrees(a1: object, a2: object, b1: object, b2: object) -> float:
    """Return image-plane separation between two line segments."""

    return angle_difference_degrees(line_angle_2d(a1, a2), line_angle_2d(b1, b2))


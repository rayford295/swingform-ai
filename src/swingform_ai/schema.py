"""Shared pose schema for SwingForm AI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Landmark:
    """One named body landmark."""

    name: str
    x: float
    y: float
    z: float = 0.0
    visibility: float | None = None

    @classmethod
    def from_value(cls, name: str, value: Any) -> "Landmark":
        if isinstance(value, dict):
            return cls(
                name=name,
                x=float(value["x"]),
                y=float(value["y"]),
                z=float(value.get("z", 0.0) or 0.0),
                visibility=value.get("visibility"),
            )

        coords = list(value)
        if len(coords) < 2:
            raise ValueError(f"Landmark {name!r} needs at least x and y.")
        z_value = coords[2] if len(coords) > 2 else 0.0
        visibility = coords[3] if len(coords) > 3 else None
        return cls(name=name, x=float(coords[0]), y=float(coords[1]), z=float(z_value), visibility=visibility)

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass(frozen=True)
class FramePose:
    """Pose landmarks for one frame."""

    time_s: float
    landmarks: dict[str, Landmark]
    phase: str | None = None
    frame_index: int | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "FramePose":
        landmarks = {
            name: Landmark.from_value(name, value)
            for name, value in payload.get("landmarks", {}).items()
        }
        return cls(
            time_s=float(payload.get("time_s", 0.0)),
            landmarks=landmarks,
            phase=payload.get("phase"),
            frame_index=payload.get("frame_index"),
        )

    def require(self, name: str) -> Landmark:
        try:
            return self.landmarks[name]
        except KeyError as exc:
            raise KeyError(f"Missing landmark {name!r} in frame at {self.time_s:.3f}s.") from exc


@dataclass(frozen=True)
class PoseSequence:
    """A sequence of frame-level poses."""

    frames: list[FramePose]
    source: str | None = None
    fps: float | None = None

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> "PoseSequence":
        return cls(
            frames=[FramePose.from_mapping(frame) for frame in payload.get("frames", [])],
            source=payload.get("source"),
            fps=payload.get("fps"),
        )


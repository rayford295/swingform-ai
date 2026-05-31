"""Analyze exported pose JSON with a selected sport profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from swingform_ai.profiles import basketball, golf
from swingform_ai.schema import PoseSequence


def analyze_pose_payload(payload: dict[str, Any], sport: str, side: str) -> dict[str, object]:
    sequence = PoseSequence.from_mapping(payload)
    if sport == "golf":
        return golf.summarize_sequence(sequence, handedness=side)
    if sport == "basketball":
        return basketball.summarize_sequence(sequence, shooting_side=side)
    raise ValueError("sport must be 'golf' or 'basketball'.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pose_json", type=Path, help="Path to exported pose JSON.")
    parser.add_argument("--sport", choices=["golf", "basketball"], default="golf")
    parser.add_argument(
        "--side",
        choices=["right", "left"],
        default="right",
        help="Right/left handedness for golf or shooting side for basketball.",
    )
    parser.add_argument("--indent", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = json.loads(args.pose_json.read_text(encoding="utf-8"))
    result = analyze_pose_payload(payload, sport=args.sport, side=args.side)
    print(json.dumps(result, indent=args.indent, sort_keys=True))


if __name__ == "__main__":
    main()


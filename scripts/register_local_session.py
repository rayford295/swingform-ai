#!/usr/bin/env python
"""Register a private local practice video without committing the raw video."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from swingform_ai.local_sessions import build_session_manifest, write_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="Path to a local personal practice video.")
    parser.add_argument("--sport", choices=["golf", "basketball"], default="golf")
    parser.add_argument("--session-id", help="Stable local session id.")
    parser.add_argument("--notes", default="", help="Private local notes for this session.")
    parser.add_argument(
        "--sessions-root",
        type=Path,
        default=Path("data/local/sessions"),
        help="Ignored local folder where manifests are written.",
    )
    parser.add_argument("--no-hash", action="store_true", help="Skip local SHA-256 deduplication hash.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    manifest = build_session_manifest(
        video_path=args.video,
        sport=args.sport,
        session_id=args.session_id,
        notes=args.notes,
        include_hash=not args.no_hash,
    )
    manifest_path = write_manifest(manifest, args.sessions_root)
    print(json.dumps({"manifest_path": str(manifest_path), "session_id": manifest["session_id"]}, indent=2))


if __name__ == "__main__":
    main()


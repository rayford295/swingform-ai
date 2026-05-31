"""Local-only personal practice session registration."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}


def slugify(value: str) -> str:
    """Return a filesystem-safe slug."""

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "session"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 hash for a local file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _mdls_raw(path: Path, attribute: str) -> str | None:
    try:
        completed = subprocess.run(
            ["mdls", "-raw", "-name", attribute, str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None

    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    if not value or value == "(null)":
        return None
    return value


def _maybe_number(value: str | None) -> float | int | str | None:
    if value is None:
        return None
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer():
        return int(number)
    return number


def probe_video_metadata(path: Path) -> dict[str, Any]:
    """Return best-effort local video metadata without uploading the file."""

    width = _maybe_number(_mdls_raw(path, "kMDItemPixelWidth"))
    height = _maybe_number(_mdls_raw(path, "kMDItemPixelHeight"))
    duration = _maybe_number(_mdls_raw(path, "kMDItemDurationSeconds"))
    codecs = _mdls_raw(path, "kMDItemCodecs")
    created_at = _mdls_raw(path, "kMDItemContentCreationDate")

    return {
        "duration_seconds": duration,
        "width": width,
        "height": height,
        "codecs": codecs,
        "content_created_at": created_at,
    }


def build_session_manifest(
    video_path: Path,
    sport: str,
    session_id: str | None = None,
    notes: str = "",
    include_hash: bool = True,
) -> dict[str, Any]:
    """Build a local-only manifest for a personal practice video."""

    resolved = video_path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(resolved)
    if resolved.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError(f"Unsupported video suffix: {resolved.suffix}")

    now = datetime.now(timezone.utc)
    safe_session_id = session_id or f"{now:%Y-%m-%d}-{slugify(resolved.stem)}"
    stat = resolved.stat()
    manifest = {
        "schema_version": "local-session-v1",
        "session_id": safe_session_id,
        "sport": sport,
        "privacy": "private-local-only",
        "source": {
            "path": str(resolved),
            "filename": resolved.name,
            "size_bytes": stat.st_size,
            "sha256": sha256_file(resolved) if include_hash else None,
        },
        "video_metadata": probe_video_metadata(resolved),
        "labels": {
            "phase_labels": [],
            "quality_notes": [],
        },
        "derived_outputs": {
            "pose_json": None,
            "metrics_json": None,
            "report_md": None,
            "annotated_video": None,
        },
        "notes": notes,
        "registered_at": now.isoformat(),
        "public_release": {
            "raw_video_committed": False,
            "faces_or_private_locations_committed": False,
            "allowed_public_outputs": [
                "synthetic examples",
                "de-identified aggregate metrics",
                "approved screenshots",
                "method documentation",
            ],
        },
    }
    return manifest


def write_manifest(manifest: dict[str, Any], sessions_root: Path) -> Path:
    """Write a local-only session manifest."""

    target_dir = sessions_root / str(manifest["session_id"])
    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


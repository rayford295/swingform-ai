"""Video encoding helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path


def reencode_h264(video_path: Path, crf: int = 26) -> bool:
    """Re-encode a video in place to web-playable H.264 via imageio-ffmpeg.

    OpenCV's mp4v output is several times larger and does not play in
    browsers. Returns False (leaving the file untouched) when imageio-ffmpeg
    is not installed or ffmpeg fails.
    """

    try:
        import imageio_ffmpeg
    except ImportError:
        return False
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_path = video_path.with_suffix(".h264.mp4")
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(tmp_path),
        ],
        capture_output=True,
    )
    if result.returncode != 0 or not tmp_path.exists():
        tmp_path.unlink(missing_ok=True)
        return False
    tmp_path.replace(video_path)
    return True

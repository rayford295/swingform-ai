#!/usr/bin/env python
"""Regenerate the Open Examples tables in both READMEs from summary.json files.

Every numeric cell comes from the committed session summaries, so the tables
cannot drift from the artifacts. Run after adding or re-analyzing a session:

    python scripts/generate_examples_table.py
"""

from __future__ import annotations

import json
from pathlib import Path

START_MARKER = "<!-- examples-table:start -->"
END_MARKER = "<!-- examples-table:end -->"

# Display order and optional context notes; everything else is derived.
SESSION_ORDER = [
    ("yifan-basketball-0710", "1v1"),
    ("yifan-golf-0601", None),
    ("yifan-golf-0520", None),
    ("golf-swing-demo", None),
]

SPORT_LABELS = {
    "golf": ("⛳ Golf", "⛳ 高尔夫"),
    "basketball": ("🏀 Basketball", "🏀 篮球"),
}


def detect_sport(summary: dict) -> str:
    return "golf" if "swing_summaries" in summary else "basketball"


def event_cell(summary: dict, lang: str) -> str:
    if "swing_summaries" in summary:
        count = len(summary["swing_summaries"])
        return f"{count} swings" if lang == "en" else f"{count} 次挥杆"
    count = len(summary["shot_events"])
    if lang == "en":
        return f"{count} release" + ("s" if count != 1 else "")
    return f"{count} 次出手"


def table_rows(lang: str) -> list[str]:
    rows = []
    for session, note in SESSION_ORDER:
        summary_path = Path("examples") / session / "summary.json"
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        sport = SPORT_LABELS[detect_sport(summary)][0 if lang == "en" else 1]
        if note:
            sport = f"{sport} · {note}"
        video = summary["video"]
        pose = summary["pose"]
        duration = video["duration_s"]
        clip = f"{duration:.1f} s · {video['width']}×{video['height']}"
        frames = f"{pose['detected_frames']} / {pose['total_frames']}"
        rows.append(
            f"| [{session}](examples/{session}/) | {sport} | {clip} | {frames} "
            f"| {event_cell(summary, lang)} |"
        )
    return rows


def build_table(lang: str) -> str:
    if lang == "en":
        header = ["| Session | Sport | Clip | Frames | Events |", "|---|---|---|---|---|"]
    else:
        header = ["| 会话 | 运动 | 视频 | 帧数 | 事件 |", "|---|---|---|---|---|"]
    return "\n".join(header + table_rows(lang))


def rewrite(readme_path: Path, lang: str) -> None:
    text = readme_path.read_text(encoding="utf-8")
    if START_MARKER not in text or END_MARKER not in text:
        raise SystemExit(f"{readme_path} is missing the examples-table markers.")
    head, rest = text.split(START_MARKER, 1)
    _, tail = rest.split(END_MARKER, 1)
    text = head + START_MARKER + "\n" + build_table(lang) + "\n" + END_MARKER + tail
    readme_path.write_text(text, encoding="utf-8")
    print(f"updated {readme_path}")


def main() -> None:
    rewrite(Path("README.md"), "en")
    rewrite(Path("README.zh-CN.md"), "zh")


if __name__ == "__main__":
    main()

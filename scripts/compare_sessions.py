#!/usr/bin/env python
"""Compare two analyzed sessions of the same sport and export a report.

The personal-motion-record loop: same athlete, same sport, two sessions,
per-event metrics side by side.

Usage:
    python scripts/compare_sessions.py examples/yifan-golf-0520 examples/yifan-golf-0601
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from swingform_ai.compare import ComparisonRow, comparison_rows, extract_records

# Categorical slots 1-2 of the validated default palette; session identity is
# fixed to the argument order (A = first, B = second), never restyled by rank.
SESSION_COLORS = ["#2a78d6", "#1baf7a"]
TEXT_PRIMARY = "#1a1a19"
TEXT_SECONDARY = "#5f5e56"
GRID = "#e5e4dc"


def load_summary(session_dir: Path) -> dict:
    return json.loads((session_dir / "summary.json").read_text(encoding="utf-8"))


def plot_comparison(
    rows: list[ComparisonRow],
    name_a: str,
    name_b: str,
    output_path: Path,
) -> None:
    cols = 2
    grid_rows = (len(rows) + cols - 1) // cols
    fig, axes = plt.subplots(grid_rows, cols, figsize=(8.6, 2.6 * grid_rows))
    axes = list(axes.flat) if hasattr(axes, "flat") else [axes]
    for axis in axes[len(rows) :]:
        axis.axis("off")
    for axis, row in zip(axes, rows):
        for idx, (name, values, color) in enumerate(
            [(name_a, row.values_a, SESSION_COLORS[0]), (name_b, row.values_b, SESSION_COLORS[1])]
        ):
            session_mean = sum(values) / len(values)
            # Mean as a thin bar-end; individual events as open markers above it.
            axis.hlines(session_mean, idx - 0.22, idx + 0.22, color=color, linewidth=3)
            axis.plot(
                [idx] * len(values),
                values,
                linestyle="none",
                marker="o",
                markersize=6,
                markerfacecolor="white",
                markeredgecolor=color,
                markeredgewidth=1.6,
            )
            unit = f" {row.unit}" if row.unit else ""
            axis.annotate(
                f"{session_mean:.2f}{unit}",
                (idx, session_mean),
                textcoords="offset points",
                xytext=(28, -4),
                fontsize=8,
                color=TEXT_PRIMARY,
            )
        axis.set_xlim(-0.6, 1.6)
        axis.set_xticks([0, 1])
        axis.set_xticklabels([name_a, name_b], fontsize=8, color=TEXT_SECONDARY)
        axis.set_title(row.label, fontsize=9, color=TEXT_PRIMARY, loc="left")
        axis.tick_params(axis="y", labelsize=8, colors=TEXT_SECONDARY)
        axis.grid(True, axis="y", color=GRID, linewidth=0.8)
        for spine in axis.spines.values():
            spine.set_visible(False)
    fig.suptitle(f"{name_a} vs {name_b} · per-event metrics", fontsize=11, color=TEXT_PRIMARY)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=180, facecolor="white")
    plt.close(fig)


def write_report(
    sport: str,
    rows: list[ComparisonRow],
    summary_a: dict,
    summary_b: dict,
    name_a: str,
    name_b: str,
    chart_rel_path: str,
    output_path: Path,
) -> None:
    event_word = "swings" if sport == "golf" else "shots"
    lines = [
        f"# Session Comparison: {name_a} vs {name_b}",
        "",
        f"Same athlete, same sport ({sport}), two sessions. Values are per-{event_word[:-1]} "
        "means; open dots on the chart are individual events.",
        "",
        f"![Comparison chart]({chart_rel_path})",
        "",
        "| Metric | " + f"{name_a} | {name_b} | Delta |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        unit = f" {row.unit}" if row.unit else ""
        lines.append(
            f"| {row.label} | {row.mean_a:.2f}{unit} | {row.mean_b:.2f}{unit} | "
            f"{row.delta:+.2f}{unit} |"
        )
    lines.extend(
        [
            "",
            "## Sessions",
            "",
            "| | " + f"{name_a} | {name_b} |",
            "| --- | --- | --- |",
            f"| Events | {len(summary_a.get('swing_summaries', summary_a.get('shot_events', [])))} "
            f"| {len(summary_b.get('swing_summaries', summary_b.get('shot_events', [])))} |",
            f"| Duration | {summary_a['video']['duration_s']:.1f}s | {summary_b['video']['duration_s']:.1f}s |",
            f"| Resolution | {summary_a['video']['width']}x{summary_a['video']['height']} "
            f"| {summary_b['video']['width']}x{summary_b['video']['height']} |",
            f"| Pose coverage | {summary_a['pose']['coverage_pct']:.1f}% | {summary_b['pose']['coverage_pct']:.1f}% |",
            "",
            "## Limitations",
            "",
            "- Single-camera pose proxies; camera angle and distance differ between sessions, so cross-session deltas are directional, not calibrated measurements.",
            "- Metrics compare only events the detector isolated in both sessions.",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_a", type=Path, help="First session directory (e.g. examples/yifan-golf-0520)")
    parser.add_argument("session_b", type=Path, help="Second session directory")
    parser.add_argument("--output-doc", type=Path, default=None, help="Defaults to docs/examples/compare-<a>-vs-<b>.md")
    parser.add_argument("--asset-output", type=Path, default=None, help="Defaults to docs/assets/compare-<a>-vs-<b>")
    args = parser.parse_args(argv)

    name_a = args.session_a.name
    name_b = args.session_b.name
    slug = f"compare-{name_a}-vs-{name_b}"
    output_doc = args.output_doc or Path("docs/examples") / f"{slug}.md"
    asset_output = args.asset_output or Path("docs/assets") / slug

    summary_a = load_summary(args.session_a)
    summary_b = load_summary(args.session_b)
    sport_a, records_a = extract_records(summary_a)
    sport_b, records_b = extract_records(summary_b)
    if sport_a != sport_b:
        raise SystemExit(f"Cannot compare {sport_a} against {sport_b}.")
    rows = comparison_rows(sport_a, records_a, records_b)
    if not rows:
        raise SystemExit("No shared metrics between the two sessions.")

    chart_path = asset_output / "metric_comparison.png"
    plot_comparison(rows, name_a, name_b, chart_path)
    write_report(
        sport_a,
        rows,
        summary_a,
        summary_b,
        name_a,
        name_b,
        f"../assets/{slug}/metric_comparison.png",
        output_doc,
    )
    print(json.dumps({"doc": str(output_doc), "chart": str(chart_path), "metrics": len(rows)}, indent=2))


if __name__ == "__main__":
    main()

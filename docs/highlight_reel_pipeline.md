# Long Video Highlight-Reel Pipeline

## Product Task

Input: one long practice video.

Output:

1. Swing count.
2. A ranked list of the best swings in the video.
3. Short exported clips for the best swings.
4. One combined high-quality highlight reel.
5. Ball trajectory overlay or a clearly marked low-confidence proxy trail.
6. `swing_report.json` with all timings, scores, and output paths.

This is the first product-shaped workflow for SwingForm AI:

```text
long practice video
  -> motion timeline
  -> swing candidate detection
  -> transparent scoring
  -> best-swing selection
  -> clip export
  -> ball-trail overlay
  -> short highlight reel
```

## Command

```bash
python -m pip install -e ".[pose]"
python scripts/build_highlight_reel.py path/to/long_practice_video.mp4 \
  --session-id range-session-001 \
  --top-k 3 \
  --shot-direction right \
  --motion-threshold-quantile 0.55
```

Outputs are written under:

```text
outputs/highlight-reels/range-session-001/
```

The output directory is ignored by git. Long personal videos and generated private clips should stay local unless a session is explicitly cleared for release.

## Scoring Standard

The first scoring model is intentionally simple and inspectable.

| Component | Weight | Meaning |
| --- | ---: | --- |
| Motion energy | 30 | Stronger peak movement during the swing segment |
| Tempo window | 20 | Preference for a complete swing-length segment around 3.2 seconds |
| Setup and finish stability | 20 | Lower motion before and after the swing |
| Image quality | 15 | Brightness and sharpness proxies |
| Complete motion | 15 | Sustained movement across the segment, not only one spike |

This score is not a coaching verdict. It is a clip-selection score: which swings are most worth saving, watching, and sharing from a long practice video.

## Ball Trajectory Overlay

The MVP supports three trail modes:

| Mode | Use |
| --- | --- |
| `auto` | Use labels when available; otherwise draw a low-confidence proxy trail |
| `labels` | Draw only human-checked ball labels from CSV |
| `proxy` | Draw a cinematic shot arc as a visual placeholder |
| `none` | Export clips without ball trail |

Ball label CSV format:

```csv
frame_index,x,y,confidence
125,0.54,0.66,1.0
130,0.62,0.51,1.0
135,0.70,0.41,0.9
```

`x` and `y` can be normalized coordinates in `[0, 1]` or pixel coordinates.

## Current Limits

1. Swing detection uses video motion, not a trained golf event model.
2. The default trajectory is a visual proxy if no ball labels are supplied.
3. Exported video does not preserve original audio.
4. The score ranks shareable clips, not technical golf quality.

## Next Upgrades

1. Replace motion-only candidate detection with pose-aware address, top, impact, and finish events.
2. Add ball detection from labels, then YOLO or TrackNet-style tracking.
3. Add club-head proxy tracking.
4. Replace proxy trail with fitted 2D trajectory and confidence bands.
5. Add a web viewer for reviewing every detected swing before export.

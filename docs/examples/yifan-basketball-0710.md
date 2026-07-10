# Yifan Basketball 07.10

This session is the first contested-gameplay example: a 57-second 1v1 clip ("vs Dreamway", indoor court), also published as a [YouTube Short](https://www.youtube.com/shorts/9nPEMg---YA).
Unlike the earlier solo-practice clip, this footage has two athletes, occlusion, and stretches where the primary athlete leaves the frame — which is exactly what made it a useful stress test.

![Demo](../assets/yifan-basketball-0710/demo.gif)

![Contact sheet](../assets/yifan-basketball-0710/contact_sheet.jpg)

![Metric timeline](../assets/yifan-basketball-0710/metric_timeline.png)

![Skeleton keyposes](../assets/yifan-basketball-0710/skeleton_keyposes.png)

## Open Example Files

| File | Use |
| --- | --- |
| `examples/yifan-basketball-0710/basketball.mp4` | Source basketball court clip |
| `examples/yifan-basketball-0710/basketball_overlay.mp4` | Skeleton overlay review video |
| `examples/yifan-basketball-0710/pose_sequence.json` | MediaPipe pose landmarks for tracked frames |
| `examples/yifan-basketball-0710/metrics.csv` | Per-frame basketball motion metrics |
| `examples/yifan-basketball-0710/summary.json` | Demo summary for reports |

## Video and Detection

- Duration: 57.07s
- Resolution: 480x854
- FPS: 30.00
- Pose coverage: 1616 of 1712 frames (94.4%)
- Mean landmark visibility: 0.857
- Reliable shot-form events isolated: 1

## Main Read

- Contested 1v1 footage is much harder than solo practice: without filtering, the detector reported 4 "release" events, of which only 1 was a real shot. The other 3 were a dribble mislabel and two phantom poses detected at the frame edge after the athlete left the frame.
- This session motivated a new plausibility gate in `detect_shot_events`: a release candidate must come from an upright, full-height pose (shoulders above hips above ankles with non-trivial extent) with sufficient landmark visibility. With the gate, exactly the one real shot at 35.70s survives.
- Pose coverage stays high (94.4%) even in gameplay, but coverage is not reliability — the tracker happily follows the wrong athlete or a phantom, so event-level gating matters more than frame-level coverage.
- The release label is pose-based: it comes from visible wrist height, wrist speed, and arm extension, not from ball contact.
- The next technical step is still ball/rim association, plus player re-identification so metrics attach to one athlete across possessions.

## Basketball Metrics

| Metric | Value |
| --- | ---: |
| Mean shooting elbow angle | 91.5 deg |
| Max shooting wrist height proxy | 0.967 |
| Min shooting knee angle | 11.7 deg |
| Mean body speed proxy | 0.275 |

## Interpretation

The best product direction is a personal multi-sport movement record: compare Yifan against Yifan first, then use cleaner labels to train sport-specific phase models later.
Golf can keep its address/top/impact/finish loop, while basketball gets set/dip/lift/release/follow-through/landing labels as pose proxies first and ball-linked events later.

## Detected Shot Events

| Shot | Set | Dip | Lift | Release proxy | Follow-through | Landing |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 34.63s | 34.90s | 35.33s | 35.70s | 36.10s | 36.67s |

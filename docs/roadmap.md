# Roadmap

## Milestone 0: Project Foundation

Status: complete for the first scaffold.

1. Define the problem and open-source release boundary.
2. Add research scan and requirements.
3. Create a small Python package with geometry helpers.
4. Add golf and basketball sport profiles.
5. Add tests and a GitHub Actions workflow.

## Milestone 1: Pose Extraction

Goal: convert one local golf swing video into pose JSON.

1. Register local personal videos with ignored session manifests.
2. Add a MediaPipe pose backend.
3. Save per-frame landmarks and confidence values.
4. Export annotated frame previews.
5. Record failure modes for lighting, camera angle, occlusion, and clothing.

## Milestone 2: Golf Swing Analysis

Goal: produce a first practice-session report.

1. Add manual phase labels for a few local videos.
2. Compute address, top, impact, and finish metrics.
3. Generate a markdown report with timestamps and key frames.
4. Compare own swings across sessions.

## Milestone 3: Golf Event Model

Goal: replace manual phase labels with a reproducible event model.

1. Reproduce a GolfDB-style event baseline.
2. Evaluate event timing error against manual labels.
3. Add confidence and uncertainty to reported phases.
4. Keep the model optional so the rule-based path still works.

## Milestone 4: Basketball Shot Profile

Goal: reuse the core for basketball shooting form.

1. Add shot-phase labels for set, dip, lift, release, follow-through, and landing.
2. Add release-height, elbow-angle, wrist-height, and landing-balance metrics.
3. Compare new shots against the user's own best session.
4. Add ball tracking only after the human-pose metrics are stable.

## Milestone 5: Product Prototype

Goal: make the workflow easier to use without hiding the research logic.

1. Add a small local web dashboard.
2. Show side-by-side sessions and metric trends.
3. Add short natural-language feedback grounded in measured frames.
4. Keep raw personal video local by default.

# Contributing

SwingForm AI is a pure open-source sports-AI project. The repo should feel useful at first glance and trustworthy after inspection.

## What Good Contributions Improve

1. The project becomes easier to run.
2. The README, charts, or reports become clearer and more beautiful.
3. A sport profile gains a useful metric or phase definition.
4. An example becomes more reproducible.
5. A claim becomes better calibrated to the evidence.

## Example Standards

Open examples should include input and output together:

1. Source video or a clear download path.
2. Pose export or instructions to generate it.
3. Metrics table.
4. Human-readable report.
5. Visual index or keypose figure.
6. Notes about limits and assumptions.

## Visual Standards

1. Favor clean charts with readable labels.
2. Keep README images useful, not decorative.
3. Use stable filenames under `docs/assets/` for report visuals.
4. Put source examples under `examples/<demo-name>/`.
5. Avoid cluttered screenshots when a cropped visual index or skeleton figure explains the result better.

## Development

Install:

```bash
python -m pip install -e .
```

Install video-analysis extras:

```bash
python -m pip install -e ".[pose]"
```

Test:

```bash
python -m unittest discover -s tests
```

Run the open golf demo:

```bash
python scripts/analyze_local_golf_video.py \
  examples/golf-swing-demo/golf.mp4 \
  --session-id golf-swing-demo \
  --handedness right \
  --events-json examples/golf_swing_demo_events.json
```


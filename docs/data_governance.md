# Data Governance

## Public-Safe Boundary

Commit:

1. Code.
2. Documentation.
3. Synthetic pose examples.
4. Small de-identified aggregate tables.
5. Public dataset metadata and download instructions.
6. Approved images where faces and private places are not visible.

Do not commit:

1. Raw personal golf or basketball videos.
2. Faces, private practice locations, or exact filming timestamps.
3. Commercial app exports unless the license clearly allows redistribution.
4. Downloaded model weights.
5. Credentials, API keys, cookies, or local database files.
6. Medical, injury, or body-health inference.

## Local Folder Convention

Use these local-only folders when needed:

```text
data/local/videos/
data/local/pose_exports/
data/local/reports/
models/local/
```

These paths are ignored by git.

## Public Dataset Convention

For public datasets, commit only:

1. Dataset citation.
2. Source URL.
3. License note.
4. Download or preprocessing script when allowed.
5. Derived aggregate metrics that do not violate the dataset license.

## Personal Feedback Boundary

Feedback should stay measurement-grounded:

1. Name the measured joint or phase.
2. Show the timestamp or frame.
3. Describe the visible pattern.
4. Suggest a practice drill.

Feedback should not diagnose injury, promise performance gains, or claim professional authority without validation.


# Data Governance

## Open-Source Data Boundary

Commit:

1. Code.
2. Documentation.
3. Synthetic pose examples.
4. Explicitly cleared practice videos.
5. Pose exports, metric tables, reports, screenshots, and visual indexes derived from cleared examples.
6. Public dataset metadata and download instructions.

Do not commit:

1. Practice videos that have not been explicitly cleared for open release.
2. Commercial app exports unless the license clearly allows redistribution.
3. Downloaded model weights when they can be fetched from their upstream source.
4. Virtual environments, caches, generated package metadata, or machine-specific files.
5. Credentials, API keys, cookies, or local database files.
6. Private chats, screenshots, meeting notes, or market conversations.
7. Medical, injury, or body-health inference.

## Local Folder Convention

Use these local-only folders when needed:

```text
data/local/videos/
data/local/pose_exports/
data/local/reports/
models/local/
```

These paths are ignored by git.

Move cleared examples into `examples/<demo-name>/` before committing them.

## Public Dataset Convention

For public datasets, commit only:

1. Dataset citation.
2. Source URL.
3. License note.
4. Download or preprocessing script when allowed.
5. Derived aggregate metrics that do not violate the dataset license.

## Feedback Boundary

Feedback should stay measurement-grounded:

1. Name the measured joint or phase.
2. Show the timestamp or frame.
3. Describe the visible pattern.
4. Suggest a practice drill.

Feedback should not diagnose injury, promise performance gains, or claim professional authority without validation.

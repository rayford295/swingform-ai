from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swingform_ai.local_sessions import build_session_manifest, slugify, write_manifest


class LocalSessionsTest(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(slugify("Golf Session 01!"), "golf-session-01")

    def test_build_and_write_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / "golf.mp4"
            video.write_bytes(b"not a real video but enough for metadata tests")
            manifest = build_session_manifest(
                video,
                sport="golf",
                session_id="test-session",
                notes="unit test",
                include_hash=False,
            )
            self.assertEqual(manifest["session_id"], "test-session")
            self.assertEqual(manifest["source"]["filename"], "golf.mp4")
            self.assertFalse(manifest["public_release"]["raw_video_committed"])

            manifest_path = write_manifest(manifest, root / "sessions")
            self.assertTrue(manifest_path.exists())


if __name__ == "__main__":
    unittest.main()


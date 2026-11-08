import tempfile
import unittest
from pathlib import Path

from longform import collect_segments


class LongFormCollectionTests(unittest.TestCase):
    def test_keeps_first_episode_and_skips_later_openers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for episode, names in {
                "ep1": ["seg_001.mp4", "seg_002.mp4"],
                "ep2": ["seg_001.mp4", "seg_002.mp4", "seg_003.mp4"],
            }.items():
                folder = root / episode / "segments"
                folder.mkdir(parents=True)
                for name in names:
                    (folder / name).touch()
            result = collect_segments(["ep1", "ep2"], tmp)
            self.assertEqual([p.name for p in result],
                             ["seg_001.mp4", "seg_002.mp4",
                              "seg_002.mp4", "seg_003.mp4"])

    def test_missing_episode_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                collect_segments(["missing"], tmp)


if __name__ == "__main__":
    unittest.main()

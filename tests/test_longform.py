import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from longform import assemble, collect_segments


class LongFormCollectionTests(unittest.TestCase):
    def test_preserves_all_scenes_by_default(self):
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
            self.assertEqual([(p.parent.parent.name, p.name) for p in result],
                             [("ep1", "seg_001.mp4"), ("ep1", "seg_002.mp4"),
                              ("ep2", "seg_001.mp4"), ("ep2", "seg_002.mp4"),
                              ("ep2", "seg_003.mp4")])

    def test_can_explicitly_skip_later_openers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for episode in ("ep1", "ep2"):
                folder = root / episode / "segments"
                folder.mkdir(parents=True)
                for name in ("seg_001.mp4", "seg_002.mp4"):
                    (folder / name).touch()
            result = collect_segments(["ep1", "ep2"], tmp, skip_openers=True)
            self.assertEqual([(p.parent.parent.name, p.name) for p in result],
                             [("ep1", "seg_001.mp4"), ("ep1", "seg_002.mp4"),
                              ("ep2", "seg_002.mp4")])

    def test_missing_episode_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                collect_segments(["missing"], tmp)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                         "FFmpeg/FFprobe required for media integration test")
    def test_assembles_real_audio_video_to_landscape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "ep1" / "segments"
            folder.mkdir(parents=True)
            source = folder / "seg_001.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=navy:s=360x640:r=25:d=1",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", str(source)
            ], check=True)
            output = root / "exports" / "documentary.mp4"
            result = assemble(["ep1"], output, str(root))
            self.assertEqual(result["scenes"], 1)
            self.assertEqual(result["qa"]["width"], 1920)
            self.assertEqual(result["qa"]["height"], 1080)
            self.assertTrue(result["qa"]["audio"])


if __name__ == "__main__":
    unittest.main()

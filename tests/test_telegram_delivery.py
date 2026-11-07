import os
import unittest
from unittest.mock import patch

import pipeline


class TelegramDeliveryTests(unittest.TestCase):
    def test_small_video_is_sent_without_transcoding(self):
        with patch("pipeline.os.path.getsize", return_value=10 * 1024 * 1024), \
             patch("pipeline.subprocess.run") as run:
            path, temporary = pipeline.telegram_ready_video("small.mp4")
        self.assertEqual(path, "small.mp4")
        self.assertIsNone(temporary)
        run.assert_not_called()

    def test_oversized_video_gets_validated_temporary_1080p_copy(self):
        created = []

        def fake_run(command, **kwargs):
            if command[0] == "ffprobe":
                return type("Result", (), {"stdout": "600"})()
            output = command[-1]
            with open(output, "wb") as handle:
                handle.write(b"compressed-video")
            created.append(output)
            return type("Result", (), {"stdout": "", "stderr": ""})()

        with patch("pipeline.os.path.getsize",
                   side_effect=[50 * 1024 * 1024, 45 * 1024 * 1024]), \
             patch("pipeline.subprocess.run", side_effect=fake_run), \
             patch("pipeline.validate_video") as validate:
            path, temporary = pipeline.telegram_ready_video("large.mp4")

        self.assertEqual(path, temporary)
        self.assertTrue(os.path.exists(path))
        validate.assert_called_once_with(path, 1080, 1920)
        os.remove(path)

    def test_rejects_invalid_duration_without_creating_upload_copy(self):
        with patch("pipeline.os.path.getsize", return_value=50 * 1024 * 1024), \
             patch("pipeline.subprocess.run",
                   return_value=type("Result", (), {"stdout": "0"})()), \
             patch("pipeline.tempfile.mkstemp") as mkstemp:
            with self.assertRaisesRegex(RuntimeError, "invalid duration"):
                pipeline.telegram_ready_video("bad.mp4")
        mkstemp.assert_not_called()

    def test_rejects_when_required_bitrate_is_below_quality_floor(self):
        with patch("pipeline.os.path.getsize", return_value=50 * 1024 * 1024), \
             patch("pipeline.subprocess.run",
                   return_value=type("Result", (), {"stdout": "100000"})()), \
             patch("pipeline.tempfile.mkstemp") as mkstemp:
            with self.assertRaisesRegex(RuntimeError, "below safe quality floor"):
                pipeline.telegram_ready_video("long.mp4")
        mkstemp.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

import render_quality


class RenderQualityTests(unittest.TestCase):
    def test_encoder_uses_h264_crf_and_bt709(self):
        args = render_quality.encoder_args(30, crf=19)
        self.assertIn("libx264", args)
        self.assertIn("19", args)
        self.assertIn("bt709", args)
        self.assertIn("yuv420p", args)

    def test_rejects_out_of_range_crf(self):
        with self.assertRaises(ValueError):
            render_quality.encoder_args(30, crf=10)

    @patch("render_quality.probe_video")
    def test_validate_requires_video_and_audio(self, probe):
        probe.return_value = {"streams": [], "format": {"duration": "10"}}
        with self.assertRaisesRegex(RuntimeError, "missing video or audio"):
            render_quality.validate_video("episode.mp4")

    @patch("render_quality.probe_video")
    def test_validate_accepts_vertical_h264_with_audio(self, probe):
        probe.return_value = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264",
                 "width": 1080, "height": 1920, "pix_fmt": "yuv420p",
                 "avg_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"duration": "12.5"},
        }
        result = render_quality.validate_video("episode.mp4")
        self.assertEqual(result["duration"], 12.5)
        self.assertEqual(result["fps"], 30)

    @patch("render_quality.probe_video")
    def test_validate_rejects_low_frame_rate(self, probe):
        probe.return_value = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264",
                 "width": 1080, "height": 1920, "pix_fmt": "yuv420p",
                 "avg_frame_rate": "15/1"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"duration": "12.5"},
        }
        with self.assertRaisesRegex(RuntimeError, "at least 24fps"):
            render_quality.validate_video("episode.mp4")


if __name__ == "__main__":
    unittest.main()

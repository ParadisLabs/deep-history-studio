"""Regression tests for moderation-safe image fallback."""
import io
import os
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

import illustrator


class IllustratorModerationFallbackTests(unittest.TestCase):
    def _moderation_error(self):
        body = (
            b'{"errors":[{"message":"Input prompt contains NSFW content",'
            b'"code":8007}],"success":false}'
        )
        return urllib.error.HTTPError(
            "https://api.cloudflare.com/test", 400, "Bad Request", {}, io.BytesIO(body)
        )

    def test_moderation_rejection_uses_neutral_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "fallback.png")
            with patch.object(illustrator, "reserve_image", return_value=True), \
                 patch.object(illustrator.urllib.request, "urlopen",
                              side_effect=self._moderation_error()), \
                 patch.object(illustrator, "_pollinations_image", return_value=True) as fallback:
                illustrator.generate_image(
                    "account", "token", "stick figure holding a historical sword", out, tries=1
                )
            self.assertTrue(fallback.called)
            prompt = fallback.call_args.args[0].lower()
            self.assertIn("peaceful museum-like setting", prompt)
            self.assertIn("no combat", prompt)
            self.assertNotIn("historical sword", prompt)

    def test_non_moderation_400_still_fails_fast(self):
        body = b'{"errors":[{"message":"Invalid request schema","code":1001}]}'
        error = urllib.error.HTTPError(
            "https://api.cloudflare.com/test", 400, "Bad Request", {}, io.BytesIO(body)
        )
        with patch.object(illustrator, "reserve_image", return_value=True), \
             patch.object(illustrator.urllib.request, "urlopen", side_effect=error), \
             patch.object(illustrator, "_pollinations_image", return_value=True) as fallback:
            with self.assertRaisesRegex(RuntimeError, "bad request"):
                illustrator.generate_image("account", "token", "ordinary prompt", "unused.png", tries=1)
        fallback.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)

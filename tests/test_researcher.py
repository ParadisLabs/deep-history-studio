import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from researcher import parse_loc_results


class LibraryOfCongressParsing(unittest.TestCase):
    def test_parses_attributed_catalog_metadata(self):
        payload = {
            "results": [{
                "title": "Letters from the 1910 expedition",
                "date": "1910",
                "contributor": ["Example Archive"],
                "partof": ["Manuscript Division"],
                "description": [
                    "A long catalog description describing the expedition, "
                    "the people involved, the location, and the surviving "
                    "documents in enough detail to provide useful context."
                ],
                "rights": "Rights status not evaluated",
                "url": "https://www.loc.gov/item/example/",
            }]
        }
        sources = parse_loc_results(payload)
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["source_type"], "Library of Congress catalog")
        self.assertIn("Catalog description:", sources[0]["text"])
        self.assertEqual(sources[0]["rights"], "Rights status not evaluated")
        self.assertEqual(sources[0]["url"], "https://www.loc.gov/item/example/")

    def test_skips_records_without_useful_description_or_url(self):
        payload = {
            "results": [
                {"title": "Too short", "description": "Tiny"},
                {"title": "No link", "description": "A " + "detailed " * 20 + "description"},
            ]
        }
        self.assertEqual(parse_loc_results(payload), [])

    def test_respects_result_limit(self):
        payload = {"results": [
            {"title": f"Record {i}", "description": "A detailed catalog description " * 8,
             "url": f"https://www.loc.gov/item/{i}/"}
            for i in range(5)
        ]}
        self.assertEqual(len(parse_loc_results(payload, limit=2)), 2)


if __name__ == "__main__":
    unittest.main()

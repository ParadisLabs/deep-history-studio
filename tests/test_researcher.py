import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from researcher import parse_loc_results, parse_crossref_results


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


class CrossrefParsing(unittest.TestCase):
    def test_parses_attributed_scholarly_metadata(self):
        payload = {"message": {"items": [{
            "title": ["Trade routes in the medieval Mediterranean"],
            "DOI": "10.1234/example.1",
            "URL": "https://doi.org/10.1234/example.1",
            "publisher": "Example University Press",
            "published": {"date-parts": [[2021, 4, 1]]},
            "author": [{"given": "Amina", "family": "Example"}],
            "abstract": "<jats:p>Examines port records and merchant networks.</jats:p>",
        }]}}
        rows = parse_crossref_results(payload)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_type"], "Crossref scholarly metadata")
        self.assertIn("Amina Example", rows[0]["text"])
        self.assertIn("2021", rows[0]["text"])
        self.assertIn("Examines port records", rows[0]["text"])
        self.assertEqual(rows[0]["doi"], "10.1234/example.1")
        self.assertIn("primary sources", rows[0]["evidence_level"])

    def test_skips_records_without_title_or_resolvable_url(self):
        payload = {"message": {"items": [
            {"DOI": "10.1/no-title"},
            {"title": ["No DOI or URL"]},
        ]}}
        self.assertEqual(parse_crossref_results(payload), [])

    def test_respects_result_limit(self):
        payload = {"message": {"items": [
            {"title": [f"Paper {i}"], "DOI": f"10.1/{i}"} for i in range(5)
        ]}}
        self.assertEqual(len(parse_crossref_results(payload, limit=2)), 2)


if __name__ == "__main__":
    unittest.main()

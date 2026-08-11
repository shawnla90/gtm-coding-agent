import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


STARTER_DIR = Path(__file__).resolve().parents[1] / "starters" / "reddit-buyer-signals"
sys.path.insert(0, str(STARTER_DIR))

import geo  # noqa: E402


class GeoEvidenceTests(unittest.TestCase):
    def test_exa_result_is_labeled_retrieval_not_citation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            terms_path = tmp_dir / "terms.json"
            out_path = tmp_dir / "geo.json"
            terms_path.write_text(json.dumps({
                "terms": [{
                    "term": "best example workflow",
                    "intent": "high",
                    "why": "buyers asked",
                    "evidence": "source-linked question",
                }]
            }))
            visibility = {
                "available": True,
                "score": 100,
                "checked": 1,
                "queries": [{"query": "best example workflow", "appears": True}],
            }
            argv = [
                "geo.py",
                "--gen", str(terms_path),
                "--brand", "Acme",
                "--out", str(out_path),
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(geo, "get_key", return_value="test-key"),
                patch.object(geo, "retrieval_visibility", return_value=visibility),
            ):
                self.assertEqual(geo.main(), 0)

            result = json.loads(out_path.read_text())
            self.assertEqual(result["retrieval_visibility_score"], 100)
            self.assertEqual(result["terms"][0]["currently_retrieved_by_exa"], "yes")
            self.assertNotIn("citation", result)
            self.assertNotIn("currently_cited_by_ai", result["terms"][0])


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "starters" / "reddit-buyer-signals"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pull = load_module("reddit_clearbox_pull", STARTER / "pull.py")
init_db = load_module("reddit_clearbox_init_db", STARTER / "init_db.py")


class RedditClearboxImportTests(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.executescript(init_db.SCHEMA)

    def tearDown(self):
        self.con.close()

    def test_import_preserves_source_contract(self):
        row = {
            "id": "op-101",
            "kind": "lead",
            "title": "Need a better workflow",
            "url": "https://www.reddit.com/r/ops/comments/abc/need_a_better_workflow/?context=3",
            "created_utc": 2_000_000_000,
        }
        self.assertEqual(pull._upsert_thread(self.con, row, cutoff=0), 1)
        stored = self.con.execute(
            "SELECT external_id, clearbox_kind, permalink, source_type FROM reddit_threads"
        ).fetchone()
        self.assertEqual(stored, (row["id"], row["kind"], row["url"], "clearbox"))

    def test_invalid_source_fields_are_rejected(self):
        valid = {
            "id": "op-102",
            "kind": "competitor",
            "url": "https://www.reddit.com/r/ops/comments/def/source_thread/",
        }
        for key, value in (("id", ""), ("kind", "unknown"), ("url", "")):
            with self.subTest(key=key):
                row = dict(valid)
                row[key] = value
                with self.assertRaises(ValueError):
                    pull._upsert_thread(self.con, row, cutoff=0)

    def test_truncated_export_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ops.json"
            path.write_text(json.dumps({"truncated": True, "opportunities": []}))
            with self.assertRaisesRegex(SystemExit, "truncated"):
                pull._items_from_export(path)

    def test_complete_export_shapes_are_accepted(self):
        row = {
            "id": "op-103",
            "kind": "engage",
            "url": "https://www.reddit.com/r/ops/comments/ghi/source_thread/",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, payload in enumerate(([row], {"opportunities": [row]}, {"rows": [row]})):
                path = root / f"ops-{index}.json"
                path.write_text(json.dumps(payload))
                self.assertEqual(pull._items_from_export(path), [row])


if __name__ == "__main__":
    unittest.main()

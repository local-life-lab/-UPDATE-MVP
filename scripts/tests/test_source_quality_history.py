import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "source_quality_history.py"
spec = importlib.util.spec_from_file_location("source_quality_history", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceQualityHistoryTests(unittest.TestCase):
    def test_appends_snapshot_without_mutating_previous_history(self):
        old = {"snapshots": [{"captured_at": "old", "candidate_count": 2}]}
        report = {"candidate_count": 3, "sources": [{"name": "媒体A"}]}
        result = module.append_snapshot(old, report, "2026-11-24T00:00:00Z")
        self.assertEqual(len(old["snapshots"]), 1)
        self.assertEqual(len(result["snapshots"]), 2)
        self.assertEqual(result["snapshots"][-1]["source_count"], 1)

    def test_keeps_only_latest_30_snapshots(self):
        history = {"snapshots": [{"captured_at": str(i)} for i in range(30)]}
        result = module.append_snapshot(history, {"candidate_count": 0, "sources": []}, "new")
        self.assertEqual(len(result["snapshots"]), 30)
        self.assertEqual(result["snapshots"][0]["captured_at"], "1")
        self.assertEqual(result["snapshots"][-1]["captured_at"], "new")

    def test_rejects_invalid_report(self):
        with self.assertRaises(ValueError):
            module.append_snapshot({}, {"candidate_count": -1, "sources": []}, "now")


if __name__ == "__main__":
    unittest.main()

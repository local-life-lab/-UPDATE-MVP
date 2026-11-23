import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "source_quality_report.py"
spec = importlib.util.spec_from_file_location("source_quality_report", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourceQualityReportTests(unittest.TestCase):
    def test_reports_completeness_and_link_health_per_source(self):
        drafts = [
            {
                "id": "a", "source_name": "媒体A",
                "source_urls": [{"source_name": "媒体A", "url": "https://example.jp/a"}],
                "published_date": "2026-11-20", "event_date": "", "body_excerpt": "記事本文",
                "review_flags": ["住所未確認"],
                "source_link_checks": [{"url": "https://example.jp/a", "source_name": "媒体A", "status": "ok"}],
            },
            {
                "id": "b", "source_name": "媒体A",
                "source_urls": [{"source_name": "媒体A", "url": "https://example.jp/b"}],
                "published_date": "", "event_date": "2026-12-01", "body_excerpt": "",
                "review_flags": [],
                "source_link_checks": [{"url": "https://example.jp/b", "source_name": "媒体A", "status": "broken"}],
            },
            {
                "id": "c", "source_name": "媒体B", "source_url": "https://example.jp/c",
                "published_date": "2026-11-19", "event_date": "2026-11-30",
                "body_excerpt": "本文", "review_flags": [],
                "source_link_checks": [{"url": "https://example.jp/c", "source_name": "媒体B", "status": "inconclusive"}],
            },
        ]
        report = module.build_source_quality_report(drafts)
        a = next(x for x in report["sources"] if x["name"] == "媒体A")
        self.assertEqual(a["candidate_count"], 2)
        self.assertEqual(a["published_date_coverage_percent"], 50.0)
        self.assertEqual(a["event_date_coverage_percent"], 50.0)
        self.assertEqual(a["body_excerpt_coverage_percent"], 50.0)
        self.assertEqual(a["review_flag_rate_percent"], 50.0)
        self.assertEqual(a["broken_link_count"], 1)
        self.assertEqual(a["expected_link_count"], 2)
        self.assertEqual(a["link_check_record_coverage_percent"], 100.0)
        self.assertEqual(a["checked_link_count"], 2)
        b = next(x for x in report["sources"] if x["name"] == "媒体B")
        self.assertEqual(b["inconclusive_link_count"], 1)
        self.assertEqual(b["link_check_record_coverage_percent"], 100.0)

    def test_merged_candidate_is_counted_once_per_source(self):
        draft = {
            "id": "merged", "source_name": "媒体A", "source_url": "https://example.jp/a",
            "source_urls": [
                {"source_name": "媒体A", "url": "https://example.jp/a"},
                {"source_name": "媒体B", "url": "https://example.jp/b"},
            ],
            "published_date": "2026-11-20", "body_excerpt": "本文",
            "source_link_checks": [
                {"url": "https://example.jp/a", "source_name": "媒体A", "status": "ok"},
                {"url": "https://example.jp/b", "source_name": "媒体B", "status": "not_checked_limit"},
            ],
        }
        report = module.build_source_quality_report([draft])
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["source_candidate_mentions_total"], 2)
        self.assertEqual([x["candidate_count"] for x in report["sources"]], [1, 1])
        self.assertEqual(report["sources"][1]["unchecked_link_count"], 1)

    def test_missing_link_check_is_counted_as_not_recorded(self):
        report = module.build_source_quality_report([{
            "id": "missing", "source_name": "媒体C",
            "source_url": "https://example.jp/missing",
            "published_date": "2026-11-20",
        }])
        source = report["sources"][0]
        self.assertEqual(source["expected_link_count"], 1)
        self.assertEqual(source["link_check_record_coverage_percent"], 0.0)
        self.assertEqual(source["unchecked_link_count"], 1)
        self.assertEqual(source["link_status_counts"]["not_recorded"], 1)

    def test_report_does_not_claim_factual_accuracy(self):
        report = module.build_source_quality_report([])
        self.assertIn("真偽を評価・保証するものではありません", report["scope_note"])
        self.assertIn("情報源別の収集品質レポート", module.render_markdown(report))


if __name__ == "__main__":
    unittest.main()

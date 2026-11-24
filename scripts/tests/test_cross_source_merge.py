import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "generate_drafts.py"
spec = importlib.util.spec_from_file_location("generate_drafts", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CrossSourceMergeTests(unittest.TestCase):
    def candidate(self, url, title, municipality, body, event_date="2026-12-01"):
        return {
            "url": url,
            "normalized_url": module.normalize_url(url),
            "source_name": url.split("/")[2],
            "source_priority": 2,
            "title": title,
            "body_excerpt": body,
            "category": ["新店・開店"],
            "area": [municipality],
            "municipality": municipality,
            "municipality_candidates": [municipality],
            "event_date": event_date,
            "published_date": "2026-11-18",
        }

    def test_identical_generic_titles_in_different_cities_are_not_merged(self):
        rows = [
            self.candidate(
                "https://media-a.example/a",
                "山口県内に新店舗がオープン",
                "宇部市",
                "宇部市内に新しい店舗がオープンする。",
            ),
            self.candidate(
                "https://media-b.example/b",
                "山口県内に新店舗がオープン",
                "下関市",
                "下関市内に新しい店舗がオープンする。",
            ),
        ]
        merged = module.merge_candidates(rows)
        self.assertEqual(len(merged), 2)
        self.assertEqual({row["municipality"] for row in merged}, {"宇部市", "下関市"})

    def test_same_store_same_event_from_different_media_is_merged(self):
        rows = [
            self.candidate(
                "https://media-a.example/a",
                "山陽小野田市にロフトがオープン",
                "山陽小野田市",
                "山陽小野田市に生活雑貨専門店ロフトがオープンする。",
            ),
            self.candidate(
                "https://media-b.example/b",
                "生活雑貨専門店ロフトが山陽小野田市に開店",
                "山陽小野田市",
                "山陽小野田市にロフトがオープンする。",
            ),
        ]
        merged = module.merge_candidates(rows)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["duplicate_sources_count"], 2)

    def test_same_listing_url_does_not_merge_distinct_explicit_store_names(self):
        rows = [
            self.candidate(
                "https://www.seamall.jp/info/new-shop/",
                "モビスク（シーモール下関）2026年12月18日オープン",
                "下関市",
                "店名「モビスク」は2026年12月18日にオープン予定です。",
                event_date="2026-12-18",
            ),
            self.candidate(
                "https://www.seamall.jp/info/new-shop/",
                "福恩麻辣湯（シーモール下関）2026年12月18日オープン",
                "下関市",
                "店名「福恩麻辣湯」は2026年12月18日にオープン予定です。",
                event_date="2026-12-18",
            ),
        ]
        merged = module.merge_candidates(rows)
        self.assertEqual(len(merged), 2)
        self.assertEqual(
            {row["title"].split("（")[0] for row in merged},
            {"モビスク", "福恩麻辣湯"},
        )

    def test_same_url_is_merged_even_when_titles_differ(self):
        rows = [
            self.candidate(
                "https://media-a.example/story?utm_source=rss",
                "宇部市の新店舗",
                "宇部市",
                "宇部市に店舗がオープンする。",
            ),
            self.candidate(
                "https://media-a.example/story",
                "新店オープン",
                "宇部市",
                "本文の別取得版。",
            ),
        ]
        merged = module.merge_candidates(rows)
        self.assertEqual(len(merged), 1)


if __name__ == "__main__":
    unittest.main()

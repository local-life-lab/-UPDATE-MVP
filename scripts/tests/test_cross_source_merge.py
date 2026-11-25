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
                "「モビスク」はオープンします。",
                event_date="2026-12-18",
            ),
            self.candidate(
                "https://www.seamall.jp/info/new-shop/",
                "福恩麻辣湯（シーモール下関）2026年12月18日オープン",
                "下関市",
                "「福恩麻辣湯」はオープンします。",
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


    def test_make_draft_ids_are_unique_for_multiple_tenants_on_same_official_page(self):
        items = [
            {
                "url": "https://www.seamall.jp/info/new-shop/",
                "title": "モビスク（シーモール下関）2026年12月18日オープン",
                "source_name": "シーモール公式",
                "category": ["新店・開店"],
                "published_date": "2026-11-24",
                "event_date": "2026-12-18",
                "body_excerpt": (
                    "店名「モビスク」は2026年12月18日にオープン予定です。"
                    "施設所在地（公式アクセス情報）: 山口県下関市竹崎町4-4-8"
                ),
            },
            {
                "url": "https://www.seamall.jp/info/new-shop/",
                "title": "福恩麻辣湯（シーモール下関）2026年12月18日オープン",
                "source_name": "シーモール公式",
                "category": ["新店・開店"],
                "published_date": "2026-11-24",
                "event_date": "2026-12-18",
                "body_excerpt": (
                    "店名「福恩麻辣湯」は2026年12月18日にオープン予定です。"
                    "施設所在地（公式アクセス情報）: 山口県下関市竹崎町4-4-8"
                ),
            },
        ]
        drafts = module.assign_unique_draft_ids([module.make_draft(item) for item in items])
        self.assertEqual(len({d["id"] for d in drafts}), 2)
        self.assertEqual(
            {d["store_name"] for d in drafts},
            {"モビスク", "福恩麻辣湯"},
        )
        # The first record retains its legacy URL-based ID for approval compatibility.
        self.assertEqual(
            drafts[0]["id"],
            module.hashlib.sha256(
                module.normalize_url(items[0]["url"]).encode("utf-8")
            ).hexdigest()[:16],
        )


    def test_verified_official_primary_is_not_blocked_by_unclassified_secondary_source(self):
        result = module.source_reliability_for_sources(
            "施設公式・店舗情報",
            [
                {"source_name": "施設公式・店舗情報", "url": "https://www.seamall.jp/info/new-shop/"},
                {"source_name": "補助情報", "url": "https://unknown.example/news"},
            ],
            "https://www.seamall.jp/info/new-shop/",
        )
        self.assertEqual(result["primary_source_rank"], 3)
        self.assertFalse(result["has_unclassified"])
        self.assertFalse(result["has_secondary_only"])

    def test_secondary_official_source_does_not_upgrade_media_primary(self):
        result = module.source_reliability_for_sources(
            "号外NET 山口市・防府市",
            [
                {"source_name": "号外NET 山口市・防府市", "url": "https://yamaguchi-hofu.goguynet.jp/story"},
                {"source_name": "店舗公式", "url": "https://www.yayoiken.com/contents/news/notice.html"},
            ],
            "https://yamaguchi-hofu.goguynet.jp/story",
        )
        self.assertEqual(result["primary_source_rank"], 2)
        self.assertTrue(result["has_secondary_only"])

    def test_approved_company_domains_are_classified_as_official_primary_sources(self):
        for url in (
            "https://www.yayoiken.com/contents/news/notice.html",
            "https://www.koshidakaholdings.co.jp/ja/news/notice/",
        ):
            with self.subTest(url=url):
                result = module.classify_source_reliability("企業公式ニュース", url)
                self.assertEqual(result["rank"], 3)


if __name__ == "__main__":
    unittest.main()

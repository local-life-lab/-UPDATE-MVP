import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "auto_publish_openings.py"
spec = importlib.util.spec_from_file_location("auto_publish_openings", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AutoOpeningTests(unittest.TestCase):
    def draft(self, **changes):
        row = {
            "id": "opening-1", "category": ["新店・開店"],
            "content_type": "店舗・商業施設", "status": "未確認・公開禁止",
            "freshness": "直近30日", "store_name": "テストカフェ",
            "address": "山口県山口市中央1-1-1", "municipality": "山口市",
            "body_excerpt": "テストカフェは山口市中央に新しく開店します。店舗公式のお知らせで開店日と所在地、営業開始について案内されています。",
            "source_url": "https://shop.example.jp/news/open",
            "source_urls": [{"source_name": "店舗公式", "url": "https://shop.example.jp/news/open"}],
            "source_link_checks": [{"url": "https://shop.example.jp/news/open", "status": "ok"}],
            "published_date": "2026-11-20", "event_date": "2026-11-28",
        }
        row.update(changes)
        return row

    def config(self):
        return {"allowed_domains": ["example.jp"]}

    def test_complete_verified_new_opening_passes(self):
        self.assertEqual(module.eligible_reasons(self.draft(), self.config(), today=module.date(2026,11,24)), [])

    def test_closed_relocation_or_renewal_category_is_blocked(self):
        for category in (["閉店"], ["移転"], ["リニューアル"], ["新店・開店", "リニューアル"]):
            with self.subTest(category=category):
                self.assertTrue(module.eligible_reasons(self.draft(category=category), self.config()))

    def test_secondary_source_is_blocked(self):
        row = self.draft(source_name="地域メディア", source_urls=[
            {"source_name":"店舗公式","url":"https://shop.example.jp/news/open"},
            {"source_name":"報道","url":"https://news.example.com/story"}
        ])
        self.assertTrue(module.eligible_reasons(row, self.config()))

    def test_missing_address_or_store_name_is_blocked(self):
        for changes in ({"address": ""}, {"store_name": ""}, {"municipality": ""}):
            with self.subTest(changes=changes):
                self.assertTrue(module.eligible_reasons(self.draft(**changes), self.config()))

    def test_unverified_source_link_is_blocked(self):
        row = self.draft(source_link_checks=[{"url":"https://shop.example.jp/news/open","status":"inconclusive"}])
        self.assertTrue(module.eligible_reasons(row, self.config()))

    def test_review_flags_and_duplicates_are_blocked(self):
        for changes in ({"review_flags":["確認が必要"]}, {"duplicate_review":"重複の可能性・要確認"}, {"manual_hold":True}):
            with self.subTest(changes=changes):
                self.assertTrue(module.eligible_reasons(self.draft(**changes), self.config()))

    def test_empty_allowlist_blocks_all(self):
        self.assertTrue(module.eligible_reasons(self.draft(), {"allowed_domains": []}))

    def test_http_source_is_blocked(self):
        row = self.draft(source_url="http://shop.example.jp/news/open")
        self.assertTrue(module.eligible_reasons(row, self.config()))

if __name__ == "__main__":
    unittest.main()

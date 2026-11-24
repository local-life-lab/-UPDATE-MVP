import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "generate_drafts.py"
spec = importlib.util.spec_from_file_location("generate_drafts_identity", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OpeningIdentityExtractionTests(unittest.TestCase):
    def test_single_store_and_explicit_address_are_extracted(self):
        result = module.extract_explicit_store_identity(
            "山口市に「青空カフェ」が11月28日オープン",
            "青空カフェは山口県山口市中央1-2-3に11月28日オープンします。",
        )
        self.assertEqual(result["store_name"], "青空カフェ")
        self.assertEqual(result["store_name_extraction_status"], "単一候補")
        self.assertEqual(result["address"], "山口県山口市中央1-2-3")
        self.assertEqual(result["municipality"], "山口市")
        self.assertEqual(result["opening_status_evidence"], "予定表現あり")

    def test_multiple_store_names_are_not_selected(self):
        result = module.extract_explicit_store_identity(
            "「青空カフェ」と「緑屋」が同時オープン",
            "青空カフェと緑屋が山口県山口市中央1-2-3にオープンします。",
        )
        self.assertEqual(result["store_name"], "")
        self.assertNotEqual(result["store_name_extraction_status"], "単一候補")

    def test_city_name_without_street_address_is_not_address(self):
        result = module.extract_explicit_store_identity(
            "山口市に新店オープン",
            "新しいカフェが山口県山口市にオープンします。",
        )
        self.assertEqual(result["address"], "")
        self.assertEqual(result["address_extraction_status"], "候補なし")

    def test_ambiguous_addresses_are_not_selected(self):
        result = module.extract_explicit_store_identity(
            "新店オープン",
            "店舗Aは山口県山口市中央1-2-3、店舗Bは山口県宇部市南4-5-6です。",
        )
        self.assertEqual(result["address"], "")
        self.assertEqual(result["address_extraction_status"], "複数候補・要確認")


    def test_official_shop_listing_extracts_quoted_name_address_and_planned_status(self):
        body = (
            "店名「モビスク」は2026年12月18日にオープン予定です。"
            "施設所在地（公式アクセス情報）: 山口県下関市竹崎町4-4-8"
        )
        result = module.extract_explicit_store_identity(
            "モビスク（シーモール下関）2026年12月18日オープン",
            body,
        )
        self.assertEqual(result["store_name"], "モビスク")
        self.assertEqual(result["store_name_extraction_status"], "単一候補")
        self.assertEqual(result["address"], "山口県下関市竹崎町4-4-8")
        self.assertEqual(result["municipality"], "下関市")
        self.assertEqual(result["opening_status_evidence"], "予定表現あり")

    def test_freshness_uses_publication_date_not_future_opening_date(self):
        today = module.now_jst().date()
        item = {
            "title": "「青空カフェ」が12月1日オープン予定",
            "url": "https://example.com/blue-cafe",
            "source_name": "店舗公式",
            "category": ["新店・開店"],
            "published_date": today.isoformat(),
            "event_date": (today + module.timedelta(days=7)).isoformat(),
            "body_excerpt": (
                "青空カフェは山口県山口市中央1-2-3に"
                "12月1日オープン予定です。"
            ),
        }
        draft = module.make_draft(item)
        self.assertEqual(draft["freshness"], "直近30日")
        self.assertEqual(draft["event_date"], item["event_date"])

    def test_generic_opening_word_without_status_is_held(self):
        result = module.extract_explicit_store_identity(
            "新店オープン情報",
            "山口県山口市中央1-2-3に店舗がオープンするとの情報があります。",
        )
        self.assertEqual(result["opening_status_evidence"], "動作語のみ・状態不明")


if __name__ == "__main__":
    unittest.main()

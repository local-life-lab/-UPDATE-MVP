import unittest

from scripts.check_source_links import collect_sources, collect_urls


class CollectSourcesTests(unittest.TestCase):
    def test_collects_primary_and_all_additional_sources(self):
        drafts = [{
            "title": "候補A",
            "source_name": "公式発表",
            "source_url": "https://example.com/main",
            "source_urls": [
                {"source_name": "公式発表", "url": "https://example.com/main"},
                {"source_name": "公式店舗情報", "url": "https://example.com/store"},
                {"source_name": "公式SNS", "url": "https://example.com/social"},
            ],
        }]

        sources = collect_sources(drafts)

        self.assertEqual(
            [item["url"] for item in sources],
            [
                "https://example.com/main",
                "https://example.com/store",
                "https://example.com/social",
            ],
        )
        self.assertEqual(sources[1]["source_name"], "公式店舗情報")
        self.assertEqual(sources[2]["title"], "候補A")

    def test_deduplicates_urls_across_candidates(self):
        drafts = [
            {
                "title": "候補A",
                "source_url": "https://example.com/shared",
                "source_name": "媒体A",
            },
            {
                "title": "候補B",
                "source_urls": [
                    {"source_name": "媒体B", "url": "https://example.com/shared"},
                    {"source_name": "媒体B", "url": "https://example.com/other"},
                ],
            },
        ]

        self.assertEqual(
            collect_urls(drafts),
            ["https://example.com/shared", "https://example.com/other"],
        )


    def test_all_primary_sources_are_checked_before_secondary_sources(self):
        import scripts.check_source_links as checker

        original_limit = checker.MAX_URLS
        checker.MAX_URLS = 2
        try:
            drafts = [
                {
                    "title": "候補A",
                    "source_url": "https://official.example/a",
                    "source_urls": [
                        {"source_name": "まとめ", "url": "https://media.example/a"},
                    ],
                },
                {
                    "title": "候補B",
                    "source_url": "https://official.example/b",
                    "source_urls": [
                        {"source_name": "まとめ", "url": "https://media.example/b"},
                    ],
                },
            ]
            self.assertEqual(
                collect_urls(drafts),
                ["https://official.example/a", "https://official.example/b"],
            )
        finally:
            checker.MAX_URLS = original_limit

    def test_ignores_invalid_urls_and_non_dictionary_sources(self):
        drafts = [{
            "source_url": "javascript:alert(1)",
            "source_urls": [
                "https://example.com/not-an-object",
                {"source_name": "invalid", "url": "ftp://example.com/file"},
                {"source_name": "valid", "url": "https://example.com/valid"},
            ],
        }]

        self.assertEqual(
            collect_urls(drafts),
            ["https://example.com/valid"],
        )


if __name__ == "__main__":
    unittest.main()

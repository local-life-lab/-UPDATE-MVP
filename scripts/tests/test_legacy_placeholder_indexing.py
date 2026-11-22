import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEGACY_PAGES = (
    'jobs.html',
    'store-drug-cosmos-yamaguchi-ogori.html',
    'store-trial-yamaguchi-ogori.html',
)

class LegacyPlaceholderIndexingTests(unittest.TestCase):
    def test_legacy_and_unverified_pages_are_noindex(self):
        for relative_path in LEGACY_PAGES:
            with self.subTest(path=relative_path):
                page = (ROOT / relative_path).read_text(encoding='utf-8')
                self.assertIn('<meta name="robots" content="noindex,follow">', page)

    def test_legacy_pages_are_not_in_sitemap(self):
        sitemap = (ROOT / 'sitemap.xml').read_text(encoding='utf-8')
        for relative_path in LEGACY_PAGES:
            self.assertNotIn('/' + relative_path, sitemap)

if __name__ == '__main__':
    unittest.main()

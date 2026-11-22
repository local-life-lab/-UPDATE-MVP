import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGE = (ROOT / "admin" / "review.html").read_text(encoding="utf-8")


class TestMobileReviewNavigation(unittest.TestCase):
    def test_selecting_candidate_scrolls_to_detail_on_mobile(self):
        expected = (
            'if(window.matchMedia&&window.matchMedia("(max-width:760px)").matches)'
            '{el("detail").scrollIntoView({behavior:"smooth",block:"start"});}'
        )
        self.assertIn(expected, PAGE)

    def test_desktop_layout_is_not_forced_to_scroll(self):
        self.assertIn('window.matchMedia("(max-width:760px)")', PAGE)
        self.assertIn('el("detail").scrollIntoView', PAGE)


if __name__ == "__main__":
    unittest.main()

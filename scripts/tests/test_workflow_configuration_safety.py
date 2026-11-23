import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / '.github' / 'workflows'

class WorkflowConfigurationSafetyTests(unittest.TestCase):
    def test_manual_refresh_targets_current_repository(self):
        workflow = (WORKFLOWS / 'test-date-quality.yml').read_text(encoding='utf-8')
        self.assertIn('GITHUB_REPOSITORY" != "local-life-lab/-UPDATE-MVP"', workflow)
        self.assertNotIn('kouki-bot/-UPDATE-MVP', workflow)
        self.assertIn('未確認・公開禁止', workflow)
        self.assertNotIn('python scripts/publish_approved.py', workflow)

    def test_legacy_indexing_tests_run_after_merge_to_main(self):
        workflow = (WORKFLOWS / 'test-public-display-safety.yml').read_text(encoding='utf-8')
        push_section = workflow.split('  push:', 1)[1].split('  workflow_dispatch:', 1)[0]
        for path in (
            'scripts/tests/test_legacy_placeholder_indexing.py',
            'jobs.html',
            'store-drug-cosmos-yamaguchi-ogori.html',
            'store-trial-yamaguchi-ogori.html',
        ):
            with self.subTest(path=path):
                self.assertIn(path, push_section)

    def test_candidate_link_checks_run_after_draft_generation_before_private_sync(self):
        workflow = (WORKFLOWS / 'update.yml').read_text(encoding='utf-8')
        steps = [
            'run: python scripts/generate_drafts.py',
            'run: python scripts/check_source_links.py',
            'run: python scripts/source_quality_report.py',
            'run: python scripts/private_review_sync.py upload',
        ]
        positions = [workflow.find(step) for step in steps]
        self.assertTrue(all(position >= 0 for position in positions))
        self.assertEqual(positions, sorted(positions))

    def test_auto_opening_publish_runs_after_private_approval_download_and_before_seo(self):
        workflow = (WORKFLOWS / 'publish-approved.yml').read_text(encoding='utf-8')
        steps = [
            'run: python scripts/private_review_sync.py download',
            'run: python scripts/publish_approved.py',
            'run: python scripts/auto_publish_openings.py',
            'run: python scripts/build_seo_pages.py',
        ]
        positions = [workflow.find(step) for step in steps]
        self.assertTrue(all(position >= 0 for position in positions))
        self.assertEqual(positions, sorted(positions))
        self.assertIn('allowed_domains', (ROOT / 'data' / 'auto_opening_sources.json').read_text(encoding='utf-8'))

if __name__ == '__main__':
    unittest.main()

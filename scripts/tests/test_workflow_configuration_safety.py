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

if __name__ == '__main__':
    unittest.main()

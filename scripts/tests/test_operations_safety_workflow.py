import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / '.github' / 'workflows' / 'notify-failures.yml').read_text(encoding='utf-8')
README = (ROOT / 'README.md').read_text(encoding='utf-8')

class OperationsSafetyWorkflowTests(unittest.TestCase):
    def test_only_automation_workflows_on_main_are_watched(self):
        self.assertIn('workflow_run:', WORKFLOW)
        self.assertIn('- Yamaguchi Local Update', WORKFLOW)
        self.assertIn('- Publish Manually Approved Articles', WORKFLOW)
        self.assertIn('branches:', WORKFLOW)
        self.assertIn('- main', WORKFLOW)

    def test_failure_and_timeout_create_notifications(self):
        self.assertIn("conclusion == 'failure'", WORKFLOW)
        self.assertIn("conclusion == 'timed_out'", WORKFLOW)
        self.assertIn('issues: write', WORKFLOW)
        self.assertIn('github.rest.issues.create', WORKFLOW)

    def test_open_notification_is_reused_instead_of_creating_duplicates(self):
        self.assertIn("state: 'open'", WORKFLOW)
        self.assertIn('issues.find(issue =>', WORKFLOW)
        self.assertIn('github.rest.issues.createComment', WORKFLOW)

    def test_notification_contains_run_link_but_not_logs_or_secrets(self):
        self.assertIn('run.html_url', WORKFLOW)
        self.assertIn('秘密情報やログ本文を転記しないでください', WORKFLOW)

    def test_readme_explains_private_approval_backup_and_notifications(self):
        self.assertIn('publication_approvals.json', README)
        self.assertIn('localStorage', README)
        self.assertIn('Watch → Custom → Issues', README)
        self.assertIn('候補・公開済みデータのどちらにも存在しないIDは警告', README)

if __name__ == '__main__':
    unittest.main()

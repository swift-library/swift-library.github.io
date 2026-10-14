"""Keep required validation independent of title edits and publication."""

from pathlib import Path
import importlib.util
from importlib.machinery import SourceFileLoader
import re
import unittest

WORKFLOWS = Path(__file__).resolve().parents[1] / '.github/workflows'
loader = SourceFileLoader('workflow_checks', str(WORKFLOWS.parents[1] / 'Scripts/check-workflows'))
spec = importlib.util.spec_from_loader(loader.name, loader)
checks = importlib.util.module_from_spec(spec)
loader.exec_module(checks)


class WorkflowTests(unittest.TestCase):
    def test_validation_keeps_the_result_context_and_no_title_edits(self):
        text = (WORKFLOWS / 'pages.yml').read_text()
        events = re.search(r'types: \[([^\]]+)\]', text)[1]
        self.assertEqual(set(events.split(', ')), {'opened', 'synchronize', 'reopened'})
        self.assertIn('  result:\n    needs: build\n    if: always()', text)
        self.assertIn('test "$BUILD" = success', text)
        self.assertNotIn('  policy:', text)
        self.assertNotIn('  deploy:', text)
        self.assertIn('cancel-in-progress: true', text)
        self.assertNotIn('  schedule:', text)

    def test_policy_caller_keeps_title_edits_and_the_policy_job(self):
        text = (WORKFLOWS / 'source-policy.yml').read_text()
        self.assertIn('types: [opened, synchronize, reopened, edited]', text)
        self.assertIn('  policy:', text)
        self.assertIn('cancel-in-progress: true', text)

    def test_publication_uses_only_the_completed_master_validation_artifact(self):
        text = (WORKFLOWS / 'publish.yml').read_text()
        self.assertIn('workflow_run:', text)
        self.assertIn('workflows: [Pages]', text)
        self.assertIn('branches: [master]', text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", text)
        self.assertIn("github.event.workflow_run.event != 'pull_request'", text)
        self.assertIn('github.event.workflow_run.head_repository.full_name == github.repository', text)
        self.assertIn('github.event.workflow_run.head_sha == github.sha', text)
        self.assertIn('run-id: ${{ github.event.workflow_run.id }}', text)
        self.assertIn('path: .build/pages-publication/artifact.tar', text)
        self.assertIn('cancel-in-progress: false', text)
        self.assertIn('queue: max', text)
        self.assertNotIn('cancel-in-progress: true', text)

    def test_weekly_refresh_dispatches_validation_on_master(self):
        text = (WORKFLOWS / 'refresh.yml').read_text()
        self.assertIn('  schedule:', text)
        self.assertIn('gh workflow run pages.yml --repo "$REPOSITORY" --ref master', text)
        self.assertNotIn('pages: write', text)
        self.assertNotIn('cancel-in-progress: true', text)

    def test_linter_input_keeps_every_supported_field(self):
        source = (WORKFLOWS / 'publish.yml').read_text()
        self.assertEqual(checks.publication_lint_input(source), source.replace('  queue: max\n', '', 1))

    def test_publication_queue_cannot_cancel_pending_or_running_work(self):
        source = (WORKFLOWS / 'publish.yml').read_text()
        for candidate in (source.replace('queue: max', 'queue: single'),
                          source.replace('cancel-in-progress: false', 'cancel-in-progress: true'),
                          source.replace('  queue: max\n', ''),
                          source.replace('  queue: max\n', '  queue: max\n  queue: max\n')):
            with self.subTest(source=candidate):
                with self.assertRaises(ValueError):
                    checks.publication_lint_input(candidate)


if __name__ == '__main__':
    unittest.main()

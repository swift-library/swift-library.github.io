# SPDX-License-Identifier: Apache-2.0 WITH Swift-exception
from contextlib import redirect_stdout, redirect_stderr
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "Scripts"))
loader = importlib.machinery.SourceFileLoader("check_site", str(ROOT / "Scripts/check-site"))
spec = importlib.util.spec_from_loader(loader.name, loader)
check_site = importlib.util.module_from_spec(spec)
loader.exec_module(check_site)


class LocalCheckTests(unittest.TestCase):
    def setUp(self):
        staging = ROOT / ".build/test-fixtures"
        staging.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=staging)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "_site"
        (self.output / "contributing").mkdir(parents=True)
        self.config = {"organization": "example", "site_url": "https://example.org/", "groups": [
            {"name": "Packages", "projects": [
                {"repository": name, "documentation": {"kind": "readme"}}
                for name in (".github", "example", "future")]}]}
        self.manifest = {"projects": [{"repository": name, "description": "Description", "release": None,
                                      "documentation": None} for name in (".github", "example")], "skipped": ["future"]}
        (self.output / "build-manifest.json").write_text(json.dumps(self.manifest))
        (self.output / "index.html").write_text('<article data-repository=".github"></article><article data-repository="example"></article>')
        (self.output / "404.html").write_text("Not found")
        (self.output / "contributing/index.html").write_text(
            '<h2 id="contributing-code">Code</h2><a href="https://github.com/example/.github/blob/master/VERSIONING.md">Policy</a>')
        (self.output / "CONTRIBUTORS.txt").write_text("Example Author\n")
        for directory in (self.root, self.output):
            (directory / "LICENSE.txt").write_text("Apache License\nVersion 2.0\n")

    def check(self, local=True, api=None):
        with patch.object(check_site, "ROOT", self.root), \
                patch.object(check_site, "configuration", return_value=self.config), \
                patch.object(check_site, "GitHub", api or Mock(side_effect=AssertionError("Unexpected network access"))), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            check_site.check(SimpleNamespace(output=self.output, local=local))

    def test_local_validation_does_not_query_github(self):
        self.check()

    def test_local_validation_still_checks_catalog_and_license(self):
        self.manifest["skipped"] = []
        (self.output / "build-manifest.json").write_text(json.dumps(self.manifest))
        with self.assertRaises(check_site.SiteError):
            self.check()
        self.manifest["skipped"] = ["future"]
        (self.output / "build-manifest.json").write_text(json.dumps(self.manifest))
        (self.output / "LICENSE.txt").write_text("Different license")
        with self.assertRaises(check_site.SiteError):
            self.check()

    def test_live_mode_keeps_remote_license_requirement(self):
        api = Mock()
        api.public_repositories.return_value = {
            ".github": {"default_branch": "master", "description": "Description", "license": {"spdx_id": "Apache-2.0"}},
            "example": {"description": "Description", "license": None}}
        api.text_file.return_value = ""
        with self.assertRaises(check_site.SiteError):
            self.check(local=False, api=Mock(return_value=api))
        api.public_repositories.assert_called_once_with("example")


if __name__ == "__main__":
    unittest.main()

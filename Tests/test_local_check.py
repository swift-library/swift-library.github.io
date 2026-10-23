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
sys.path.insert(0, str(ROOT / "scripts"))
loader = importlib.machinery.SourceFileLoader("check_site", str(ROOT / "scripts/check-site"))
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
        navigation = {name: {"label": name.title(), "url": f"https://example.org/{name}/"}
                      for name in ("documentation", "contributing", "security", "support")}
        navigation["documentation"]["url"] = "https://example.org/"
        promise = {"promise": "Packages for apps.", "description": "Packages for apps.",
                   "secondary": "Choose the APIs your app needs."}
        self.config = {"organization": "example", "site_url": "https://example.org/", "groups": [
            {"name": "Packages", "projects": [
                {"repository": name, "documentation": {"kind": "readme"}}
                for name in ("example", "future")]}]}
        self.profile = {"organization": {"login": "example"}, **promise, "navigation": navigation,
                        "groups": [{"title": "Packages", "repositories": [{"name": "example"}, {"name": "future"}]}]}
        self.manifest = {"projects": [{"repository": name, "description": "Description", "release": None,
                                      "documentation": None} for name in ("example",)], "skipped": ["future"],
                         "presentation": {**promise, "navigation": navigation}}
        (self.output / "build-manifest.json").write_text(json.dumps(self.manifest))
        (self.output / "index.html").write_text(
            '<article data-repository="example"></article>' +
            ''.join(f'<a href="{link["url"]}">{link["label"]}</a>' for link in navigation.values()))
        for name in ("security", "support"):
            (self.output / name).mkdir()
            (self.output / name / "index.html").write_text(name)
        (self.output / "404.html").write_text("Not found")
        (self.output / "contributing/index.html").write_text(
            '<h2 id="contributing-code">Code</h2><a href="https://github.com/example/.github/blob/master/VERSIONING.md">Policy</a>')
        (self.output / "CONTRIBUTORS.txt").write_text("Example Author\n")
        for directory in (self.root, self.output):
            (directory / "LICENSE.txt").write_text("Apache License\nVersion 2.0\n")

    def check(self, local=True, api=None, profile_file=None):
        with patch.object(check_site, "ROOT", self.root), \
                patch.object(check_site, "configuration", return_value=self.config), \
                patch.object(check_site, "GitHub", api or Mock(side_effect=AssertionError("Unexpected network access"))), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            check_site.check(SimpleNamespace(output=self.output, local=local, profile_file=profile_file))

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
        api.text_file.return_value = json.dumps(self.profile)
        with self.assertRaises(check_site.SiteError):
            self.check(local=False, api=Mock(return_value=api))
        api.public_repositories.assert_called_once_with("example")
        api.public_repositories.return_value["example"]["license"] = {"spdx_id": "Apache-2.0"}
        self.check(local=False, api=Mock(return_value=api))

    def test_live_membership_includes_the_website(self):
        api = Mock()
        api.public_repositories.return_value = {
            ".github": {"default_branch": "master", "license": {"spdx_id": "Apache-2.0"}},
            "example": {"description": "Description", "license": {"spdx_id": "Apache-2.0"}},
            "example.github.io": {"description": "Website", "license": {"spdx_id": "Apache-2.0"}}}
        api.text_file.return_value = json.dumps(self.profile)
        with self.assertRaises(check_site.SiteError):
            self.check(local=False, api=Mock(return_value=api))

    def test_local_profile_preview_checks_presentation_without_network(self):
        profile = self.root / "catalog.json"
        profile.write_text(json.dumps(self.profile))
        self.check(profile_file=profile)
        self.profile["navigation"]["support"]["label"] = "Help"
        profile.write_text(json.dumps(self.profile))
        with self.assertRaises(check_site.SiteError):
            self.check(profile_file=profile)

    def test_missing_published_navigation_link_fails(self):
        homepage = self.output / "index.html"
        homepage.write_text(homepage.read_text().replace('href="https://example.org/support/"', 'href="/"'))
        with self.assertRaises(check_site.SiteError):
            self.check()


if __name__ == "__main__":
    unittest.main()

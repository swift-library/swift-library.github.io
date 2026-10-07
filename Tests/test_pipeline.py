# SPDX-License-Identifier: Apache-2.0 WITH Swift-exception
"""Exercise publication boundaries and failures in the site checks."""

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent / "Scripts"
sys.path.insert(0, str(SCRIPTS))
from site_checks import Links
from site_docc import normalize_extension_hierarchy
from site_support import contributor_names, latest_release

loader = importlib.machinery.SourceFileLoader("build_site", str(SCRIPTS / "build-site"))
spec = importlib.util.spec_from_loader(loader.name, loader)
build_site = importlib.util.module_from_spec(spec)
loader.exec_module(build_site)


class LinkTests(unittest.TestCase):
    def setUp(self):
        fixtures = SCRIPTS.parent / ".build/test-fixtures"
        fixtures.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=fixtures)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_relative_directory_query_and_same_origin_links(self):
        self.write("index.html", '<a href="/guide/?q=a#topic">Guide</a><a href="https://example.org/guide/#topic">Guide</a>')
        self.write("guide/index.html", '<h1 id="topic">Guide</h1><a href="../">Home</a>')
        links = Links(self.root, "https://example.org/")
        self.assertEqual(links.scan(), [])
        self.assertEqual(links.count, 3)

    def test_missing_files_anchors_and_escaping_paths_fail(self):
        self.write("index.html", '<a href="missing/">Missing</a><a href="#missing">Anchor</a><img src="../outside.svg">')
        errors = Links(self.root, "https://example.org/").scan()
        self.assertEqual(len(errors), 3)

    def test_docc_routes_assets_and_client_anchors(self):
        self.write("index.html", '<a href="/package/documentation/module/#usage">Docs</a>')
        self.write("package/documentation/module/index.html", '<script src="/package/js/app.js"></script>')
        self.write("package/js/app.js", "")
        self.write("package/images/logo.svg", "<svg></svg>")
        self.write("package/data/documentation/module.json", json.dumps({
            "sections": [{"anchor": "usage"}],
            "references": {"self": {"url": "/documentation/module#usage"},
                           "image": {"variants": [{"url": "/images/logo.svg"}]}},
        }))
        self.assertEqual(Links(self.root, "https://example.org/").scan(), [])

    def test_broken_docc_json_and_css_assets_fail(self):
        self.write("index.html", "")
        self.write("style.css", 'body { background: url("missing.svg"); }')
        self.write("package/data/documentation/module.json", json.dumps({
            "references": {"missing": {"url": "/documentation/missing"}}
        }))
        self.assertEqual(len(Links(self.root, "https://example.org/").scan()), 2)

    def test_merged_documentation_landing_and_dotted_symbols(self):
        self.write("index.html", '<a href="/package/documentation/">Docs</a>')
        self.write("package/documentation/index.html", "")
        self.write("package/documentation/module/member.name/index.html", "")
        self.write("package/data/documentation.json", json.dumps({
            "references": {"self": {"url": "/documentation"},
                           "symbol": {"url": "/documentation/module/member.name#usage"}}
        }))
        self.write("package/data/documentation/module/member.name.json", json.dumps({"sections": [{"anchor": "usage"}]}))
        self.assertEqual(Links(self.root, "https://example.org/").scan(), [])

    def test_tutorial_chapter_labels_do_not_require_standalone_pages(self):
        self.write("package/tutorials/example/step/index.html", "")
        document = {
            "hierarchy": {"modules": [{"reference": "chapter", "projects": [{"reference": "step"}]}]},
            "references": {"chapter": {"url": "/tutorials/example/chapter"},
                           "step": {"url": "/tutorials/example/step"}},
        }
        path = self.write("package/data/tutorials/example/step.json", json.dumps(document))
        self.assertEqual(Links(self.root, "https://example.org/").scan(), [])
        document["abstract"] = [{"type": "reference", "identifier": "chapter"}]
        path.write_text(json.dumps(document))
        self.assertEqual(len(Links(self.root, "https://example.org/").scan()), 1)

    def extension_document(self):
        return {
            "hierarchy": {"paths": [["module", "module/External", "module/External/Value", "member"]]},
            "references": {
                "module": {"url": "/documentation/module", "role": "collection"},
                "module/External": {"url": "/documentation/module/external", "role": "collection"},
                "module/External/Value": {"url": "/documentation/module/external/value", "role": "symbol",
                                           "fragments": [{"kind": "keyword", "text": "extension"}]},
                "member": {"url": "/documentation/module/member", "role": "symbol"},
            },
        }

    def test_missing_external_containers_are_removed_from_breadcrumbs(self):
        document = self.extension_document()
        path = self.write("package/data/documentation/module/member.json", json.dumps(document))
        self.write("package/documentation/module/index.html", "")
        self.write("package/documentation/module/member/index.html", "")
        self.assertEqual(normalize_extension_hierarchy(self.root / "package"), 1)
        actual = json.loads(path.read_text())
        self.assertEqual(actual["hierarchy"]["paths"], [["module", "member"]])
        self.assertEqual(set(actual["references"]), {"module", "member"})
        self.assertEqual(Links(self.root, "https://example.org/").scan(), [])

    def test_rendered_extension_containers_are_preserved(self):
        document = self.extension_document()
        path = self.write("package/data/documentation/module/member.json", json.dumps(document))
        self.write("package/data/documentation/module/external/value.json", "{}")
        self.assertEqual(normalize_extension_hierarchy(self.root / "package"), 0)
        self.assertEqual(json.loads(path.read_text()), document)

    def test_missing_authored_links_and_regular_ancestors_still_fail(self):
        document = self.extension_document()
        document["abstract"] = [{"type": "reference", "identifier": "module/External/Value"}]
        path = self.write("package/data/documentation/module/member.json", json.dumps(document))
        self.write("package/documentation/module/member/index.html", "")
        normalize_extension_hierarchy(self.root / "package")
        actual = json.loads(path.read_text())
        self.assertIn("module/External/Value", actual["references"])
        errors = Links(self.root, "https://example.org/").scan()
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("/documentation/module/external/value" in error for error in errors))
        self.assertTrue(any(error.endswith("missing target /documentation/module") for error in errors))


class InputTests(unittest.TestCase):
    def test_documentation_traits_follow_tagged_manifest_and_keep_explicit_defaults(self):
        manifest = {"traits": [{"name": "Experimental"}]}
        self.assertEqual(build_site.documentation_traits(manifest, None), [])
        self.assertEqual(build_site.documentation_traits(manifest, ["Experimental", "default"]),
                         ["--traits", "Experimental,default"])

    def test_invalid_trait_selection_fails_before_compilation(self):
        manifest = {"traits": [{"name": "Experimental"}]}
        for selection in [[], "Experimental", [True], ["Missing"],
                          ["Experimental", "Experimental"], ["--disable-sandbox"]]:
            with self.subTest(selection=selection):
                with self.assertRaises(build_site.SiteError):
                    build_site.documentation_traits(manifest, selection)

    def test_first_published_prerelease_enables_documentation(self):
        class API:
            def pages(self, endpoint):
                return [{"tag_name": "v0.2.0", "draft": True, "prerelease": False},
                        {"tag_name": "v0.1.0-beta.1", "draft": False, "prerelease": True}]
        self.assertEqual(latest_release(API(), "example", "repo")["tag_name"], "v0.1.0-beta.1")

    def test_repository_without_public_releases_skips_documentation(self):
        class API:
            def pages(self, endpoint):
                return [{"tag_name": "v0.1.0", "draft": True}]
        self.assertIsNone(latest_release(API(), "example", "repo"))

    def test_contributors_come_from_history_and_exclude_bots_and_emails(self):
        class API:
            def pages(self, endpoint):
                return [
                    {"author": {"type": "User"}, "commit": {"author": {"name": "A Person", "email": "a@example.org"}}},
                    {"author": {"type": "Bot"}, "commit": {"author": {"name": "Automation", "email": ""}}},
                    {"author": None, "commit": {"author": {"name": "robot[bot]", "email": ""}}},
                    {"author": None, "commit": {"author": {"name": "a@example.org", "email": ""}}},
                ]
        self.assertEqual(contributor_names(API(), "example", {"repo": {"size": 1, "default_branch": "master"}}), ["A Person"])

    def test_documentation_targets_follow_the_tagged_public_products(self):
        manifest = {"products": [
            {"type": {"library": ["automatic"]}, "targets": ["One", "Two"]},
            {"type": {"library": ["dynamic"]}, "targets": ["One"]},
            {"type": {"executable": None}, "targets": ["CLI"]},
        ]}
        self.assertEqual(build_site.library_targets(manifest, "library-products"), ["One", "Two"])
        with self.assertRaises(build_site.SiteError):
            build_site.library_targets(manifest, ["CLI"])


if __name__ == "__main__":
    unittest.main()

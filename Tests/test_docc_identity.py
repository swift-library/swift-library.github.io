# SPDX-License-Identifier: Apache-2.0 WITH Swift-exception
"""Cover source isolation, preserved DocC metadata, and published identity checks."""

import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent / "Scripts"
sys.path.insert(0, str(SCRIPTS))
from site_docc import add_identity, archive_source, design_colors, identity_records, merged_identity
from site_support import SiteError


class DocCTests(unittest.TestCase):
    def setUp(self):
        fixtures = SCRIPTS.parent / ".build/test-fixtures"
        fixtures.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=fixtures)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_hue_mapping_is_derived_from_design_and_wraps(self):
        design = '```json\n{"icons":{"one":{"hue":350},"two":{"hue":35}}}\n```\n| 330 to 35 | `red` |\n| 35 to 330 | `blue` |\n'
        self.assertEqual(design_colors(design), {"one": "red", "two": "blue"})
        with self.assertRaises(SiteError):
            design_colors(design.replace('| 35 to 330 | `blue` |', ''))

    def test_existing_identity_is_preserved_byte_for_byte(self):
        page = self.root / "Module.md"
        content = '# ``Module``\n\n@Metadata {\n @PageColor(purple)\n @PageImage(purpose: icon, source: "original.png")\n}\n'
        page.write_text(content)
        add_identity(self.root, "Module", "blue", b"new")
        self.assertEqual(page.read_text(), content)
        self.assertFalse((self.root / "Resources").exists())

    def test_partial_metadata_and_fenced_examples(self):
        for fence in ['```', '~~~~']:
            with self.subTest(fence=fence):
                page = self.root / "Module.md"
                example = f'{fence}swift\n@Metadata {{\n @PageImage(purpose: icon, source: "example.png")\n}}\n{fence}\n'
                page.write_text('# ``Module``\n\n' + example + '\n@Metadata {\n @PageColor(green)\n}\n')
                add_identity(self.root, "Module", "blue", b"new")
                output = page.read_text()
                self.assertIn(example, output)
                self.assertIn('@Metadata {\n  @PageImage(purpose: icon, source: "module-site-icon.png"', output)
                self.assertEqual(output.count('@PageColor'), 1)
                self.assertIn('@PageColor(green)', output)

    def test_missing_landings_get_distinct_module_resources(self):
        for module in ['One', 'Two']:
            path = add_identity(self.root / module, module, "blue", b"new")
            self.assertIn(f'{module.lower()}-site-icon.png', path.read_text())
        self.assertNotEqual((self.root / 'One/Resources/one-site-icon.png').name,
                            (self.root / 'Two/Resources/two-site-icon.png').name)

    def test_collision_and_duplicate_landings_fail(self):
        (self.root / 'Resources').mkdir()
        (self.root / 'Resources/module-site-icon.png').write_bytes(b'owned')
        with self.assertRaises(SiteError):
            add_identity(self.root, 'Module', 'blue', b'new')
        (self.root / 'Other.md').write_text('# ``Module``\n')
        with self.assertRaises(SiteError):
            add_identity(self.root, 'Module', 'blue', b'new')

    def test_merged_landing_has_verified_asset_and_tamper_changes_receipt(self):
        (self.root / 'data').mkdir()
        (self.root / 'data/documentation.json').write_text('{}')
        merged_identity(self.root, 'repo', 'blue', b'icon')
        records = identity_records(self.root, [], True, 'repo')
        self.assertEqual(records[0]['color'], 'blue')
        self.assertEqual(records[0]['icons'][0]['sha256'], hashlib.sha256(b'icon').hexdigest())
        (self.root / 'images/site/repo-site-icon.png').write_bytes(b'changed')
        self.assertNotEqual(identity_records(self.root, [], True, 'repo'), records)
        (self.root / 'images/site/repo-site-icon.png').unlink()
        with self.assertRaises(SiteError):
            identity_records(self.root, [], True, 'repo')

    def archive(self, name, data=b'// manifest'):
        result = io.BytesIO()
        with tarfile.open(fileobj=result, mode='w:gz') as bundle:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            bundle.addfile(info, io.BytesIO(data))
        return result.getvalue()

    def test_source_archive_has_no_git_and_is_removed_after_build(self):
        with patch('site_docc.urlopen', return_value=io.BytesIO(self.archive('repo-sha/Package.swift'))):
            with archive_source('org', 'repo', 'a' * 40, self.root) as source:
                self.assertEqual((source / 'Package.swift').read_bytes(), b'// manifest')
                self.assertFalse((source / '.git').exists())
            self.assertFalse(source.exists())
            self.assertFalse((self.root / 'source-archives/repo/source.tar.gz').exists())

    def test_archive_rejects_git_metadata_and_escaping_members(self):
        for member in ['repo-sha/.git/config', '../../escape']:
            with self.subTest(member=member):
                with patch('site_docc.urlopen', return_value=io.BytesIO(self.archive(member))):
                    with self.assertRaises((SiteError, tarfile.FilterError)):
                        with archive_source('org', 'repo', 'a' * 40, self.root):
                            self.fail('Invalid archive was accepted')
                self.assertFalse((self.root / 'source-archives/repo/source').exists())


if __name__ == '__main__':
    unittest.main()

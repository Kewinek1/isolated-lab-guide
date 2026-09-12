"""Static Pages artifact tests: scope, manifest and repository-relative entrypoints."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import build_pages
import release
import render_diagrams

class PagesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "source"
        self.root.mkdir()
        self.output = self.base / "website"
        for name, text in {
            "app/index.html": '<head><link href="/app/style.css"><script src="/app/app.js"></script></head>',
            "app/app.js": "export const example = true;",
            "app/style.css": "body { color: black; }",
            "tools/mermaid.config.json": "{}",
            "app/diagram-index.json": json.dumps({
                "renderer": "@mermaid-js/mermaid-cli@" + render_diagrams.VERSION,
                "configuration_sha256": hashlib.sha256(b"{}").hexdigest(),
                "diagrams": {},
            }),
            "docs/guide.md": "Public guide",
            ".github/workflows/pages.yml": "name: Public build",
            ".gitignore": "private/",
        }.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        self.save_manifest()

    def save_manifest(self):
        (self.root / release.MANIFEST).write_text(json.dumps({
            "classification": "PUBLIC — FICTIONAL EXAMPLES", "files": release.files(self.root)
        }))

    def test_public_artifact_has_relative_assets_and_no_repository_or_private_metadata(self):
        (self.base / "private").mkdir()
        (self.base / "private" / "profile.json").write_text('{"private":"synthetic"}')
        build_pages.build(self.output, self.root)
        page = (self.output / "index.html").read_text()
        self.assertIn('href="./app/style.css"', page)
        self.assertIn('src="./app/app.js"', page)
        self.assertIn('content="public-static"', page)
        self.assertNotIn('="/app/', page)
        nested = (self.output / "app/index.html").read_text()
        self.assertIn('src="./app.js"', nested)
        self.assertTrue((self.output / "docs/guide.md").is_file())
        self.assertTrue((self.output / ".nojekyll").is_file())
        for name in (".github", ".gitignore", "private", "api"):
            self.assertFalse((self.output / name).exists())

    def test_changed_or_extra_content_refuses_build_before_creating_output(self):
        p = self.root / "docs/guide.md"
        p.write_text("Unreviewed edit")
        with self.assertRaisesRegex(ValueError, "Manifest mismatch"):
            build_pages.build(self.output, self.root)
        self.assertFalse(self.output.exists())
        self.save_manifest()
        (self.root / "docs/extra.md").write_text("Extra")
        with self.assertRaises(ValueError):
            build_pages.build(self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_output_cannot_replace_or_live_in_source(self):
        self.output.mkdir()
        with self.assertRaises(ValueError):
            build_pages.build(self.output, self.root)
        with self.assertRaises(ValueError):
            build_pages.build(self.root / "site", self.root)

    def test_changed_diagram_refuses_build_even_with_updated_public_manifest(self):
        (self.root / "docs/guide.md").write_text("```mermaid\nflowchart LR\n A --> B\n```\n")
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "Mermaid sources changed"):
            build_pages.build(self.output, self.root)
        self.assertFalse(self.output.exists())

    def test_only_the_named_workflow_is_allowed_as_hidden_source(self):
        (self.root / ".github" / "secret.yml").write_text("Unreviewed")
        with self.assertRaises(ValueError):
            self.save_manifest()

if __name__ == "__main__":
    unittest.main()

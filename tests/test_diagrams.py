"""Diagram publication checks use source/asset fixtures, without browser dependencies."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import render_diagrams as diagrams


class DiagramTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def fixture(self):
        source = 'flowchart LR\n A --> B'
        self.put('guide.md', '# Path\n```mermaid\n' + source + '\n```\n')
        self.put(diagrams.CONFIG, '{}')
        asset = diagrams.ASSETS + '/' + hashlib.sha256(source.encode()).hexdigest()[:20] + '.svg'
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50"><text>Path</text></svg>'
        self.put(asset, svg)
        index = {'renderer': '@mermaid-js/mermaid-cli@' + diagrams.VERSION,
                 'configuration_sha256': hashlib.sha256(b'{}').hexdigest(),
                 'diagrams': {source: {'path': asset, 'alt': 'Flowchart: Path',
                                      'sha256': hashlib.sha256(svg.encode()).hexdigest()}}}
        self.put(diagrams.INDEX, json.dumps(index))
        return asset

    def test_only_real_mermaid_fences_are_collected_and_duplicates_share_assets(self):
        self.put('a.md', '# Route\r\n```mermaid\r\nflowchart LR\r\n A --> B\r\n```\r\n'
                 '```css\nflowchart LR\n X --> Y\n```\n'
                 '````markdown\n```mermaid\nflowchart LR\n Hidden --> Example\n```\n````\n')
        self.put('b.md', '~~~mermaid\nflowchart LR\n A --> B\n~~~\n')
        self.assertEqual(diagrams.sources(self.root), {'flowchart LR\n A --> B': 'Flowchart: Route'})

    def test_incomplete_or_empty_diagrams_refuse_publication(self):
        for text in ('```mermaid\nflowchart LR\n A --> B', '```mermaid\n\n```'):
            with self.subTest(text=text):
                self.put('guide.md', text)
                with self.assertRaises(ValueError):
                    diagrams.sources(self.root)

    def test_current_fixture_passes_but_edited_svg_fails(self):
        asset = self.fixture()
        self.assertEqual(diagrams.check(self.root), 1)
        self.put(asset, '<svg/>')
        with self.assertRaisesRegex(ValueError, 'SVG changed'):
            diagrams.check(self.root)

    def test_stale_source_theme_and_missing_asset_fail(self):
        for name, content, error in [('guide.md', '# Different heading\n```mermaid\nflowchart LR\n A --> B\n```', 'metadata'),
                                     ('guide.md', '```mermaid\nflowchart LR\n A --> C\n```', 'sources changed'),
                                     (diagrams.CONFIG, '{"theme":"default"}', 'theme changed')]:
            with self.subTest(name=name, error=error):
                self.fixture()
                self.put(name, content)
                with self.assertRaisesRegex(ValueError, error):
                    diagrams.check(self.root)
        asset = self.fixture()
        (self.root / asset).unlink()
        with self.assertRaisesRegex(ValueError, 'Missing'):
            diagrams.check(self.root)

    def test_svg_accepts_local_markers_but_rejects_active_or_remote_content(self):
        def svg(body):
            return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 50">' + body + '</svg>').encode()
        diagrams.validate_svg(svg('<style>path{stroke:url(#local-marker)}</style><path marker-end="url(#arrow)"/>'))
        for body in ('<script>alert(1)</script>', '<foreignObject/>', '<path onclick="alert(1)"/>',
                     '<image href="https://example.com/image.svg"/>', '<style>@import "https://example.com/style.css";</style>',
                     '<path style="fill:url(https://example.com/color)"/>', '<style>path{fill:url(\'https://example.com/color\')}</style>'):
            with self.subTest(body=body), self.assertRaises(ValueError):
                diagrams.validate_svg(svg(body))


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Render reviewed Mermaid blocks to local SVGs; check them without Node or a browser."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
VERSION = '11.17.0'
INDEX = 'app/diagram-index.json'
CONFIG = 'tools/mermaid.config.json'
ASSETS = 'figures/mermaid'


def normalize(source):
    return source.replace('\r\n', '\n').replace('\r', '\n').strip()


def sources(root=ROOT):
    result = {}
    for path in sorted(root.rglob('*.md')):
        if any(part.startswith('.') or part == '__pycache__' for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            raise ValueError('Symlink documentation refused')
        heading = path.stem.replace('-', ' ')
        fence = None
        block = []
        for line in path.read_text().splitlines():
            if fence:
                if re.fullmatch(r'\s*' + re.escape(fence[0]) + r'{' + str(fence[1]) + r',}\s*', line):
                    if fence[2] == 'mermaid':
                        source = normalize('\n'.join(block))
                        if not source:
                            raise ValueError('Empty Mermaid block: ' + str(path.relative_to(root)))
                        kind = 'Sequence diagram' if source.startswith('sequenceDiagram') else 'Flowchart'
                        result.setdefault(source, kind + ': ' + heading)
                    fence = None
                    block = []
                else:
                    block.append(line)
                continue
            opening = re.match(r'^\s*(`{3,}|~{3,})([^`~]*)$', line)
            if opening:
                fence = (opening[1][0], len(opening[1]), opening[2].strip().lower())
            elif re.match(r'^#{1,6}\s+', line):
                heading = re.sub(r'^#{1,6}\s+', '', line).replace('`', '')
        if fence and fence[2] == 'mermaid':
            raise ValueError('Unclosed Mermaid block: ' + str(path.relative_to(root)))
    return result


def validate_urls(value):
    # SVG markers and gradients refer to local identifiers, never network URLs.
    stripped = re.sub(r"url\(\s*(['\"]?)#[A-Za-z0-9_.:-]+\1\s*\)", '', value, flags=re.I)
    if re.search(r'url\(|@import', stripped, re.I):
        raise ValueError('External SVG/CSS resources refused')


def validate_svg(data):
    text = data.decode('utf-8')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('External XML declarations refused')
    svg = ET.fromstring(text)
    if svg.tag != '{http://www.w3.org/2000/svg}svg' or 'viewBox' not in svg.attrib:
        raise ValueError('Expected an SVG with a viewBox')
    allowed = {'svg', 'g', 'defs', 'marker', 'path', 'rect', 'line', 'polyline', 'polygon',
               'circle', 'ellipse', 'text', 'tspan', 'title', 'desc', 'style', 'clipPath',
               'linearGradient', 'radialGradient', 'stop', 'symbol', 'filter',
               'feGaussianBlur', 'feOffset', 'feMerge', 'feMergeNode', 'feColorMatrix',
               'feBlend', 'feFlood', 'feComposite', 'feDropShadow'}
    for element in svg.iter():
        if element.tag not in {'{http://www.w3.org/2000/svg}' + tag for tag in allowed}:
            raise ValueError('Unexpected active or embedded SVG element: ' + element.tag)
        for name, value in element.attrib.items():
            local = name.split('}')[-1].lower()
            if local.startswith('on') or local in {'href', 'src'}:
                raise ValueError('SVG event handlers and external resources refused')
            validate_urls(value)
        if element.tag.endswith('}style'):
            validate_urls(element.text or '')
    return svg


def check(root=ROOT):
    index_path = root / INDEX
    if index_path.is_symlink():
        raise ValueError('Diagram index symlink refused')
    index = json.loads(index_path.read_text())
    expected = sources(root)
    if index.get('renderer') != '@mermaid-js/mermaid-cli@' + VERSION:
        raise ValueError('Unexpected diagram renderer version')
    if index.get('configuration_sha256') != hashlib.sha256((root / CONFIG).read_bytes()).hexdigest():
        raise ValueError('Diagram theme changed; regenerate the diagrams')
    entries = index.get('diagrams', {})
    if set(entries) != set(expected):
        raise ValueError('Mermaid sources changed; run tools/render_diagrams.py render before publishing')
    asset_paths = set()
    for source, entry in entries.items():
        name = ASSETS + '/' + hashlib.sha256(source.encode()).hexdigest()[:20] + '.svg'
        if entry.get('path') != name or entry.get('alt') != expected[source]:
            raise ValueError('Diagram metadata changed; regenerate the diagrams')
        path = root / name
        if any(p.is_symlink() for p in [path, *path.parents]) or not path.is_file():
            raise ValueError('Missing or symlink diagram asset')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry.get('sha256'):
            raise ValueError('Diagram SVG changed; regenerate and review it')
        validate_svg(data)
        asset_paths.add(name)
    actual = {p.relative_to(root).as_posix() for p in (root / ASSETS).rglob('*') if p.is_file()}
    if actual != asset_paths:
        raise ValueError('Unlisted generated diagram assets')
    return len(entries)


def render(root, mmdc, puppeteer_config=None):
    version = subprocess.check_output([mmdc, '--version'], text=True).strip()
    if version != VERSION:
        raise ValueError('Use Mermaid CLI ' + VERSION + '; found ' + version)
    expected = sources(root)
    index = {'renderer': '@mermaid-js/mermaid-cli@' + VERSION,
             'configuration_sha256': hashlib.sha256((root / CONFIG).read_bytes()).hexdigest(),
             'diagrams': {}}
    prepared = {}
    with tempfile.TemporaryDirectory(prefix='lab-diagram-render-') as folder:
        for source, alt in expected.items():
            key = hashlib.sha256(source.encode()).hexdigest()[:20]
            input_path = Path(folder) / (key + '.mmd')
            output_path = Path(folder) / (key + '.svg')
            input_path.write_text(source + '\n')
            command = [mmdc, '-i', str(input_path), '-o', str(output_path), '-c', str(root / CONFIG),
                       '-b', 'white', '--svgId', 'diagram-' + key, '--quiet']
            if puppeteer_config:
                command += ['-p', str(puppeteer_config)]
            print('Rendering: ' + alt, flush=True)
            subprocess.run(command, check=True)
            data = output_path.read_bytes()
            svg = validate_svg(data)
            # Intrinsic dimensions keep wide figures readable in scroll containers.
            _, _, width, height = svg.attrib['viewBox'].split()
            svg.set('width', width)
            svg.set('height', height)
            ET.register_namespace('', 'http://www.w3.org/2000/svg')
            data = ET.tostring(svg, encoding='utf-8') + b'\n'
            name = ASSETS + '/' + key + '.svg'
            prepared[name] = data
            index['diagrams'][source] = {'path': name, 'alt': alt, 'sha256': hashlib.sha256(data).hexdigest()}
    target = root / ASSETS
    if target.is_symlink():
        raise ValueError('Diagram output symlink refused')
    target.mkdir(parents=True, exist_ok=True)
    # Replace only generated hash-named assets, after every render has succeeded.
    for p in target.iterdir():
        if p.is_symlink() or not re.fullmatch(r'[0-9a-f]{20}\.svg', p.name):
            raise ValueError('Unexpected file in the generated diagram directory')
    for name, data in prepared.items():
        (root / name).write_bytes(data)
    for p in target.iterdir():
        if p.relative_to(root).as_posix() not in prepared:
            p.unlink()
    (root / INDEX).write_text(json.dumps(index, indent=2, ensure_ascii=False) + '\n')
    return check(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'render'])
    parser.add_argument('--mmdc', default='mmdc', help='Path to the pinned Mermaid CLI executable')
    parser.add_argument('--puppeteer-config', type=Path, help='Optional private browser launch configuration')
    args = parser.parse_args()
    try:
        count = check() if args.action == 'check' else render(ROOT, args.mmdc, args.puppeteer_config)
        print(f'PASS: {count} Mermaid diagrams match their source, theme and SVGs.')
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, subprocess.SubprocessError) as error:
        parser.exit(2, f'Diagram preparation failed: {error}\n')

if __name__ == '__main__':
    main()

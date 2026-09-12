#!/usr/bin/env python3
"""Build a public static website from the reviewed manifest. No upload or API."""
import argparse
import hashlib
from pathlib import Path
import release
import render_diagrams

def build(output, root=release.ROOT):
    root = root.resolve()
    output = Path(output)
    if output.is_symlink() or output.exists() or output.resolve().is_relative_to(root):
        raise ValueError("Use a new output directory outside the public source tree")
    inventory = release.check(root)
    render_diagrams.check(root)
    # Read and verify before creating any output. Hidden workflow/config files
    # are repository metadata and do not belong in the website artifact.
    content = {}
    for name, digest in inventory.items():
        if name.startswith("."):
            continue
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("Source changed during build: " + name)
        content[name] = data
    html = content["app/index.html"].decode("utf-8")
    marker = '<meta name="lab-edition" content="public-static">'
    html = html.replace("<head>", "<head>\n" + marker, 1)
    # Local server serves the source at /; static Pages serves /REPOSITORY/.
    content["index.html"] = html.replace('href="/app/style.css"', 'href="./app/style.css"').replace('src="/app/app.js"', 'src="./app/app.js"').encode()
    content["app/index.html"] = html.replace('href="/app/style.css"', 'href="./style.css"').replace('src="/app/app.js"', 'src="./app.js"').encode()
    content[".nojekyll"] = b""
    output.mkdir(parents=True)
    for name, data in content.items():
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    return len(content)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        count = build(args.output)
        print(f"Built {count} public website files. No private endpoints or uploads.")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Website build refused: {error}\n")

if __name__ == "__main__":
    main()


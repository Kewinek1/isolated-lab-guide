#!/usr/bin/env python3
"""Verify a reviewed public tree and export only its exact manifest. No upload."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "PUBLIC_MANIFEST.json"
IGNORED_DIRS = {".git", "__pycache__"}
ALLOWED_SUFFIXES = {".md", ".py", ".js", ".mjs", ".css", ".html", ".json", ".svg", ".ino", ".h", ".cpp", ".example", ".sh"}
SPECIAL_PUBLIC_FILES = {".gitignore", ".github/workflows/pages.yml"}
FORBIDDEN_NAMES = {"config.py", ".env", "profile.json", "config.local.json", "server.properties", "eula.txt", "server-settings.json", "whitelist.json"}
PATTERNS = [
    (re.compile(r"(?i)\b(?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2}\b"), "MAC address"),
    (re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"\b(?:tskey-auth|tskey-api|ghp_|github_pat_)[A-Za-z0-9_-]{8,}"), "access token"),
    (re.compile(r"(?i)IMG_[0-9]+\.(?:jpg|jpeg|png)|friend-[0-9]"), "private photo reference"),
]

def files(root=ROOT):
    result = {}
    for current, dirs, names in os.walk(root, followlinks=False):
        for name in dirs:
            if (Path(current) / name).is_symlink():
                raise ValueError("Symlink directory refused")
        dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS)
        for name in sorted(names):
            p = Path(current) / name
            if name == MANIFEST and p.parent == root:
                continue
            if p.is_symlink():
                raise ValueError("Symlink refused: " + str(p.relative_to(root)))
            if p.suffix == ".pyc" and "__pycache__" in p.parts:
                continue
            relative = p.relative_to(root).as_posix()
            if relative not in SPECIAL_PUBLIC_FILES and (p.suffix not in ALLOWED_SUFFIXES or any(part.startswith(".") for part in Path(relative).parts)):
                raise ValueError("Unreviewed file type/name: " + relative)
            if p.name in FORBIDDEN_NAMES or ".local." in p.name or any(part in {"private", "local", "build", "node_modules"} for part in Path(relative).parts):
                raise ValueError("Private or generated path refused: " + relative)
            data = p.read_bytes()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError("Binary file refused: " + relative) from exc
            for pattern, label in PATTERNS:
                if pattern.search(text):
                    raise ValueError(label + " found; review file: " + relative)
            result[relative] = hashlib.sha256(data).hexdigest()
    return result

def check(root=ROOT):
    manifest = root / MANIFEST
    if manifest.is_symlink():
        raise ValueError("Manifest cannot be a symlink")
    expected = json.loads(manifest.read_text())
    if expected.get("classification") != "PUBLIC — FICTIONAL EXAMPLES":
        raise ValueError("Unexpected manifest classification")
    actual = files(root)
    if actual != expected.get("files"):
        changed = sorted(set(actual) ^ set(expected.get("files", {})) | {k for k in actual if k in expected.get("files", {}) and actual[k] != expected["files"][k]})
        raise ValueError("Manifest mismatch; review added/changed/missing files: " + ", ".join(changed))
    return actual

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("check")
    review = sub.add_parser("manifest", help="Explicitly rebuild after manual privacy review")
    review.add_argument("--reviewed-public-content", action="store_true", required=True)
    export = sub.add_parser("export")
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "manifest":
            inventory = files()
            manifest = ROOT / MANIFEST
            if manifest.is_symlink():
                raise ValueError("Manifest cannot be a symlink")
            manifest.write_text(json.dumps({"classification": "PUBLIC — FICTIONAL EXAMPLES", "files": inventory}, indent=2) + "\n")
            print(f"Recorded {len(inventory)} reviewed public files.")
            return
        inventory = check()
        if args.action == "check":
            print(f"PASS: {len(inventory)} files match the reviewed public manifest.")
            return
        output = args.output.resolve()
        if output.is_relative_to(ROOT):
            raise ValueError("Write exports outside the public source directory")
        if args.output.is_symlink() or output.exists():
            raise ValueError("Export destination already exists or is a symlink")
        # Exclusive creation prevents accidental replacement.
        with output.open("xb") as stream, zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for relative in sorted([*inventory, MANIFEST]):
                data = (ROOT / relative).read_bytes()
                if relative != MANIFEST and hashlib.sha256(data).hexdigest() != inventory[relative]:
                    raise ValueError("File changed during export")
                info = zipfile.ZipInfo(relative, date_time=(2026, 9, 11, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o644 & 0xFFFF) << 16
                archive.writestr(info, data)
        print(f"Exported {len(inventory)+1} public files to {output.name}. No upload performed.")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"Release refused: {exc}\n")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
r"""Inspect one local firmware file without executing or unpacking it.

Requires Python 3.10+ on a POSIX system with O_NOFOLLOW support. Input must be a
regular file of at most 128 MiB. Symlinks in input/output paths are refused.
Reports can contain embedded credentials or identifiers and must remain private.
An explicit --output creates a new 0600 file outside the shared repository.
Without --output, JSON goes to stdout and a privacy notice goes to stderr.

Examples (run from the shared repository root):
  python3 tools/inspect_firmware.py ../private/vendor-firmware.bin \
      --output ../private/firmware-report.json
  python3 tools/inspect_firmware.py ../private/vendor-firmware.bin --max-strings 0
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

MAX_FILE_BYTES = 128 * 1024 * 1024
CHUNK_BYTES = 64 * 1024
PUBLIC_ROOT = Path(__file__).resolve().parents[1]
PRIVACY_NOTICE = "PRIVATE REPORT: header bytes and strings may contain credentials or identifiers. Keep the report and terminal output out of GitHub."


def open_without_symlinks(path, flags, mode=0o600):
    """Open each path component relative to an already-open directory descriptor."""
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY") or os.open not in os.supports_dir_fd:
        raise ValueError("This tool requires POSIX O_NOFOLLOW and directory-relative open support")
    absolute = Path(path).absolute()
    if not absolute.name:
        raise ValueError("A file path is required")
    directory = os.open(absolute.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in absolute.parts[1:-1]:
            next_directory = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        return os.open(absolute.name, flags | os.O_NOFOLLOW, mode, dir_fd=directory)
    finally:
        os.close(directory)


def signature_hint(header):
    # Hints only: no full-format validation, board matching or embedded extraction.
    # UF2 constants: https://github.com/microsoft/uf2#file-format
    if header.startswith(b"UF2\nWQ\x5d\x9e"):
        return "UF2 starting magic; blocks, family and compatibility unverified"
    if header.startswith(b"\x7fELF"):
        return "ELF starting magic; architecture and executable validity unverified"
    if header.startswith(b"PK\x03\x04"):
        return "ZIP local-header magic; contents not opened"
    if header.startswith(b"\x1f\x8b"):
        return "gzip starting magic; content not decompressed"
    return "No recognized starting magic; the file may be raw, wrapped, compressed or another format"


class StringSamples:
    """Retain bounded samples of printable ASCII runs, including chunk boundaries."""
    def __init__(self, max_strings=64, string_chars=128):
        if type(max_strings) is not int or not 0 <= max_strings <= 256:
            raise ValueError("max_strings must be from 0 to 256")
        if type(string_chars) is not int or not 6 <= string_chars <= 256:
            raise ValueError("string_chars must be from 6 to 256")
        self.max_strings = max_strings
        self.string_chars = string_chars
        self.items = []
        self.found = 0
        self.offset = 0
        self.run_start = 0
        self.run_length = 0
        self.prefix = bytearray()

    def finish_run(self):
        if self.run_length >= 6:
            self.found += 1
            if len(self.items) < self.max_strings:
                self.items.append({"offset": self.run_start, "length_bytes": self.run_length,
                                   "sample": self.prefix.decode("ascii"),
                                   "sample_truncated": self.run_length > len(self.prefix)})
        self.run_length = 0
        self.prefix.clear()

    def feed(self, data):
        for value in data:
            if 32 <= value <= 126:
                if self.run_length == 0:
                    self.run_start = self.offset
                self.run_length += 1
                if len(self.prefix) < self.string_chars:
                    self.prefix.append(value)
            elif self.run_length:
                self.finish_run()
            self.offset += 1


def inspect(path, max_strings=64, string_chars=128):
    samples = StringSamples(max_strings, string_chars)
    digest = hashlib.sha256()
    total = 0
    header = b""
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    descriptor = open_without_symlinks(path, flags)
    with os.fdopen(descriptor, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Input must be a regular file, not a directory, device, socket or pipe")
        if before.st_size > MAX_FILE_BYTES:
            raise ValueError("Firmware exceeds the 128 MiB inspection limit")
        while True:
            chunk = source.read(min(CHUNK_BYTES, MAX_FILE_BYTES - total + 1))
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                raise ValueError("Firmware grew beyond the 128 MiB inspection limit")
            if len(header) < 64:
                header += chunk[:64 - len(header)]
            digest.update(chunk)
            if max_strings:
                samples.feed(chunk)
        after = os.fstat(source.fileno())
        if (total != before.st_size or before.st_size != after.st_size
                or before.st_mtime_ns != after.st_mtime_ns or before.st_ctime_ns != after.st_ctime_ns):
            raise ValueError("Input changed during inspection; inspect a stable local copy")
    samples.finish_run()
    return {
        "privacy": PRIVACY_NOTICE,
        "size_bytes": total,
        "sha256": digest.hexdigest(),
        "header_hex_first_64_bytes": header.hex(" "),
        "starting_signature_hint": signature_hint(header),
        "strings": {"enabled": bool(max_strings), "encoding": "printable ASCII only (bytes 32-126)",
                    "minimum_length": 6, "sample_limit": max_strings, "characters_per_sample_limit": string_chars,
                    "matching_runs": samples.found if max_strings else None,
                    "omitted_runs": max(0, samples.found - len(samples.items)) if max_strings else None,
                    "samples": samples.items},
        "limits": ["No execution, decompression, extraction or network access.",
                   "Magic and strings are hints; random bytes may resemble text.",
                   "No malware, vulnerability, hardware-compatibility or authenticity verdict.",
                   "Compare the full SHA-256 with an independently authenticated vendor value when available."]
    }


def write_private_report(path, report, public_root=PUBLIC_ROOT):
    absolute = Path(os.path.abspath(path))
    protected = Path(public_root).resolve()
    if absolute == protected or protected in absolute.parents:
        raise ValueError("Report output must be outside the shared repository")
    # Directory-relative no-follow traversal rejects both final and ancestor symlinks.
    descriptor = open_without_symlinks(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(report, output, indent=2, ensure_ascii=True)
        output.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("firmware", type=Path, help="One local regular file, at most 128 MiB; no symlink components")
    parser.add_argument("--output", type=Path, help="Create a NEW private report outside the shared repository; default stdout")
    parser.add_argument("--max-strings", type=int, default=64, help="Retain 0-256 text samples; 0 disables string inspection; default 64")
    parser.add_argument("--string-chars", type=int, default=128, help="Maximum characters in each sample, 6-256; default 128")
    args = parser.parse_args(argv)
    print(PRIVACY_NOTICE, file=sys.stderr)
    try:
        report = inspect(args.firmware, args.max_strings, args.string_chars)
        if args.output is not None:
            write_private_report(args.output, report)
            print("Created a private report. No firmware was modified or executed.", file=sys.stderr)
        else:
            json.dump(report, sys.stdout, indent=2, ensure_ascii=True)
            print()
    except (OSError, ValueError) as error:
        parser.exit(2, "Inspection refused: " + str(error) + "\n")


if __name__ == "__main__":
    main()

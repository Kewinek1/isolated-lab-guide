"""Bounded read-only inspection and private output safety checks."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

TOOL = Path(__file__).resolve().parents[1] / "tools" / "inspect_firmware.py"
spec = importlib.util.spec_from_file_location("firmware_inspector", TOOL)
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


class FirmwareInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "sample.bin"

    def test_sha256_header_and_no_input_modification(self):
        data = b"\x7fELF\x00fictional lesson string\x00"
        self.image.write_bytes(data)
        report = inspector.inspect(self.image)
        self.assertEqual(report["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(report["header_hex_first_64_bytes"], data.hex(" "))
        self.assertIn("ELF", report["starting_signature_hint"])
        self.assertEqual(self.image.read_bytes(), data)

    def test_strings_cross_chunk_boundary_and_truncate(self):
        data = b"\x00" * (inspector.CHUNK_BYTES - 3) + b"ABCDEFGH" * 20 + b"\x00SECOND-RUN\x00THIRD-RUN"
        self.image.write_bytes(data)
        report = inspector.inspect(self.image, max_strings=2, string_chars=8)
        strings = report["strings"]
        self.assertEqual(strings["matching_runs"], 3)
        self.assertEqual(strings["omitted_runs"], 1)
        self.assertEqual(strings["samples"][0], {"offset": inspector.CHUNK_BYTES - 3,
                          "length_bytes": 160, "sample": "ABCDEFGH", "sample_truncated": True})

    def test_strings_disabled(self):
        self.image.write_bytes(b"a private fictional phrase")
        strings = inspector.inspect(self.image, max_strings=0)["strings"]
        self.assertFalse(strings["enabled"])
        self.assertEqual(strings["samples"], [])
        self.assertIsNone(strings["matching_runs"])

    def test_limit_rejects_before_reading_large_content(self):
        self.image.write_bytes(b"a" * 17)
        with mock.patch.object(inspector, "MAX_FILE_BYTES", 16):
            with self.assertRaisesRegex(ValueError, "limit"):
                inspector.inspect(self.image)

    def test_empty_file_and_uf2_hint(self):
        self.image.write_bytes(b"")
        self.assertEqual(inspector.inspect(self.image)["size_bytes"], 0)
        self.image.write_bytes(b"UF2\nWQ\x5d\x9e" + b"\x00" * 24)
        self.assertIn("unverified", inspector.inspect(self.image)["starting_signature_hint"])

    def test_input_and_ancestor_symlinks_refused(self):
        self.image.write_bytes(b"fictional payload")
        direct = self.root / "image-link.bin"
        direct.symlink_to(self.image)
        directory = self.root / "directory-link"
        directory.symlink_to(self.root, target_is_directory=True)
        for path in (direct, directory / self.image.name):
            with self.subTest(path=path):
                with self.assertRaises(OSError):
                    inspector.inspect(path)

    def test_pipe_refused_without_blocking(self):
        pipe = self.root / "not-firmware"
        os.mkfifo(pipe)
        with self.assertRaisesRegex(ValueError, "regular file"):
            inspector.inspect(pipe)

    def test_report_private_permissions_and_exclusive_create(self):
        output = self.root / "report.json"
        inspector.write_private_report(output, {"fixture": "synthetic"})
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertEqual(json.loads(output.read_text()), {"fixture": "synthetic"})
        with self.assertRaises(FileExistsError):
            inspector.write_private_report(output, {})

    def test_report_inside_public_tree_or_via_symlink_refused(self):
        public = self.root / "share"
        public.mkdir()
        with self.assertRaisesRegex(ValueError, "outside"):
            inspector.write_private_report(public / "report.json", {}, public_root=public)
        alias = self.root / "alias"
        alias.symlink_to(public, target_is_directory=True)
        with self.assertRaises(OSError):
            inspector.write_private_report(alias / "report.json", {}, public_root=public)
        self.assertFalse((public / "report.json").exists())

    def test_stdout_has_private_notice_on_stderr(self):
        self.image.write_bytes(b"a fictional sample")
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            inspector.main([str(self.image), "--max-strings", "0"])
        self.assertIn("PRIVATE REPORT", stderr.getvalue())
        self.assertIn("sha256", json.loads(stdout.getvalue()))

    def test_sample_limits_are_not_unbounded(self):
        for count, chars in ((257, 128), (-1, 128), (64, 257), (64, 5)):
            with self.assertRaises(ValueError):
                inspector.StringSamples(count, chars)


if __name__ == "__main__":
    unittest.main()

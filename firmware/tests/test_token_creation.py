"""Private token output boundaries, permissions and refusal behavior."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / "linux_target" / "create_tokens.py"
spec = importlib.util.spec_from_file_location("create_tokens", MODULE)
create_tokens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(create_tokens)


class TokenCreationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_private_tokens_created_without_printing_secrets(self):
        output = self.root / "tokens.json"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            create_tokens.main([str(output)])
        tokens = json.loads(output.read_text())
        self.assertEqual(set(tokens), {"alpha", "beta"})
        self.assertNotEqual(tokens["alpha"], tokens["beta"])
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        for token in tokens.values():
            self.assertGreaterEqual(len(token), 32)
            self.assertNotIn(token, stdout.getvalue())

    def test_cli_refuses_destination_inside_public_tree(self):
        public = self.root / "share"
        public.mkdir()
        output = public / "tokens.json"
        with mock.patch.object(create_tokens, "PUBLIC_ROOT", public):
            with self.assertRaisesRegex(SystemExit, "outside the public repository"):
                create_tokens.main([str(output)])
        self.assertFalse(output.exists())

    def test_existing_destination_is_preserved(self):
        output = self.root / "tokens.json"
        output.write_text("existing private data")
        with self.assertRaises(SystemExit):
            create_tokens.main([str(output)])
        self.assertEqual(output.read_text(), "existing private data")

    def test_final_and_ancestor_symlinks_refused(self):
        real = self.root / "real"
        real.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(real, target_is_directory=True)
        link = self.root / "tokens-link.json"
        link.symlink_to(real / "tokens.json")
        for path in (alias / "tokens.json", link):
            with self.subTest(path=path):
                with self.assertRaises(SystemExit):
                    create_tokens.main([str(path)])
        self.assertFalse((real / "tokens.json").exists())


if __name__ == "__main__":
    unittest.main()

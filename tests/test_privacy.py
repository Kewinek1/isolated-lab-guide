"""Privacy boundaries for local serving and reviewed export; no sockets opened."""
import contextlib
import ast
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def module(name):
    spec = importlib.util.spec_from_file_location("privacy_test_" + name, TOOLS / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


serve = module("serve")
release = module("release")
materialize = module("materialize")


class PublicFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="public-boundary-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "public"
        self.root.mkdir()

    def write(self, relative, content="Fictional public example\n"):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        return target

    def manifest(self, names=None):
        if names is None:
            entries = release.files(self.root)
        else:
            entries = {name: hashlib.sha256((self.root / name).read_bytes()).hexdigest() for name in names}
        (self.root / release.MANIFEST).write_text(json.dumps({
            "classification": "PUBLIC — FICTIONAL EXAMPLES", "files": entries,
        }))
        return entries


class ServingTests(PublicFixture):
    def setUp(self):
        super().setUp()
        self.write("app/index.html", "<!doctype html><title>Public example</title>")
        self.write("docs/guide.md")
        self.write("firmware/config.example.py", 'ENABLE_NETWORK = False\n')
        self.manifest()

    def test_only_reviewed_public_files_are_served(self):
        for name in ("app/index.html", "docs/guide.md", "firmware/config.example.py"):
            self.assertEqual(serve.public_file("/" + name, self.root), self.root / name)
        self.write("firmware/lesson-tokens.json", '{"secret":"synthetic-runtime-value"}')
        self.write("network/site.json", '{"note":"unreviewed runtime settings"}')
        self.assertIsNone(serve.public_file("/firmware/lesson-tokens.json", self.root))
        self.assertIsNone(serve.public_file("/network/site.json", self.root))
        self.assertIsNone(serve.public_file("/docs/", self.root))

    def test_traversal_encoded_separators_and_private_paths_are_rejected(self):
        for path in ("/docs/../private/config.json", "/docs/%2e%2e/private/config.json",
                     "/docs/%2e%2e%2fprivate/config.json", "/app/../../README.md",
                     "/docs/%00guide.md", "/docs%5cguide.md", "/.git/config",
                     "/private/profile.json", "/docs/__pycache__/file.pyc"):
            with self.subTest(path=path):
                self.assertIsNone(serve.public_file(path, self.root))

    def test_sensitive_names_remain_denied_even_if_erroneously_listed(self):
        names = ["firmware/config.py", "docs/.env", "network/site.local.json",
                 "games/server.properties", "games/server-settings.json",
                 "docs/capture.pcap", "docs/private.key", "docs/photo.jpg"]
        for name in names:
            self.write(name)
        self.manifest(names)
        for name in names:
            with self.subTest(name=name):
                self.assertIsNone(serve.public_file("/" + name, self.root))

    def test_file_and_directory_symlinks_cannot_escape_even_with_manifest_entry(self):
        outside = self.base / "outside"
        outside.mkdir()
        secret = outside / "secret.md"
        secret.write_text("Synthetic private content")
        (self.root / "docs" / "alias.md").symlink_to(secret)
        (self.root / "docs" / "linked").symlink_to(outside, target_is_directory=True)
        self.manifest(["docs/alias.md", "docs/linked/secret.md"])
        self.assertIsNone(serve.public_file("/docs/alias.md", self.root))
        self.assertIsNone(serve.public_file("/docs/linked/secret.md", self.root))

    def test_missing_invalid_and_symlink_manifests_fail_closed(self):
        manifest = self.root / release.MANIFEST
        manifest.unlink()
        self.assertIsNone(serve.public_file("/docs/guide.md", self.root))
        manifest.write_text("not json")
        self.assertIsNone(serve.public_file("/docs/guide.md", self.root))
        manifest.unlink()
        external = self.base / "external-manifest.json"
        external.write_text('{"files":{"docs/guide.md":"unused"}}')
        manifest.symlink_to(external)
        self.assertIsNone(serve.public_file("/docs/guide.md", self.root))


class RequestTests(PublicFixture):
    def request(self, path, headers=None, private_dir=None, method="GET"):
        # Construct the real handler without BaseHTTPRequestHandler's socket setup.
        handler = serve.Handler.__new__(serve.Handler)
        handler.path = path
        handler.command = method
        handler.headers = {"Host": "127.0.0.1:8765", **(headers or {})}
        handler.server = SimpleNamespace(server_port=8765)
        handler.private_dir = private_dir
        handler.wfile = io.BytesIO()
        handler.response_headers = {}
        handler.send_response = lambda status: setattr(handler, "response_status", status)
        handler.send_header = lambda name, value: handler.response_headers.__setitem__(name, value)
        handler.end_headers = lambda: None
        handler.do_HEAD() if method == "HEAD" else handler.do_GET()
        return handler.response_status, handler.response_headers, handler.wfile.getvalue()

    def test_public_mode_has_no_private_document_routes(self):
        status, headers, body = self.request("/api/mode")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"private_available": False})
        self.assertEqual(headers["Cache-Control"], "no-store")
        for path in ("/api/private-profile", "/api/private-guide", "/api/private-inventory", "/api/private-secret"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_foreign_hosts_origins_and_cross_site_requests_are_rejected(self):
        for headers in ({"Host": "untrusted.invalid:8765"}, {"Host": "127.0.0.1:8000"},
                        {"Origin": "https://untrusted.invalid"}, {"Origin": "null"},
                        {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("/api/mode", headers)[0], 403)
        self.assertEqual(self.request("/api/mode", {"Origin": "http://127.0.0.1:8765"})[0], 200)

    def test_explicit_private_mode_returns_display_metadata_only(self):
        private = self.base / "private-data"
        private.mkdir()
        metadata = {"labels": {"mainRouter": "Local display name"}, "inventory": [], "address_note": "Unverified"}
        (private / "profile.json").write_text(json.dumps({**metadata, "wifi_password": "synthetic-secret-value",
                                                         "runtime_tokens": ["synthetic-token-value"]}))
        status, headers, body = self.request("/api/private-profile", private_dir=private)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), metadata)
        self.assertNotIn(b"synthetic-secret-value", body)
        self.assertNotIn(b"runtime_tokens", body)
        self.assertEqual(headers["Cross-Origin-Resource-Policy"], "same-origin")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("/api/private-config.local.json", private_dir=private)[0], 404)
        self.assertEqual(self.request("/api/private-profile/../config.local.json", private_dir=private)[0], 404)

    def test_private_document_symlinks_and_head_bodies_are_denied(self):
        private = self.base / "private-data"
        private.mkdir()
        external = self.base / "secret.md"
        external.write_text("Synthetic secret")
        (private / "START-HERE.md").symlink_to(external)
        self.assertEqual(self.request("/api/private-guide", private_dir=private)[0], 404)
        status, headers, body = self.request("/api/mode", method="HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertGreater(int(headers["Content-Length"]), 0)


class ReleaseTests(PublicFixture):
    def setUp(self):
        super().setUp()
        self.write("README.md")
        self.expected = self.manifest()

    def test_exact_manifest_passes_and_changed_missing_added_files_fail(self):
        self.assertEqual(release.check(self.root), self.expected)
        original = (self.root / "README.md").read_text()
        self.write("README.md", "Changed content")
        with self.assertRaisesRegex(ValueError, "Manifest mismatch"):
            release.check(self.root)
        self.write("README.md", original)
        unlisted = self.write("docs/unlisted.md")
        with self.assertRaisesRegex(ValueError, "Manifest mismatch"):
            release.check(self.root)
        unlisted.unlink()
        (self.root / "README.md").unlink()
        with self.assertRaisesRegex(ValueError, "Manifest mismatch"):
            release.check(self.root)

    def test_runtime_names_binary_files_and_symlinks_are_rejected(self):
        for name in ("firmware/config.py", "private/notes.md", "docs/settings.local.json", "docs/data.zip"):
            path = self.write(name)
            with self.subTest(name=name), self.assertRaises(ValueError):
                release.files(self.root)
            path.unlink()
        binary = self.root / "docs" / "binary.md"
        binary.write_bytes(bytes([255, 254]))
        with self.assertRaisesRegex(ValueError, "Binary file refused"):
            release.files(self.root)
        binary.unlink()
        outside = self.base / "outside.md"
        outside.write_text("Synthetic outside content")
        alias = self.root / "alias.md"
        alias.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Symlink refused"):
            release.files(self.root)
        alias.unlink()
        directory_alias = self.root / "alias"
        directory_alias.symlink_to(self.base, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink directory refused"):
            release.files(self.root)

    def test_secret_patterns_prevent_export_inventory(self):
        # Compose synthetic patterns at runtime so the public test file is itself clean.
        cases = [(':'.join(['ab'] * 6), "MAC address"),
                 ('-' * 5 + 'BEGIN ' + 'PRIVATE KEY' + '-' * 5, "private key"),
                 ('tskey-' + 'auth-' + 'x' * 32, "access token"),
                 ('IMG_' + '999999' + '.jpg', "private photo reference")]
        for value, message in cases:
            with self.subTest(message=message):
                self.write("README.md", value)
                with self.assertRaisesRegex(ValueError, message):
                    release.files(self.root)

    def run_export(self, output):
        real_check = release.check
        with patch.object(release, "ROOT", self.root), \
                patch.object(release, "check", side_effect=lambda: real_check(self.root)), \
                patch("sys.argv", ["release.py", "export", "--output", str(output)]), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            release.main()

    def test_export_contains_only_reviewed_files_and_manifest(self):
        output = self.base / "public-export.zip"
        self.run_export(output)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(set(archive.namelist()), {"README.md", release.MANIFEST})
            self.assertEqual(archive.read("README.md"), (self.root / "README.md").read_bytes())
            for entry in archive.infolist():
                self.assertEqual(entry.date_time, (2026, 9, 11, 0, 0, 0))
                self.assertEqual((entry.external_attr >> 16) & 0o777, 0o644)

    def test_export_refuses_existing_files_and_public_tree_destinations(self):
        existing = self.base / "existing.zip"
        existing.write_bytes(b"Preserve this file")
        for output in (existing, self.root / "export.zip"):
            with self.subTest(output=output.name), self.assertRaises(SystemExit) as raised:
                self.run_export(output)
            self.assertEqual(raised.exception.code, 2)
        self.assertEqual(existing.read_bytes(), b"Preserve this file")
        self.assertFalse((self.root / "export.zip").exists())


class MaterializeTests(PublicFixture):
    def setUp(self):
        super().setUp()
        self.config = {
            "site": "A", "addresses_confirmed": False, "isolated_lab_confirmed": False,
            "lab_cidr": "10.77.10.0/24", "relay_cidr": "10.78.10.0/24",
            "management_cidr": "10.79.10.0/24", "protected_home_cidrs": [],
            "target_ip": "10.77.10.20", "pico_ip": "10.77.10.30",
            "protected_external_cidrs": [], "relay_internet_https": False,
            "pico": {"enable_network": False, "ssid": "", "wifi_password": "", "country": "XX"},
        }

    def input(self):
        path = self.root / "config.local.json"
        path.write_text(json.dumps(self.config))
        path.chmod(0o600)

    def test_unconfirmed_build_is_inert_and_all_generated_state_is_private(self):
        self.input()
        with patch("socket.socket", side_effect=AssertionError("No network connection is permitted")), \
                patch("subprocess.run", side_effect=AssertionError("No external process is permitted")):
            built = materialize.build(self.root)
        self.assertFalse((built / "network/firewall.candidate").exists())
        self.assertTrue((built / "network/NOT-GENERATED.txt").exists())
        text = (built / "firmware/pico_w/config.py").read_text()
        assignments = {node.targets[0].id: ast.literal_eval(node.value)
                       for node in ast.parse(text).body if isinstance(node, ast.Assign)}
        self.assertIs(assignments["ENABLE_NETWORK"], False)
        self.assertIs(assignments["ALLOW_UNAUTHENTICATED_LAB"], False)
        self.assertEqual(assignments["MODE"], "token")
        self.assertEqual(assignments["PORT"], 8080)
        self.assertEqual(len(assignments["API_TOKEN"]), 64)
        tokens = json.loads((built / "firmware/lesson-tokens.json").read_text())
        self.assertEqual(set(tokens), {"alpha", "beta"})
        self.assertNotEqual(tokens["alpha"], tokens["beta"])
        for path in [built, *built.rglob("*")]:
            self.assertFalse(path.is_symlink())
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)
        for secret in [assignments["API_TOKEN"], *tokens.values()]:
            self.assertNotIn(secret, (built / "README.md").read_text())

    def test_confirmation_flags_require_actual_booleans(self):
        for field in ("addresses_confirmed", "isolated_lab_confirmed", "relay_internet_https"):
            self.config[field] = "true"
            self.input()
            with self.subTest(field=field), self.assertRaises(ValueError):
                materialize.build(self.root)
            self.assertFalse((self.root / "build").exists())
            self.config[field] = False
        self.config["pico"]["enable_network"] = "true"
        self.input()
        with self.assertRaises(ValueError):
            materialize.build(self.root)

    def test_network_enablement_requires_both_confirmations_and_valid_country(self):
        self.config["pico"].update(enable_network=True, ssid="SYNTHETIC-LAB", wifi_password="synthetic-only-password", country="SE")
        for addresses, isolation in ((False, False), (True, False), (False, True)):
            self.config.update(addresses_confirmed=addresses, isolated_lab_confirmed=isolation)
            self.input()
            with self.subTest(addresses=addresses, isolation=isolation), self.assertRaises(ValueError):
                materialize.build(self.root)
            self.assertFalse((self.root / "build").exists())
        self.config.update(addresses_confirmed=True, isolated_lab_confirmed=True)
        self.config["protected_home_cidrs"] = ["192.168.222.0/24"]
        for country in ("XX", "xx", "ßa"):
            self.config["pico"]["country"] = country
            self.input()
            with self.subTest(country=country), self.assertRaises(ValueError):
                materialize.build(self.root)
            self.assertFalse((self.root / "build").exists())

    def test_existing_build_symlink_input_and_public_destination_are_refused(self):
        self.input()
        built = self.root / "build"
        built.mkdir()
        marker = built / "preserve.md"
        marker.write_text("Retain previous state")
        with self.assertRaises(ValueError):
            materialize.build(self.root)
        self.assertEqual(marker.read_text(), "Retain previous state")
        config_path = self.root / "config.local.json"
        external = self.base / "external-input.json"
        external.write_text(config_path.read_text())
        config_path.unlink()
        config_path.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "symlink"):
            materialize.build(self.root)
        with patch.object(materialize, "PUBLIC", self.root), self.assertRaisesRegex(ValueError, "outside"):
            materialize.build(self.root)

    def test_custom_target_hosts_are_validated_and_preserved_in_confirmed_candidate(self):
        for key, value in (("target_ip", "10.77.20.20"), ("pico_ip", "10.77.10.1"),
                           ("pico_ip", "10.77.10.255"), ("target_ip", "10.77.10.30"),
                           ("target_ip", 173870612)):
            original = self.config[key]
            self.config[key] = value
            self.input()
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                materialize.build(self.root)
            self.assertFalse((self.root / "build").exists())
            self.config[key] = original
        self.config.update(target_ip="10.77.10.42", pico_ip="10.77.10.43",
                           addresses_confirmed=True, isolated_lab_confirmed=True,
                           protected_home_cidrs=["192.168.222.0/24"])
        self.input()
        built = materialize.build(self.root)
        candidate = (built / "network/firewall.candidate").read_text()
        self.assertIn("option dest_ip '10.77.10.43'", candidate)
        self.assertIn("option dest_ip '10.77.10.42'", candidate)
        self.assertNotIn("relay_public_https", candidate)
        ssh = (built / "network/sshd-relay.conf.example").read_text()
        self.assertIn("PermitOpen 10.77.10.43:8080 10.77.10.42:8081", ssh)


if __name__ == "__main__":
    unittest.main()

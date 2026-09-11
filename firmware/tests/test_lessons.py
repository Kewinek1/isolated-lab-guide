"""CPython checks for security semantics; these do not emulate Pico hardware."""
import contextlib
import http.client
import importlib.util
import io
from pathlib import Path
import sys
import threading
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pico_w"))
import http_core

spec = importlib.util.spec_from_file_location("lab_server", ROOT / "linux_target" / "server.py")
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

TOKENS = {"alpha": "a" * 43, "beta": "b" * 43}  # Test-only fixtures, no deployed credentials.


def pico_request(method="GET", path="/status", token=None, extra=b""):
    raw = (method + " " + path + " HTTP/1.1\r\nHost: lab.example\r\n").encode()
    if token is not None:
        raw += ("Authorization: Bearer " + token + "\r\n").encode()
    return raw + extra + b"\r\n"


class PicoTests(unittest.TestCase):
    def test_token_required_before_led_change(self):
        status, _, state = http_core.dispatch(pico_request("POST", "/led/on"), "token", TOKENS["alpha"], False)
        self.assertEqual((status, state), (401, False))

    def test_token_changes_led(self):
        status, body, state = http_core.dispatch(pico_request("POST", "/led/on", TOKENS["alpha"]), "token", TOKENS["alpha"], False)
        self.assertEqual((status, body["led"], state), (200, True, True))

    def test_lab_mode_missing_auth_is_visible(self):
        status, _, state = http_core.dispatch(pico_request("POST", "/led/on"), "lab", "", False)
        self.assertEqual((status, state), (200, True))

    def test_get_does_not_change_led(self):
        status, _, state = http_core.dispatch(pico_request("GET", "/led/on"), "lab", "", False)
        self.assertEqual((status, state), (405, False))

    def test_ambiguous_or_oversized_requests_rejected(self):
        cases = [
            pico_request(extra=b"Host: second.example\r\n"),
            pico_request(extra=b"Content-Length: 4\r\n"),
            pico_request(extra=b"Transfer-Encoding: chunked\r\n"),
            pico_request(extra=b"X-Pad: " + b"a" * 2048 + b"\r\n"),
            b"GET / HTTP/1.1\r\n\r\n",
            pico_request() + b"body",
        ]
        for raw in cases:
            with self.subTest(raw=raw[:60]):
                self.assertEqual(http_core.dispatch(raw, "lab", "", False)[0], 400)

    def test_bad_token_and_invalid_mode_fail_closed(self):
        self.assertEqual(http_core.dispatch(pico_request(token="wrong"), "token", TOKENS["alpha"], False)[0], 401)
        self.assertEqual(http_core.dispatch(pico_request(), "typo", "", False)[0], 503)

    def test_example_config_cannot_connect(self):
        config = types.SimpleNamespace(ENABLE_NETWORK=False)
        with self.assertRaises(ValueError):
            http_core.validate_config(config)

    def test_lab_mode_needs_explicit_enable(self):
        config = types.SimpleNamespace(ENABLE_NETWORK=True, WIFI_SSID="isolated-test", WIFI_PASSWORD="test-only-password",
                                       MODE="lab", ALLOW_UNAUTHENTICATED_LAB=False, COUNTRY="DE", PORT=8080)
        with self.assertRaises(ValueError):
            http_core.validate_config(config)
        config.ALLOW_UNAUTHENTICATED_LAB = True
        http_core.validate_config(config)


class LinuxIntegrationTests(unittest.TestCase):
    def request(self, mode, path, token=None):
        with server.LabServer(("127.0.0.1", 0), mode, TOKENS) as service:
            worker = threading.Thread(target=service.handle_request, daemon=True)
            worker.start()
            client = http.client.HTTPConnection("127.0.0.1", service.server_port, timeout=3)
            headers = {} if token is None else {"Authorization": "Bearer " + token}
            try:
                client.request("GET", path, headers=headers)
                response = client.getresponse()
                result = response.status, response.read()
            finally:
                client.close()
                worker.join(timeout=4)
            self.assertFalse(worker.is_alive())
            return result

    def test_insecure_mode_exposes_other_dummy_record(self):
        status, body = self.request("insecure", "/records/2", TOKENS["alpha"])
        self.assertEqual(status, 200)
        self.assertIn(b'"owner": "beta"', body)

    def test_secure_mode_denies_other_dummy_record(self):
        status, body = self.request("secure", "/records/2", TOKENS["alpha"])
        self.assertEqual(status, 403)
        self.assertNotIn(b"Fictional record B", body)

    def test_secure_mode_permits_own_record(self):
        self.assertEqual(self.request("secure", "/records/1", TOKENS["alpha"])[0], 200)

    def test_both_modes_require_authentication(self):
        for mode in ("secure", "insecure"):
            self.assertEqual(self.request(mode, "/records/1")[0], 401)

    def test_missing_record_is_404(self):
        self.assertEqual(self.request("secure", "/records/999", TOKENS["alpha"])[0], 404)

    def test_non_loopback_requires_explicit_enable(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                server.parse_args(["--bind", "192.0.2.10", "--tokens-file", "unused.json"])
            with self.assertRaises(SystemExit):
                server.parse_args(["--bind", "0.0.0.0", "--allow-lab-listener", "--tokens-file", "unused.json"])

    def test_reused_tokens_are_rejected(self):
        with self.assertRaises(ValueError):
            server.validate_tokens({"alpha": "x" * 43, "beta": "x" * 43})


if __name__ == "__main__":
    unittest.main()

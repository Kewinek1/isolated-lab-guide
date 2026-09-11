import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("game_launch", Path(__file__).parents[1] / "launch.py")
launch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launch)


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / "state"
        self.state.mkdir(mode=0o700)
        self.config_file = self.root / "launcher.json"
        self.config_file.write_text("{}")
        self.config_file.chmod(0o600)
        # Invented fixture address, never an actual assigned endpoint.
        self.address = "100.101.102.103"
        self.config = {"game_directory": str(self.state), "bind_ip": self.address,
                       "isolation_verified": True}

    def test_default_unapproved_network_is_refused(self):
        self.config["isolation_verified"] = False
        with self.assertRaisesRegex(launch.ConfigError, "acceptance"):
            launch.validate_common(self.config, self.config_file)

    def test_non_overlay_and_wildcard_bind_addresses_refused(self):
        for address in ("0.0.0.0", "127.0.0.1", "10.77.11.20", "::"):
            with self.subTest(address=address):
                self.config["bind_ip"] = address
                with self.assertRaises(launch.ConfigError):
                    launch.validate_common(self.config, self.config_file)

    def test_private_directory_permissions_required(self):
        self.state.chmod(0o755)
        with self.assertRaisesRegex(launch.ConfigError, "700"):
            launch.validate_common(self.config, self.config_file)

    def test_duplicate_json_refused(self):
        self.config_file.write_text('{"visibility": false, "visibility": true}')
        with self.assertRaisesRegex(launch.ConfigError, "Duplicate"):
            launch.load_json(self.config_file)

    def test_property_escapes_and_duplicates_refused(self):
        path = self.state / "server.properties"
        for content in ("server-ip=a\nserver-ip=b\n", "server\\u002dip=b\n",
                        "server-ip=a\\\nb\n"):
            with self.subTest(content=content):
                path.write_text(content)
                with self.assertRaises(launch.ConfigError):
                    launch.checked_properties(path)

    def test_changed_artifact_refused(self):
        path = self.state / "artifact"
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(launch.ConfigError, "mismatch"):
            launch.verify_hash(path, hashlib.sha256(b"original").hexdigest())

    def minecraft_fixture(self):
        java = self.root / "java"
        java.write_bytes(b"test fixture; never executed")
        java.chmod(0o700)
        artifact = self.state / "server.jar"
        artifact.write_bytes(b"test fixture; never executed")
        self.config.update({"java_binary": str(java), "java_major": 25, "memory_mib": 2048,
                            "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()})
        template = Path(__file__).parents[1] / "minecraft" / "server.properties.example"
        self.properties = template.read_text().replace("REPLACE_WITH_ASSIGNED_TAILSCALE_IPV4", self.address)
        (self.state / "server.properties").write_text(self.properties)
        (self.state / "whitelist.json").write_text("[]")
        (self.state / "eula.txt").write_text("eula=true\n")

    @patch.dict(os.environ, {}, clear=True)
    @patch.object(launch.subprocess, "run", return_value=SimpleNamespace(stderr='openjdk version "25.0.1"', stdout=""))
    def test_minecraft_rejects_unaccepted_eula(self, *_):
        self.minecraft_fixture()
        (self.state / "eula.txt").write_text("eula=false\n")
        with self.assertRaisesRegex(launch.ConfigError, "EULA"):
            launch.minecraft_command(self.config, self.state, self.address)
        self.assertEqual((self.state / "eula.txt").read_text(), "eula=false\n")

    @patch.dict(os.environ, {}, clear=True)
    @patch.object(launch.subprocess, "run", return_value=SimpleNamespace(stderr='openjdk version "25.0.1"', stdout=""))
    def test_minecraft_rejects_disabled_authentication(self, *_):
        self.minecraft_fixture()
        (self.state / "server.properties").write_text(self.properties.replace("online-mode=true", "online-mode=false"))
        with self.assertRaisesRegex(launch.ConfigError, "online-mode"):
            launch.minecraft_command(self.config, self.state, self.address)

    @patch.dict(os.environ, {}, clear=True)
    @patch.object(launch.subprocess, "run", return_value=SimpleNamespace(stderr='openjdk version "25.0.1"', stdout=""))
    def test_minecraft_builds_explicit_jar_command(self, *_):
        self.minecraft_fixture()
        command = launch.minecraft_command(self.config, self.state, self.address)
        self.assertEqual(command[-3:], ["-jar", str(self.state / "server.jar"), "nogui"])

    @patch.object(launch.shutil, "which", return_value="/usr/bin/fixture")
    @patch.object(launch.subprocess, "run")
    def test_overlay_rejects_address_belonging_to_another_node(self, run, _):
        run.return_value = SimpleNamespace(stdout=json.dumps({"BackendState": "Running", "Self": {"TailscaleIPs": []}}))
        with self.assertRaisesRegex(launch.ConfigError, "not assigned"):
            launch.verify_overlay(self.address)

    @patch.object(launch.shutil, "which", return_value="/usr/bin/fixture")
    @patch.object(launch.subprocess, "run")
    def test_overlay_requires_actual_local_interface(self, run, _):
        run.side_effect = [SimpleNamespace(stdout=json.dumps({"BackendState": "Running", "Self": {"TailscaleIPs": [self.address]}})),
                           SimpleNamespace(stdout="[]")]
        with self.assertRaisesRegex(launch.ConfigError, "not present"):
            launch.verify_overlay(self.address)

    def factorio_fixture(self):
        binary = self.root / "distribution" / "bin" / "x64" / "factorio"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"test fixture; never executed")
        binary.chmod(0o700)
        (self.root / "distribution" / "data").mkdir()
        self.config.update({"factorio_binary": str(binary),
                            "artifact_sha256": hashlib.sha256(binary.read_bytes()).hexdigest()})
        self.settings = {"visibility": {"public": False, "lan": False},
                         "require_user_verification": True, "allow_commands": "admins-only",
                         "game_password": "fictional-fixture-password"}
        (self.state / "server-settings.json").write_text(json.dumps(self.settings))
        (self.state / "server-whitelist.json").write_text('["training-account"]')
        return binary

    @patch.object(launch.platform, "system", return_value="Linux")
    @patch.object(launch.platform, "machine", return_value="x86_64")
    def test_factorio_create_refuses_existing_save(self, *_):
        self.factorio_fixture()
        (self.state / "saves").mkdir()
        (self.state / "saves" / "world.zip").write_bytes(b"existing world")
        with self.assertRaisesRegex(launch.ConfigError, "overwrite"):
            launch.factorio_command(self.config, self.state, self.address, True)

    @patch.object(launch.platform, "system", return_value="Linux")
    @patch.object(launch.platform, "machine", return_value="x86_64")
    def test_factorio_unsafe_settings_refused(self, *_):
        self.factorio_fixture()
        for field, value in (("game_password", "REPLACE_WITH_LONG_SECRET"),
                             ("require_user_verification", False),
                             ("visibility", {"public": True, "lan": False})):
            with self.subTest(field=field):
                bad = dict(self.settings)
                bad[field] = value
                (self.state / "server-settings.json").write_text(json.dumps(bad))
                with self.assertRaises(launch.ConfigError):
                    launch.factorio_command(self.config, self.state, self.address, True)

    @patch.object(launch.platform, "system", return_value="Linux")
    @patch.object(launch.platform, "machine", return_value="x86_64")
    def test_factorio_command_limits_listener_and_requires_allowlist(self, *_):
        self.factorio_fixture()
        (self.state / "saves").mkdir()
        (self.state / "saves" / "world.zip").write_bytes(b"fixture")
        command, _ = launch.factorio_command(self.config, self.state, self.address)
        self.assertEqual(command[command.index("--bind") + 1], self.address)
        self.assertEqual(command[command.index("--port") + 1], "34197")
        self.assertIn("--use-server-whitelist=true", command)
        self.assertNotIn("--rcon-port", command)


if __name__ == "__main__":
    unittest.main()

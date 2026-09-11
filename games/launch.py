#!/usr/bin/env python3
"""Explicit, private game launchers. No installs, downloads or firewall changes."""

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

PUBLIC_TREE = Path(__file__).resolve().parents[1]


class ConfigError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ConfigError(message)


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def private_path(value, label, directory=False):
    require(isinstance(value, str) and "REPLACE" not in value and "ABSOLUTE" not in value,
            label + " needs an explicit local absolute path")
    path = Path(value)
    require(path.is_absolute(), label + " must be an absolute path")
    path = path.resolve()
    require(not path.is_relative_to(PUBLIC_TREE), label + " must be outside the public source tree")
    require(path.is_dir() if directory else path.is_file(), label + " does not exist")
    return path


def verify_hash(path, expected):
    require(isinstance(expected, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected),
            "Record the verified artifact SHA-256 in artifact_sha256")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    require(digest.hexdigest() == expected.lower(), "Artifact SHA-256 mismatch")


def checked_properties(path):
    result = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith(("#", "!")):
            continue
        # Accept a deliberately narrow subset of Java .properties syntax so
        # escapes/continuations cannot change the meaning after this check.
        require(raw == raw.strip() and "\\" not in raw and "=" in raw,
                "Use simple key=value properties at line " + str(number))
        key, value = raw.split("=", 1)
        require(re.fullmatch(r"[a-z0-9-]+", key) and key not in result,
                "Invalid or duplicate property at line " + str(number))
        result[key] = value
    return result


def validate_common(config, config_path):
    require(isinstance(config, dict), "Configuration must be a JSON object")
    require(config.get("isolation_verified") is True,
            "Complete the services-zone acceptance worksheet, then set isolation_verified to true")
    require(not config_path.resolve().is_relative_to(PUBLIC_TREE),
            "The filled configuration must be outside the public source tree")
    game_dir = private_path(config.get("game_directory"), "game_directory", directory=True)
    require(game_dir.stat().st_mode & 0o077 == 0,
            "Private game directory needs mode 700: chmod 700 PATH")
    require(config_path.stat().st_mode & 0o077 == 0,
            "Private configuration needs mode 600: chmod 600 PATH")
    try:
        address = ipaddress.IPv4Address(config.get("bind_ip", ""))
    except ipaddress.AddressValueError:
        raise ConfigError("bind_ip must be the assigned Tailscale IPv4 address")
    require(address in ipaddress.IPv4Network("100.64.0.0/10"),
            "This launcher accepts only an assigned Tailscale IPv4 endpoint")
    return game_dir, str(address)


def verify_overlay(address):
    executable = shutil.which("tailscale")
    require(executable is not None, "Tailscale must be installed and joined before launch")
    result = subprocess.run([executable, "status", "--json"], capture_output=True,
                            text=True, timeout=15, check=True)
    status = json.loads(result.stdout)
    require(status.get("BackendState") == "Running", "Tailscale is not running")
    own_addresses = status.get("Self", {}).get("TailscaleIPs", [])
    require(address in own_addresses, "bind_ip is not assigned to this Tailscale node")
    # The daemon may retain an identity without an active OS interface.
    ip_command = shutil.which("ip")
    require(ip_command is not None, "Linux iproute2 is required for interface verification")
    result = subprocess.run([ip_command, "-j", "address", "show", "dev", "tailscale0"],
                            capture_output=True, text=True, timeout=10, check=True)
    interfaces = json.loads(result.stdout)
    require(any(info.get("local") == address for link in interfaces
                for info in link.get("addr_info", [])),
            "The address is not present on the local tailscale0 interface")


def minecraft_command(config, game_dir, address):
    java = private_path(config.get("java_binary"), "java_binary")
    require(os.access(java, os.X_OK), "java_binary is not executable")
    artifact = game_dir / "server.jar"
    require(artifact.is_file(), "Place the official selected release at game_directory/server.jar")
    verify_hash(artifact, config.get("artifact_sha256"))
    require(not any(os.environ.get(name) for name in
                    ("JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS")),
            "Unset Java option injection environment variables for this launcher")
    major = config.get("java_major")
    memory = config.get("memory_mib")
    require(type(major) is int and 17 <= major <= 99, "java_major must be the selected release requirement")
    require(type(memory) is int and 512 <= memory <= 32768, "memory_mib must be 512..32768")
    version = subprocess.run([str(java), "-version"], capture_output=True, text=True,
                             timeout=15, check=True)
    match = re.search(r'version "(\d+)', version.stderr + version.stdout)
    require(match is not None and int(match.group(1)) == major,
            "Installed Java major does not match java_major")
    require(checked_properties(game_dir / "eula.txt").get("eula") == "true",
            "Review the Minecraft EULA and explicitly edit local eula.txt before launch")
    properties = checked_properties(game_dir / "server.properties")
    expected = {"server-ip": address, "server-port": "25565", "online-mode": "true",
                "white-list": "true", "enforce-whitelist": "true", "enable-rcon": "false",
                "enable-query": "false", "enable-jmx-monitoring": "false",
                "management-server-enabled": "false"}
    for key, value in expected.items():
        require(properties.get(key) == value, "server.properties must set " + key + "=" + value)
    require(isinstance(load_json(game_dir / "whitelist.json"), list), "whitelist.json must be an array")
    return [str(java), "-Xms512M", "-Xmx" + str(memory) + "M", "-jar", str(artifact), "nogui"]


def factorio_command(config, game_dir, address, create_world=False):
    require(platform.system() == "Linux" and platform.machine().lower() in ("x86_64", "amd64"),
            "This workflow requires Linux x86_64 and the official Linux64 Factorio package")
    artifact = private_path(config.get("factorio_binary"), "factorio_binary")
    require(os.access(artifact, os.X_OK), "factorio_binary is not executable")
    verify_hash(artifact, config.get("artifact_sha256"))
    data_dir = artifact.parents[2] / "data"
    require(data_dir.is_dir(), "Expected official package layout: bin/x64/factorio and data/")
    settings_path = game_dir / "server-settings.json"
    settings = load_json(settings_path)
    require(isinstance(settings, dict), "server-settings.json must be an object")
    require(settings.get("visibility") == {"public": False, "lan": False},
            "Factorio public and LAN advertisement must both be disabled")
    require(settings.get("require_user_verification") is True, "Require authenticated Factorio users")
    password = settings.get("game_password", "")
    require(isinstance(password, str) and len(password) >= 16 and "REPLACE" not in password.upper(),
            "Set a unique game_password of at least 16 characters")
    require(settings.get("allow_commands") == "admins-only", "Use allow_commands=admins-only")
    for key in ("username", "password", "token"):
        require(settings.get(key, "") == "", "Private unlisted mode needs no publisher account secret")
    allowlist = load_json(game_dir / "server-whitelist.json")
    require(isinstance(allowlist, list) and allowlist and all(
        isinstance(name, str) and name and "REPLACE" not in name.upper() for name in allowlist),
        "Fill server-whitelist.json with approved Factorio usernames")
    save = game_dir / "saves" / "world.zip"
    if create_world:
        require(not save.exists(), "Refusing to overwrite an existing world")
    else:
        require(save.is_file(), "Create a world with --create-world before starting Factorio")
    command = [str(artifact), "--config", str(game_dir / "launcher-config.ini"),
               "--mod-directory", str(game_dir / "mods")]
    if create_world:
        command += ["--create", str(save)]
    else:
        command += ["--start-server", str(save), "--server-settings", str(settings_path),
                    "--bind", address, "--port", "34197", "--use-server-whitelist=true",
                    "--server-whitelist", str(game_dir / "server-whitelist.json"),
                    "--server-adminlist", str(game_dir / "server-adminlist.json"),
                    "--server-banlist", str(game_dir / "server-banlist.json")]
    return command, data_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", choices=("minecraft", "factorio"))
    parser.add_argument("config", type=Path, help="Absolute path to PRIVATE JSON configuration")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Validate only; launch no game")
    action.add_argument("--create-world", action="store_true", help="Factorio only; refuses overwrite")
    args = parser.parse_args()
    try:
        require(platform.system() == "Linux", "These launchers target Linux")
        require(os.geteuid() != 0, "Run as an unprivileged services account, not root")
        require(args.config.is_absolute(), "Use an absolute path for the private JSON configuration")
        config = load_json(args.config)
        game_dir, address = validate_common(config, args.config)
        verify_overlay(address)
        if args.game == "minecraft":
            require(not args.create_world, "--create-world is only for Factorio")
            command = minecraft_command(config, game_dir, address)
        else:
            command, data_dir = factorio_command(config, game_dir, address, args.create_world)
        if args.check:
            print("Configuration checks passed; no game started. Physical isolation still requires its recorded tests.")
            return 0
        os.umask(0o077)
        if args.game == "factorio":
            (game_dir / "saves").mkdir(exist_ok=True)
            (game_dir / "mods").mkdir(exist_ok=True)
            require("\n" not in str(data_dir) + str(game_dir), "Paths cannot contain newlines")
            (game_dir / "launcher-config.ini").write_text(
                "[path]\nread-data=" + str(data_dir) + "\nwrite-data=" + str(game_dir) + "\n",
                encoding="utf-8")
        os.chdir(game_dir)
        os.execv(command[0], command)
    except (ConfigError, OSError, ValueError, subprocess.SubprocessError) as error:
        print("Launch refused: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

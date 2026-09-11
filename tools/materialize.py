#!/usr/bin/env python3
"""Prepare a private, inert code instance from public templates; never configure devices."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil

PUBLIC = Path(__file__).resolve().parents[1]
def private_write(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)

def build(private_dir):
    root = private_dir.resolve()
    if root.is_relative_to(PUBLIC):
        raise ValueError("Private output must be outside the public source tree")
    config_path = root / "config.local.json"
    if config_path.is_symlink():
        raise ValueError("Private input must not be a symlink")
    config = json.loads(config_path.read_text())
    required = {"site", "addresses_confirmed", "isolated_lab_confirmed", "lab_cidr", "relay_cidr", "management_cidr", "target_ip", "pico_ip", "protected_home_cidrs", "protected_external_cidrs", "pico", "relay_internet_https"}
    optional = {"firewall_platform", "architecture"}
    if not required.issubset(config) or set(config) - required - optional:
        raise ValueError("Configuration keys do not match private-config.example.json")
    platform = config.get("firewall_platform", "openwrt")
    architecture = config.get("architecture", "tunnel")
    if platform not in {"openwrt", "pfsense", "opnsense"} or architecture not in {"offline", "single", "tunnel", "games", "edge", "split", "dmz"}:
        raise ValueError("Invalid firewall platform or architecture")
    if config["site"] not in {"A", "B", "C"} or any(type(config[k]) is not bool for k in ("addresses_confirmed", "isolated_lab_confirmed", "relay_internet_https")):
        raise ValueError("Invalid site or confirmation flags")
    pico = config["pico"]
    if set(pico) != {"enable_network", "ssid", "wifi_password", "country"} or type(pico["enable_network"]) is not bool:
        raise ValueError("Invalid Pico fields")
    if not isinstance(pico["country"], str) or not re.fullmatch(r"[A-Za-z]{2}", pico["country"]):
        raise ValueError("Use a two-letter installation country code")
    pico["country"] = pico["country"].upper()
    if pico["enable_network"] and (not config["addresses_confirmed"] or not config["isolated_lab_confirmed"] or not isinstance(pico["ssid"], str) or not pico["ssid"] or not isinstance(pico["wifi_password"], str) or len(pico["wifi_password"]) < 8 or pico["country"] == "XX"):
        raise ValueError("Pico network enablement requires confirmed isolation, addresses, country and private Wi-Fi credentials")
    import ipaddress
    nets = [ipaddress.ip_network(config[k], strict=True) for k in ("lab_cidr", "relay_cidr", "management_cidr")]
    private_ranges = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    if any(n.version != 4 or n.prefixlen != 24 or not any(n.subnet_of(r) for r in private_ranges) for n in nets) or len(set(nets)) != 3:
        raise ValueError("Use three distinct private IPv4 /24 networks")
    target_addresses = {}
    for key in ("target_ip", "pico_ip"):
        if not isinstance(config[key], str):
            raise ValueError(key + " must be a literal IPv4 address")
        address = ipaddress.IPv4Address(config[key])
        if address not in nets[0] or address <= nets[0].network_address + 1 or address >= nets[0].broadcast_address:
            raise ValueError(key + " must be a host from .2 through .254 in the lab network")
        target_addresses[key] = str(address)
    if target_addresses["target_ip"] == target_addresses["pico_ip"]:
        raise ValueError("The Linux target and Pico require different addresses")
    site = {
        "site": config["site"], "lab_cidr": str(nets[0]), "relay_cidr": str(nets[1]), "management_cidr": str(nets[2]),
        "relay_ip": str(nets[1].network_address + 2), "management_host": str(nets[2].network_address + 2),
        "protected_home_cidrs": config["protected_home_cidrs"], "protected_external_cidrs": config["protected_external_cidrs"],
        "target_services": [{"address": target_addresses["pico_ip"], "tcp_port": 8080},
                            {"address": target_addresses["target_ip"], "tcp_port": 8081}],
        "relay_internet_https": config["relay_internet_https"],
    }
    firewall = None
    if config["addresses_confirmed"]:
        if not config["isolated_lab_confirmed"]:
            raise ValueError("Firewall generation also requires confirmed isolation/interface planning")
    if config["addresses_confirmed"] and platform == "openwrt" and architecture == "tunnel":
        spec = importlib.util.spec_from_file_location("lab_firewall", PUBLIC / "network/generate_firewall.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        firewall = module.generate(site)
    destination = root / "build"
    if destination.is_symlink() or destination.exists():
        raise ValueError("private/build already exists. Preserve it and choose a fresh private directory, or rename the old build before rebuilding.")
    destination.mkdir(mode=0o700)
    for name in ("firmware", "games"):
        source = PUBLIC / name
        if any(p.is_symlink() for p in source.rglob("*")):
            raise ValueError("Public templates must not contain symlinks")
        shutil.copytree(source, destination / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
    for current, directories, files in os.walk(destination):
        os.chmod(current, 0o700)
        for name in files:
            os.chmod(Path(current) / name, 0o600)
    token = secrets.token_hex(32)
    pico_text = "# PRIVATE INSTANCE. Never commit this file.\n" + "\n".join([
        f"ENABLE_NETWORK = {pico['enable_network']!r}",
        f"WIFI_SSID = {(pico['ssid'] or 'REPLACE_WITH_ISOLATED_LAB_SSID')!r}",
        f"WIFI_PASSWORD = {(pico['wifi_password'] or 'REPLACE_WITH_LAB_WIFI_PASSWORD')!r}",
        f"COUNTRY = {pico['country'].upper()!r}", "PORT = 8080", "MODE = 'token'",
        "ALLOW_UNAUTHENTICATED_LAB = False", f"API_TOKEN = {token!r}", ""
    ])
    private_write(destination / "firmware/pico_w/config.py", pico_text)
    private_write(destination / "firmware/lesson-tokens.json", json.dumps({"alpha": secrets.token_hex(32), "beta": secrets.token_hex(32)}, indent=2)+"\n")
    (destination / "network").mkdir(mode=0o700)
    private_write(destination / "network/site.local.json", json.dumps(site, indent=2)+"\n")
    if firewall:
        private_write(destination / "network/firewall.candidate", firewall)
    else:
        reason = "Actual addresses and interface isolation are unconfirmed."
        if platform != "openwrt" or architecture != "tunnel":
            reason = f"The {platform} platform / {architecture} architecture requires a manual firewall configuration. No compatible configuration generator is provided for this combination. Read network/PFSENSE-OPNSENSE.md and network/ARCHITECTURES.md; OpenWrt UCI is not a pfSense or OPNsense configuration."
        private_write(destination / "network/NOT-GENERATED.txt", "Firewall generation withheld: " + reason + " No sample home subnet has been substituted.\n")
    private_write(destination / "network/platform.local.json", json.dumps({"firewall_platform": platform, "architecture": architecture, "firewall_candidate_generated": firewall is not None}, indent=2) + "\n")
    for name in ("tailscale.policy.json", "sshd-relay.conf.example"):
        text = (PUBLIC / "network" / name).read_text()
        if name == "sshd-relay.conf.example":
            text = text.replace("10.77.10.30:8080", target_addresses["pico_ip"] + ":8080")
            text = text.replace("10.77.10.20:8081", target_addresses["target_ip"] + ":8081")
        private_write(destination / "network" / name, text)
    private_write(destination / "README.md", """# Private code instance
This directory contains private generated tokens and configuration. Never publish it.

- firmware/uno_serial/: open uno_serial.ino in Arduino IDE and select the classic Uno.
- firmware/pico_w/: upload main.py, http_core.py and config.py using the firmware guide. Network is disabled unless the local input explicitly enabled it.
- firmware/linux_target/: run the server with the private ../lesson-tokens.json file. Default bind is loopback; use the documented lesson commands.
- network/: site-specific inputs and platform.local.json; a firewall candidate exists only for the dedicated OpenWrt tunnel design when addresses and isolation were confirmed. pfSense, OPNsense and other layouts require the matching manual recipe.
- games/: runnable shared launchers and templates. Copy examples to private runtime filenames and complete the game guide before launch.

A code instance does not deploy a firewall or establish isolation. Runtime firmware and game tests still require the actual hardware. Documentation remains in the public source's firmware/, network/ and games/ README files. The local hardware inventory is ../INVENTORY.md.
""")
    return destination

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        path = build(args.private_dir)
        print("Prepared private code in " + str(path))
        print("No credentials printed. No device, firewall or VPN settings changed.")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, "Private build refused: " + str(exc) + "\n")

if __name__ == "__main__":
    main()

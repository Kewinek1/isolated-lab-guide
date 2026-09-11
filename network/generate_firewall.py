#!/usr/bin/env python3
"""Generate a complete, fail-closed dedicated OpenWrt firewall; never apply it.

Four preconfigured, isolated logical interfaces are required: uplink, mgmt,
relay, lab. Read OPENWRT.md first. Output contains site details: keep it private.
"""
import argparse
import ipaddress
import json
from pathlib import Path

RFC1918 = tuple(map(ipaddress.ip_network, ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")))
BLOCKED = (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24",
    "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24",
    "224.0.0.0/4", "240.0.0.0/4",
)


def network(value):
    if not isinstance(value, str):
        raise ValueError("CIDR values must be strings")
    n = ipaddress.ip_network(value, strict=True)
    if n.version != 4:
        raise ValueError("This baseline uses IPv4; routed IPv6 remains denied.")
    return n


def host(value, subnet):
    if not isinstance(value, str):
        raise ValueError("Host addresses must be strings")
    ip = ipaddress.ip_address(value)
    if ip not in subnet or ip in (subnet.network_address, subnet.broadcast_address, subnet.network_address + 1):
        raise ValueError(f"Host must be a usable address other than gateway .1 inside {subnet}")
    return str(ip)


def validate(config):
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object")
    required = {"site", "lab_cidr", "relay_cidr", "management_cidr", "relay_ip",
                "management_host", "protected_home_cidrs", "protected_external_cidrs",
                "target_services", "relay_internet_https"}
    if set(config) != required:
        raise ValueError(f"Configuration keys must be exactly: {', '.join(sorted(required))}")
    if config["site"] not in ("A", "B", "C"):
        raise ValueError("site must be A, B or C")
    subnets = [network(config[key]) for key in ("lab_cidr", "relay_cidr", "management_cidr")]
    for subnet in subnets:
        if subnet.prefixlen != 24 or not any(subnet.subnet_of(r) for r in RFC1918):
            raise ValueError("Each segment must be a private RFC1918 /24")
    for index, subnet in enumerate(subnets):
        if any(subnet.overlaps(other) for other in subnets[index + 1:]):
            raise ValueError("Lab, relay and management segments must not overlap")
    for key in ("protected_home_cidrs", "protected_external_cidrs"):
        if not isinstance(config[key], list):
            raise ValueError(f"{key} must be a list")
        for entry in config[key]:
            n = network(entry)
            if n.prefixlen == 0:
                raise ValueError("A protected /0 would block all Internet access")
            if any(n.overlaps(s) for s in subnets):
                raise ValueError("Protected home/external ranges must not overlap lab segments")
    if not config["protected_home_cidrs"]:
        raise ValueError("Record the actual upstream home subnet before generation")
    host(config["relay_ip"], subnets[1])
    host(config["management_host"], subnets[2])
    if not isinstance(config["relay_internet_https"], bool):
        raise ValueError("relay_internet_https must be true or false")
    if not isinstance(config["target_services"], list) or not config["target_services"]:
        raise ValueError("Specify at least one approved target service")
    seen = set()
    for service in config["target_services"]:
        if not isinstance(service, dict) or set(service) != {"address", "tcp_port"}:
            raise ValueError("A target service has only address and tcp_port")
        host(service["address"], subnets[0])
        port = service["tcp_port"]
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("tcp_port must be an integer from 1 to 65535")
        pair = (service["address"], port)
        if pair in seen:
            raise ValueError("Duplicate target service")
        seen.add(pair)
    return config


def generate(config):
    c = validate(config)
    output = ["# GENERATED PRIVATE CONFIGURATION. Dedicated lab firewall only.",
              "# Replaces /etc/config/firewall after manual review; never append.",
              "# No interface definitions, route advertisements or public forwards.", ""]

    def section(kind, identifier, **options):
        output.append(f"config {kind} '{identifier}'")
        for key, value in options.items():
            if isinstance(value, list):
                for item in value:
                    output.append(f"\tlist {key} '{item}'")
            else:
                output.append(f"\toption {key} '{value}'")
        output.append("")

    def rule(name, **options):
        section("rule", name, name=name, **options)

    section("defaults", "defaults", input="REJECT", output="ACCEPT", forward="REJECT",
            drop_invalid="1", synflood_protect="1", flow_offloading="0",
            flow_offloading_hw="0", auto_includes="0")
    for zone in ("uplink", "mgmt", "relay", "lab"):
        options = dict(name=zone, network=[zone], input="REJECT", output="ACCEPT", forward="REJECT")
        if zone == "uplink":
            options.update(masq="1", mtu_fix="1")
        section("zone", f"zone_{zone}", **options)
    rule("uplink_dhcp_client", src="uplink", proto="udp", src_port="67", dest_port="68", family="ipv4", target="ACCEPT")
    for zone in ("mgmt", "relay", "lab"):
        rule(f"{zone}_dhcp", src=zone, proto="udp", src_port="68", dest_port="67", family="ipv4", target="ACCEPT")
    rule("mgmt_admin", src="mgmt", src_ip=c["management_host"], proto="tcp", dest_port="22 443", family="ipv4", target="ACCEPT")
    rule("relay_dns", src="relay", src_ip=c["relay_ip"], proto="tcp udp", dest_port="53", family="ipv4", target="ACCEPT")
    rule("mgmt_relay_ssh", src="mgmt", src_ip=c["management_host"], dest="relay", dest_ip=c["relay_ip"],
         proto="tcp", dest_port="22", family="ipv4", target="ACCEPT")
    for index, target in enumerate(c["target_services"]):
        rule(f"relay_target_{index}", src="relay", src_ip=c["relay_ip"], dest="lab", dest_ip=target["address"],
             proto="tcp", dest_port=str(target["tcp_port"]), family="ipv4", target="ACCEPT")
    denied = list(dict.fromkeys(BLOCKED + tuple(c["protected_home_cidrs"]) + tuple(c["protected_external_cidrs"])))
    rule("relay_protected_destinations", src="relay", dest="uplink", dest_ip=denied,
         proto="all", family="ipv4", target="REJECT")
    if c["relay_internet_https"]:
        rule("relay_public_https", src="relay", src_ip=c["relay_ip"], dest="uplink", proto="tcp", dest_port="443",
             family="ipv4", target="ACCEPT")
    output.extend(["# Stateful reply traffic is handled by firewall4.",
                   "# No lab-to-uplink, lab-to-relay, or IPv6 forward permission exists.",
                   "# Router-originated output is permitted: keep this firewall trusted.", ""])
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, help="Create a NEW private file with mode 0600; default stdout")
    args = parser.parse_args()
    try:
        text = generate(json.loads(args.config.read_text()))
        if args.output:
            public_root = Path(__file__).resolve().parents[1]
            if args.output.resolve().is_relative_to(public_root):
                raise ValueError("Generated configuration must be written outside the public repository")
            # Exclusive create: no accidental replacement of existing router files.
            import os
            fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write(text)
        else:
            print(text, end="")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"Configuration rejected: {exc}\n")


if __name__ == "__main__":
    main()

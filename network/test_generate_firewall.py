"""Safety invariants; does not claim to emulate OpenWrt or prove isolation."""
import copy
import json
import unittest
from pathlib import Path
from generate_firewall import generate


class FirewallTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads(Path(__file__).with_name("site.example.json").read_text())

    def test_offline_default_has_no_forwarding_or_internet_accept(self):
        text = generate(self.config)
        self.assertNotIn("config forwarding", text)
        self.assertNotIn("relay_public_https", text)
        self.assertNotIn("config redirect", text)
        for section in text.split("config rule ")[1:]:
            if "option src 'lab'" in section:
                self.assertIn("option dest_port '67'", section)
                self.assertNotIn("option dest '", section)
        self.assertNotIn("family 'ipv6'", text)

    def test_online_rule_follows_destination_denial(self):
        self.config["relay_internet_https"] = True
        text = generate(self.config)
        self.assertLess(text.index("relay_protected_destinations"), text.index("relay_public_https"))
        section = text.split("config rule 'relay_public_https'")[1]
        self.assertIn("option src_ip '10.78.10.2'", section)
        self.assertIn("option proto 'tcp'", section)
        self.assertIn("option dest_port '443'", section)
        self.assertIn("option family 'ipv4'", section)

    def test_unsafe_inputs_rejected(self):
        mutations = [
            ("relay_cidr", "10.77.10.0/24"),
            ("lab_cidr", "0.0.0.0/0"),
            ("lab_cidr", "fd00::/64"),
            ("relay_ip", "10.78.10.1"),
            ("relay_ip", "10.78.10.2'\nconfig forwarding"),
            ("management_host", "10.77.10.2"),
            ("relay_ip", 173673474),
            ("protected_home_cidrs", []),
            ("protected_home_cidrs", [3232248320]),
            ("protected_home_cidrs", ["10.77.10.0/24"]),
            ("relay_internet_https", "false"),
            ("target_services", [{"address":"10.77.10.30","tcp_port":True}]),
            ("target_services", ["invalid"]),
            ("target_services", [{"address":"192.168.50.1","tcp_port":80}]),
        ]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                config = copy.deepcopy(self.config)
                config[key] = value
                with self.assertRaises((ValueError, TypeError)):
                    generate(config)


if __name__ == "__main__":
    unittest.main()

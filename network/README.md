# Network workshop

Start with an isolated, offline bench. Add a trusted firewall before connecting experimental equipment to a household network. Add a private tunnel only after the isolation checks pass.

This folder contains public instructions and synthetic examples. Its addresses describe a plan, not any participant's actual network. Copy templates into a private working folder before filling in real addresses, keys, names or account details.

| Goal | Architecture | Additional requirements |
|---|---|---|
| Learn Wi-Fi, HTTP and Arduino serial | Offline bench | Experimental access point, separate test computer; no home uplink |
| Share a Pico web exercise remotely | Dedicated firewall and trusted relay | Supported firewall with separate networks; Linux relay |
| Use one router for home and lab | One capable firewall with independent zones | Verified port/VLAN and firewall support; household gateway remains trusted |
| Share a Linux target directly over VPN | Host VPN inside a contained segment | Linux board/PC, restricted VPN policy, explicitly reviewed Internet egress |
| Host games | Separate service segment and host VPN | Suitable Linux/PC server; game software and sufficient resources |
| Experiment with router firmware/exploits | Experimental router downstream of containment | Separate trusted firewall, or completely offline bench |

The number of boxes is secondary. A router combining a home network with a correctly isolated lab can be sufficient. A basic home router followed by a second router with its default settings can still allow lab devices to reach the household. A router being attacked cannot also be the only device responsible for containment.

Read in this order:

1. [Architectures and networking vocabulary](ARCHITECTURES.md).
2. [Build the dedicated OpenWrt boundary](OPENWRT.md).
3. [Connect participants through a private tunnel](REMOTE-ACCESS.md).
4. [Verify isolation and run a session](VALIDATION.md).
5. [WireGuard alternative](wireguard/README.md), when endpoint routing is understood.

Code entry points:

```bash
# From the public repository root; this only prints a candidate firewall.
python3 network/generate_firewall.py network/site.example.json
python3 -m unittest discover -s network -p 'test_*.py'
```

The generator cannot identify physical ports, configure a switch, validate a router model or prove that a deployed network is isolated. Hardware checks and the validation procedure are required before enabling access. The supplied profile intentionally keeps targets offline; HTTPS Internet access for the trusted relay starts disabled.

Software references were checked on **2026-09-11**. Hardware-specific firmware and installed versions must be checked at deployment. Some OpenWrt documentation pages returned a browser challenge; indexed official documentation and the official firewall4 source were used together.

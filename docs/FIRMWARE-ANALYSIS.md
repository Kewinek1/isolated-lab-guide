# Router firmware analysis

Firmware analysis begins with a copy of a file, not a public-facing router. The intended target is an owned experimental device on the offline island. A discovered string, open port or old component version is a lead to investigate; it is not proof of an exploitable vulnerability.

## 1 · Identify and preserve

Record the exact manufacturer, model, hardware revision, regional variant, installed firmware build and power supply in the private inventory. Record a factory-reset procedure and a proven recovery route before any write to flash storage. An exported settings backup is not necessarily a complete firmware/bootloader backup.

Obtain the relevant firmware from the manufacturer's official support page for that exact revision and region. Preserve the downloaded archive unchanged, record its source and date, and compare a publisher checksum/signature when available. A locally computed SHA-256 hash records identity and detects later changes; without a trusted comparison value it does not independently establish authenticity. TP-Link specifies matching hardware and purchase region for firmware selection. [TP-Link firmware update guidance](https://www.tp-link.com/us/support/faq/2796/)

Keep stock firmware, an extracted working copy and notes in separate private directories. Vendor GPL source releases can help explain components, but may not correspond exactly to the shipped binary. Do not publish proprietary firmware bundles or private configuration dumps as part of the teaching repository.

## 2 · Static inspection

Use a disposable offline analysis VM with a snapshot, no home network adapter, no shared home folder and an unprivileged account. Treat firmware files and archive metadata as untrusted inputs to analysis tools.

```bash
sha256sum /ABSOLUTE/PRIVATE/PATH/firmware.bin
file /ABSOLUTE/PRIVATE/PATH/firmware.bin
strings -a -n 8 /ABSOLUTE/PRIVATE/PATH/firmware.bin > /ABSOLUTE/PRIVATE/PATH/strings.txt
```

Replace the uppercase paths with local absolute paths before running. These commands inspect the file and produce a text inventory; they do not execute the firmware. Analyze the text with searches for boot messages, filesystem markers, version labels and service names. A lack of strings can indicate compression or encryption, not an empty firmware image.

The repository also supplies a bounded read-only inspector. From the public repository root, after replacing the paths:

```bash
python3 tools/inspect_firmware.py /ABSOLUTE/PRIVATE/PATH/firmware.bin --output /ABSOLUTE/PRIVATE/PATH/firmware-report.json
```

It computes a hash and reports limited header/string information without extraction, execution or network access. Its new output file must be outside the public tree. Reports can contain embedded secrets or identifying strings and remain private.

Filesystem identification/extraction tools such as Binwalk are optional later tools. Check their current official documentation and installed version before selecting flags. Run extraction inside the disposable VM as an ordinary user, set disk/memory limits, and inspect resulting paths and symlinks. Never execute extracted binaries or init scripts on a trusted workstation, and never run unknown firmware with root privileges merely to satisfy an extraction helper.

A useful first report lists candidate CPU architecture, containers/filesystems, services, configuration paths and evidence offsets. Candidate credentials stay private and are not tried against unrelated equipment. Version-based findings are confirmed against exact build behavior and vendor advisories before being treated as vulnerabilities.

## 3 · Observe an owned router

Connect a lab-only computer to the experimental router with its WAN disconnected and all wireless uplinks disabled. Confirm the exact target address from the local configuration. Inventory a small documented set of TCP ports on this single owned target; broad subnet or public scans are unnecessary for the first exercise. An open port means a listener answered, not that authentication is absent.

Record port, observed protocol, banner if offered, required authentication and firmware build. Compare behavior before and after one controlled configuration change. Preserve a stock baseline so a later test can distinguish a vulnerability from an intentionally changed setting. Subsequent exploit work needs a specific confirmed target/build and reproducible behavior; no generic “root every router” step exists.

With Nmap installed from the analysis operating system's maintained package source, this first inventory uses TCP connect scanning of four ports on one confirmed offline router. Run it on the isolated bench after replacing the placeholder:

```bash
ROUTER_LAB_IP='REPLACE_WITH_CONFIRMED_OFFLINE_ROUTER_IP'
nmap -sT -Pn -n -p 22,23,80,443 --max-retries 1 --host-timeout 20s "$ROUTER_LAB_IP"
```

`-sT` uses ordinary TCP connections and does not need a privileged raw-packet scan. `-Pn` skips discovery and assumes the specified target is present; `-n` disables DNS lookups. A timeout or filtered result alone does not prove isolation. No exploit scripts, broad port range or entire subnet is selected here. [Nmap TCP scan methods](https://nmap.org/book/man-port-scanning-techniques.html), [Nmap host-discovery options](https://nmap.org/book/man-host-discovery.html)

The restricted SSH relay carries only approved TCP services. It is not an arbitrary remote scan route. Ethernet discovery, ARP and local Wi-Fi capture stay within a site's local link; a routed VPN does not extend that radio or Ethernet segment. Broader remote experiments require a separate approved target/route policy and repeated containment tests.

## 4 · Serial console, only after identification

A router's internal UART may use 3.3 V, 1.8 V or another logic level. A real RS-232 interface uses different electrical signaling and must not be connected directly to a TTL UART. The exact pinout and voltage are established from device documentation and appropriate measurement before wiring. [OpenWrt serial console](https://openwrt.org/docs/techref/hardware/port.serial)

Use a matching USB-to-UART adapter. Normally the router uses its own power supply; ground, transmit and receive connect only after the pinout and levels are verified. Do not assume an exposed header is serial, connect its power pin, or use the Uno's 5 V output as a safe substitute. Serial access may expose a boot log without granting a shell. A console login, authenticated administrative shell, bootloader access and an exploited root shell are different findings.

## 5 · Installation is a separate decision

| System | Intended platform | Decision |
|---|---|---|
| OpenWrt | Specific supported embedded devices and other supported targets | Follow the exact model/revision device page and image type |
| pfSense | Compatible x86_64 systems and supported Netgate appliances | The general installer is not router firmware for an arbitrary ARM/MIPS device |
| OPNsense | Supported x86_64 PC/appliance hardware | Check architecture, NIC support, storage and resource needs |
| Linux Raspberry Pi gateway | Suitable Linux Raspberry Pi board and network interfaces | Possible router/gateway project; distinct from Pico W and not generic pfSense hardware |

Current pfSense guidance lists amd64/x86_64, at least 1 GB RAM, 8 GB storage and compatible network interfaces for general third-party hardware, while explicitly excluding arbitrary Raspberry Pi/non-Netgate ARM systems. These are installation minima, not throughput promises. [pfSense requirements](https://docs.netgate.com/pfsense/en/latest/hardware/minimum-requirements.html), [pfSense architecture support](https://docs.netgate.com/pfsense/en/latest/hardware/)

OPNsense's official platform is x86_64; its recommended sizing is higher than its basic/minimum configuration. Select resources for the actual VPN throughput and enabled features. [OPNsense hardware guidance](https://docs.opnsense.org/manual/hardware.html)

The proposed small firewall computer must be identified before assigning software or ports. Case colour is insufficient. No flashing command is justified without the exact hardware revision and documented recovery method.

## Reverse proxy, tunnel and DMZ are different jobs

A **reverse proxy** receives an application request and forwards it to a backend service. An HTTP reverse proxy can terminate TLS and apply application authentication. It does not generally carry arbitrary port scans, all TCP/UDP protocols, or Factorio UDP unless the selected product explicitly supports that transport. A public proxy also makes the backend application reachable through a public entry point.

A **VPN** creates a private network path. A **firewall** limits permitted traffic. A **real DMZ** places services in a separately filtered network. Connecting an experimental router's WAN to a main router's LAN creates an upstream connection, not automatically a DMZ. These components can be combined, but none of their names substitutes for tested isolation.

Public exposure is a later mode for a patched service in the services zone. Intentionally vulnerable firmware remains on the offline island or behind an independent boundary with narrowly approved private access. The initial firmware project needs neither a public address nor a reverse proxy.

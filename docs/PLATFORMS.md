# pfSense, OPNsense and OpenWrt

All three can turn compatible equipment into a router and firewall. Their job in this lab is the same: keep home, management, relay, targets and services separated, then permit a small set of intentional connections. The best choice depends on supported hardware, a maintained release and an understandable operating procedure. The product name alone does not establish a secure configuration.

## Software first, equipment second

An **operating system** controls the hardware and runs services. A firewall distribution packages that operating system with network configuration, firewall rules and administration tools. It can arrive preinstalled on an appliance, or be installed on compatible equipment. The red case in an equipment photograph is an enclosure; it does not identify the operating system inside it.

| Question | pfSense | OPNsense | OpenWrt |
|---|---|---|---|
| Underlying operating system | FreeBSD-based firewall distribution | FreeBSD-based firewall distribution | Linux distribution, commonly used on embedded routers |
| Typical installation | Compatible x86_64 PC/appliance; supported Netgate hardware | Compatible x86_64 PC/appliance | Exact supported router/board revision, or supported x86 target |
| Main administration style | Web interface with interface rules, aliases and packages | Web interface with interface rules, aliases and plugins | LuCI web interface plus UCI configuration files and commands |
| Hardware discovery that matters | CPU architecture, supported NICs, RAM/storage and installer support | CPU architecture, supported NICs, RAM/storage and installer support | Exact board and hardware revision, flash/RAM, switch and radio support |
| Update approach | Product-specific update workflow; CE and Plus are distinct editions | Firmware/update workflow with its own release and plugin repositories | Device-specific firmware upgrades; Attended Sysupgrade where supported |
| Fit for this handbook | PC/appliance firewall before home, or dedicated lab firewall | Same topology options with OPNsense-specific controls | Supplied strict firewall candidate on compatible dedicated equipment |

The projects document their platforms separately: [pfSense hardware](https://docs.netgate.com/pfsense/en/latest/hardware/), [OPNsense hardware](https://docs.opnsense.org/manual/hardware.html), [OpenWrt overview](https://openwrt.org/docs/start). OPNsense describes its FreeBSD-based system in its [documentation overview](https://docs.opnsense.org/index.html).

### pfSense

pfSense Community Edition, **CE**, is the open-source edition. **Plus** is a distinct Netgate product with additional capabilities and its own release schedule and entitlement/support terms. A Plus-only feature in a guide must not be assumed present in CE. Check the selected edition before following menus or an upgrade procedure. [Netgate CE/Plus distinction](https://docs.netgate.com/pfsense/en/latest/general/plus.html)

Netgate documents compatible x86_64 third-party hardware and supported Netgate ARM appliances. It explicitly excludes ordinary Raspberry Pi and other arbitrary non-Netgate ARM boards. A working USB/Ethernet connector is therefore insufficient evidence that a generic pfSense image can boot a device. [pfSense architecture support](https://docs.netgate.com/pfsense/en/latest/hardware/)

The package manager extends the base system. Package availability and maintenance vary, including software developed by Netgate and by the community. Check the installed platform's package catalogue and retain only packages needed for the selected role. [pfSense packages](https://docs.netgate.com/pfsense/en/latest/packages/index.html)

### OPNsense

OPNsense is a separate project with its own interface, configuration development and plugin ecosystem. Similar firewall concepts do not make pfSense configuration backups or packages interchangeable with it. Its official general hardware guidance specifies x86_64 and gives resource levels for different feature sets. It does not establish support for a generic Raspberry Pi image. [OPNsense hardware sizing](https://docs.opnsense.org/manual/hardware.html)

Its System → Firmware workflow manages the selected update source and available plugins. Community and Business release choices have different purposes; the chosen edition's documentation and support terms determine the appropriate update path. [OPNsense firmware management](https://docs.opnsense.org/manual/firmware.html)

### OpenWrt

OpenWrt often suits equipment with integrated Ethernet switching and Wi-Fi radios, provided the **exact hardware revision** is supported. A supported product family does not guarantee every similarly named revision works. Old hardware may run an old release while lacking a maintained secure release; that is a reason to assign it to the target side.

The supplied generator writes OpenWrt UCI firewall configuration. Modern OpenWrt uses firewall4 with nftables; LuCI edits the corresponding configuration. This file cannot be imported into pfSense or OPNsense. The policy can be translated, but each platform requires its own implementation and verification. [OpenWrt firewall configuration](https://openwrt.org/docs/guide-user/firewall/firewall_configuration)

## Updates and recovery

| Platform | Documented cadence/workflow | Lab operating decision |
|---|---|---|
| pfSense CE / Plus | CE releases when ready; Plus typically targets three releases per year | Follow the actual edition's supported release and upgrade notes |
| OPNsense | Two major releases yearly, with minor updates approximately every two weeks | Plan regular maintenance and verify required plugins after upgrades |
| OpenWrt | Firmware release upgrades matched to the device; supported Attended Sysupgrade can include installed packages | Read model-specific changes and preserve a working recovery route |

Cadence is a maintenance fact, not a security ranking. Release availability does not promise that a particular NIC, plugin or older appliance remains supported. [pfSense release schedule](https://docs.netgate.com/pfsense/en/latest/development/release-schedule.html), [OPNsense update schedule](https://docs.opnsense.org/manual/updates.html), [OpenWrt release notes](https://github.com/openwrt/openwrt/releases)

OpenWrt 25.12 and newer use `apk`, while older instructions may use `opkg`. Its documentation recommends a coherent firmware upgrade rather than blindly upgrading every package in place. Commands must match the installed release. [OpenWrt package-management guidance](https://openwrt.org/docs/guide-user/additional-software/apk)

Before an upgrade, save configuration privately, identify the exact recovery image/method and retain a local management connection. Afterward, test the intended allow and deny paths, persistence after reboot and any optional plugin. An edge firewall also carries household internet, so its maintenance needs a planned household outage window and a physical rollback path.

## CrowdSec in the proposed layouts

**CrowdSec** analyzes selected logs and produces decisions about suspicious activity. A **remediation component**, sometimes called a bouncer, uses those decisions to block traffic. Detection and enforcement are distinct parts. Without the right logs, decisions and enforcement integration, installing an agent does not establish that unwanted traffic is blocked. [CrowdSec Security Engine](https://docs.crowdsec.net/security-engine/)

| Platform | Status checked for this guide | Consequence |
|---|---|---|
| OPNsense | `os-crowdsec` is available through official repositories | Use the documented plugin path and verify compatibility with the selected release |
| pfSense | CrowdSec's integration is supplied outside the official pfSense repositories and requires manual installation | It is an additional third-party integration, not an assumed standard Netgate package |
| OpenWrt | No CrowdSec deployment is supplied here | Retain the baseline firewall policy; any later integration needs its own resource/support review |

These distinctions come from the publisher's current [OPNsense installation guide](https://docs.crowdsec.net/u/getting_started/installation/opnsense/) and [pfSense installation guide](https://docs.crowdsec.net/docs/getting_started/install_crowdsec_pfsense/). The pfSense guide also notes additional backup/reconfiguration work and possible reinstall needs after major upgrades. Plugin availability can change; verify it again before installation.

CrowdSec stays optional in this lab. It does not create zones, replace a firewall deny rule, encrypt a connection, or contain a compromised router. Its detections can also interfere with an intentionally authorized exercise, so monitoring policy and temporary exceptions must be explicit. Data sharing, local/private-address exclusions and log retention are reviewed before enabling it; synthetic lesson traffic should not accidentally become an external incident report.

## Interpreting the Pi and Docker part of the diagrams

A Docker **image** packages an application and its dependencies. A **container** is a running instance. On a Linux host, those containers share the host kernel. A **virtual machine** has its own guest kernel. Container names, separate images or different Docker networks do not give each target a separate computer's trust boundary. [Docker containers and VMs](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/)

For intentionally vulnerable services, use a disposable dedicated target host, or a reviewed VM arrangement with separate virtual networks. Keep gateway authority, home files, game saves and backup mounts away from that target environment. Do not grant a target container privileged mode, the host network namespace or access to the Docker socket as a shortcut. The external trusted firewall still contains the entire target host. [Docker security model](https://docs.docker.com/engine/security/)

Three VLAN lines drawn above a Pi require actual implementation. A direct tagged link needs matching VLAN interfaces and host/VM/container networking. Distributing tagged networks to several devices requires a suitably configured managed switch, or separate physical interfaces for each segment. An unmanaged switch cannot configure the required VLAN access-port boundaries. Merely choosing three subnets on a host does not force container-to-container traffic through the external firewall. [OPNsense VLAN/trunk guide](https://docs.opnsense.org/manual/how-tos/vlan_and_lagg.html)

The Pi in these scenarios means a suitable **Linux Raspberry Pi computer**, not a Pico W. Container software must also match the host's CPU architecture; an amd64 game binary does not become native ARM software by placing it in a container. [Docker platform compatibility](https://docs.docker.com/build/building/multi-platform/)

## Select a topology separately

The **edge** scenario places the firewall before the home router and gives home its own filtered interface. The **split** scenario gives home and lab separate router WAN connections through an ISP handoff, when that service actually supports both. Either scenario can use an appropriate pfSense or OPNsense appliance; OpenWrt can also express the same policy on verified capable hardware.

Read [the architecture comparison](02-architectures.md) for the packet paths and [the pfSense/OPNsense implementation guide](../network/PFSENSE-OPNSENSE.md) for platform-specific setup. The offline island remains the initial default until the required hardware and handoff facts are known.

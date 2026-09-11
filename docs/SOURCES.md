# Primary sources and review notes

Technical references checked 2026-09-11. Release requirements and hardware support should be checked again at deployment. Architecture and acceptance procedures are this handbook's design recommendations; they do not certify any unidentified router.

| Source | Used for |
|---|---|
| [Arduino Uno Rev3](https://docs.arduino.cc/hardware/uno-rev3/) | Board capabilities and USB/I/O role |
| [Raspberry Pi Pico documentation](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html) | Microcontroller role and Pico W capabilities |
| [Raspberry Pi computer setup](https://www.raspberrypi.com/documentation/computers/getting-started.html) | Linux board setup, distinct from Pico |
| [OpenWrt network/firewall model](https://openwrt.org/docs/guide-user/firewall/fw3_network) | Interfaces, zones and VLAN relationships; conceptual page includes older fw3 terminology |
| [OpenWrt firewall documentation](https://openwrt.org/docs/guide-user/firewall/start) | Current firewall documentation entry point |
| [OpenWrt Table of Hardware](https://openwrt.org/toh/start) | Exact device lookup; no support claim made for unknown equipment |
| [OpenWrt firmware upgrade guide](https://openwrt.org/docs/guide-quick-start/sysupgrade.luci) | Device-specific image selection and installation/upgrade distinction |
| [TP-Link DMZ explanation](https://www.tp-link.com/us/support/faq/28/) | Consumer exposed-host feature versus a separate DMZ |
| [Tailscale access control](https://tailscale.com/docs/features/access-control) | Identity/destination permission model |
| [Tailscale subnet routers](https://tailscale.com/docs/features/subnet-routers) | Route advertisement, approval and subnet access |
| [Tailscale exit nodes](https://tailscale.com/docs/features/exit-nodes) | General internet routing versus selected subnet access |
| [Tailscale installation](https://tailscale.com/docs/install) | Supported installation entry point |
| [Minecraft Java server](https://www.minecraft.net/en-us/download/server) | Official server acquisition and Java Edition scope |
| [Minecraft Java 26.1](https://www.minecraft.net/en-us/article/minecraft-java-edition-26-1) | Java 25 requirement for that release |
| [Minecraft EULA](https://www.minecraft.net/en-us/eula) | Operator review and explicit acceptance |
| [Minecraft Bedrock server](https://www.minecraft.net/en-us/download/server/bedrock) | Separate server/platform workflow |
| [Factorio downloads](https://www.factorio.com/download) | Official headless package and checksums |
| [Factorio multiplayer](https://wiki.factorio.com/Multiplayer) | UDP port, version matching and headless operation |
| [Factorio command-line reference](https://wiki.factorio.com/Command_line_parameters) | Binding, save creation and explicit settings paths |
| [Wube server-settings example](https://raw.githubusercontent.com/wube/factorio-data/master/server-settings.example.json) | Visibility, verification and server password settings |
| [Minecraft 1.21.9](https://www.minecraft.net/pl-pl/article/minecraft-java-edition-1-21-9) | Server management protocol property; kept disabled in the launcher |
| [Tailscale status structure](https://github.com/tailscale/tailscale/blob/main/ipn/ipnstate/ipnstate.go) | Read-only local daemon state and assigned endpoint checks |
| [TP-Link firmware update guidance](https://www.tp-link.com/us/support/faq/2796/) | Hardware and region matching |
| [OpenWrt serial console](https://openwrt.org/docs/techref/hardware/port.serial) | UART pinout and voltage verification |
| [pfSense minimum requirements](https://docs.netgate.com/pfsense/en/latest/hardware/minimum-requirements.html) | Third-party x86_64 host minimum requirements |
| [pfSense architecture support](https://docs.netgate.com/pfsense/en/latest/hardware/) | Supported architectures and Raspberry Pi exclusion |
| [OPNsense hardware](https://docs.opnsense.org/manual/hardware.html) | x86_64 platform and resource sizing |

No third-party exploit guide, unverified firmware download or model guess is used as an installation authority. The included programs require local configuration and actual hardware verification before use.

# Hardware and build order

## Assign jobs before assigning cables

| Hardware class | Suitable job | Capability boundary |
|---|---|---|
| Classic Arduino Uno / Uno R3 | USB serial commands, LEDs, sensors, embedded input validation | ATmega328P microcontroller; no built-in Wi-Fi/Ethernet or Linux shell |
| Raspberry Pi Pico W | Small MicroPython/C programs and Wi-Fi lab services | Microcontroller, not a Linux Raspberry Pi; no Minecraft/Factorio or ordinary Tailscale daemon |
| Linux Raspberry Pi board | Linux target, small service, gateway with suitable interfaces | Different product from Pico W; model, memory, power, storage and workload must be checked |
| Linux x86_64 computer | VPN access gateway or game server | Keep gateway and intentionally vulnerable target roles separate |
| Experimental router | Router configuration and vulnerability target | Never the sole trusted boundary during router compromise exercises |
| Supported trusted firewall/router | Enforces zone separation | Requires maintained firmware, independent interfaces/zones and a recovery method |

The Uno Rev3 provides USB connectivity and digital/analog I/O around an ATmega328P. A serial monitor sends bytes to the program; it does not turn the board into a Unix terminal. Networking requires extra hardware and a suitable library. [Arduino Uno Rev3](https://docs.arduino.cc/hardware/uno-rev3/)

The Pico W adds wireless connectivity to a microcontroller board. It runs embedded firmware and is programmed separately from Linux Raspberry Pi computers. USB serial provides a convenient programming and observation path. [Raspberry Pi Pico documentation](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html)

For the introductory firmware, USB power and the built-in LED are sufficient. Classic Uno I/O operates at 5 V; Pico GPIO is a 3.3 V interface. Directly connecting a 5 V Uno output to Pico GPIO is outside the supplied wiring plan. Any later board-to-board circuit needs the correct level conversion, common ground and a reviewed pinout.

## Minimum equipment by stage

| Stage | Equipment |
|---|---|
| Offline serial | Lab computer, USB data cable, Uno; Pico W optional |
| Offline network | Lab computer, isolated router/access point, Pico W or Linux target |
| Remote target exercises | Above, plus tested trusted boundary and an always-on Linux access gateway |
| Private game server | Trusted services segment and suitably sized Linux computer; x86_64 for the supplied Factorio workflow |
| VLAN expansion | VLAN-capable firewall and any intermediate switch/access point carrying multiple zones |

An old computer can fill the Linux role; no purchase is implied before its capabilities are assessed. A network adapter adds an interface, but separate interfaces still need correct routing and firewall rules. Linux installation guidance is available in the [Raspberry Pi computer getting-started documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html).

## Commission in small steps

1. Record model, exact hardware revision, firmware version, port labels and power requirements privately. A photograph's colour is insufficient to identify a router or establish OpenWrt support.
2. Export router settings and record a local recovery method. Disconnect experimental equipment from the home before changing it.
3. Run the USB serial exercise. Confirm a command reaches the board and its response returns. No network is needed.
4. Build the offline island. Confirm the lab computer has only the intended lab network path.
5. Assign the local target subnet and DHCP pool. Test one harmless request to one target.
6. Choose the trusted isolation architecture. Configure the boundary before attaching the home uplink. Retain a physical administration/recovery path.
7. Execute the acceptance matrix with benign test hosts. Treat an inconclusive negative test as unresolved.
8. Establish remote access to one target and one permitted port. Record an allowed result and a denied result before broadening scope.
9. Add services on their own zone. Run game servers only after service-to-home and target-to-service denials pass.

## Receiving another router or firewall

Incoming equipment begins on the offline island. Existing firmware, configuration, credentials and storage are untrusted. Record the exact model and revision, obtain the manufacturer's reset/recovery procedure, reset or reinstall supported firmware, update it, replace credentials and test every physical port assignment. Personal settings from the previous installation are not reused.

**OpenWrt is firmware, not a feature that can be enabled on every router.** Check the exact device and hardware revision in the [OpenWrt Table of Hardware](https://openwrt.org/toh/start), then follow that device's installation page. Factory installation and upgrades of existing OpenWrt can use different image types; generic flashing commands are intentionally absent. [OpenWrt upgrade and installation distinction](https://openwrt.org/docs/guide-quick-start/sysupgrade.luci)

If supported, configure its roles offline and repeat the same acceptance tests before replacing any working boundary. If unsupported or no longer maintained, assign it to the target side. A more capable device can become the trusted firewall only after its exact capabilities and configuration have been verified.

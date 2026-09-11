# Build the dedicated firewall

This recipe is for a **dedicated, maintained OpenWrt firewall using firewall4**, with physical recovery access. It replaces that appliance's firewall configuration. It is not a firmware flashing guide and must not be applied to a household gateway that also serves everyday devices.

## Check the hardware before configuration

Record the exact model, hardware revision, flash/RAM, processor architecture, port count and existing firmware privately. Look up the exact revision in the [OpenWrt Table of Hardware](https://openwrt.org/toh/start) and its device installation page. Similar cases and colors do not establish compatibility. Small legacy 4 MB flash/32 MB RAM devices are unsuitable as a current maintained security boundary; an unsupported experimental router stays downstream or offline. [OpenWrt warning about 4/32 devices](https://openwrt.org/supported_devices/432_warning).

Confirm a supported release, firewall4 availability, power supply, backup method and recovery method. No firmware filename can safely be chosen from a generic architecture diagram. An x86 appliance may use a disk image; an embedded router may require a board-specific factory image. These are not interchangeable.

## Prepare the clean equipment

1. Update the trusted firewall and clean Linux relay before introducing vulnerable software. Download packages and images from their official sources. Give the relay a separate administration account and keep personal files off it.
2. Disconnect the firewall uplink and all target cables during network reconfiguration. Connect only the management computer. Keep a local console or documented recovery method available. Save the current network, DHCP and firewall backups in private storage.
3. Disable automatic port mapping (UPnP/NAT-PMP/PCP), public remote administration, mesh/repeater uplinks and unnecessary services. The trusted firewall runs no target application, container runtime or VPN subnet router.
4. Identify ports using the device documentation and a one-cable-at-a-time link test. On OpenWrt, `ip link show`, `ubus call system board`, and LuCI's device view help identify interfaces. Outputs may contain identifiers and remain private.

## Create four isolated interfaces in LuCI

Use **Network → Interfaces → Devices** to separate physical ports from the default LAN bridge. A device/port assigned to `lab` must not also remain in the management or uplink bridge. With a supported DSA switch, a dedicated bridge per group of ports or correctly filtered VLAN interfaces can implement the separation; the exact device names are board-specific. [OpenWrt DSA mini tutorial](https://openwrt.org/docs/guide-user/network/dsa/dsa-mini-tutorial).

Under **Network → Interfaces**, create these logical interface names exactly. Site A addresses are examples:

| Interface name | Protocol | Address | Connected equipment |
|---|---|---|---|
| `uplink` | DHCP client, IPv4 | Supplied by the household router | Household LAN port |
| `mgmt` | Static IPv4 | `10.79.10.1/24` | Management computer `.2` |
| `relay` | Static IPv4 | `10.78.10.1/24` | Clean Linux relay `.2` |
| `lab` | Static IPv4 | `10.77.10.1/24` | Target access point / targets |

Set the management computer manually to `10.79.10.2/24`; no default gateway or DNS is needed for local administration. Keep management Wi-Fi and other adapters disconnected during setup. There is only one IPv4 default route on the firewall: through `uplink`. The static internal interfaces have no upstream gateway field.

For `lab`, `relay` and `mgmt`, set IPv6 assignment length to disabled/none. In each interface's DHCP IPv6 settings, disable Router Advertisement, DHCPv6 and NDP proxy services. Remove/disable any automatically created upstream `wan6` interface and IPv6 prefix delegation for this IPv4 baseline. Do not put upstream and lab ports in one bridge. Retain the host OS's local IPv6 support for the VPN; this procedure concerns routed physical networks.

Enable IPv4 DHCP pools `.100`–`.149` if needed. Keep fixed roles outside those pools. The relay can use static `10.78.10.2/24`, gateway and DNS `10.78.10.1`. A target uses gateway `10.77.10.1`; the lab is intentionally denied DNS, so target tests use numeric addresses. The supplied Pico firmware uses DHCP: create a reservation for `.30` and reconnect it before testing that address. Reservations use real MAC addresses and belong only in private configuration. The firewall generator does not create DHCP services or reservations.

On the experimental access point: use a unique lab SSID/password, disable its DHCP server, give its management interface an unused lab address such as `.3`, connect a LAN socket to the firewall's lab port, and leave its WAN empty. Avoid default home subnet addresses. The access point is an attack target; the upstream firewall remains the boundary.

Configure SSH and, if installed, LuCI HTTPS on the trusted firewall. The candidate allows administration from the fixed management workstation to TCP 22/443 only. Plain LuCI HTTP on TCP 80 will stop working after activation; use SSH or install/configure HTTPS first.

## Generate and inspect a candidate

On the workstation, copy `site.example.json` to a private directory outside the public export. Replace its home subnet with the actual upstream subnet and add every protected household IPv4 network. Record any externally reachable household IPv4 address under `protected_external_cidrs`; a connection to a household public address could otherwise return through NAT reflection or another public path. Include every household public endpoint that must remain unreachable. Dynamic addresses require updating these entries; disconnect the relay's Internet access if the inventory is uncertain. IPv6 routed forwarding is denied separately.

Leave `relay_internet_https` as `false` for initial tests. By default only Pico TCP 8080 is reachable from the relay. To add the supplied Linux web target, add `{"address":"10.77.10.20","tcp_port":8081}` to `target_services` and also retain the matching SSH `PermitOpen` entry. Do not add a subnet or all-ports forwarding rule.

```bash
# Run from the public repository root. Paths point outside the public export.
python3 network/generate_firewall.py /path/to/private/site.json \
  --output /path/to/private/firewall.candidate
```

The script creates a new mode-0600 file and refuses to overwrite one. It validates subnet separation and individual target services, then writes a **complete** `/etc/config/firewall` candidate. It never logs in to a router, modifies the network, or applies rules. Do not append it to an old configuration: existing broad rules would remain effective.

Its zone policies reject input and forwarding, with explicit exceptions. The relay's public HTTPS exception, when enabled, comes after protected-address rejections. Automatic firewall includes and flow offloading are disabled to keep the reference behavior inspectable. Other packages or custom nftables rules can still alter behavior; use a dedicated clean appliance and inspect the final ruleset. [OpenWrt firewall configuration](https://openwrt.org/docs/guide-user/firewall/firewall_configuration), [official firewall4 implementation](https://github.com/openwrt/firewall4).

## Stage, check and activate locally

Transfer the candidate to the firewall through the management connection:

```bash
scp /path/to/private/firewall.candidate root@10.79.10.1:/tmp/firewall.candidate
```

On the firewall, keep uplink and targets disconnected. The first commands inspect UCI syntax without modifying the running firewall:

```sh
mkdir -p /tmp/lab-firewall-check
cp /tmp/firewall.candidate /tmp/lab-firewall-check/firewall
uci -c /tmp/lab-firewall-check show firewall
cp /etc/config/firewall /root/firewall.before-lab
```

Review the output and verify that all four interfaces exist and map to distinct networks. The following step changes the persistent configuration, checks the compiled nftables rules, and reloads only if that check succeeds:

```sh
cp /tmp/firewall.candidate /etc/config/firewall
if fw4 check; then
    /etc/init.d/firewall restart
else
    cp /root/firewall.before-lab /etc/config/firewall
    echo 'Candidate rejected; original persistent configuration restored.'
fi
```

`fw4 check` checks the compiled rules without applying them. It cannot prove cable isolation or correct interface assignment. Treat unknown-option warnings, missing-interface warnings or restart errors as a failed deployment, even if a command returns zero. [Official firewall4 check implementation](https://github.com/openwrt/firewall4/blob/master/root/sbin/fw4).

Open a second SSH session from the management port before closing the first. Inspect:

```sh
fw4 network lab
fw4 network relay
fw4 network mgmt
fw4 network uplink
fw4 print
nft list ruleset
```

Each lookup must return its matching zone. A zone lookup does not replace checking the actual port/VLAN membership. Reboot while uplink and targets are still disconnected; this also removes stale connection state from an earlier permissive setup. Recheck administration after boot, connect the clean test devices, and complete [validation](VALIDATION.md) before introducing vulnerable targets.

To recover through the local console/management path, while upstream and targets are unplugged:

```sh
cp /root/firewall.before-lab /etc/config/firewall
fw4 check
/etc/init.d/firewall restart
```

If network-interface edits caused the loss of access, restoring only the firewall is insufficient; restore the saved network/DHCP configuration through the device's documented recovery method.

## Enable the remote relay

After the offline isolation checks pass, change the private profile's `relay_internet_https` to `true`, generate a new candidate filename, and repeat inspection and activation. Then connect the uplink and install/configure the VPN on the relay as described in [remote access](REMOTE-ACCESS.md).

The profile permits relay TCP 443 to public destinations and DNS to the trusted firewall. This supports Tailscale's encrypted relay fallback and HTTPS downloads. It does not allow arbitrary public UDP or inbound port forwards, so direct VPN paths and game latency may be worse than a less restricted design. Tailscale can fall back to relays when direct paths fail; TCP 80 is optional, while TCP 443 is used by coordination and relays. [Tailscale firewall requirements](https://tailscale.com/docs/reference/faq/firewall-ports).

The relay also needs an accurate clock for TLS. Set its clock locally during provisioning or configure a separately reviewed time-sync path; this profile does not permit public UDP NTP. OS repositories using HTTP will need HTTPS repository URLs or an offline maintenance workflow. These failures are resolved explicitly, not by enabling a blanket relay-to-WAN forwarding rule.

For a direct Linux-target VPN or a separate game server, build a distinct target/service zone and review its egress and target identity lifecycle. This candidate deliberately implements the stricter relay architecture; it does not silently enable target Internet access.

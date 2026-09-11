# Architecture choices

The number of routers is less important than where the trusted boundary sits. This design assumes that the target can eventually gain full control of its own operating system or experimental router. Home devices, firewall management and game saves remain outside that scope.

## Compare the options

| Scenario | Required capability | Good fit | Main limitation |
|---|---|---|---|
| Offline island | Lab-only switch/router and lab computer; no uplink | First exercises, router exploitation | No remote participants or internet |
| One trusted firewall with separate zones | Independent physical interfaces or correctly configured VLANs; IPv4/IPv6 policy | Long-term home, targets and services separation | Misconfiguration of the shared firewall affects all zones |
| Existing home router plus dedicated trusted lab firewall | Lab firewall with enforced target-to-upstream restrictions; independent target equipment | Retaining an existing home router | The home is on the upstream side and must be explicitly protected |
| Edge firewall before the home router (`edge`) | Trusted firewall with a separately filtered HOME interface and independent lab roles | Central control of home and lab paths | It becomes part of household internet; configuration/maintenance affects both |
| Parallel WAN connections (`split`) | ISP handoff explicitly supporting two simultaneous router connections; WAN-only switch | Independent home and lab router WANs | Provider approval/address delivery is required; the shared WAN link remains untrusted |
| Verified isolated guest network as uplink | Guest network blocking main LAN and management on both IP families; suitable wired or Wi-Fi attachment | Low equipment count after capability testing | Many guest features isolate wireless clients only or still permit router management |
| Ordinary second NAT router | Default consumer router configuration | Routing demonstrations | Does not provide the required target-to-home boundary |
| Public port forward into a real services DMZ | Real separated subnet and reviewed ingress/egress policy | Later public game hosting | Public attack surface and operational responsibilities increase |

A VPN is added to one of the isolated designs. It is not a competing replacement for a firewall or VLAN.

The [platform comparison](PLATFORMS.md) explains pfSense, OPNsense and OpenWrt. A topology describes where equipment connects; a platform describes the software enforcing its rules. The same diagram can be implemented on different supported platforms, but their configuration files are not interchangeable.

## A · Offline island

```mermaid
flowchart LR
  C[Lab-only computer] --> R[Experimental router or switch]
  R --> P[Linux target]
  R --> W[Pico W]
  C -->|USB serial| U[Arduino Uno]
```

The experimental router's WAN port remains unplugged. A lab computer has home Wi-Fi, tethering, internet sharing, bridging and other network interfaces disabled. The router has no wireless repeater, mesh or client uplink. USB connection to a trusted personal computer also crosses a boundary: use a disposable lab computer when experimenting with hostile firmware or USB behavior.

This is the starting architecture while router capabilities are unknown. Wi-Fi radio can still reach beyond a room; a detached WAN cable does not contain radio interference. Exercises use the lab's own access point and clients, low-impact traffic and a distinct lab SSID. Wired exercises make the boundaries easier to inspect.

## B · One trusted firewall, several zones

```mermaid
flowchart TB
  I[Internet] --> F[Trusted firewall]
  F --> H[Home · personal devices]
  F --> M[Management · administrator]
  F --> S[Services · game host]
  F --> T[Targets · disposable systems]
```

The firewall has a separate interface or VLAN for each zone. Home-to-target access is not automatically broad: only the administration path explicitly required for setup is allowed. Target-to-home, target-to-management and target-to-services initiation is denied. The firewall itself stays updated and is not an exploitation target.

One capable router can implement this. An unmanaged switch attached to one LAN port cannot create those four networks. Separate Wi-Fi names work only when each maps to an appropriately isolated network. Physical ports are easier to learn first; VLANs reduce cabling once port assignment and tagging are understood.

## C · Existing home router plus a trusted lab firewall

```mermaid
flowchart LR
  I[Internet] --> R[Home router]
  R --> H[Home devices]
  R -->|Upstream transport| F[Trusted lab firewall]
  F --> T[Targets]
  F --> S[Separate services interface]
```

The lab firewall's upstream interface sits beside home devices. Its policy must block lab-initiated traffic to the real home subnet, router management addresses, every other local subnet and any globally addressed local IPv6 prefixes. Internet access is restricted to deliberate needs such as a VPN transport and maintenance windows. DNS and time dependencies are explicitly assigned; they do not justify unrestricted access to the upstream network.

If the second router is the device being attacked, it cannot be the only lab firewall in this diagram. Its compromise removes its own rules and gives access to its upstream link. Two existing routers are enough only when the first independently isolates the second's uplink, or when the second remains trusted and separate hosts are the only targets. Otherwise, an independent firewall/isolated segment is needed, or the lab stays offline.

An attacker changing a target's static address must not bypass the boundary. That test catches designs which depend only on cooperative IP settings while sharing one Ethernet network.

## D · Why ordinary double NAT fails

```mermaid
flowchart LR
  T[Compromised lab target] --> N[Second router: default LAN-to-WAN allow]
  N --> H[Upstream home device]
```

The second router treats the home network as its WAN. Default LAN-to-WAN forwarding often permits a new connection from the target to a home address. NAT rewrites the source to the second router's WAN address, making the traffic look like it came from that router. The main router might never inspect this as internet traffic because both endpoints are on its LAN.

“Different IP range,” “behind another router” and “the internet cannot initiate a connection” therefore do not demonstrate the required protection. Testing both directions matters.

## E · The two meanings of DMZ

A **real DMZ** is a separate subnet with firewall rules between it, the internet and protected networks. A **DMZ host** menu on a consumer router commonly forwards otherwise unmatched inbound ports to one internal host. It does not move that host away from the home LAN. The vendor explicitly distinguishes this exposed-host feature from a true DMZ. [TP-Link DMZ explanation](https://www.tp-link.com/us/support/faq/28/)

The exposed-host option remains disabled for experiment targets. Later public game hosting belongs in the services zone, with only the exact game port forwarded and a tested services-to-home denial. Public hosting is a separate operating mode; the private overlay workflow needs no broad exposure.

## F · Edge firewall before the home router (`edge`)

![Edge architecture: a trusted firewall before the home router, with a separately filtered HOME connection and independent lab roles](../figures/edge.svg)

This is the corrected implementation of the layout with a firewall before a home router. The home router's **WAN** connects to its own HOME transit network. It does not share an interface or bridge with targets. The edge firewall explicitly denies targets, relay clients and services from initiating connections to HOME, home-router management and other protected destinations, including applicable IPv6 addresses and public aliases that route back home.

The home router may remain in router mode. In that case, IPv4 home traffic can pass through NAT on both devices; this is a double-NAT **home path**, with potential game/NAT-traversal implications. An alternative is a reviewed access-point conversion: its Wi-Fi and LAN join only the protected HOME zone, and the edge firewall becomes their gateway. That changes household addressing/services and is a separate configuration step.

“Closed firewall” means a reviewed ingress policy, not that no traffic can ever pass. A home router often allows connections initiated by home clients and their replies. Its WAN administration, port forwards, automatic mappings and IPv6 rules need review. The independent edge firewall provides the required lab-to-HOME denial even while ordinary home access works.

The example can require WAN plus five internal roles: HOME, management, relay, targets and services. Dedicated physical ports or correctly configured VLANs implement those roles. The sketch does not prove that the chosen appliance has enough ports, a managed switch, or a host with the necessary VLAN configuration.

This design makes the edge firewall part of the household's uptime and trust boundary. It remains maintained and outside exploitation scope. CrowdSec and a WireGuard VPN are optional additions after baseline isolation; neither changes that rule. Follow [the platform implementation procedure](../network/PFSENSE-OPNSENSE.md).

## G · Separate home and lab WANs (`split`)

![Split architecture: a provider-approved handoff and WAN-only switch connect separate home and lab router WAN interfaces](../figures/split.svg)

This is the corrected implementation of the two-branch drawing. The switch connects **WAN interfaces only** to the provider handoff. Home LAN sockets, target devices and management laptops do not attach to that switch. The two routers share the same untrusted upstream link; the switch itself performs no security filtering between them.

Two public addresses are available only if the provider supplies them in a compatible form. The service may allow multiple DHCP leases, separate authenticated sessions or a static allocation; it may also bind service to one device or permit only one session. A routed public block is a different delivery arrangement and does not necessarily place two usable leases on a switch. Record the provider's actual method, gateway, limits and IPv6 prefix behavior before choosing this scenario. [Netgate additional-public-address methods](https://docs.netgate.com/pfsense/en/latest/firewall/additional-ip-addresses.html)

If only one lease/session is supplied, adding a switch does not create another. If the handoff is an ordinary routed LAN instead, both downstream WANs may receive **private** addresses; that is a separate behind-router/double-NAT variant and does not demonstrate two public connections. Its upstream private subnet and any other attached trusted networks need explicit protection.

Separate public addresses do not prevent lab traffic from targeting the home router's public WAN. The lab firewall must block those home endpoints, protect its own management plane and constrain target egress. The home router separately denies unsolicited ingress, with no exposed administration or target forwards. Test both directions and both IP families. This architecture also depends on a trustworthy lab firewall: compromise of that firewall would put the shared WAN link itself within the attacker's reach.

An unmanaged switch is acceptable here only because its one purpose is extending the **untrusted WAN link**. This does not make it suitable for distributing multiple trusted/lab VLANs. Internal segmentation still uses dedicated interfaces or a configured managed switch and appropriate host networking.

## The policy to implement

| Initiator | Destination | Default decision | Narrow exception |
|---|---|---|---|
| Targets | Home and management | Deny | None |
| Targets | Services | Deny | None |
| Targets | Internet | Deny | Recorded maintenance dependency/window |
| Participants | Targets | Deny | Approved exercise address and ports |
| Participants | Game services | Deny | TCP 25565 and/or UDP 34197 |
| Participants | Firewall/gateway administration | Deny | Separate administrator identity, when required |
| Management | Lab administration | Deny | Required administration port and destination |
| Any zone | Previously allowed connection | Stateful reply handling | Does not permit an unrelated new connection |

Apply the same policy to IPv4 and IPv6. Keep UPnP/NAT-PMP automatic mappings and WAN administration disabled on the lab boundary. A consumer feature name is evidence of a possible capability, not acceptance evidence.

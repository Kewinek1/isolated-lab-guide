# Prove the intended paths

Configuration syntax checks are necessary, but they cannot establish isolation. Run this procedure before the first shared session, after each firewall/VLAN/firmware change, and after changing the household's address ranges.

## Prepare a small, observable test

Use a clean test computer in the lab segment with household adapters disconnected. Record the physical port/SSID, IPv4 address, IPv6 addresses and route table privately. Keep attack targets disconnected until the boundary passes.

```bash
ip address show
ip route show
ip -6 route show
```

For a meaningful denied-connection test, use a temporary known listener on a dedicated test host in the destination segment. First confirm the listener works from another authorized machine in that segment. Then attempt the same port from the lab and confirm the firewall rejected it. A timeout against a nonexistent service proves little. The household test uses a temporary consented test machine, not TVs, consoles or unrelated devices.

Example listener on an empty directory of a temporary test host:

```bash
mkdir -p /tmp/lab-boundary-probe
python3 -m http.server 8765 --bind 0.0.0.0 --directory /tmp/lab-boundary-probe
```

From the lab computer, use its actual destination address privately:

```bash
TEST_DESTINATION='REPLACE_WITH_CONSENTED_TEST_HOST'
curl --connect-timeout 3 --max-time 5 "http://${TEST_DESTINATION}:8765/"
```

Stop the temporary listener after the test. For IPv6, create a listener using `--bind ::`, use `curl -6` with `http://[IPv6-address]:8765/`, and repeat against a real routed destination when IPv6 is present. If the baseline has no IPv6 default route, record that fact and verify router IPv6 forwarding policies; do not claim an end-to-end IPv6 test passed when no route exists.

## Acceptance table

| Origin | Check | Expected result |
|---|---|---|
| Local management `.2` | Firewall HTTPS 443 and SSH 22 if explicitly enabled | Works; verify a second session after applying rules/restarting |
| Lab test computer | IPv4 address on correct lab subnet | Works via DHCP or static configuration |
| Lab test computer | Router administration on all its interface addresses | Denied |
| Lab test computer | Known listener on household test host | Denied |
| Lab test computer | Known listener on relay and management test host | Denied |
| Lab test computer | Public HTTPS request | Denied in the strict profile |
| Lab test computer | DNS to firewall and external DNS service | Denied in the strict profile |
| Lab test computer | Routed IPv6 toward home/relay/Internet | Denied; record no-route cases separately |
| Lab test computer | Another target on the same lab segment | May work; this is one exercise trust domain |
| Relay `.2` | Pico `http://10.77.10.30:8080/` | Works when target is running |
| Relay `.2` | Unapproved target TCP port | Denied when crossing the firewall |
| Relay `.2` | Household private addresses and protected public addresses | Denied |
| Relay `.2` | Public HTTPS | Works only after the explicit online setting |
| Enrolled client role | Forwarding account plus localhost web tunnel | Works |
| Enrolled client role | Relay shell via forwarding account | Denied |
| Enrolled client role | Target SSH or game-server SSH | Denied by policy |
| Target VPN role, if used | New connection to a peer's SSH | Denied by policy and active test |
| Unapproved VPN node | Target / relay access | Denied |
| External connection without VPN | Lab service | No configured public entry point |

Use a known service on a controlled public test endpoint for the outbound test where practical. The destination must be in the approved exercise scope; this procedure does not require scanning arbitrary networks. A deny result can be a firewall rejection or a silent timeout. Inspect the firewall counters and topology to distinguish an actual rule match from a wrong cable or route.

On the dedicated OpenWrt firewall:

```sh
nft list ruleset
logread
```

On pfSense or OPNsense, use the interface rules, automatic rules, logs and filtered state views in the selected GUI. Inspect both IP families, floating/group rules, the initial LAN allow-any rules and anti-lockout exception. A rule allowing replies through existing state is different from permitting a new connection. The [platform procedure](PFSENSE-OPNSENSE.md) specifies rule order and management recovery; do not run OpenWrt commands on those systems.

Record the rule that matched, the initiating segment, the actual destination and result. Keep that evidence private because addresses and device identities may be included. Public session reports retain role labels and outcomes only.

## Additional checks for edge and split-uplink designs

For the **edge firewall**, verify HOME_TRANSIT is separate from the actual household LAN and every lab role. The retained router's WAN receives its transit address; its LAN/Wi-Fi use the recorded household subnet. Before attaching targets, check household DNS, browsing, console sign-in and any application affected by double NAT. Record whether household IPv6 is separately configured or unavailable in the IPv4 baseline.

For a **split handoff**, establish provider permission for two simultaneous connections, then verify both router WANs work and renew while connected together. The switch contains only the ISP handoff and trusted WAN ports. A second temporary lease does not establish provider support, and a routed address block is not a promise of two DHCP leases.

For either design, test LAB denial to the household's actual LAN, router WAN and public endpoints. Also test relay/services denial to those endpoints, including when the household WAN is public or shares the same upstream Ethernet segment. Protect new/dynamic household addresses before continuing egress. Use a consented known listener rather than interpreting a timeout on a closed router-management port as proof.

Before changing the ISP cable, retain the original connection settings and cable path. Test the [documented rollback](PFSENSE-OPNSENSE.md#cutover-and-acceptance) while the new lab remains disconnected. Review affected lab/relay states after rule changes; a planned state removal or controlled restart is needed when an old permitted connection would otherwise survive. A full edge-firewall state reset can interrupt household sessions.

## A session has a beginning and an end

Before starting, agree on target identifiers, permitted ports/protocols, the exercise window, allowed techniques, and whether device resets/data loss are expected. Router management, relay administration and household equipment are outside target scope. Radio testing additionally stays within the agreed lab radios; Wi-Fi broadcast range is a real boundary consideration.

Use disposable accounts and data. Keep reset images and a physical disconnect available. The first exercises are requests to a toy web app and serial commands, followed by observation of the intended insecure and corrected behavior. Save game worlds separately from attack images.

If a forbidden path succeeds: stop the exercise and disconnect the target networks. For a dedicated lab firewall, also disconnect its uplink; for a shared edge firewall, preserve or restore the household's planned safe path. Correct the route/bridge/rule problem locally, remove affected stale connection state or perform a controlled restart, then repeat the acceptance checks. Ending a session includes stopping targets, removing temporary permissions and revoking identities of rebuilt/compromised hosts.

# Acceptance and learning exercises

## What counts as evidence

An isolation test needs a source, a destination, a known listening service and an expected result. A failed ping alone proves little: the destination may ignore ping or be powered off. A service timeout without a baseline is inconclusive.

Use a disposable **canary host** to represent a protected device. Start a harmless test listener on it, confirm it responds from its own trusted zone, then test the same address and port from the lab. This avoids scanning TVs, consoles or personal computers. Record private addresses and logs only in the private worksheet. Firewall counters or packet capture on the correct interface help distinguish an explicit block from a dead service.

The network probe tools supplied elsewhere in this repository are diagnostic aids. They cannot certify the whole network or replace a physical port audit.

## Acceptance matrix

| Test origin | Destination/action | Required result |
|---|---|---|
| Trusted baseline host | Canary's known test service | Connection succeeds |
| Target zone | Same protected canary service | Connection denied; expected boundary observes/drop counts traffic |
| Target zone | Home router administration | Denied |
| Target zone | Trusted firewall/gateway management | Denied except necessary DHCP/DNS services explicitly designed for lab clients |
| Target zone | Services canary | Denied |
| Services zone | Protected canary and management | Denied |
| Approved remote participant | Exact scoped target service | Expected response |
| Approved remote participant | Unapproved port and management endpoint | Denied |
| Unapproved identity | Scoped service | Denied |
| Target | Unapproved overlay peer | Denied |
| Target | External benign test destination | Denied outside documented maintenance allowance |
| Target with alternate static address | Protected canary | Still denied; changing address cannot cross the link boundary |
| IPv6-capable test host | Equivalent protected destination | Denied, or IPv6 deliberately absent on this path |
| Internet, outside overlay | Experiment service | No public reachability |
| After firewall reboot | Repeat positive/negative checks | Same policy persists |
| After overlay disconnect/revocation | Previously permitted remote access | No new connection succeeds |
| Edge targets/relay/services | HOME transit host and protected home endpoint | Denied at the edge firewall; home router alone is not the sole evidence |
| Edge home client | Ordinary approved internet service | Works with the chosen router/AP mode and documented NAT behavior |
| Split provider handoff | Both router WAN connections active simultaneously | Provider-approved leases/sessions and expected routing; no assumption from switch link lights |
| Split target | Home router's public WAN/IPv6 endpoint | Denied by lab policy; test address aliases and return-through-public paths |
| VLAN target host/container | Other target/service/management VLANs | No unapproved path through host bridges, forwarding or shared container privileges |

Do not mark tests “pass” when hardware or an IPv6 test destination is unavailable. Mark them **not tested** and keep the corresponding deployment stage unapproved. IPv6 link-local addresses require an interface scope and are not routed across normal boundaries; check that targets do not share a protected link as well as checking routed addresses.

Before changing policy, prepare a local console or known recovery port and a configuration backup. Keep the target uplink disconnected until the new policy is in place. A firewall management lockout is a recovery problem, not a reason to temporarily bridge the lab to home.

In a split deployment, a WAN address shown by a router is classified against the recorded provider contract and actual route. A private or shared CGNAT address must not be relabeled as a public address to match the drawing. In an edge deployment, record and test the household rollback path before changing the live ISP attachment. A diagram and a passing configuration syntax check do not prove either condition.

## A learning sequence

| Lesson | Activity | Observable result | Reset |
|---|---|---|---|
| 1 · Serial | Send valid and invalid commands to Uno firmware | Accepted commands change LED/state; invalid input is rejected | Reset board |
| 2 · Addressing | Read the Pico's lease on the isolated lab | Address, subnet and gateway match the plan | Reconnect lab Wi-Fi |
| 3 · Service | Request the Pico or Linux demo's documented endpoint | TCP connection followed by application response | Restart demo |
| 4 · Input validation | Compare short valid input, invalid input and a length limit | Error response without unintended state change | Reset demo state |
| 5 · Plaintext | Capture traffic from an owned lab client making a synthetic HTTP request | The synthetic request is readable on the observed link | Delete capture after notes |
| 6 · Encryption | Compare the synthetic request's underlying transport while using a VPN path | The outside capture sees tunnel traffic; the target-side HTTP hop can remain plaintext | Disconnect overlay |
| 7 · Authorization | Repeat a request with an approved and unapproved identity/token | Only the authorized request succeeds | Rotate training token |
| 8 · Containment | Treat the target as fully compromised and run acceptance checks | It still cannot initiate protected connections | Reimage target |
| 9 · Collaboration | One scoped target and one remote participant | Expected request, response, logs and revocation | Revoke session access |

All credentials and payload data in plaintext exercises are invented and single-use. On switched Ethernet, a capture normally sees the capturing host's traffic plus relevant broadcast/multicast, not every other conversation. Use capture on an owned endpoint or an explicitly configured lab capture port. Do not assume Wi-Fi monitor mode or a network tap is present.

The secure firmware is a baseline for comparison. Authentication on a plaintext HTTP hop does not encrypt a token; anyone able to capture that hop may learn it. An encrypted overlay to a gateway protects the cross-site leg, while the final gateway-to-microcontroller leg still needs an isolated link or separately supported TLS.

Router administration exercises begin offline. A firmware compromise exercise requires an independent trusted boundary. Radio disruption, denial-of-service traffic, credential reuse and public address scanning are outside the introductory scope because they change the impact and recovery model.

## Troubleshoot from the closest layer outward

1. **Power and link:** correct USB data cable, Ethernet link and intended Wi-Fi association.
2. **Address:** address, prefix and gateway match the selected segment; no duplicate address.
3. **Listener:** the application is running and bound to the intended address/port; local logs show startup success.
4. **Route:** the sender has a route to the intended destination; no overlapping site subnet or unexpected exit node.
5. **Policy:** overlay permissions, gateway forwarding and zone firewall agree on direction and protocol.
6. **Application:** correct game edition/version, credentials, allowlist and requested path.
7. **Return path:** target replies reach the gateway; NAT or an explicit route accounts for remote source addresses.

Game lags while a connection still works suggests CPU, storage, memory, bandwidth or relay latency, rather than an automatic need for a public port forward. A UDP probe without an application-level response is not proof that Factorio is unreachable; the actual game client is the meaningful final test.

# WireGuard as an advanced alternative

WireGuard provides encrypted peer tunnels with explicit keys and routes. It does not include automatic invitations, application-port permissions or a general relay service. The two example files describe **one workstation contacting one relay host**, not a bridged household network. Repeat with separate relay tunnel subnets for sites B and C.

At least one side must be reachable. A relay listening on UDP 51820 needs a routable endpoint: a reachable public address with the necessary controlled port forwards, or an appropriately secured public relay/VPS. With two home routers, the UDP forward path must be configured through both, and the trusted firewall must forward only to its maintained relay. Under provider CGNAT, a home port forward alone is insufficient. None of the example placeholders represents an actual reachable endpoint. [WireGuard quick start](https://www.wireguard.com/quickstart/).

Keep the strict Tailscale profile unchanged unless intentionally building this separate variant. It has no UDP ingress forward and no WireGuard permission. The required WireGuard transport rule is a new explicit firewall change; putting the relay into a consumer “DMZ host” setting is not part of the procedure.

## Keys and host configuration

Install `wireguard-tools` from the operating system's supported packages. Generate each machine's key on that machine, inside private storage:

```sh
umask 077
wg genkey > wireguard.private
wg pubkey < wireguard.private > wireguard.public
```

Exchange public keys through the agreed private setup channel; retain private keys locally. Fill [relay.conf.example](relay.conf.example) and [workstation.conf.example](workstation.conf.example) privately. Before writing the relay's `/etc/wireguard/wg-lab.conf`, establish an appropriate host firewall policy:

- Accept the chosen UDP WireGuard transport port only on the intended interface.
- Permit each registered tunnel peer to the relay's TCP 22 only.
- Reject all forwarding from the tunnel to physical networks and between tunnel peers.
- Permit relay-originated TCP connections to only the approved lab services at the external firewall.
- Keep Linux IPv4/IPv6 forwarding disabled; use the same forwarding-only SSH accounts as the Tailscale recipe.

These host rules are prerequisites, not a ready-made ruleset: the OS firewall backend and existing administration path must be identified before producing an applicable host firewall. A confirmed endpoint and host firewall are required before activation. The supplied files deliberately contain no auto-running `PostUp` or firewall flush commands.

Install the private config with mode `600`, then activate and inspect on each host:

```sh
sudo wg-quick up wg-lab
sudo wg show wg-lab
```

On a workstation use the same SSH local-forward command as the main guide with relay address `10.76.10.1`. Deactivate with `sudo wg-quick down wg-lab`. Do not enable boot activation until handshake, permitted-service and denied-path checks succeed.

## Understand the peer fields

`AllowedIPs` is both the route selection for sending and a source-address check for received peer traffic. It is not an application-port firewall. The workstation routes only the relay's `/32` address. On the relay, every workstation gets a unique `/32`, for example `.11`, `.12`, `.13`; private keys and peer identities are never shared. No peer receives `0.0.0.0/0`, a home subnet or another operator's range. [WireGuard protocol and cryptokey routing](https://www.wireguard.com/).

`PersistentKeepalive = 25` on a peer behind NAT can keep an established translation available. It does not make a provider's CGNAT publicly forward a new inbound port. Public relay/VPS deployment also adds cost, patching, abuse handling and independent host firewall responsibilities; it is an alternative deployment rather than a missing setting in a home router.

Revoke access by deleting the corresponding peer from the relay configuration and applying the change, plus removing its SSH forwarding key/account. Never commit a filled WireGuard file, endpoint address or generated private key to the public repository.

# Join three sites through a private tunnel

The reference uses one dedicated Tailscale network, called a **tailnet**, for registered workshop devices. Each site independently contains its targets. Ordinary household devices do not join this workshop tailnet. A tailnet administrator can change policy and assign identities, so that role stays outside exercises.

The strict route is **workstation → VPN → forwarding account on relay → one target TCP service**. The firewall's lab segment remains offline. The same policy also provides optional direct Linux target and game-server roles, which require separately configured service/target egress as explained in the architecture guide.

## Define roles before enrolling devices

The included [tailscale.policy.json](tailscale.policy.json) contains no personal identity or actual VPN address. It uses three site labels and distinct device tags:

| Tag pattern | Intended machine | Permissions initiated by this role |
|---|---|---|
| `tag:client-a`, `-b`, `-c` | Dedicated exercise workstation | Relay SSH 22; Linux target HTTP 8081; specified game ports |
| `tag:relay-a`, `-b`, `-c` | Maintained forwarding host | No newly initiated connections to other VPN nodes |
| `tag:target-a`, `-b`, `-c` | Optional direct-VPN Linux target | No newly initiated connections to other VPN nodes |
| `tag:game-a`, `-b`, `-c` | Maintained game server | No newly initiated connections to other VPN nodes |
| `tag:admin-a`, `-b`, `-c` | Separate administration workstation | SSH to that site's relay, target and game server |

The forwarding host reaches the Pico's physical IP through the local firewall, not through a Tailscale grant. The Pico itself has no tag. Only tailnet administrators can assign tags. A client tag must not also be assigned to a target, and an admin tag must not be placed on a machine used for attacks. Multiple tags and grants add permissions together; a narrower rule cannot cancel a broad allow. [Tailscale grant syntax](https://tailscale.com/docs/reference/syntax/grants).

## Tailnet administrator procedure

1. Create a workshop-only tailnet using a maintained identity-provider account with multifactor authentication. Use the provider's normal authentication flow; no shared passwords.
2. Before target enrollment, replace the new tailnet's default allow-all policy with `tailscale.policy.json`. Do not paste it below existing broad grants or legacy ACLs. This file intentionally provides no access to untagged personal devices, home subnet routes, exit nodes or public Funnel services.
3. Save it in the policy editor and require every supplied test to pass. Tests assert permitted services and rejected administration/pivot paths for A, B and C. Local JSON parsing does not substitute for the service's policy compiler. [Tailscale policy tests](https://tailscale.com/docs/reference/syntax/policy-file#tests).
4. Invite the participating accounts through the service's normal user-management flow. Enable device approval and approve only the planned workshop nodes. Keep the invitation links private. [Tailscale device approval](https://tailscale.com/docs/features/access-control/device-management/device-approval).
5. Assign each enrolled device exactly its intended role tag in the Machines view. A tagged node acts as a device role rather than inheriting its enrolling user's access. Keep a private register of node, role, operator and retirement date.

The policy's network TCP 22 permission is for the ordinary OpenSSH server. Tailscale SSH is deliberately disabled. Network permission alone does not supply an operating-system account, password or SSH key.

## Site operator procedure

Complete the firewall procedure and its local isolation checks. The relay uses one physical network connection only: the relay segment, e.g. `10.78.10.2/24`. Its gateway and DNS are `10.78.10.1`. It does not connect to household Wi-Fi or directly to the lab. The firewall routes the one permitted application connection to the target.

Install Tailscale from the [official installation instructions](https://tailscale.com/docs/install), selecting the exact Linux distribution and architecture from the [stable package page](https://pkgs.tailscale.com/stable/). A full Linux Raspberry Pi, mini PC or supported VM can host this software; a Pico W or Uno cannot use the Linux package.

On a fresh installation:

```bash
sudo tailscale up --accept-routes=false --accept-dns=false --ssh=false
tailscale status
tailscale ip -4
```

Complete login privately, obtain device approval, and have the administrator apply the appropriate role tag. No subnet routes or exit node are advertised. The `--accept-dns=false` setting leaves OS DNS under local control; these instructions therefore use the relay's actual VPN IP shared privately, not an assumed MagicDNS name. Existing installations require reviewing their prior settings rather than assuming a fresh invocation clears all route advertisements.

Keep Linux packet forwarding off on the relay:

```bash
sudo sysctl -w net.ipv4.ip_forward=0
sudo sysctl -w net.ipv6.conf.all.forwarding=0
```

Persist those two settings in a dedicated file in `/etc/sysctl.d/` and verify after reboot. Ordinary SSH local forwarding opens a new application socket and does not require kernel IP forwarding. Containers, virtual bridges, NetworkManager sharing and other packages can change forwarding behavior; the relay has none of those roles in this design.

## Create forwarding-only SSH accounts

On a dedicated Debian/Raspberry Pi OS relay, install `openssh-server` during clean provisioning. Create a distinct non-admin account for each operator. The following is one synthetic account; repeat using another account name for each access holder:

```bash
sudo groupadd -f lab-forwarders
sudo adduser --disabled-password --gecos '' lab-operator-a
sudo usermod -aG lab-forwarders lab-operator-a
sudo install -d -m 700 -o lab-operator-a -g lab-operator-a /home/lab-operator-a/.ssh
```

Each workstation generates its own key locally, protected by a passphrase:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/lab_forwarding -C lab-forwarding
```

Transfer only `lab_forwarding.pub` through a private agreed channel. The relay operator writes its single public-key line to the matching account's `~/.ssh/authorized_keys`, owned by that account, mode `600`. Private keys stay on their originating workstation. Forwarding accounts have no sudo, Docker, LXD, disk or other administrative group membership.

Merge [sshd-relay.conf.example](sshd-relay.conf.example) into a dedicated file under `/etc/ssh/sshd_config.d/`, after checking the main configuration includes that directory. Verify a non-root administrator can already log in with an SSH key: the template disables root and password login globally. Adjust both target addresses for the site. `PermitOpen` names the only target host:port pairs; `MaxSessions 0` blocks shells and SFTP while retaining forwarding. The configuration also disables remote forwarding, Unix-socket forwarding, agent forwarding and tunnel devices. [OpenSSH forwarding and session controls](https://man.openbsd.org/sshd_config).

Keep an existing administrative session open, then validate before reloading:

```bash
sudo sshd -t
sudo sshd -T -C user=lab-operator-a,host=relay,addr=100.64.0.10
sudo systemctl reload ssh
```

`100.64.0.10` here is a synthetic test-context address, not an enrolled device. Inspect the effective settings, especially `maxsessions 0`, `allowtcpforwarding local`, `permitopen`, `permitlisten none` and disabled password authentication. The `-T` command checks matched settings; it does not make a network connection. On a distribution using service name `sshd`, reload that service instead. Any syntax failure is corrected before reload.

Restrict administrative relay accounts to trusted operators and keys. On this relay, TCP 22 arriving from the VPN must remain subject to the account restrictions above. Bind or filter other unintended listeners with the host firewall; the upstream firewall already denies lab-initiated connections to the relay zone. Audit Linux listeners using `sudo ss -lntup`.

## Participant connection procedure

Install the VPN on the exercise workstation, enroll it, and obtain its `client` role. Receive the relay's actual VPN IP, forwarding account name and SSH host-key fingerprint privately. The site operator obtains the fingerprint locally with:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

Compare that fingerprint at the first connection; do not disable host-key verification. The participant stores the address in a local shell variable and starts the following tunnel for site A:

```bash
# Fill the value privately; it is assigned by the VPN service.
RELAY_VPN_IP='REPLACE_WITH_RELAY_VPN_IP'
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
  -i ~/.ssh/lab_forwarding \
  -L 127.0.0.1:18080:10.77.10.30:8080 \
  "lab-operator-a@${RELAY_VPN_IP}"
```

Keep the command running and visit `http://127.0.0.1:18080`. The listening endpoint is the participant's own loopback address and is not shared with that participant's household LAN. Close the SSH process with Ctrl+C when the session ends. Replace the target third octet with `20` or `30` for sites B or C, and use the corresponding site's relay/account.

For an approved Linux HTTP target, use `-L 127.0.0.1:18081:10.77.10.20:8081` after adding that service to both the firewall candidate and the relay's `PermitOpen`. A serial-to-web service on that Linux target follows the same pattern. Never forward the relay's shell or an arbitrary subnet to make a single service work.

`ExitOnForwardFailure` verifies the local forwarding listener was created; it does not prove the remote target works. An HTTP request is the actual service check. An unknown target/port should fail when used. A shell request such as `ssh lab-operator-a@...` should fail because this is a forwarding-only account.

## Direct Linux target and game variants

For a clean game server, install the VPN directly on the server in a separate service segment, assign its `game` role, and connect game clients to its privately supplied VPN address and permitted port. No subnet router is needed. The policy grants no player SSH access to that host.

For a direct-VPN Linux attack target, use a distinct contained segment with an explicit public HTTPS egress exception and an appropriate `target` tag. Do not simply move it onto the trusted relay subnet. This variant permits target-originated public HTTPS; the firewall cannot tell legitimate VPN traffic from every other encrypted application on that port. For strict no-egress exercises, use the forwarding relay. After compromise, revoke the VPN node and replace the target image before the next session.

The supplied strict firewall profile does not implement these additional segments; [architectures](ARCHITECTURES.md) describes their boundary. A device-wide VPN tag grants the listed port on every matching host; tag assignment is part of the access review.

## Data visibility and retirement

The VPN coordinator manages identities, public keys and connectivity metadata; encrypted traffic may travel directly or through a relay depending on connectivity. Endpoint addresses can be visible to the VPN service and peers as needed for connectivity. A private repository export therefore does not imply anonymity toward invited participants. Application endpoints see the application data; the SSH relay opens the plaintext Pico HTTP connection inside the lab. [Tailscale connection paths](https://tailscale.com/docs/reference/connection-types).

End a session by stopping targets and disconnecting the lab uplink when remote access is no longer needed. To remove an operator, remove their forwarding key/account access and revoke the appropriate VPN node or role. Deleting an enrollment/auth key alone does not revoke already enrolled nodes; remove the node from the service's Machines view. Keep an offline copy of the clean target image and rebuild after exercises involving compromise. [Tailscale key and node revocation](https://tailscale.com/docs/features/access-control/auth-keys).

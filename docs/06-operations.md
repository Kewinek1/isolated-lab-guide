# Operations and recovery

## Keep the durable and disposable systems apart

Targets are disposable. Game saves, firewall configuration and enrollment authority are durable. A compromised target must not have a writable mount of backups, a container-engine socket, reusable administrator keys or a shared home directory from a trusted host. Containers are useful packaging; they share their host kernel and do not replace the external network boundary. Virtual machines improve separation, but a host that also holds sensitive personal data is still an undesirable attack platform.

Run game servers as a dedicated unprivileged OS account inside the services zone. Keep games out of the attack target image. A separate physical host is the simplest strong separation; a carefully configured hypervisor with distinct networks can be a later alternative.

The diagrams showing several Docker images on a Pi describe application packaging, not independent kernels. Host bridges, VLAN interfaces and container networking determine the actual packet path. The [platform guide](PLATFORMS.md) explains that boundary and the current optional CrowdSec integration differences. CrowdSec stays outside the baseline acceptance decision: home remains protected even when an optional detection service is stopped.

For **edge**, schedule firewall upgrades as household internet maintenance and preserve a way to restore the previous uplink. For **split**, retain the provider's simultaneous-connection requirements and update protected home public endpoints when leases change. If that endpoint inventory becomes uncertain, stop the affected lab egress until the rules and tests agree again. The WAN-only switch is never repurposed as a convenient home or lab LAN expansion port.

## Routine cycle

| Moment | Action | Evidence |
|---|---|---|
| Before session | Approve scope, confirm backups, update trusted boundary, check time and logs | Scope record and restore point |
| Before access | Repeat key isolation checks and verify current overlay grants | Allowed/denied test results |
| During session | Monitor resource use and designated logs; keep stop path available | Time-stamped local notes |
| After session | Revoke temporary access, remove routes no longer needed, stop targets | Revocation test |
| After compromise | Reimage target from trusted media; revoke and rotate exposed device credentials | Fresh image/version and enrollment |
| Periodically | Restore a backup into a disconnected staging environment | Successful restore and integrity checks |

Trusted firewall and gateway software receives maintained security updates. Vulnerable target versions are intentionally pinned for reproducible exercises and kept off uncontrolled networks. An update window for a target is a temporary, recorded exception with a closing step; it does not become permanent broad egress.

## Game maintenance

The runnable instructions live in [games/README.md](../games/README.md). Choose an exact release, obtain it from the publisher, verify available checksums and keep a local manifest of version, archive hash, runtime and mods. Minecraft's runtime requirement changes with its release: the official 26.1 release requires Java 25. The launcher asks for an explicitly selected Java major version instead of assuming every release uses Java 21. [Minecraft 26.1 technical changes](https://www.minecraft.net/en-us/article/minecraft-java-edition-26-1)

Stop the server cleanly before copying a world. Keep several dated backups outside the server's writable account. Test upgrades on a copy with the selected clients and mods before replacing a working installation. An upgraded world may not safely load in an older game version; retain the matching old software and pre-upgrade world together.

Minecraft Java normally uses TCP 25565; Factorio uses UDP 34197, and Factorio clients must match the server's game and mod versions. These are separate service permissions, not a reason to allow all traffic between participants. [Minecraft server download](https://www.minecraft.net/en-us/download/server), [Factorio multiplayer](https://wiki.factorio.com/Multiplayer)

Minecraft's EULA is an operator decision: the supplied launcher refuses to start until `eula.txt` has explicitly been edited to accept it. No download or acceptance is automated. [Minecraft EULA](https://www.minecraft.net/en-us/eula)

The supplied Factorio launcher targets the official Linux x86_64 headless distribution. It does not provide an ARM emulation path or support the Pico/Uno as game servers. The official download page supplies the supported package and release checksums. [Factorio downloads](https://www.factorio.com/download)

## Stop and recover

1. Stop the active exercise and disconnect the target-side uplink at the trusted boundary. Avoid disconnecting the home router as the first response.
2. Revoke overlay access to the affected target or gateway. Revoke device credentials if that machine was compromised.
3. Preserve only the logs necessary to understand the event in private storage. Do not upload captures, raw router exports or access tokens to a public issue.
4. Restore or reinstall the target offline. If the trusted gateway/firewall was compromised, treat its credentials and configuration as untrusted too and rebuild the boundary.
5. Replace exposed secrets and inspect unexpected routes, port forwards, UPnP mappings, DNS changes, Wi-Fi associations and administrator accounts.
6. Repeat the acceptance matrix before reconnecting remote participants.

A power cycle is not a reliable cleanup for a persistent compromise. A factory reset may preserve the installed firmware; firmware integrity and support must be checked separately when the router itself was attacked.

## Public and private publication boundaries

The public copy contains reusable source, fictional addresses, diagrams and unfilled templates. The private copy contains real inventory, addresses, router exports, configuration, connection cards, logs and photos. Real firmware code and public firmware code can remain identical while reading different local settings; duplicating source is unnecessary and makes fixes drift.

Never commit filled credentials or a directory merely because its filename says “example.” Public export should copy a known allowlist of distributable files into a fresh output directory, then scan and inspect the result. Git ignore rules prevent many accidental additions but do not remove data already tracked or erase Git history.

Review image metadata and visible labels, QR codes, network names, usernames, browser tabs and background screens before sharing any picture. An edited screenshot can still reveal an account or endpoint even when an IP address is covered. Prefer generic diagrams in the public copy.

Participants necessarily learn an endpoint or route needed for approved access, and an overlay provider processes account/connection metadata. “No personal information in the public repository” is the intended publication guarantee; it is not a claim of anonymity from invited participants or the service provider.

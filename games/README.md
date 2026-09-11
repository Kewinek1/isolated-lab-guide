# Private game servers

These Linux launchers run an official Minecraft Java or Factorio server on the host's **assigned Tailscale IPv4 address only**. They download nothing, change no firewall rules and perform no account enrollment. Their checks prevent common configuration mistakes; the services-zone firewall and overlay access policy must already be tested.

The supplied `network/generate_firewall.py` profile implements upstream, management, relay and target zones. **It does not create a game-services zone.** Before running these launchers, provision a separate reviewed services zone with its own ingress/egress rules using the [architecture guide](../network/ARCHITECTURES.md) and [OpenWrt procedure](../network/OPENWRT.md). Installing a game on the relay or target subnet would combine roles that this design keeps separate; the launcher's `isolation_verified` field cannot create the missing boundary.

The runtime state belongs outside the public repository. No server binary, save, log, secret, real address or accepted EULA belongs in this directory.

## Prerequisites

| Component | Required state |
|---|---|
| Host | Linux computer in a services zone; dedicated unprivileged account |
| Local tools | Python 3.9+, Linux `ip` from iproute2, current Tailscale client |
| Overlay | Joined/approved node, running `tailscale0` interface, restricted participant access policy |
| Boundary | Services-to-home/management denied; targets-to-services denied; IPv4 and IPv6 verified |
| Egress | DNS/time and publisher authentication/update dependencies explicitly supported |
| Minecraft | Official Java Edition server JAR and a Java runtime appropriate to that exact release |
| Factorio | Official Linux64 headless package on x86_64; matching player game/mod versions |

The Pico W and Arduino Uno cannot host these games. A Linux Raspberry Pi is a different machine; Minecraft workload/runtime compatibility needs checking, and this Factorio workflow does not support native ARM. The official [Factorio download](https://www.factorio.com/download) supplies the headless package. The official [Minecraft server page](https://www.minecraft.net/en-us/download/server) supplies Java Edition software.

The initial port policy is participant → game host **TCP 25565** for Minecraft and **UDP 34197** for Factorio. No router DMZ host or public port forward is needed. Only the site administrator receives OS administration access. These commands do not enable RCON remote administration.

## Prepare private directories

Run from the public repository root containing `games/`. The path created below is local state, outside the repository. The variables are shell conveniences; filled launcher JSON still requires literal absolute paths.

```bash
umask 077
LAB_PRIVATE="$HOME/.local/share/isolated-lab"
mkdir -p "$LAB_PRIVATE/minecraft" "$LAB_PRIVATE/factorio-state"
chmod 700 "$LAB_PRIVATE" "$LAB_PRIVATE/minecraft" "$LAB_PRIVATE/factorio-state"
cp games/minecraft/launcher.example.json "$LAB_PRIVATE/minecraft-launcher.json"
cp games/minecraft/server.properties.example "$LAB_PRIVATE/minecraft/server.properties"
cp games/minecraft/eula.txt.example "$LAB_PRIVATE/minecraft/eula.txt"
cp games/minecraft/whitelist.json.example "$LAB_PRIVATE/minecraft/whitelist.json"
cp games/factorio/launcher.example.json "$LAB_PRIVATE/factorio-launcher.json"
cp games/factorio/server-settings.example.json "$LAB_PRIVATE/factorio-state/server-settings.json"
cp games/factorio/server-whitelist.example.json "$LAB_PRIVATE/factorio-state/server-whitelist.json"
cp games/factorio/server-adminlist.example.json "$LAB_PRIVATE/factorio-state/server-adminlist.json"
cp games/factorio/server-banlist.example.json "$LAB_PRIVATE/factorio-state/server-banlist.json"
chmod 600 "$LAB_PRIVATE/minecraft-launcher.json" "$LAB_PRIVATE/factorio-launcher.json"
```

Copy commands overwrite files at the listed destinations. Run this preparation once for fresh directories; preserve existing game configuration and saves during updates. The launcher also refuses a filled configuration or runtime directory inside the public source tree.

## Minecraft Java

1. Select an exact release and download its official server JAR manually into the private Minecraft directory as `server.jar`. Record the source release and verify available publisher integrity metadata. Compute `sha256sum` on that file and record the result in `artifact_sha256`; a locally computed hash pins a file but is not by itself proof of publisher authenticity.
2. Install the Java runtime required for the selected server. For example, Minecraft **26.1 requires Java 25**, so the template's `java_major` is `25`; other releases must be checked independently. [Official 26.1 release notes](https://www.minecraft.net/en-us/article/minecraft-java-edition-26-1)
3. Fill `minecraft-launcher.json`: absolute private `game_directory`, absolute `java_binary`, selected `java_major`, memory limit, artifact hash and the address reported locally by `tailscale ip -4`.
4. Put that same address in `server.properties` under `server-ip`. Retain the supplied authentication, allowlist and disabled management settings. A blank bind address or wildcard listener is rejected.
5. Review the [Minecraft EULA](https://www.minecraft.net/en-us/eula). Only an operator choosing to accept it changes the **local** `eula.txt` from `eula=false` to `eula=true`. The launcher never makes this decision.
6. Complete the network acceptance worksheet, then set the local JSON `isolation_verified` to `true`. This field records the operator's completed checks; it does not test a router remotely.
7. Validate and start:

```bash
python3 games/launch.py minecraft "$LAB_PRIVATE/minecraft-launcher.json" --check
python3 games/launch.py minecraft "$LAB_PRIVATE/minecraft-launcher.json"
```

The initial allowlist is empty, so player admission is closed. After the server reaches its ready state, use its **local server console** to run `whitelist add APPROVED_PLAYER_NAME`, replacing the placeholder with an authenticated Minecraft Java account name. The game stores the resolved identity in the private `whitelist.json`. Use `whitelist list` to inspect it. The launcher keeps `online-mode=true` and `enforce-whitelist=true`; it supplies no generic server password because vanilla Java admission uses account authentication plus the allowlist.

An approved participant opens Minecraft Java Multiplayer and connects to the private endpoint on port 25565. The client/server release must be compatible. Enter `stop` in the server console for a clean shutdown before a backup. A console operator may grant game operator privileges deliberately; joining the server does not require operator privileges.

Memory values are starting settings, not a capacity promise. Leave memory for Linux and monitor world size, CPU and storage. The check verifies the Java major selected in the JSON, not whether the operator selected the correct release requirement. Older releases may ignore unfamiliar disabled feature properties; the host firewall remains necessary for every version.

## Factorio

1. Download an exact official Linux64 headless release from the [publisher](https://www.factorio.com/download), verify its available release checksum, and extract it in private storage. Retain the package's `bin/x64/factorio` and `data/` layout. The game's supplied `--help` remains the final reference for its installed version.
2. Fill `factorio-launcher.json` with the absolute private state directory, absolute `factorio_binary`, verified binary's SHA-256 and assigned Tailscale IPv4. The binary hash differs from the archive hash; record both in the local release manifest, and use the **binary** hash in the launcher field.
3. Replace `game_password` in local `server-settings.json` with a unique random secret of at least 16 characters. Keep `visibility.public=false`, `visibility.lan=false`, account verification enabled and commands limited to administrators. The unlisted server requires no publisher account password/token in its settings.
4. Replace the entry in `server-whitelist.json` with approved Factorio usernames. Keep the admin list empty unless administrative game commands are needed. Share the game password privately, separately from the public documentation.
5. Complete the services acceptance worksheet and set `isolation_verified=true` in the local launcher JSON.
6. Create a fresh world. This action writes state and refuses to overwrite `saves/world.zip`:

```bash
python3 games/launch.py factorio "$LAB_PRIVATE/factorio-launcher.json" --create-world
```

7. Validate and start the existing world:

```bash
python3 games/launch.py factorio "$LAB_PRIVATE/factorio-launcher.json" --check
python3 games/launch.py factorio "$LAB_PRIVATE/factorio-launcher.json"
```

`--check` requires an existing world; use `--create-world` first on a fresh installation. The launcher generates `launcher-config.ini` locally so write data remains in the specified private state directory, and passes explicit settings, save, whitelist and bind paths. RCON is not enabled. Mods reside in the private `mods/` directory; keep them aligned with the selected package and participating clients.

Connect through Factorio's Multiplayer → Connect to address using the private endpoint, port 34197 and the separately shared password. The protocol is UDP, and game/mod versions must match. [Factorio multiplayer reference](https://wiki.factorio.com/Multiplayer)

Use the server's orderly shutdown path, normally a single Ctrl+C/SIGINT while attached, and wait for saving to finish. Back up the stopped state directory and the matching software/mod manifest. Never run `--create-world` as a reset shortcut over an existing game; the launcher refuses that overwrite.

## Limits and diagnostic results

`--check` validates files, selected runtime, identity/address assignment and several security settings. It starts no game, though it executes local `java -version` for Minecraft and read-only Tailscale/interface status commands. Normal launch replaces the Python process with the game process and may contact its publisher's authentication services. World creation runs Factorio to create local data.

A launcher refusal reports the missing prerequisite. Do not work around it by binding to `0.0.0.0`, disabling account verification or opening router-wide exposure. Resolve the specific failed check. The scripts validate before launch; a later change to policy, interface configuration or files requires fresh acceptance checks.

Run `python3 -m unittest discover -s games/tests -v` for the local configuration/refusal tests. These use temporary files and mocked status/runtime responses, launch no game and prove no physical network property. Hardware hosting and real participant connections require the deployment tests in [the handbook](../docs/05-validation.md).

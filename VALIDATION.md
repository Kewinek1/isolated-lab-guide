# Verification record

Prepared and checked on 2026-09-11. This record distinguishes executable host checks from deployment acceptance.

## Executed successfully

- Python firmware tests: loopback HTTP requests reproduce the fictional IDOR and verify the ownership fix; token, input-size, LED authorization and private-token-file checks pass.
- Native C++ Uno parser test: compiled with warnings enabled; command handling, CRLF, buffer overflow rejection and recovery pass.
- Minecraft/Factorio launcher tests: unsafe defaults, wrong overlay addresses, missing approval flags, altered artifacts, invalid properties, authentication, save overwrite and private path/permission checks pass.
- Dedicated-firewall generator tests: no target egress by default, protected-destination ordering and rejected invalid configurations pass.
- Read-only firmware inspector tests: input limits, hash identity, bounded strings, report privacy, symlink and nonregular-file rejection pass.
- Public/private serving and release tests: manifest drift, extra files, runtime names, secret patterns, traversal, symlinks, foreign origins and private-mode boundaries pass.
- Private builder tests: disabled network defaults, confirmation gates, private permissions, refusal to overwrite and country validation pass.
- JavaScript model tests: site plans, ports, scenarios, validation, escaping and public SVG export behavior pass.
- Browser checks: seven scenario buttons, three site presets, documentation loading, form rejection, packet walkthroughs and responsive layouts checked. Desktop and mobile views have no page-level horizontal overflow; diagrams and tables scroll within their own containers when needed.
- Release: the export matches its public manifest and contains no original photographs, private directory, filled runtime settings or Git history.

The local application was exercised in headless Chromium. Browser print produces a vector PDF; it does not require an online document service. Public figure/PDF output uses fictional network examples.

## Not executed on physical infrastructure

- Arduino AVR compilation/upload, actual Uno USB behavior, Pico MicroPython execution, radio-country operation, Wi-Fi association and electrical wiring.
- Router configuration, firmware download/flash, obtaining a router shell, OpenWrt interface mapping, fw4 configuration compilation or live firewall application.
- pfSense/OPNsense installation, NIC compatibility, GUI rule entry, CrowdSec integration, ISP eligibility for parallel WAN connections, household cutover or IPv4/IPv6 acceptance on the new layouts.
- Actual home/target IPv4 and IPv6 isolation, DHCP behavior, DNS/UPnP effects and alternate network paths.
- Tailscale policy compilation in a real tailnet, participant enrollment, SSH daemon deployment, relay reachability or WireGuard handshakes.
- Game binary downloads, EULA acceptance, actual Minecraft/Factorio startup, multiplayer compatibility, performance and world restoration.

Prepared configurations deliberately retain unresolved device/endpoint details. Passing host tests is not proof of network isolation. Follow [network acceptance checks](network/VALIDATION.md) before enabling remote sessions and the game-specific checks before hosting.


## GitHub Pages preparation

The static builder and repository workflow were added and checked after the initial manual. Four additional tests cover manifest enforcement, generated entrypoints, hidden workflow scope and output-directory safety. Browser checks passed under a simulated `/isolated-lab-guide/` prefix and its `/app/` entrypoint: all seven scenarios, all 18 chapters, repository-relative source links and public print preparation. The local private edition still loads correctly. Static mode does not request the private API. The supplied Actions workflow performs publication when the reviewed changes reach main. Deployment status is recorded by its build/deploy jobs; it is separate from appliance acceptance.

## Edge/split and platform update

The public guide includes seven architectures and 18 reference chapters. The two added diagrams are original SVG interpretations of proposed layouts, with fictional data. Source images stay outside the release. The software selector distinguishes OpenWrt, pfSense and OPNsense and preserves the choice in private builder inputs.

The 15 JavaScript cases cover all seven scenarios, SVG XML/escaping and public-export privacy, private home-transit ranges, overlap rejection, platform/scenario validation and nine confirmed platform/topology builds. Only OpenWrt with the dedicated tunnel architecture can produce a UCI candidate; pfSense, OPNsense and edge/split builds remain manual. The 34 Python public-tool tests also pass, including compatibility with older input files.

Browser checks cover all scenario/site/platform selections, scoped code downloads, chapter and SVG loading, fragment navigation, the repository URL prefix, mobile overflow and public/private PDF generation. The platform-specific rules are a documented policy specification; no importable BSD configuration or successful physical-network deployment is claimed.

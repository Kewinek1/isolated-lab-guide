# Worksheets

These are blank public templates. Filled copies belong in private storage outside the distributable source tree. `REPLACE_…` is a placeholder, not a valid deployment value.

## Inventory and capability record

| Field | Private value |
|---|---|
| Site label | REPLACE_SITE |
| Device role | REPLACE_ROLE |
| Manufacturer, model, exact hardware revision | REPLACE_MODEL |
| Current supported firmware/version | REPLACE_FIRMWARE |
| Physical ports and intended zones | REPLACE_PORT_MAP |
| VLAN/guest isolation support and evidence | REPLACE_CAPABILITIES |
| IPv4 and IPv6 behavior | REPLACE_IP_FAMILIES |
| Management-only path | REPLACE_ADMIN_PATH |
| Reset/recovery procedure and backup location | REPLACE_RECOVERY |
| Power supply and data cable requirements | REPLACE_POWER |

## ISP handoff and topology record

| Field | Private value |
|---|---|
| Selected scenario | offline / behindrouter / edge / split |
| Handoff equipment and mode | REPLACE_MODEM_ONT_OR_ROUTED_GATEWAY |
| Provider address delivery | REPLACE_SINGLE_LEASE_MULTIPLE_LEASES_SESSION_OR_ROUTED_BLOCK |
| Simultaneous permitted connections | REPLACE_PROVIDER_CONFIRMED_LIMIT |
| Required authentication, VLAN or device registration | Private configuration reference; no secret in this table |
| IPv4 status of each WAN | REPLACE_PUBLIC_PRIVATE_OR_SHARED_CGNAT |
| IPv6 prefix allocation and protection | REPLACE_VERIFIED_PREFIX_POLICY |
| Edge HOME port/VLAN and retained router/AP mode | REPLACE_HOME_ASSIGNMENT |
| Split WAN-only switch port inventory | REPLACE_WAN_PORT_ASSIGNMENT |
| Home public aliases/endpoints blocked from lab | REPLACE_PROTECTED_ENDPOINT_REFERENCE |
| Household maintenance and rollback method | REPLACE_REHEARSED_ROLLBACK |

## Scope record

| Field | Private value |
|---|---|
| Session identifier and date | REPLACE_SESSION |
| Owner approval and participants | REPLACE_APPROVAL |
| Start/end time and timezone | REPLACE_WINDOW |
| Exact target address(es) | REPLACE_TARGETS |
| Protocols and ports | REPLACE_PORTS |
| Allowed exercise and expected impact | REPLACE_ACTIVITY |
| Excluded assets | Home, management, services and all unlisted targets |
| Resource/traffic limits | REPLACE_LIMITS |
| Data permitted on target | Synthetic exercise data only |
| Stop signal and reachable operator | REPLACE_STOP_PATH |
| Snapshot/reimage and restore location | REPLACE_RESTORE |
| Expiry/revocation owner | REPLACE_REVOKER |

## Participant connection card

| Field | Private value |
|---|---|
| Site/session | REPLACE_SITE_SESSION |
| Overlay identity/network to join | REPLACE_ENROLLMENT_REFERENCE |
| Approved endpoint or target route | REPLACE_ENDPOINT |
| Protocol/port and service | REPLACE_SERVICE |
| Credentials | Separate secret-sharing reference, never the secret itself |
| Expected benign response | REPLACE_EXPECTED_RESPONSE |
| Permitted activity | Reference approved scope record |
| Access expiry and stop contact | REPLACE_EXPIRY_STOP |

## Acceptance result

| Time | Source zone | Destination/test | Expected | Observed | Boundary log/counter | Result |
|---|---|---|---|---|---|---|
| REPLACE_TIME | REPLACE_SOURCE | REPLACE_DESTINATION | REPLACE_EXPECTED | REPLACE_OBSERVED | REPLACE_EVIDENCE | PASS / FAIL / NOT TESTED |

## Data-flow record

| Step | Sender/interface | Receiver/interface | Address/protocol/port | Encryption | Decision point |
|---|---|---|---|---|---|
| 1 | Participant | Overlay peer/gateway | Private approved endpoint | Tunnel | Identity and destination policy |
| 2 | Gateway target link | Target | Private approved target | Depends on final application hop | Forwarding rule |
| 3 | Target | Participant through gateway | Established reply | Tunnel on cross-site leg | Stateful return path |

## Deployment decision

The selected design is ready for the next stage only when required capabilities are verified, protected paths are denied, permitted paths work, and recovery has been rehearsed. The result field records one of **offline only**, **remote target access approved**, **private services approved**, or **blocked pending a named failed/unperformed test**. Approval for one stage does not automatically approve public hosting or router exploitation.

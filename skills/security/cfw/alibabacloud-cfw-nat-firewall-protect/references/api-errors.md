# CFW NAT Firewall API Error Codes

Error codes observed for Cloud Firewall NAT firewall APIs. Some are string codes, some are numeric.

## Parameter Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `MissingNatRouteEntryList` | CreateSecurityProxy | Route entry list is mandatory | The `create` command assembles it automatically via VPC route discovery, or pass `--route-entry-json` manually |
| `ErrorParameters` | CreateSecurityProxy | Generic parameter error; observed cause: `VswitchCidr` missing while `VswitchAuto=true` (conditionally required, docs-only rule) | Always pass `--vswitch-cidr` with a free CIDR inside the VPC |
| `MissingVswitchCidr` | CreateSecurityProxy | Auto mode (`VswitchAuto=true`) requires a diversion CIDR | Pass `--vswitch-cidr` (use the `assess` plan's `suggested_vswitch_cidr`), or switch to manual mode with `--vswitch-id` |
| `Missing*NatGatewayId` / `Missing*RegionNo` / `Missing*VpcId` / `Missing*ProxyName` / `Missing*ProxyId` / `Missing*Switch` | Various | A required parameter is missing | Check script usage (`--help`) and provide all required parameters |

## Route / Network Validation Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorNatCustomRouteEntryDifferent` | CreateSecurityProxy / switch-on | "The custom route entries in the routing tables are inconsistent" - the VPC's route tables carry different custom entries (typically extra VpnGateway / peer / prefix-list routes in some tables). Top cause of auto-mode failure in service orders. **Why the check exists (route propagation perspective):** auto mode builds the firewall's own diversion-vswitch route table from the VPC's custom entries; if the business route tables are inconsistent, the firewall vswitch's route table would inherit entries (e.g. vppeer / vpngateway routes) that some business vswitches deliberately do NOT want. Because ALL diverted traffic is forwarded through the firewall vswitch, its route table becomes the effective forwarding table for that traffic - the extra entries would propagate routes into traffic paths that were never designed to carry them (route diffusion: traffic misdirected onto VPN/peering paths, unintended forwarding changes). The consistency check blocks this before any change is made | Either align the custom entries of ALL route tables (only if business allows), or **switch to manual mode** (`--vswitch-id`) with a dedicated vswitch + dedicated custom route table. `assess` detects this client-side before creation (route-entry consistency check) |
| `ErrorVswitchCidrNotInVpc` | CreateSecurityProxy | The `VswitchCidr` supplied for auto mode lies outside the VPC's primary/secondary CIDR blocks | Pick a CIDR inside the VPC range; the `create` pre-check (`check_vswitch_cidr`) catches this client-side |
| `ErrorDefaultRouteConflicts` | CreateSecurityProxy (manual mode) | The custom route table bound to the chosen `--vswitch-id` already contains a `0.0.0.0/0` entry; the server injects its own default route and refuses to overwrite one | Bind a freshly created custom route table without a default route (`prepare` does this), or pick another vswitch. The manual-mode pre-check detects it client-side before the API call |
| Default-route conflict (check item / creation rejection) | CreateNatFirewallPreCheck, CreateSecurityProxy | A conflicting 0.0.0.0/0 default route exists - either another outbound route in the VPC (e.g. a second NAT gateway) or a route learned from CEN (e.g. HaVip) | Remove/adjust the conflicting route, or restrict what the VPC learns via CEN route policy; if the network cannot be changed, use manual mode with a dedicated route table |

## Resource Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `-360838` ("The NAT gateway was not found") | CreateNatFirewallPreCheck, CreateSecurityProxy | The NAT gateway is not visible to Cloud Firewall | Verify NAT gateway ID / region / VPC ID. New NAT gateways take 1~5 minutes to sync - use "Asset Sync" in the console or retry later |
| `ErrorNatGatewayNotExist` / `InvalidNatGatewayId.NotFound` | CreateNatFirewallPreCheck, CreateSecurityProxy, VPC reads | Same root cause as `-360838` in string form: wrong ID/region, or the gateway has not synced into Cloud Firewall yet | Re-verify the ID with `assess`, wait 1~5 minutes, or trigger "Asset Sync" in the console |
| `ErrorProxyAlreadyExist` / `ErrorNatFirewallAlreadyExist` | CreateSecurityProxy | The NAT gateway already has a NAT firewall (one gateway maps to exactly ONE firewall) | Query it with `nat-fw-switch.sh query --nat-gateway-id <id>` and use the switch workflow instead of creating; `assess --nat-gateway-id` reports this as `plan.actionable: false` |
| `ErrorProxyNotExist` / `ErrorNatFirewallNotExist` | SwitchSecurityProxy, DeleteSecurityProxy, UpdateSecurityProxy | The referenced ProxyId does not exist (often a stale ID from an earlier report) | Re-query the current ProxyId. Note these APIs may also return success silently for unknown IDs - always verify per the behavioral notes below |

## Quota / Spec Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| Quota-exceeded errors (numeric codes) | CreateSecurityProxy | NAT firewall authorization count reached the purchased limit | Check usage with `nat-fw-lifecycle.sh quota` (`UsedCount` vs `TotalCount`); purchase more quota or delete unused NAT firewalls |
| `ErrorNatFirewallQuotaExceed` / `ErrorQuotaExceed` / `ErrorInstanceSpecFull` | CreateSecurityProxy | String-code form of the above: NAT firewall authorization count exhausted, or the CFW instance spec is full | Same handling. `assess` surfaces it beforehand via `quota` (`used` vs `total`) and `plan.quota.sufficient: false` |
| `ErrorNatFirewallPreCheckFailed` / `ErrorPreCheckFailed` | CreateSecurityProxy | Creation was rejected because the server-side pre-check does not pass (dependency missing: DNAT entries exist, no SNAT entry, default-route conflict, no free subnet, EIP count out of range ...) | Run `assess --nat-gateway-id <id>` (or `precheck`) and fix every failed item - its `display` label states the requirement - then retry |
| `ErrorInstanceStatusNotNormal` | All write APIs | CFW instance abnormal (unpaid, expired) | Check instance status and billing in the Cloud Firewall console |

## Auth Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorAuthentication` | All APIs | Authentication failed | Check AK/SK validity via `validate-cli.sh` |
| `NoPermission` / `Forbidden.*` | All APIs | RAM permission missing | Grant the missing action; the RAM Action prefix for Cloud Firewall is `yundun-cloudfirewall` (NOT `cloudfw`) - using the wrong prefix makes the policy silently ineffective |
| `Forbidden.RAM` | VPC write APIs (CreateVSwitch / CreateRouteTable / AssociateRouteTable) during manual-mode `prepare`/create | Per-action VPC write permission missing - granting one action does NOT imply the others | Run `validate-cli.sh --check-permission --mode manual` to list ALL missing actions in one shot (each reported as `granted` / `missing` / `unknown`), then grant every `missing` one |
| `Throttling` | All APIs | Rate limited | Wait a few seconds and retry |

## Important Behavioral Notes (verified by live testing)

1. **`SwitchSecurityProxy`, `DeleteSecurityProxy`, and `UpdateSecurityProxy` do NOT validate ProxyId** - calling them with a non-existent proxy ID returns success silently. Phase 3 verification (`nat-fw-switch.sh query --proxy-id <id>`) is the only way to confirm the operation actually took effect. If the queried proxy does not exist or its status did not transition, treat the operation as failed. Script-level enforcement (since 2026-08-10): `update` re-reads the proxy via `DescribeSecurityProxy` (existence + RegionNo) and compares `ProxyName`/`StrictMode` via `DescribeNatFirewallList`, failing with exit 2 on mismatch; `delete` pre-checks existence and status via `DescribeSecurityProxy`, refusing to run with `ProxyNotFound` (exit 2) for unknown IDs and printing status-based flap warnings.
2. **`DescribeNatFirewallQuota` returns**: `TotalCount` (purchased authorizations), `UsedCount` (in use), `ExceptionCount` (abnormal NAT firewalls). Creation is only possible while `UsedCount < TotalCount`.
3. Numeric error codes (e.g. `-360838`) are not documented exhaustively - for unlisted numeric codes, read the `Message` field and provide the `RequestId` to support.
4. **VPC route APIs (verified 2026-08-10)**: `DescribeRouteTableList` returns route tables under `RouterTableList.RouterTableListType` (NOT `RouteTables.RouteTable`); `DescribeRouteEntryList` does NOT accept `NextHopId`/`NextHopType` filters (`OperationFailed.FilterParamUnderWrongRouteType`) - fetch all entries and filter locally.
5. **`CreateSecurityProxy` with `VswitchAuto=true` requires `VswitchCidr`** (conditionally required, otherwise `ErrorParameters`). `NatRouteEntryList` must be passed in dot-index form (`--NatRouteEntryList.1.DestinationCidr ...`); JSON-array form is rejected with `MissingNatRouteEntryList`.
6. **`DescribeSecurityProxy` pagination uses `PageNo` (NOT `CurrentPage`)** - unlike other CFW list APIs; passing `--CurrentPage` fails with "not a valid parameter or flag" (verified 2026-08-10).
7. **`CreateSecurityProxy` manual mode**: pass `--VswitchAuto false --VswitchId <vsw-xxx>` (mutually exclusive with `VswitchCidr`). The NAT gateway's availability zone is NOT a top-level field - read it from `DescribeNatGateways` -> `NatGatewayPrivateInfo.IzNo` (enhanced gateways have no top-level `ZoneId`); bound-EIP count comes from `IpLists.IpList` length. If the chosen vswitch's bound route table already contains a 0.0.0.0/0 entry, the server rejects the creation (default-route conflict) - the `create` pre-check detects this client-side. Manual-mode vswitches are NOT reclaimed on `DeleteSecurityProxy` (verified against official docs, 2026-08-12).
8. **Creation timeouts (service-order evidence, 2026-08-12)**: `CreateSecurityProxy` validates CEN route conflicts and can time out when the CEN holds many instances (observed `SocketTimeoutException`; the pre-check's CIDR and multi-route-table validations can also time out). A timeout does NOT prove the request was rejected - one order showed backend HTTP 200 despite the console error. Script-level enforcement: on timeout-like failures `create` verifies via `DescribeSecurityProxy --NatGatewayId` whether the firewall was created anyway, and only retries (max 3 attempts) when it was not.
9. **Auto-mode availability-zone blind spot (service-order evidence)**: auto mode auto-selects the availability zone based on the customer's existing business vswitches. If that AZ no longer allows new vswitch creation (e.g. the AZ is being decommissioned), creation fails with "firewall vswitch creation failed" even though the API may return 200. Not detectable client-side. Remedy: retry in **manual mode** with a vswitch in a still-active AZ, or release the vswitches in the decommissioned AZ first.
10. **Quota release is asynchronous**: after `DeleteSecurityProxy` succeeds, `DescribeNatFirewallQuota.UsedCount` may still include the deleted firewall until the deletion finishes (status `deleting`, then the proxy disappears from `DescribeSecurityProxy`). Creating a replacement firewall immediately can fail with a quota-exceeded error even though quota "should" be free. Remedy: poll until the deleted proxy disappears from query results, then re-check `quota` before retrying `create`.
11. **`SnatIpList` semantics**: `DescribeSecurityProxy.SnatIpList` lists the NAT gateway's EIPs (the SNAT public egress IPs being protected) - it is NOT the IP of the diversion vswitch, and an empty list only means the gateway has no SNAT-bound EIP visible to CFW (asset sync delay), not a firewall malfunction.
12. **`assess` results are a point-in-time snapshot (environment drift)**: users may change the environment in the console at any time (delete vswitches, add DNAT entries, bind/unbind EIPs, modify route tables), which silently invalidates a previous `assess` report. The report carries `assessed_at` and a `freshness_warning`; `create` re-validates its inputs (vswitch existence/constraints, CIDR overlap) at execution time and points back to `assess` when referenced resources are gone. Treat any assess output older than the last console change as stale - re-run `assess` before `create` when in doubt.

# CFW VPC Boundary Firewall API Error Codes

Error codes observed for the Cloud Firewall VPC boundary firewall (Express Connect / VPC peering)
APIs. Every code diagnosed by the scripts is listed here.

## Parameter / Identity Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorFirewallId` | ModifyVpcFirewallSwitchStatus, ModifyVpcFirewallConfigure, DescribeVpcFirewallDetail | The firewall ID parameter is invalid | Verify the `vfw-xxxx` ID with the query command |
| `ErrorParametersFirewallId` | describe-vpc-firewall-default-ips-config, modify-vpc-firewall-default-ips-config, ModifyVpcFirewallAclEngineMode | The ID is not valid for this engine API. Nearly always a firewall whose `FirewallSwitchStatus` is `notconfigured`: it carries no IPS/ACL engine instance | Check the state with the query command; create and open the firewall before tuning the engine |
| `ErrorVpcFirewallNotFound` / `ErrorFirewallNotFound` | Switch, Modify, Detail | The specified VPC firewall does not exist (often a stale ID) | Re-query the current VpcFirewallId; the pair may not be configured yet |
| `ErrorFirewallSwitch` | ModifyVpcFirewallSwitchStatus | The switch parameter is incorrect | `FirewallSwitch` must be exactly `open` or `close` |
| `ErrorFirewallName` | Create, Modify | The firewall name is invalid | Provide a name of 2~128 characters |
| `ErrorVpcIdError` / `ErrorVpcIdPara` / `ErrorLocalVpcIdPeerVpcIdError` | Create, Detail | A VPC ID parameter is invalid, missing, or inconsistent | Confirm LocalVpcId / PeerVpcId (Detail requires at least one of LocalVpcId / PeerVpcId with the firewall ID) |
| `ErrorRegionNoError` | Create | A region parameter is invalid | Confirm LocalVpcRegion / PeerVpcRegion against a supported region |
| `ErrorAliUid` | All | The aliuid is invalid | Check the credential identity |
| `ErrorInvalidMemberUid` / `ErrorInvalidMemberUidStatus` | All (with MemberUid) | The member UID is invalid or in an unsupported state | Verify `--member-uid` refers to a member of the current management account |

## State / Transition Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorFirewallCannotOpen` | ModifyVpcFirewallSwitchStatus | The firewall status does not allow opening right now | Wait for the state to settle (switching takes 5~30 minutes), then retry |
| `ErrorVpcFirewall.CannotOpen` | ModifyVpcFirewallSwitchStatus | Cannot open in the current state; the message carries the state and a retry-after hint | Follow the retry-after seconds in the message, then retry |
| `ErrorFirewallStatus` | DescribeVpcFirewallList, Detail | Firewall status error | Retry later; the firewall is transitioning |
| `ErrorFirewallStatusCannotModify` | ModifyVpcFirewallConfigure, modify-vpc-firewall-default-ips-config, ModifyVpcFirewallAclEngineMode | The current status does not allow a configuration change | Wait until the firewall is stable (not creating/switching), then modify |
| `ErrorVpcFirewallExist` | CreateVpcFirewallConfigure | A firewall already exists for this peering pair | Query it and use the switch workflow instead of creating |

## Route / CIDR Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorDestCidrError` | Create, Modify | The destination CIDR block is invalid | Re-discover the peering route entries or correct the CIDR JSON |
| `ErrorDestCidrEmpty` | Create, Modify | The target CIDR list is empty | At least one route entry per side is required; confirm the peering routes exist |
| `ErrorSameCidrIp` | Create, Modify | The same CIDR is configured more than once | De-duplicate the CIDR list |
| `ErrorCidrFormat` | Create, Modify | CIDR format error | Use valid CIDR notation (e.g. `192.168.0.0/24`) |
| `ErrorCidrIpAddress` | Create, Modify | Target CIDR error | Correct the target network segment |
| `ErrorCustomRouteEntryMax` | Create, Modify | Too many target CIDRs | Reduce the number of protected route entries |
| `ErrorRouteTableIdNotFound` | Create, Modify | The route table ID does not exist | Re-discover route tables; the ID may be stale |

## Quota / Spec Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorFirewallQuotaNotEmpty` | CreateVpcFirewallConfigure | The VPC firewall quota is exceeded | Purchase more VPC firewall quota in the Cloud Firewall console |
| `ErrorGeneralInstanceSpecFull` | CreateVpcFirewallConfigure | The Cloud Firewall instance spec is full | Upgrade the CFW instance spec, then retry |
| `ErrorBandwidthPenalty` | CreateVpcFirewallConfigure | Bandwidth over-use penalty in effect | Resolve the bandwidth over-use, then retry |
| `ErrorCenVpcEcConflict` | CreateVpcFirewallConfigure | A CEN VPC conflicts with this Express Connect VPC | A VPC pair can be protected by only one connection type; this skill covers the Express Connect / peering family |

## Network / Auth Errors

| Error Code | APIs | Meaning | Action |
|---|---|---|---|
| `ErrorNetworkInterfaceNotFound` | Switch, Modify | The firewall ENI is invalid / its configuration is broken | Do not modify the CFW-created vswitch, route table, or `Cloud_Firewall_Security_Group`; contact support with the RequestId |
| `ErrorAuthentication` | All | Authentication failed | Check AK/SK validity via the CLI validation script |
| `NoPermission` / `Forbidden.RAM` / `Forbidden.*` | All | RAM permission missing | Grant the missing action; the RAM prefix is `yundun-cloudfirewall` (NOT `cloudfw`) |
| `Throttling` | All | Rate limited (10 QPS per user) | Wait a few seconds and retry |

## Skill-emitted codes (not returned by the API)

| Code | Emitted by | Meaning | Action |
|---|---|---|---|
| `RouteDiscoveryFailed` | create | VPC route auto-discovery failed (missing read permission or no peering route) | Grant the VPC read permissions, or pass `--local-cidr-json` / `--peer-cidr-json` |
| `ErrorPreCheckFailed` | create | The local pre-check reported blocking items | Resolve every failed pre-check item, or re-run with `--skip-precheck` after accepting the risk |
| `VerifyFailed` | update, engine ips, engine acl-engine | Post-write read-back did not confirm the requested value | Re-query the firewall; the write may still be converging, or the modify call was rejected after returning 200 |
| `DeletionDisabled` | delete | Deletion is intentionally not supported | Close the switch, then release in the console |
| `ProxyNotFound` | update | The detail lookup for the firewall failed | Verify the VpcFirewallId |
| `ConfirmationRequired` | engine ips, engine acl-engine | A write was requested without `--yes` | Show the impact preview to the user, get an explicit confirmation, then re-run the same command with `--yes` |
| `FirewallNotConfigured` | engine ips, engine acl-engine | The firewall is `notconfigured`, so it has no engine instance to modify | Create and open the VPC firewall first, then adjust the engine settings |

## Important Behavioral Notes

1. **`ModifyVpcFirewallSwitchStatus` returns only a `RequestId`.** A success response means the switch
   request was accepted - it does NOT mean the switch finished. Route re-learning takes 5~30 minutes
   (depends on the route entry count). The only reliable confirmation is polling the query command until
   `FirewallSwitchStatus` becomes `opened` / `closed`.
2. **`ModifyVpcFirewallConfigure` requires the name AND both CIDR table lists.** For a rename-only change,
   read the current values back via the detail command and pass them through unchanged (the `update`
   command does this automatically).
3. **Route entries are discovered locally.** The VPC route APIs do not accept a next-hop filter; fetch all
   entries and keep the ones whose `NextHopType` is `VpcPeer` (VPC peering) or `RouterInterface`
   (Express Connect). `DescribeRouteTableList` returns tables under `RouterTableList.RouterTableListType`.
4. **`DescribeVpcFirewallList` paginates with `CurrentPage` (NOT `PageNo`)**, unlike the NAT firewall
   `DescribeSecurityProxy` API. `FirewallSwitchStatus` accepts `opened` / `closed` / `notconfigured` /
   `configured` / `configuring`.
5. **A `/32` masked peering route is unsupported**: it is not diverted, and enabling the firewall will
   interrupt access to that CIDR. Change the mask to `<= /30` before enabling. The pre-check flags this.
6. **Creation leaves Cloud-Firewall-managed assets behind**: custom route entries (marked `Created by
   cloud firewall. Do not modify or delete it.`) and the `Cloud_Firewall_Security_Group`. Deleting these
   breaks traffic diversion - never remove them while the firewall exists.
7. **The IPS and ACL engine settings are NOT parameters of `CreateVpcFirewallConfigure` /
   `ModifyVpcFirewallConfigure`.** They live behind `modify-vpc-firewall-default-ips-config`
   (`run-mode` 0 observe / 1 block, `rule-class` 1 loose / 2 medium / 3 strict, `basic-rules` and
   `enable-all-patch` 0/1) and `ModifyVpcFirewallAclEngineMode` (`StrictMode` 1 strict / 0 loose).
   `run-mode`, `basic-rules` and `enable-all-patch` are REQUIRED on the IPS modify call while
   `rule-class` is optional, so a partial change must first read the current values and pass the
   untouched required ones through - otherwise the CLI rejects the call.
8. **The service couples `RuleClass` to `RunMode` and does not simply store what you send.** Measured
   live: in observe mode (`run-mode 0`) the stored `RuleClass` is always `0` ("not applicable")
   whatever was passed; in block mode (`run-mode 1`) an omitted `--rule-class` preserves the current
   group, while an explicit `0` is normalized to `3` (strict). A naive read-back that compares against
   the requested value reports a false `VerifyFailed` on every switch to observe mode. Send
   `--rule-class` only when the user asked for the rule group, and derive the expected stored value
   from this coupling; `vpc-fw-engine.sh` does both and reports `rule_class_derived_by_service`.
9. **aliyun CLI 3.4.x registers the two IPS APIs under kebab-case names only.** Calling
   `aliyun Cloudfw DescribeVpcFirewallDefaultIpsConfig` fails with "is not a valid api" and suggests
   `describe-vpc-firewall-default-ips-config`; a kebab-case API name also accepts kebab-case flags
   only. `ModifyVpcFirewallAclEngineMode` and `DescribeVpcFirewallList` are PascalCase and take
   PascalCase flags. The kebab describe API accepts only `--vpc-firewall-id` and `--member-uid` - it has
   no `--lang`.
10. **`DescribeVpcFirewallList` is the only API that returns `AclConfig.StrictMode`.**
    `DescribeVpcFirewallDetail` omits `AclConfig` entirely, so the engine mode must be read from the list
    API (filterable by `--VpcFirewallId`). The list also answers for a `notconfigured` firewall, where it
    reports the account defaults rather than a live instance - label that case explicitly instead of
    presenting it as the current setting. Those defaults are provably not the instance's: `StrictMode`
    was read as `1` while the pair was still `notconfigured` and became `0` after creation.
11. **Both engine modify APIs return only a `RequestId`.** As with the switch API, that proves the
    request was accepted, not that it took effect. Confirm by reading the value back; the skill retries
    three times before reporting `VerifyFailed`.
12. **`configuring` is a real transitional `FirewallSwitchStatus`.** Undocumented, but observed for a
    minute or two after `CreateVpcFirewallConfigure` returns and before the first `closed`. Accept it in
    status validation and keep polling; treating it as an invalid enum aborts a healthy creation. It is
    also counted as `configured` by `assess`, so a pair that is still provisioning is never offered as
    protectable.
13. **`create --dry-run` still runs the pre-check first and stops there when it fails.** That is
    deliberate: a pair that already has a firewall must not be handed a copy-pastable create command.
    The output is the 7-item pre-check plus `ErrorPreCheckFailed`, with no `CreateVpcFirewallConfigure`
    line. Report the blocker instead of inventing a preview; `--skip-precheck` is not the workaround.
14. **A failed `DescribeVpcFirewallList` inside the pre-check is reported as an API failure, not as an
    invisible pair.** `run_precheck` returns `failed_items: ["PeeringPairVisible"]` with a non-empty
    top-level `cfw_list_error` carrying the real error code and text. The suggestion then depends on the
    cause: retry only for `Throttling` / `InternalError`, fix the request for a parameter error, grant
    `yundun-cloudfirewall:DescribeVpcFirewallList` for a permission error. The console Synchronize
    Assets action is the remedy only when the call succeeded and the pair really is absent
    (`cfw_list_error` empty).

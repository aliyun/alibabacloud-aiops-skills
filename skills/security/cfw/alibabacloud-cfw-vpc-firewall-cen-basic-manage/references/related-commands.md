# Command Table

Every `aliyun` command this Skill may run, grouped by purpose. All flags below were
verified against `aliyun {product} {action} --help`.

Commands are in plugin mode throughout: the action name is lowercase words joined
by hyphens. PascalCase API action names are not accepted by the plugin and the
static checker rejects them, so every invocation below uses the hyphenated form.

## Contents

- [1. Local environment commands](#1-local-environment-commands)
- [2. Discovery and inspection](#2-discovery-and-inspection)
- [3. Precheck](#3-precheck)
- [4. Mutating operations](#4-mutating-operations)
- [5. Supporting reads](#5-supporting-reads)
- [6. Cross-product commands](#6-cross-product-commands)
- [7. Not available, or out of scope](#7-not-available-or-out-of-scope)

## 1. Local environment commands

These run locally and reach no cloud API, so they must **not** carry
`--user-agent`.

| Command | Purpose |
|---|---|
| `aliyun version` | Confirm CLI >= 3.3.3 |
| `aliyun upgrade` | Routine CLI update, available from 3.3.5 |
| `aliyun configure list` | The only permitted credential check |
| `aliyun configure set --auto-plugin-install true` | Enable automatic plugin installation |
| `aliyun plugin update` | Refresh installed plugins |
| `aliyun cloudfw --help` | Enumerate the plugin's commands |
| `aliyun {product} {action} --help` | Verify a command, its flags and its enum values |
| `aliyun {product} {action} --cli-dry-run ...` | Print the request without sending it |

## 2. Discovery and inspection

| Command | Key flags | Notes |
|---|---|---|
| `aliyun cloudfw describe-vpc-firewall-cen-summary-list` | `--transit-router-type`, `--current-page`, `--page-size`, `--lang` | Account-level summary, the cheapest entry point |
| `aliyun cloudfw describe-vpc-firewall-cen-list` | `--transit-router-type`, `--cen-id`, `--region-no`, `--firewall-switch-status`, `--vpc-firewall-id`, `--network-instance-id`, `--current-page`, `--page-size`, `--lang` | The primary read. `--cen-id` is optional, so it can scan the whole account. Also accepts a slot id or a VPC id for direct lookup |
| `aliyun cloudfw describe-vpc-firewall-cen-detail` | `--vpc-firewall-id`, `--network-instance-id`, `--lang` | Does **not** accept `--region-no` or `--member-uid` |
| `aliyun cloudfw describe-firewall-task` | `--child-instance-id`, `--task-id`, `--task-type`, `--lang` | `--child-instance-id` takes the **business VPC id**, not a slot id |

`describe-vpc-firewall-cen-list` needs `--transit-router-type Basic` with that exact
capitalisation. The value is case sensitive and is **silently ignored when wrong**,
returning every slot in the account instead. Assert
`LocalVpc.TransitRouterType == "Basic"` on each returned row.

A list row already embeds `IpsConfig` (`BasicRules`, `EnableAllPatch`, `RuleClass`,
`RunMode`), `AclConfig.StrictMode`, `PrecheckStatus` and `MemberUid`, so a status
sweep needs no further call. The row's `PrecheckStatus` is the last stored verdict
and carries no timestamp, so it is a hint rather than a fresh result.

`--page-size` is capped at 50 through the CLI.

## 3. Precheck

| Command | Key flags | Notes |
|---|---|---|
| `aliyun cloudfw create-vpc-firewall-precheck` | `--cen-id`, `--vpc-id`, `--network-instance-type`, `--biz-region`, `--transit-router-id`, `--lang` | Returns a `PrecheckId` immediately |
| `aliyun cloudfw describe-vpc-firewall-precheck-detail` | same as above | Returns the stored verdict |

`--network-instance-type` is `cen_firewall` for CEN Basic. `cen_tr_firewall` is the
Enterprise transit router and `ec_firewall` is Express Connect peering; both are out
of scope. The service does not strongly validate this value, so it is not an edition
guard.

`--biz-region` is the business region and is required in practice - omitting it yields
`400 ErrorRegionNoError`. It is **not** `--region`, which is the global endpoint flag.

The detail call returns whatever verdict the service last stored, so re-issue the
create call before trusting a result.

## 4. Mutating operations

| Command | Key flags | Effect |
|---|---|---|
| `aliyun cloudfw create-vpc-firewall-cen-configure` | `--cen-id`, `--network-instance-id`, `--vpc-region`, `--vpc-firewall-name`, `--firewall-switch`, `--vswitch-id`, `--firewall-vpc-cidr-block`, `--firewall-vswitch-cidr-block`, `--firewall-vpc-zone-id`, `--firewall-vpc-standby-zone-id`, `--firewall-vswitch-zone-id`, `--lang` | Attaches a VPC. `--firewall-switch open` also starts diversion in the same call |
| `aliyun cloudfw modify-vpc-firewall-cen-switch-status` | `--vpc-firewall-id`, `--firewall-switch`, `--lang` | `open` or `close` diversion for one slot |
| `aliyun cloudfw modify-vpc-firewall-cen-configure` | `--vpc-firewall-id`, `--vpc-firewall-name`, `--lang` | **Rename only.** Nothing else is editable |
| `aliyun cloudfw delete-vpc-firewall-cen-configure` | `--vpc-firewall-id-list`, `--lang` | Removes access. Space separated for batching |

None of these accepts a `--client-token`, and none is idempotent - repeating a call
against a slot already in the target state returns an error. Read
`FirewallSwitchStatus` first and skip the call when the desired state is already
reached.

None of them asks for confirmation either. The `--yes` gate belongs to the bundled
script, not to the CLI, so calling these directly bypasses it. Two of the four need one:
starting or stopping diversion, and any removal.

The four regional flags on the create call - firewall VPC CIDR, firewall vSwitch CIDR,
primary zone, standby zone - take effect **only on the first access in a region**,
which is when `FirewallVpc.AllowConfiguration` reads `1`. Afterwards they are fixed
and passing them is ignored. The firewall VPC CIDR must be `10.0.0.0/8`,
`172.16.0.0/12`, `192.168.0.0/16` or a subnet of one, and the vSwitch CIDR must be a
subnet of the firewall VPC CIDR. The mask-length limits stated in the API help
contradict both the service defaults and configurations that were accepted, so they
are not enforced.

`--vpc-firewall-id-list` accepts several slot ids separated by spaces. Whichever call
removes the last access in a region also tears down the shared firewall VPC and runs
considerably longer.

## 5. Supporting reads

| Command | Key flags | Notes |
|---|---|---|
| `aliyun cloudfw describe-vpc-firewall-zone` | `--cen-id`, `--region-no`, `--environment`, `--transit-router-id`, `--lang` | Returns `ZoneList` as two-element arrays, each element an object with `LocalName` and `ZoneId`, each pair a legal primary and standby combination. Pair order is not stable between calls |
| `aliyun cloudfw describe-vpc-zone` | `--region-no`, `--environment`, `--lang` | `--environment VPC` for choosing the business vSwitch zone; `TransitRouter` returns a different list |
| `aliyun cloudfw describe-region-info` | `--source-code`, `--lang` | `--source-code` is **required**; `cfw` returns the 33 CFW regions |
| `aliyun cloudfw describe-user-buy-version` | `--instance-id` | Edition probe. Takes **no** `--lang` flag |
| `aliyun cloudfw describe-vpc-firewall-default-ips-config` | `--vpc-firewall-id` | Takes the **CEN id**. A slot id yields `400 ErrorParametersFirewallId` |
| `aliyun cloudfw describe-vpc-firewall-asset-region-list` | `--vpc-firewall-id` | Takes the **CEN id**. A slot id yields an empty list with HTTP 200, which is indistinguishable from a real empty answer |

Do not compose a primary and a standby zone independently. Pick a pair from
`describe-vpc-firewall-zone`, because an arbitrary combination may be invalid.

## 6. Cross-product commands

Needed to choose the business vSwitch, to explain a precheck failure, and to verify
that regional resources were created or destroyed.

| Command | Key flags | Purpose |
|---|---|---|
| `aliyun vpc describe-vswitches` | `--biz-region-id`, `--vpc-id`, `--page-size` | Candidate vSwitches in the business VPC. Results under `VSwitches.VSwitch[*]` |
| `aliyun vpc describe-vpcs` | `--biz-region-id`, `--vpc-id`, `--page-size` | Confirm `Cloud_Firewall_VPC` exists or is gone |
| `aliyun vpc describe-route-table-list` | `--biz-region-id`, `--vpc-id` | Name the custom route table a failed precheck complains about. Results under `RouterTableList.RouterTableListType[*]` |
| `aliyun ecs describe-network-interfaces` | `--biz-region-id`, `--vpc-id`, `--network-interface-id` | Confirm the diversion ENI exists or is gone |
| `aliyun cbn list-transit-routers` | `--cen-id` | Per-region transit router `Type`, which is where edition actually lives. Diagnostic only: the Skill asserts edition on every returned row instead. Its RAM action is `cen:ListTransitRouters`, not `cbn:` |

In the `vpc` and `ecs` products the API-level region parameter is `--biz-region-id`.
`--region` is the global endpoint override and `--region-id` is not a valid flag:
passing it returns a JSON error object with exit code 0, which a tolerant parser
reads as "nothing found".

**The transit router listing is the one command here whose RAM prefix does not match
its CLI product name.** The CLI product is `cbn`; the RAM action is
`cen:ListTransitRouters`, access level `get`, resource
`acs:cen:*:{accountId}:ceninstance/{ceninstanceId}`. Writing `cbn:ListTransitRouters`
into a policy produces an action that never matches any request, and it surfaces as
`NoPermission` rather than as a policy syntax error - the same trap as using `cloudfw`
in place of `yundun-cloudfirewall`. It is not part of the Skill's own permission set,
because the Skill asserts edition on every row it reads instead; grant it separately,
and only while investigating an edition mismatch by hand.

`aliyun vpc create-vswitch`, `create-route-table`, `associate-route-table`,
`unassociate-route-table`, `delete-route-table` and `delete-vswitch` exist and were
used during verification, but this Skill never calls them. Creating or deleting
customer network resources is outside its contract.

## 7. Not available, or out of scope

| Item | Status |
|---|---|
| `describe-vpc-firewall-manual-vswitch-list` | Exists but unusable: fails with `400 MissingOwnerId` and exposes no `--owner-id` flag. Use `aliyun vpc describe-vswitches` instead |
| `BatchCloseVpcFirewallCen` | Console-only, no CLI command and no RAM action. Close a whole region by iterating the switch call |
| `DescribeVpcFirewallZoneSwitch` | Console-only, no CLI command and no RAM action |
| Asset sync for newly joined VPCs | No CLI equivalent of the console button exists. Direct the user to the console |
| `create-vpc-firewall-cen-manual-configure`, `RouteMode`, `ManualVSwitchId` | Manual route mode. `SupportManualMode` is `0` on Basic, so it is unavailable |
| `*-vpc-firewall-control-policy`, `describe-vpc-firewall-acl-group-list`, batch copy and delete | Access control policies. Outside this Skill's scope |
| `modify-vpc-firewall-default-ips-config`, IPS whitelist and rules | IPS writes. Outside this Skill's scope; the read-only IPS config is in scope |
| `--member-uid` on `describe-vpc-firewall-cen-detail` and `describe-firewall-task` | Not offered, so multi-account detail and task queries are unsupported |

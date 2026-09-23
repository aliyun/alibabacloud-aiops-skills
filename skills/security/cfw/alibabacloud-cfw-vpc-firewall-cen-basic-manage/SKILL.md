---
name: alibabacloud-cfw-vpc-firewall-cen-basic-manage
description: >
  Manage Cloud Firewall (CFW) VPC border firewalls on CEN Basic Edition
  (transit-router-type Basic) on Alibaba Cloud. Use this Skill to inventory the
  VPC firewall slots and their diversion switch status, onboard or offboard a
  business VPC, toggle traffic diversion, and troubleshoot stuck firewall
  states. Only for CEN Basic Edition, not the Enterprise transit router,
  access-control policies, or manual routing.
  管理阿里云云防火墙（CFW）基于云企业网 CEN 基础版的 VPC 边界防火墙；
  仅适用于基础版，不涉及企业版转发路由器、访问控制策略与手动路由模式。
  Triggers: list VPC firewall slots, check VPC firewall diversion switch status, inspect VPC firewall detail and defended CIDR, run the VPC firewall pre-access check, attach a business VPC to the firewall, open or close traffic diversion, rename a VPC firewall, remove a VPC firewall access configuration, query available firewall zone pairs, diagnose a VPC firewall stuck opening or closing, 查看 CEN 基础版 VPC 墙清单与引流开关状态, 为业务 VPC 接入防火墙, 打开或关闭引流, 给 VPC 防火墙改名, 移除 VPC 接入配置, 排查开墙预检查失败或任务卡住
license: Apache-2.0
compatibility: >
  Requires aliyun CLI >= 3.3.3 with the cloudfw plugin installed, and python3
  for the bundled scripts. Compatible engines: qwen-code, qoder, openclaw.
metadata:
  domain: aiops
  owner: cfw-team
allowed-tools: Bash Read
---

## 1. Scenario Description

A CEN Basic Edition transit router interconnects VPCs, VBRs and CCNs in a region.
A VPC border firewall inspects the traffic between them.

Architecture:

```
CEN (Basic transit router, one per region)
  +-- business VPC 1..N -- diversion ENI each --+--> Cloud_Firewall_VPC (shared)
                                                +-- Cloud_Firewall_Security_Group
```

Three facts drive everything else, and the API names obscure all of them. Read
`references/workflow.md` section 1 before reasoning about any response.

**A `vfw-` id is a slot, not a created resource.** It is the stable identity of a
`(CEN, attached VPC)` pair, minted when the VPC joins the CEN. Listing therefore
never "finds nothing" - an unprotected VPC appears as `notconfigured`, which is how
protection candidates are discovered - and removal resets a slot rather than deleting
it, so the id is still listed afterwards and `TotalCount` never changes.

**Three layers have three different lifetimes.** The firewall VPC is shared per CEN
per region: the first access creates it and the last removal destroys it. The
diversion ENI is per VPC. The diversion switch is per VPC and toggles independently.
Removing the last VPC in a region therefore has a far wider blast radius than
removing one of several.

**Two unrelated vSwitches appear in the same call.** `--vswitch-id` is a vSwitch in
the customer's business VPC that will host the diversion ENI, while
`--firewall-vswitch-*` describes a vSwitch inside the CFW-managed firewall VPC.
Different VPCs, usually different zones.

## 2. Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**

> Verify: `aliyun version` — must be >= 3.3.3.
> - First install or major upgrade:
>   `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - Routine update (CLI >= 3.3.5): `aliyun upgrade`
> - Alternative on macOS: `brew install aliyun-cli` / `brew upgrade aliyun-cli`
> - See `references/cli-installation-guide.md` for full instructions.

**Pre-check: plugin readiness**

> ```bash
> aliyun configure set --auto-plugin-install true
> aliyun plugin update
> ```

Run the bundled gate, which checks the CLI version, the `aliyun-cli-cloudfw`
plugin, the active profile and the manifest version in one pass, and prints a JSON
verdict on stdout:

```bash
bash scripts/validate-cli.sh
bash scripts/validate-cli.sh --install-guide      # setup instructions
```

Stop and show the user the install guide when `cli_version_ok`, `plugin_installed`
or `skill_version_ok` is not true: every later step depends on them.

## 3. Environment Variables

Only one variable is used, and it carries no secret:

| Variable | Required | Purpose |
|---|---|---|
| `SKILL_SESSION_ID` | yes, for every command | 32-character lowercase hex id, generated once per session and reused so all calls share one trace |

```bash
python3 -c "import uuid;print(uuid.uuid4().hex)"
```

No credential variable is read, set or requested. The scripts rely on the default
credential chain exactly as the CLI does.

## 4. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
> If no valid profile exists, STOP here: obtain credentials from the RAM console,
> configure them **outside of this session**, then re-run after the profile shows up.

The active profile is the row whose first column ends with ` *`; a plain search for `*`
also matches masked cells such as `AK:***rpY`, so anchor on the column boundary.
`aliyun configure list` is the only permitted credential inspection: it calls no API and
exposes no secret, which is why it is safe where reading a key would not be.

To confirm the credentials actually work against Cloud Firewall, which also checks
the RAM grant:

```bash
SKILL_SESSION_ID={session-id} bash scripts/validate-cli.sh --check-permission
```

It skips rather than issues an unattributed call when `SKILL_SESSION_ID` is absent.
That run also reports the purchased edition as `edition_version`: VPC border firewalls
need Enterprise, Ultimate or pay-as-you-go, and Premium cannot use them. It is advisory
and never blocks, for the reason in `references/workflow.md` pitfall 14. Relay it if an
attach later fails on entitlement.

## 5. RAM Policy and Permission Handling

Full list in `references/ram-policies.md`. The prefix is `yundun-cloudfirewall`, not
`cloudfw`; a policy written with the wrong prefix never matches and surfaces as
`NoPermission` or `ImplicitDeny` rather than as a syntax error, so check the prefix
before concluding the user genuinely lacks access.

Read-only work needs just the Read section. Attaching, switching and removing need
the Write section. Four VPC and ECS read actions are also required, because choosing
the business vSwitch and verifying teardown cross product boundaries.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission
> errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

Three groups, confirmed at different moments, because the third group is only
meaningful in one situation.

| Parameter | Flag | Required | Confirm when |
|---|---|---|---|
| CEN instance id | `--cen-id` | optional | Always, unless discovering first |
| Region id | `--region` | yes | Always |
| Business VPC id | `--vpc-id` | yes for attach and precheck | Always |
| Slot id | `--slot-id` | yes for switch, rename, remove | Confirm a supplied id; when the user gives a firewall name, discover the id with `list` instead of asking them for it |
| Firewall name | `--name` | yes for attach and rename | Always, at most 128 characters |
| Business vSwitch id | `--vswitch-id` | yes for attach | Always; hosts the diversion ENI |
| Diversion at attach | `--firewall-switch` | yes for attach | Always: `close` attaches dormant, `open` also starts diversion |
| Firewall VPC CIDR | `--fw-vpc-cidr` | only on first access in a region | Only when `AllowConfiguration` is `1` |
| Firewall vSwitch CIDR | `--fw-vswitch-cidr` | only on first access in a region | Only when `AllowConfiguration` is `1` |
| Primary and standby zone | `--fw-zone`, `--fw-standby-zone` | only on first access in a region | Only when `AllowConfiguration` is `1` |
| Consent | `--yes` | yes for every removal, every `switch`, and for `--firewall-switch open` | Only after telling the user what it costs |

Read `AllowConfiguration` from the detail call before asking about the last four. When
it is `0` the regional firewall VPC already exists, those parameters are fixed, and
anything the user supplies is silently ignored, so asking would be worse than not
asking. When it is `1` this is the first access in the region and the choice is genuinely
the user's.

Two constraints on the CIDR pair are worth validating before the call: the firewall
VPC CIDR must be `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` or a subnet of one,
and the vSwitch CIDR must be a subnet of the firewall VPC CIDR. Do not enforce the
mask-length limits the API help states; `references/workflow.md` section 4.1 explains
why they cannot be trusted.

Zones come as pairs. Leaving both unset selects dual-active mode, which suits
latency-insensitive traffic; naming both selects active-standby mode, which lowers
latency. Present that trade-off rather than choosing for the user, and take the pair
from the zones subcommand below instead of composing one.

The business vSwitch is a latency decision, not an arbitrary one: the official guide
recommends the same zone as the firewall vSwitch primary zone. List the candidates
for the user instead of picking the first.

```bash
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py zones --region {region}
```

When the user has no CEN id, discover first with the `list` command in section 8.1,
which needs none.

## 7. Observability

Generate one 32-character lowercase hex session id when the Skill loads and reuse it
for every call in the session, so a whole run is attributable to one trace. Regenerate
it only for a new session.

Read the version segment from `references/manifest.json` before any cloud API call. It
is the only permitted source: a missing file, invalid JSON, or an absent, empty or
non-string `version` is a hard stop, because guessing would put a wrong value into every
record for the session. After switching to another Skill and back, re-read this manifest.

User-Agent template, applied to every command that reaches a cloud API:

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
```

Local commands - `configure`, `plugin`, `version`, `upgrade`, `help` - do not support
the flag and must not carry it.

The scripts take the session id from the environment and read the version themselves:

```bash
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py list --region {region}
SKILL_SESSION_ID={session-id} bash scripts/validate-cli.sh --check-permission
```

Two deprecated mechanisms must not be used. The CLI's persistent AI-mode configuration
subcommand rewrites global settings and survives across processes, so an exit path that
misses turning it off leaks the AI user agent into later manual CLI use on that machine.
Exporting a user-agent variable does not survive either, because each tool call starts a
fresh shell. Per-command flags are the only mechanism that works here.

## 8. Core Workflow

All eight operations are subcommands of one script. Each prints a single JSON object
on stdout and progress on stderr, validates its inputs before calling anything, reads
state before mutating, and exits non-zero on failure. Pass `--dry-run` before any
mutating subcommand to see the exact call that would be made; reads still execute, so
the plan reflects real state.

### 8.0 Execution contract
Use `scripts/cfw_cen_basic.py` for every workflow below; do not replace it with raw `aliyun cloudfw` calls. Follow these sequences exactly:

| User intent | Required sequence |
|---|---|
| Inventory or filtered status | `list` once, then report the region, every matched slot/VPC, and its switch status; explicitly report an empty result |
| Detail for the first/selected slot | `list` first, copy the returned id, then `detail --slot-id` |
| Detail by business VPC | `list` first, copy `slots[].VpcId`, then `detail --vpc-id`; do not substitute the slot id |
| Open or close diversion | `list` to resolve a name, explain the impact, wait for a new explicit user confirmation, then run `switch ... --yes` |
| Rename | `list` to resolve a name, then run `rename`; no extra consent is required |
| Remove access | `list` to resolve a name and determine blast radius, explain it, wait for a new explicit user confirmation, then run `remove ... --yes` |
A firewall name or an instruction such as "pick the first slot" is enough for read-only discovery. Never ask the user for an id that `list` can resolve. The original request to change state is not the separate consent required for `switch`, `remove`, or attach-with-open: do not pass `--yes` until the user replies after seeing the operation-specific impact. For a removal, stop after the impact explanation and wait for a second user message that explicitly confirms the named firewall; a dry run, the original request, or the Agent's own summary is never that confirmation. A no-op needs no consent.

Full parameter sets, the state machine and the polling contracts are in
`references/workflow.md`. Error codes and what to do about them are in
`references/api-errors.md`.

### 8.1 Discover and inspect

```bash
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py list [--cen-id {cen-id}] [--region {region}] [--status opened]
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py detail --slot-id {slot-id}
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py detail --vpc-id {vpc-id}
```

The list row already carries `FirewallSwitchStatus`, `PrecheckStatus`,
`DefendCidrList`, `IpsConfig` and `AclConfig.StrictMode`, so a status sweep needs no
further call. The script drops any row whose `LocalVpc.TransitRouterType` is not `Basic`
and reports how many it dropped, because the edition filter is silently ignored when its
value is wrong.

In the final answer, keep each returned slot tied to its VPC and status. For an `opened` filter, exclude other states; when no rows match, report a successful query with zero matches.

`DefendCidrList` holds values before attachment and after removal, since it reflects
the business VPC's own routing. Do not read it as evidence that protection is active.

### 8.2 Precheck before attaching

```bash
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py precheck \
  --cen-id {cen-id} --vpc-id {vpc-id} --region {region}
```

This issues the check and waits for a verdict that is provably fresh, comparing the
returned timestamp against the moment of the call in UTC+8. Reading the stored
verdict without re-issuing reports a problem the user may already have fixed.

On failure the script returns every failing entity across all groups, because only the
top-level status is an aggregate, and resolves the offending custom route tables locally:
a failing entity names no resource, so the service's own `Suggestion` is not actionable
alone. Relay that resolved detail to the user.

Bad input never reaches a verdict: a VPC outside the CEN, a nonexistent VPC id or a
wrong region is rejected with HTTP 400 first. A `failed` verdict is reserved for real
environmental conditions such as quota, route policy or custom route tables.

### 8.3 Attach a VPC

```bash
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py --dry-run attach \
  --cen-id {cen-id} --vpc-id {vpc-id} --region {region} \
  --vswitch-id {vswitch-id} --name {name} [--firewall-switch close|open] [--yes] \
  [--fw-vpc-cidr {cidr} --fw-vswitch-cidr {cidr} --fw-zone {zone} --fw-standby-zone {zone}]
```

Review the dry run with the user, then re-run without `--dry-run`.

Prefer two steps over one: attach with `--firewall-switch close`, verify, then open in a
window the user chooses. `--firewall-switch open` starts diversion immediately and needs
`--yes`, exactly as the switch subcommand does, because the flapping is identical and an
ungated path here would be a way around that gate. A dormant attach needs no consent.

The regional parameters are all-or-nothing and apply only to the first access in a
region; supplying part of the set is rejected rather than partly sent. On a later access
the whole set is dropped with a message, because the regional firewall VPC already
exists. The script locates the slot for the VPC, refuses unless it is `notconfigured`,
reads `AllowConfiguration` to decide whether the regional parameters apply, validates
the CIDR pair, snapshots the previously stored task id, then attaches and waits. It
polls the task by business VPC id and ignores any result that predates the call, then
polls the list until the slot reaches `closed`, or `opened` when diversion was requested
in the same call.

Attaching is not idempotent and there is no client token, so the state check is what
makes a retry safe. If the VPC is already attached the service returns
`ErrorFirewallStatus` with a message telling the caller to try again later; retrying
never succeeds. Report that the VPC is already attached and ask whether the user
wants to switch, rename, or remove and recreate.

### 8.4 Open or close diversion

```bash
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py switch \
  --slot-id {slot-id} --switch open|close --yes
```

Before passing `--yes`, tell the user that established long-lived connections flap for
sub-second intervals while short connections are unaffected, that SLB and RDS sessions
can drop so a low-traffic window is advised, that the operation cannot be paused or
rolled back, and that the guide allows 5 to 30 minutes by route entry count. Without
`--yes` the script prints that list and stops, so it cannot be skipped by accident.

It checks the current state first and only then asks for confirmation, so a no-op never
demands `--yes`: a gate that fires on no-ops teaches the caller to pass the flag by
reflex, which disarms it on the run where it matters. It short-circuits when the slot is
already in the requested state, because repeating the call returns `-360142` rather than
succeeding. It refuses a `notconfigured` slot, which has nothing to switch, and waits
for a transient state to settle. Polling treats `opening` and `closing` as progress.

A poll that times out, or that loses the ability to read status, reports
`outcome: "unknown"` rather than a plain failure, as section 9 describes. Never re-issue
the switch: the repeat returns `ErrorFirewallStatus` or `-360142` and neither will ever
succeed.

To close every slot in a region, list them and iterate. There is no batch close in
the CLI; the console action has no command and no RAM action.

### 8.5 Rename

```bash
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py rename --slot-id {slot-id} --name {new-name}
```

Renaming is the only editable field. The console labels this operation "edit", which
suggests it can revise the configuration; it cannot. The firewall VPC CIDR, the
vSwitch CIDRs, the zones and the business vSwitch are fixed after creation, and the
only way to change them is removal followed by a fresh attach. Tell the user that
when they ask to change one of them.

The slot must be attached first; a `notconfigured` slot returns
`ErrorFirewallStatusCannotModify`.

### 8.6 Remove access

```bash
SKILL_SESSION_ID={session-id} python3 scripts/cfw_cen_basic.py remove --slot-id {slot-id} --yes
```

This is the highest-impact operation in the Skill, so `--yes` is required on every
removal, not only the last one in a region: it destroys a working configuration, and
restoring it means a fresh attach plus an open, which flaps connections again. The
script also counts the other configured slots in the same region and, when this is the
last one, widens the warning: removal also destroys the shared regional firewall VPC,
its vSwitch and its security group, and the next attachment in that region must recreate
all of them and supply the CIDR and zone pair again. Pass `--yes` only after the user
has agreed.

It skips a `notconfigured` slot without asking for confirmation, because that slot is
already removed and the call would only return `-360134`. It waits for a transient
state to settle. It warns when the slot is `opened`, because closing diversion first is
the verified path; removing straight from `opened` needs `--force-open` and is
unverified. That is a second gate, separate from `--yes`: one confirms the consequence,
the other an unverified path.

Afterwards it confirms the reset. Every removal must clear the slot name and diversion
ENI; only the last configured slot in a region must also clear the shared
`Cloud_Firewall_VPC`. Matching that fixed name is more reliable than matching on a CIDR
the operator chose. Reaching `notconfigured` is not on its own enough: a slot can report
the reset status while still holding an ENI, so the reported success requires every
applicable reset check to pass. If the slot has left the list entirely, that is also a
removal end state and is reported as one.

Removal is the slowest operation observed, up to 140 seconds on a lightly routed CEN
and longer when it tears down the region. The timeout allows 35 minutes.

## 9. Success Verification Method

The scripts verify as they go and include the result in their JSON, so a separate
pass is usually unnecessary. Check these fields in the response:

| Operation | Confirms success |
|---|---|
| attach | `task.finished` true, `switch.reached` true, `detail.Eni.EniId` non-empty, `detail.Eni.matches_requested_vswitch` true |
| switch | `result.reached` true and `result.path` shows the transient state it passed through |
| rename | `ok` true, meaning the re-read name equals the requested one |
| remove | `result.reached` true plus every reset check in `reset_confirmed` true |
| precheck | `is_fresh` true, which proves the verdict belongs to this run |

`reset_confirmed` reports the status returning to `notconfigured`, the firewall VPC
and ENI cleared, the name cleared, and `AllowConfiguration` back to `1` when the
region was released.

Every write reports one of three outcomes, and they must not be conflated:

| `outcome` | Means | Response |
|---|---|---|
| `confirmed` | The change landed and verification agreed | Report success |
| `unknown` | The write was accepted; verification did not complete | Recheck with the `recheck` command. Never re-issue the write |
| `confirmed_incomplete` | The transition finished but a check came back negative | Follow `investigate`. Rechecking cannot change this answer |

Both unsuccessful outcomes exit non-zero and carry `mutation_sent: true` and
`do_not_retry`. Treating either as a plain failure and retrying is the most damaging
mistake available here, because no operation is idempotent. A non-zero exit with
`mutation_sent: false` is the opposite case: nothing was sent, so retrying is correct.
`stage: lock` is that case.

Step-by-step commands for verifying by hand, including the cross-product checks
against VPC and ECS, are in `references/verification-method.md`. That file also has a
short diagnostic order for the common case where a change appears not to have taken
effect, which is usually a transient state or a stale read rather than a failure.

## 10. Cleanup

Removing access is the cleanup path, covered in section 8.6. Two things look like a
failed cleanup but are not: the slot id stays listed, because removal resets a slot
rather than deleting it (section 1); and `DefendCidrList` still holds values (section 8.1).

When the last access in a region was removed, the `regional_teardown` block in the
remove output reports whether a VPC named `Cloud_Firewall_VPC` still exists. To check
the diversion ENI independently use `references/verification-method.md` section 5, which
also covers `--biz-region-id` and why an empty answer must not be trusted as it stands.

The skill creates no local files, so there is nothing else to clean up. The firewall
VPC, its vSwitch and the security group are removed by the service as part of the last
regional removal; never delete them by hand, because the security group and its allow
rule are load-bearing while any firewall in that region is active.

## 11. Command Tables

`references/related-commands.md` lists every command this Skill may run, with the
verified flags, the cross-product commands, and what has no CLI equivalent or is unusable.
Read it before composing a call by hand: several actions take the CEN id where a slot id
looks natural.

## 12. Best Practices

`references/acceptance-criteria.md` has the full correct-and-incorrect pairs. The
ones that cause the most damage:

- Assert `LocalVpc.TransitRouterType` is `Basic` on every row before acting. The filter
  is case sensitive and silently dropped when wrong, returning every slot in the account
  with HTTP 200 and no warning.
- Never translate `ErrorFirewallStatus` (already attached) or `ErrorVpcFirewallExist`
  (the slot id does not exist) into success; both messages say the opposite of the truth.
- Never mutate one region from two runs at once. The firewall VPC is a regional
  singleton, so `attach` and `remove` hold a host-local lock and refuse with
  `stage: lock` and `mutation_sent: false` if another run has it. Wait and retry.
- Size timeouts from the official guide, not from a quick test. A lightly routed CEN
  finishes in under a minute where the guide allows 30.
- A nonexistent CEN id returns `TotalCount: 0`, which cannot be told apart from a CEN
  with no attached VPCs; confirm the id before reporting a VPC unprotected.
- State the scope limits: IPv6 is not protected, `100.64.0.0/10` is not diverted, at most
  31 VPCs per CEN per region, and the firewall VPC consumes VPC and transit router quota.
- A VPC missing from the list needs the console's asset sync, which has no CLI
  equivalent; manual route mode is unavailable on Basic.
- Treat a `failed` precheck as blocking and ask before proceeding. Whether it truly
  blocks attachment is unconfirmed, and attaching into an environment the service has
  just flagged is not worth the risk.

## 13. Reference Links

- `references/workflow.md` — resource model, state machine, asynchronous contracts,
  parameter reference, operational pitfalls
- `references/api-errors.md` — error catalogue, retry policy, silent failures, precheck
- `references/verification-method.md` — step-by-step verification commands
- `references/related-commands.md` — full command table with verified flags
- `references/acceptance-criteria.md` — correct and incorrect usage pairs
- `references/ram-policies.md` — required RAM actions and resource ARNs
- `references/cli-installation-guide.md` — CLI installation and troubleshooting
- [Configure a VPC firewall for a Basic Edition transit router](https://help.aliyun.com/zh/cloud-firewall/cloudfirewall/user-guide/configure-a-vpc-firewall-for-a-basic-edition-transit-router)
- [Cloud Firewall RAM permission list](https://help.aliyun.com/zh/cloud-firewall/cloudfirewall/developer-reference/api-cloudfw-2017-12-07-ram)

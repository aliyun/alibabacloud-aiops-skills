# API Error Handling

Every code below was observed live against CEN Basic Edition VPC firewalls. The
`Accurate` column is the one that matters when deciding how much of the message to
relay to the user verbatim.

## Contents

- [1. Error catalogue](#1-error-catalogue)
- [2. Two messages that actively mislead](#2-two-messages-that-actively-mislead)
- [3. Retry policy](#3-retry-policy)
- [4. Silent failures: HTTP 200 with a wrong answer](#4-silent-failures-http-200-with-a-wrong-answer)
- [5. Precheck failures are not API errors](#5-precheck-failures-are-not-api-errors)
- [6. Permission errors](#6-permission-errors)

## 1. Error catalogue

All observed cases are HTTP 400.

| Code | Message | Raised by | Accurate |
|---|---|---|---|
| `-360142` | `firewall is already opened` | opening an already `opened` slot | yes |
| `ErrorFirewallNotConfig` | `Firewall not config` | switching a `notconfigured` slot, either direction | yes |
| `ErrorFirewallStatusCannotModify` | `Current firewall status, configuration not allowed` | renaming a `notconfigured` slot | yes |
| `ErrorRegionNoError` | `Region invalid.` | precheck with a region the VPC is not in, or `--biz-region` omitted | yes |
| `ErrorVpcFirewallNotFound` | `Vpc firewall not found.` | precheck with a VPC outside the CEN, or a nonexistent VPC id | yes |
| `ErrorParametersFirewallId` | - | IPS config called with a `vfw-` slot id instead of the CEN id | yes |
| `-360133` | `firewall id invalid` | `describe-vpc-firewall-asset-region-list` with no id | yes |
| `-360134` | `firewall status error` | deleting a `notconfigured` or `deleting` slot | vague |
| `ErrorFirewallStatus` | `Firewall status error, please try again later.` | attaching a VPC that is already attached | **misleading** |
| `ErrorVpcFirewallExist` | `The firewall has been configured and cannot be created repeatedly` | a slot id that does not exist | **misleading** |

`ErrorPreCheckDoing` also arrives as HTTP 400, but unlike every code above it is not
a failure - it means the precheck is still running. See section 3.

## 2. Two messages that actively mislead

These two will send an agent down the wrong path if the message is taken at face
value, so handle them by code and never by text.

**`ErrorFirewallStatus` says "please try again later".** Retrying never succeeds,
because the real cause is that the VPC is already attached to the firewall. Backing
off and retrying turns a one-line answer into an indefinite loop. Treat the code as
terminal for the attach path: re-read `FirewallSwitchStatus`, report that the VPC is
already attached, and ask what the user actually wants - rename, switch, or remove
and recreate.

**`ErrorVpcFirewallExist` reads as "already exists, so this is effectively done".**
It is raised when the slot id does not exist at all. Mapping it to success reports a
completed firewall that was never created. Verify the id against
`describe-vpc-firewall-cen-list` before interpreting it, and tell the user the id is
not a valid slot for that CEN.

Note the asymmetry with a bad CEN id: that raises nothing at all and returns
`TotalCount: 0`, so it cannot be distinguished from a CEN that simply has no attached
VPCs.

## 3. Retry policy

| Situation | Retry? | Why |
|---|---|---|
| `ErrorPreCheckDoing` on the precheck detail call | **Yes**, poll | It is the service's "still running" signal. It arrives as HTTP 400 with a non-zero exit, so it is easy to mistake for a real failure and abort a healthy precheck |
| `IncorrectStatus.RouteTable` from `vpc associate-route-table` | **Yes**, poll for `Status: Available` | A freshly created route table is briefly unusable |
| `dial tcp ...: connect: bad file descriptor` | **Yes**, once | Transport or environment fault, not an API error. Observed on the `cloudfw` plugin while `vpc`, `ecs` and a direct `curl` to the same endpoint all succeeded; an identical retry worked |
| Transient slot states `opening` / `closing` / `deleting` | **Yes**, keep polling the list | Expected on the way to a steady state |
| A failed status read **during** a poll loop | **Yes**, up to six in a row | The write is already in flight and a failed read says nothing about it. Count consecutive failures, not cumulative ones: scattered faults over a 35 minute window are normal, and a cumulative cap would abort a healthy transition because of early jitter |
| Six consecutive failed status reads | No, stop and report `outcome: unknown` | Sustained unreadability. The write was accepted, so this is an unconfirmed outcome, not a failure. Report the measured elapsed time, not the interval times the count: one read can block for the CLI timeout plus a retry, so six slow failures span minutes |
| A poll timeout | No, report `outcome: unknown` | Same as above. The most likely truth is that the operation succeeded slowly |
| `ErrorFirewallStatus` on attach | No | Already attached; retrying never helps |
| `ErrorFirewallNotConfig` on switch | No | The slot needs attaching first |
| `-360142` on open | No | Already in the desired state |
| `-360134` on delete | No | Already `notconfigured`, or already deleting |
| `ErrorVpcFirewallExist` | No | The slot id does not exist |
| `ErrorRegionNoError`, `ErrorVpcFirewallNotFound` | No | Input is wrong; fix the parameters |
| Permission errors | No | Read the RAM policy list, diagnose the grant, pause for the user |
| `stage: lock` with `mutation_sent: false` | Yes, after the other run finishes | Another run on this host holds the regional write lock, so this command never started. Nothing was sent, which makes this the one non-zero exit on a write path that is safe to repeat |

**No mutating call in this product is idempotent.** Repeating any of attach, open,
close, delete or rename against a slot already in the target state returns an error
rather than a no-op, and none of these actions accepts a `ClientToken`. Idempotency
therefore has to be built as check-then-act: read `FirewallSwitchStatus` first, and
skip the call when the slot is already where the user wants it.

**Timeouts must come from the official guide, not from observed test timings.** The
guide budgets about 5 minutes to create and 5 to 30 minutes to open or close
depending on route entry count, plus 15 to 30 minutes of route relearning after a
route table change. A lightly routed test CEN completed the same operations in 28 to
140 s, which is not representative. A timeout tuned to those numbers reports healthy
slow operations as failures on a production CEN. Budget at least 30 minutes for a
switch transition and 10 minutes for an attach task, and keep polling rather than
declaring failure early.

Do not add `--read-timeout` or `--connect-timeout` to a plugin-mode call: the
`cloudfw` plugin does not expose them and rejects the flag. The CLI applies its own
default timeouts, which is also why no explicit timeout declaration is required for
these commands.

**An unconfirmed outcome must not be reported as a failure.** Once a write has been
accepted, the only three honest results are `confirmed`, `confirmed_incomplete`, and
`unknown`.

A refusal carrying `mutation_sent: false` sits outside that set, because no write was
accepted. `stage: lock` is the case: `attach` and `remove` take a host-local lock keyed
on the region before reading anything that decides what to write, since the firewall VPC
is a regional singleton and two runs that both read it as absent would each try to create
it. The payload names the holding process and the lock file, has no `outcome` field, and
is the one non-zero exit on a write path where retrying is the correct response. A lock
whose holder is gone, or which is older than the longest bounded operation, is reclaimed
automatically. A run that finds nowhere writable to keep a lock proceeds without one and
says so, rather than refusing to work.

`unknown` covers a timeout or a lost status read: the state may still settle, so the
payload carries `mutation_sent: true`, an explicit instruction not to retry, and the
exact command that rechecks the slot.

`confirmed_incomplete` is the opposite and must stay separate. The transition finished
and a verification check came back negative - a slot reporting `notconfigured` while it
still holds a diversion ENI, or a switch reaching `opened` with no ENI provisioned. No
amount of waiting changes it, so the payload names the failing check and where to look
instead of offering a recheck. Collapsing it into `unknown` sends the caller round a
recheck loop whose answer cannot change; collapsing it into success is worse, because
that one reports traffic as protected, or as no longer diverted, when it is neither.

Presenting either as a plain failure invites the caller to repeat the write, and every
repeat lands in the "No" rows above - the worst being `ErrorFirewallStatus`, which reads
like a transient fault and tells the caller to try again later.

One parsing trap applies to every code in the table above: the SDKError blob contains
both a `StatusCode: 400` line and a `Code:` line carrying the real error code, so a
naive search for `Code:` matches the status line first and yields `400`. Read the
embedded JSON `Code` field, or anchor the search so it cannot match inside
`StatusCode:`.

## 4. Silent failures: HTTP 200 with a wrong answer

These four return a success status while giving a result that must not be acted on.
They are more dangerous than the 400s above because nothing signals a problem.

| Trigger | What comes back | Why it is dangerous |
|---|---|---|
| `--transit-router-type basic` (lowercase) or any invalid value, or the flag omitted | Every slot in the account, all editions | The filter is dropped without a warning, so out-of-scope slots enter the result set |
| `describe-vpc-firewall-asset-region-list` given a `vfw-` slot id | `RegionNoList: []` | Indistinguishable from "no regions" |
| A nonexistent `--cen-id` on the list call | `TotalCount: 0` | Indistinguishable from a CEN with no attached VPCs |
| A wrong region flag (`--region-id` instead of `--biz-region-id`) on `vpc` or `ecs` commands | A JSON object with no `TotalCount` key, exit code 0 | A parser using a default reports "nothing found", which can fake a successful cleanup |

Defences, in order of value:

1. Pass the exact string `Basic`, and assert `LocalVpc.TransitRouterType == "Basic"`
   on every row before acting. This assertion holds regardless of whether the filter
   was applied.
2. When an answer is empty, confirm the identifier was of the right kind before
   reporting "nothing found".
3. Assert that an expected response key exists before reading it with a default.

## 5. Precheck failures are not API errors

A `failed` verdict arrives as HTTP 200 with a populated body, so it never surfaces as
an exception and must be read deliberately. Do not confuse it with
`ErrorPreCheckDoing`, which is an HTTP 400 that means "not finished yet".

A failing entity carries only `Name`, `Status`, `Info` and `Suggestion`. There is no
code and no resource identifier, so match on `Name`. `Suggestion` is the remediation
text worth relaying; `Info` restates the check name as an assertion and adds nothing.

Observed failure, from the custom-route-table check:

```
PrecheckStatus    failed
group             路由策略检查            FailedCount 1
entity Name       在云企业网中VPC是否存在自定义路由表且绑定vSwitch
entity Info       在云企业网中VPC存在自定义路由表且绑定vSwitch
entity Suggestion 您可以删除相关的自定义路由表或vSwitch解除绑定自定义路由表
```

Neither field says which route table or which vSwitch, so the answer is not
actionable as-is. Resolve it locally with `aliyun vpc describe-route-table-list
--biz-region-id {region} --vpc-id {vpc}` and report the entries whose
`RouteTableType` is `Custom` together with their bound `VSwitchIds`.

Walk every group and every entity: only the top-level `PrecheckStatus` is an
aggregate, and just the offending group flips while the others still report `passed`.

Because the verdict persists server-side, re-issue
`create-vpc-firewall-precheck` after the user fixes something. Reading the stored
verdict alone will report a problem that no longer exists.

Whether a `failed` verdict actually blocks `create-vpc-firewall-cen-configure` or is
merely advisory is unconfirmed. Treat it as blocking and ask the user before
proceeding, which is the safe reading either way.

## 6. Permission errors

A policy written with the `cloudfw` prefix instead of `yundun-cloudfirewall` never
matches, and the failure surfaces as `NoPermission` or `ImplicitDeny` rather than as
a policy syntax error - so a policy that looks correct in the console can still deny
every call. Check the prefix before concluding that the user genuinely lacks access.

On any permission failure, read this Skill's RAM permission list for the required
actions, use the `ram-permission-diagnose` skill to guide the user through the
request, then pause until the user confirms the grant has been made.

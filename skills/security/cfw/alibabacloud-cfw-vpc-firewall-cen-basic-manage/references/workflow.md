# CEN Basic VPC Firewall Workflow

Runtime knowledge for the eight operations in this Skill: the resource model that
the API names obscure, the state machine every flow keys on, the three
incompatible asynchronous contracts, the parameter sets, and the pitfalls that
produce silently wrong answers.

## Contents

- [1. The resource model](#1-the-resource-model)
- [2. Switch status state machine](#2-switch-status-state-machine)
- [3. Asynchronous polling contracts](#3-asynchronous-polling-contracts)
- [4. Parameter reference](#4-parameter-reference)
- [5. Operational pitfalls](#5-operational-pitfalls)

## 1. The resource model

The action names are misleading and cost real debugging time if taken at face
value. `CreateVpcFirewallCenConfigure` does not create a firewall instance, and
`DeleteVpcFirewallCenConfigure` does not delete one.

### 1.1 A `vfw-` id is a slot, not a created resource

A `vfw-` id is the stable identity of a `(CEN, attached VPC)` pair. It is minted
when the VPC joins the CEN, not when the firewall is configured. Verified two
ways: `TotalCount` stayed constant across two full create-and-delete cycles with
the same three ids, and `create-vpc-firewall-cen-configure` returned a slot id
that already existed before the call.

Consequences:

- Listing never "finds nothing". An unprotected VPC appears as `notconfigured`,
  which is exactly how protection candidates are discovered.
- Removal is a reset to `notconfigured`, not a deletion. Reporting "firewall
  deleted" and then still seeing the id is correct behaviour, not a bug.
- A slot id supplied by the user must be checked against the list before use. An
  id that does not exist produces an error whose message claims the opposite, so
  never infer "already done" from an error code alone.

### 1.2 Three layers, three different lifetimes

| Layer | Scope | Created by | Torn down by |
|---|---|---|---|
| Firewall VPC (`Cloud_Firewall_VPC`) with its vSwitch and security group | One per CEN **per region**, shared | The **first** VPC access in that region | The **last** access removal in that region |
| Diversion ENI inside the business VPC | One per attached VPC | Every access configuration | That VPC's access removal |
| Diversion switch (`FirewallSwitchStatus`) | One per attached VPC | Toggled independently | Toggled independently |

The regional firewall VPC is a separate VPC that Cloud Firewall provisions in the
customer account; it is not one of the business VPCs. Inspecting a second VPC in
the same region returns the **same** firewall VPC id, which is the direct evidence
that the layer is shared.

Auto-created resources carry fixed names, which makes them reliable assertions:

| Resource | Name |
|---|---|
| firewall VPC | `Cloud_Firewall_VPC` |
| firewall vSwitch | `Cloud_Firewall_VSWITCH` |
| security group, on the firewall VPC **and** on each business VPC | `Cloud_Firewall_Security_Group` |
| route entries | remark `Created by cloud firewall. Do not modify or delete it.` |

### 1.3 `AllowConfiguration` tells you which case you are in

| Moment | `FirewallVpc.VpcId` | `AllowConfiguration` | Meaning |
|---|---|---|---|
| Before any access in the region | `""` | `1` | First access - firewall VPC CIDR and zones are the user's to choose |
| After the first access | `vpc-...` | `0` | Firewall VPC exists - those parameters are fixed |

Read this before building an attach call rather than guessing, because it decides
whether asking for CIDR and zone values is even meaningful. It is **not** an
edition discriminator - use `LocalVpc.TransitRouterType` for that.

### 1.4 Two unrelated vSwitches, easily conflated

| Parameter | Which VPC | Purpose | Lifetime |
|---|---|---|---|
| `--firewall-vswitch-cidr-block`, `--firewall-vswitch-zone-id` | The CFW-managed firewall VPC | vSwitch used for traffic handling | Regional, first access only |
| `--vswitch-id` | The customer's **business** VPC | Hosts the diversion ENI | Per VPC, every access |

After an attach, `LocalVpc.EniList[0].EniVSwitchId` equals the `--vswitch-id` that
was passed. That equality is the assertion that the ENI landed where intended.

### 1.5 The three-step provisioning task

`describe-firewall-task` names what an access actually builds:

```
创建云防火墙安全组     create the cloud firewall security group
配置云防火墙VPC        configure the cloud firewall VPC
创建云防火墙弹性网卡   create the cloud firewall ENI
```

Step-level progress separates regional work from per-VPC work. On a first access
all three run from scratch. On a subsequent access in the same region, steps 1 and
2 report `finished` within about ten seconds because those resources already
exist, and only the ENI is built. This is the cheapest way to tell the two cases
apart while the task is still running.

## 2. Switch status state machine

```
notconfigured  --[create configure]-->  closed  --[open]-->  opening  -->  opened
      ^                                   ^                                  |
      |                                   |                                  |
      +---[deleting]<--[delete configure]--+---  closed  <--  closing  <------+
                                                                  [close]
```

| Status | Kind | Meaning |
|---|---|---|
| `notconfigured` | steady | VPC is attached to the CEN, no firewall access configured |
| `closed` | steady | Access configured, ENI exists, diversion switch off |
| `opened` | steady | Diversion switch on, traffic being inspected |
| `opening` | transient | Switch turning on |
| `closing` | transient | Switch turning off |
| `deleting` | transient | Access configuration being removed |

Two cautions:

- The `--firewall-switch-status` filter enum documented in the CLI help is
  `opened / closed / configured / notconfigured`. **The filter values and the
  returned values are not the same set**: `configured` has never been observed,
  while `opening`, `closing` and `deleting` all occur in practice. Polling logic
  that does not tolerate the three transient states will misread a healthy
  transition as an unexpected one.
- There is no shortcut from `notconfigured` straight to `opened`. Access must be
  configured first, so enabling protection on a fresh VPC is inherently two calls
  unless `--firewall-switch open` is passed at attach time.

Observed transient durations on a lightly routed test CEN: `opening` to `opened`
30 to 46 s, `closing` to `closed` 28 to 34 s, `deleting` to `notconfigured` 61 s
for a normal removal and 123 to 140 s when it was the last access in the region.
The official guide budgets far longer - about 5 minutes to create and 5 to 30
minutes to open or close, depending on route entry count. Size timeouts from the
guide, not from a lightly loaded test environment.

## 3. Asynchronous polling contracts

Three different patterns appear. They are not interchangeable.

### 3.1 Precheck - a 400 that means "still running"

`create-vpc-firewall-precheck` returns a `PrecheckId` immediately. Polling
`describe-vpc-firewall-precheck-detail` before the check finishes fails with
**HTTP 400** and `Code: ErrorPreCheckDoing`. That is a retry signal, not a failure;
treating it as a failure aborts a healthy precheck. It is the single easiest mistake
in this workflow, because a 400 status normally does mean an error, and the CLI
surfaces it as a non-zero exit.

One parsing trap goes with it: the error blob contains both `StatusCode: 400` and
`Code: ErrorPreCheckDoing`, so a naive search for `Code:` matches the status line
first and yields `400`. Read the embedded JSON `"Code"` field, or anchor the search
so it cannot match inside `StatusCode:`.

Settled response shape:

```
IsFound                              true
PrecheckDetail.PrecheckStatus        passed | failed
PrecheckDetail.PrecheckTimestamp     "YYYY-MM-DD HH:MM:SS"
PrecheckDetail.FirewallId            the CEN id
PrecheckDetail.NetworkInstanceId     the business VPC id
PrecheckDetail.RegionNo              the business region
PrecheckDetail.PrecheckEntityGroups  [ {Name, PrecheckEntityGroupStatus, FailedCount, PrecheckEntities} ]
PrecheckEntities                     [ {Name, Status, Info, Suggestion} ]
```

Three groups and twelve entities are checked:

```
账号地域检查
    - 云企业网中VPC所在的地域是否都是VPC边界防火墙支持的地域
VPC规格检查
    - 云企业网中只有1个网络实例或不存在VPC
    - 开启防火墙的VPC是否已开启高速通道防火墙
    - 是否同地域可以开启防火墙的VPC数量超过上限
    - 防火墙配额是否已满
    - 每个地域不超过该地域的vpc数目上限减一（即VPC边界防火墙会占用1个配额）
路由策略检查
    - 校验网段是否重复配置, 目前只允许VBR和VBR的网段重复, VPC和VPC、VPC和VBR不能重复
    - 检查策略路由优先级配额是否足够
    - 在云企业网中VPC是否存在自定义路由表且绑定vSwitch
    - 云企业网中是否存在拒绝类型的路由策略（系统默认的优先级为5000拒绝类型路由策略除外）
    - VPC实例自定义路由数是否超过上限
    - 云企业网开墙后的路由数不超过云企业网路由数上限
```

On failure, walk **every** group and entity: only the top-level `PrecheckStatus`
is an aggregate, and the offending group is the only one that flips while the
others still report `passed`. A failing entity carries just four keys - `Name`,
`Status`, `Info`, `Suggestion`. There is no error code and no resource identifier,
so failures can only be matched on `Name`. `Suggestion` holds the remediation
text; `Info` merely restates the check name as an assertion and adds nothing.
Neither names the offending resource, so resolve it locally - for the custom route
table check, `aliyun vpc describe-route-table-list --biz-region-id {region}
--vpc-id {vpc}` and report entries whose `RouteTableType` is `Custom` with their
bound `VSwitchIds`.

Bad input never reaches a verdict. A VPC outside the CEN, a nonexistent VPC id or
a wrong region is rejected with HTTP 400 before the check runs.

The stored verdict is keyed by the four-tuple of CEN, VPC, network instance type
and region, and it persists. Reading it without re-issuing the create call returns
whatever the service last stored, including a `failed` verdict for a problem the
user has since fixed.

### 3.2 VPC access provisioning - task polling

`create-vpc-firewall-cen-configure` returns the slot id immediately while
provisioning continues. Poll `describe-firewall-task` with `--child-instance-id`
set to the **business VPC id**, not the `vfw-` slot id:

```
TaskStatus          init -> running -> finished
TaskId              integer
TaskName            创建VPC边界防火墙任务
TaskWaitingTime     30
TaskSteps           [ {StepName, StepStatus, ...} ]
```

`TaskWaitingTime` is a hint, not the real duration. Observed 111 to 116 s for a
first access in the region and 46 to 49 s for a subsequent one, against an official
budget of about 5 minutes.

The task result also persists server-side, so snapshot `TaskId` and
`TaskStartTimestamp` before the mutating call and ignore any poll that returns the
snapshot id or a start time earlier than the call. Without that, a naive poll reads
the previous run's `finished` and reports instant success.

### 3.3 Switch and removal transitions - list polling

Switch changes and access removals expose no task API. Re-read
`describe-vpc-firewall-cen-list` until `FirewallSwitchStatus` leaves the transient
state and settles on the target. Observed transitions took 28 to 140 s, against an
official budget of 5 to 30 minutes, so the timeout must be sized from the guide and
not from a quick run. A 10 s interval keeps the call count over a 35 minute window
low enough not to invite throttling.

Removal has one extra outcome to recognise. A slot normally stays listed and resets
to `notconfigured`, but it can instead leave the list altogether. Both are the same
end state, and a poll that only accepts `notconfigured` reports a successful removal
as a timeout. Absence must be treated as success for removal only: during a switch
the slot is known to be listed, so its disappearance means the filter or the id is
wrong, and calling that success would hide the mistake.

### 3.4 What a poll may report

All three contracts poll after a write has already been accepted, which constrains
what they are allowed to conclude.

A failed read is not a result. Distinguish three outcomes and never collapse them: the
read did not happen, the read succeeded and the slot is absent, and the read succeeded
with a status. Reporting absence for a failed read is the worst of the three, because
during removal absence reads as "already removed".

An intermittent read failure must be retried, not surfaced. Throttling and transient
transport faults were both observed against this plugin, and neither says anything
about the change in flight. The counter that gives up has to be consecutive rather than
cumulative: over a 35 minute window a handful of scattered failures is normal, and a
cumulative cap would abort a healthy long transition because of early jitter. Six
consecutive failures is the point where continuing stops being useful.

What that costs in wall-clock time is not the interval times the count. A single read
can block for the CLI's own timeout plus one transport retry, so six *slow* failures
span minutes rather than a minute. Report the measured elapsed time instead of
multiplying out the interval, or the diagnostic sends the reader looking for the wrong
class of fault.

A permission denial is the exception. It will not clear on retry, so it aborts at once;
retrying it only buries the real cause under noise. Decide that on the error **code**
rather than on the whole message: a retryable server error whose text merely contains a
word like Forbidden would otherwise abandon a write that was still landing.

Polling is also not free. A fixed ten second interval across a 35 minute window issues
over two hundred list calls for one operation, which is itself enough to invite the
throttling that then shows up as these read failures. Poll tightly for the first two
minutes, where the fast completions land, then back off.

Giving up, and timing out, are both an **unconfirmed outcome rather than a failure**.
The payload has to say so explicitly, because the natural response to a non-zero exit
is to repeat the write, and nothing here is idempotent: the repeat returns
`ErrorFirewallStatus`, `-360142` or `-360134`, and the first of those tells the caller
to try again later, which can never succeed. Carry `mutation_sent`, an `outcome` of
`unknown`, an instruction not to retry, and the exact command that rechecks the slot.

A poll only ever produces `confirmed` or `unknown`, because reaching the target state is
all it can observe. The verdict on whether the operation actually did its job belongs to
the step after the poll, which compares the provisioned resources against what was asked
for - and that step has a third answer, `confirmed_incomplete`, for a transition that
finished while its side effects did not. Keep it distinct from `unknown`: one says the
answer may still change, the other says it will not.

## 4. Parameter reference

### 4.1 `create-vpc-firewall-cen-configure`

One call spans both the regional and the per-VPC layer. The Layer column is what
matters when deciding what to ask the user for.

| CLI flag | Required | Layer | Note |
|---|---|---|---|
| `--cen-id` | yes | target | CEN instance id |
| `--network-instance-id` | yes | target | Business VPC id |
| `--vpc-region` | yes | target | Region of the business VPC |
| `--vpc-firewall-name` | yes | target | Unique, human meaningful |
| `--firewall-switch` | yes | target | `open` attaches and starts diverting, `close` attaches dormant |
| `--vswitch-id` | no | **per VPC** | Business vSwitch that will host the diversion ENI |
| `--firewall-vpc-cidr-block` | no | **regional, first access only** | `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` or a subnet of one |
| `--firewall-vswitch-cidr-block` | no | **regional, first access only** | Must be a subnet of the firewall VPC CIDR |
| `--firewall-vpc-zone-id` | no | **regional, first access only** | Primary zone |
| `--firewall-vpc-standby-zone-id` | no | **regional, first access only** | Standby zone |
| `--firewall-vswitch-zone-id` | no | **regional, first access only** | |
| `--lang` | no | - | `zh` default |

Allowed firewall VPC CIDRs are `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` and
their subnets; omitted, the service defaults to `10.0.0.0/8` with vSwitch
`10.219.219.216/29`. The firewall VPC CIDR, the vSwitch CIDRs, the zones and the
business vSwitch **cannot be changed after creation** - the only path is removal
and recreation.

**Do not enforce the documented mask limits.** The API help asks for a subnet mask
of no more than 28 bits on the firewall VPC and 29 on its vSwitch, which would mean
a prefix length of at least 28 and 29. That contradicts the service's own default of
`10.0.0.0/8`, and it contradicts configurations that were accepted in practice: a
`/24` firewall VPC with a `/26` vSwitch succeeded twice. The opposite reading is
contradicted by the vSwitch default of `/29`. The only mask-related rule that holds
in every observed case is that the vSwitch CIDR must be a subnet of the firewall VPC
CIDR, so validate that and let the service adjudicate anything else.

Leaving both zones on the automatic default selects **dual-active mode**, which
suits latency-insensitive traffic. Naming both zones explicitly selects
**active-standby mode**, which lowers latency; traffic prefers the primary zone and
fails over to the standby. Do not compose a primary and a standby independently -
`describe-vpc-firewall-zone` returns `ZoneList` as a list of **two-element arrays**,
where each element is an object carrying `LocalName` and `ZoneId`, and each pair is
a legal combination. Picking a pair from that list avoids invalid combinations. The
order of the pairs is not stable between calls, so never select one by position.
A CEN-scoped query (`--cen-id`) returned the same six pairs as an unscoped one for
the region tested.

`describe-vpc-zone --region-no {region} --environment VPC` returns the zone list
for choosing the business vSwitch, and `--environment TransitRouter` returns a
different list. The official guide recommends putting the business vSwitch in the
same zone as the firewall vSwitch primary zone to reduce latency, which makes the
business vSwitch a latency decision rather than an arbitrary one.

Candidate business vSwitches come from `aliyun vpc describe-vswitches
--biz-region-id {region} --vpc-id {vpc}`, with results under `VSwitches.VSwitch[*]`.
`describe-vpc-firewall-manual-vswitch-list` cannot be used: it fails with
`400 MissingOwnerId` and exposes no `--owner-id` flag.

Prerequisites stated by the CLI help: the CEN must already exist and the VPC must
already be attached to it.

### 4.2 `create-vpc-firewall-precheck` and `describe-vpc-firewall-precheck-detail`

| CLI flag | Note |
|---|---|
| `--cen-id` | |
| `--vpc-id` | |
| `--network-instance-type` | `cen_firewall` for CEN Basic |
| `--biz-region` | **Not** `--region`, which is the global endpoint flag. In practice required: omitting it yields `400 ErrorRegionNoError` |
| `--lang` | |

`--network-instance-type` enumerates the three VPC firewall flavours and is the
clearest place to see the product split: `cen_firewall` is CEN Basic and the scope
of this Skill, `cen_tr_firewall` is the CEN Enterprise transit router, and
`ec_firewall` is Express Connect peering. The service does not strongly validate
this value, so it cannot be relied on as an edition guard.

The console also sends a `FirewallId` that the CLI does not expose.

### 4.3 `modify-vpc-firewall-cen-switch-status`

| CLI flag | Required | Values |
|---|---|---|
| `--vpc-firewall-id` | yes | `vfw-` slot id |
| `--firewall-switch` | yes | `open` / `close` |
| `--lang` | no | |

### 4.4 `modify-vpc-firewall-cen-configure`

Rename only. The CLI exposes just `--vpc-firewall-id` and `--vpc-firewall-name`
plus `--lang`. The console labels this operation "edit", which suggests it can
revise the configuration; it cannot. Requires the slot to be attached first.

### 4.5 `delete-vpc-firewall-cen-configure`

| CLI flag | Required | Format |
|---|---|---|
| `--vpc-firewall-id-list` | yes | Space separated: `--vpc-firewall-id-list vfw-a vfw-b` |
| `--lang` | no | |

Batching is allowed even though the console issues one call per VPC. Whichever
call removes the **last** access in a region also carries the firewall VPC teardown
and its longer runtime.

### 4.6 `describe-vpc-firewall-cen-list`

| CLI flag | Note |
|---|---|
| `--transit-router-type` | `Basic` selects CEN Basic. Case sensitive, and silently dropped when wrong - see section 5 |
| `--cen-id` | Optional; omit to scan the whole account |
| `--region-no` | Business region |
| `--firewall-switch-status` | Filter enum only; returned values include the three transient states |
| `--current-page`, `--page-size` | `--page-size` max 50 through the CLI |

A row already embeds `IpsConfig` (`BasicRules`, `EnableAllPatch`, `RuleClass`,
`RunMode`), `AclConfig.StrictMode`, `PrecheckStatus` and `MemberUid`, so a status
sweep needs neither the IPS call nor the detail call. `PrecheckStatus` on the row is
the last **stored** verdict and carries no timestamp, so it is a hint only - a fresh
verdict still requires re-issuing the precheck and reading the detail call.

The list also accepts `--vpc-firewall-id` and `--network-instance-id`, so a single
slot or a single VPC can be looked up directly instead of paging through the CEN.

### 4.7 `describe-vpc-firewall-cen-detail`

Takes `--vpc-firewall-id`, `--network-instance-id` and `--lang`. It does **not**
accept `--region-no` or `--member-uid`.

## 5. Operational pitfalls

Ordered by how badly they mislead.

1. **`--transit-router-type` is case sensitive and silently ignored when invalid.**
   Passing `basic`, any bogus value, or omitting the flag drops the filter
   entirely and returns every slot in the account with HTTP 200 and no warning.
   Always pass the exact string `Basic`, and assert
   `LocalVpc.TransitRouterType == "Basic"` on each row before acting, because that
   assertion does not depend on the filter having been applied.
2. **Two actions take the CEN id where a slot id looks natural.**
   `describe-vpc-firewall-default-ips-config` and
   `describe-vpc-firewall-asset-region-list` both want the CEN instance id in
   `--vpc-firewall-id`. The IPS call rejects a slot id with
   `400 ErrorParametersFirewallId`, but the region list call returns an **empty
   list with HTTP 200**, which is indistinguishable from "no regions" unless the
   caller knows the argument was wrong.
3. **`--biz-region-id`, not `--region-id`.** Across the `vpc` and `ecs` products
   the API-level region parameter is `--biz-region-id`; `--region` is the global
   endpoint override. A wrong flag returns a JSON object without the expected keys
   rather than a non-zero exit, so a parser reading `TotalCount` with a default
   silently reports "nothing found" and appears to confirm a clean teardown. Assert
   the expected key exists before trusting any answer.
4. **A nonexistent CEN id raises nothing.** The list call returns `TotalCount: 0`,
   so a bad CEN id and a CEN with no attached VPCs cannot be told apart from the
   response alone.
5. **`DefendCidrList` is not firewall state.** It reflects the business VPC's own
   routing, so it holds values both before attachment and after removal.
6. **Response timestamps are UTC+8 with no zone marker.** Convert before comparing
   them against a local clock, or freshness checks will be wrong by hours.
7. **Manual route mode is unavailable on Basic.** `LocalVpc.SupportManualMode` is
   `0`, so `create-vpc-firewall-cen-manual-configure`, `RouteMode` and
   `ManualVSwitchId` are out of scope.
8. **There is no asset-sync command.** The console has a "sync assets" button for
   newly joined VPCs, but the plugin exposes sync tasks only for internet and NAT
   assets. If an expected VPC is absent from the list, direct the user to the
   console.
9. **The zone pair order is not stable.** `describe-vpc-firewall-zone` returned a
   different first pair on separate calls, so never cache or hardcode a position.
10. **Scope limits worth stating to the user.** IPv6 traffic is not protected,
    traffic to the cloud service range `100.64.0.0/10` is not diverted, at most 31
    VPCs per CEN per region may be protected, and the firewall VPC consumes one VPC
    quota plus one Basic transit router network instance quota in the region.
11. **Switching flaps long-lived connections.** Opening or closing causes
    sub-second flapping of established connections; short connections are
    unaffected, but SLB and RDS sessions can drop. The open process cannot be
    paused or rolled back - on failure the system rolls back by itself. Advise a
    low-traffic window.
12. **Route relearning is slow.** After a route table change while protection is
    on, allow 15 to 30 minutes before judging the result.
13. **Transport-level errors are worth one retry.** A `dial tcp ...: connect: bad
    file descriptor` failure was observed on the `cloudfw` plugin while the same
    account's `vpc` and `ecs` calls and a direct `curl` to the endpoint all
    succeeded; an identical retry moments later worked. It is an environment or
    transport fault rather than an API error, so retry once before reporting
    failure, and do not read it as a permission or parameter problem.
    One retry at the call layer is not enough inside a poll loop, where the same
    fault can recur for minutes; section 3.4 covers that case separately, and the
    two are not interchangeable. Retrying a permission denial, by contrast, is
    never useful.
14. **Edition support.** Only the Enterprise, Ultimate and pay-as-you-go editions
    of Cloud Firewall support this feature; Premium does not.
    `describe-user-buy-version` is the probe, but the mapping from its numeric
    `Version` field to an edition name is not documented, so treat it as a soft
    check on `UserStatus`, `InstanceStatus` and `Expire` rather than a hard gate.
    `describe-postpay-user-vpc-status` returned `closed` on an account that created
    and opened firewalls successfully throughout testing, so it is **not** a
    capability gate.
15. **A confirmation gate that fires on a no-op disarms itself.** Asking for consent
    before reading state means invocations that change nothing also demand it, and a
    caller that learns to pass the flag reflexively will pass it on the run that
    really does flap production traffic. Read state first, let the no-op and
    invalid-state guards reject what they can, and gate only the run that will
    actually send a write. Two operations here need one: anything that starts or
    stops diversion, and any removal. Attaching dormant is traffic-neutral and needs
    none.
16. **One region, one writer, and the decision must be read under the lock.** The
    firewall VPC is a regional singleton, so `attach` and `remove` take a host-local
    lock keyed on the region. Serialising the writes is only half of it: whatever the
    write decision rests on has to be read after the lock is held. `attach` takes the
    lock before it reads `AllowConfiguration`, because two runs reading that flag in
    the same moment would each conclude they are the first access and each try to
    create the shared VPC. `remove` cannot key a lock on a region it has not read yet,
    so it lists once to learn the region, takes the lock, then **lists again** and
    derives the slot status and the sibling count from that second answer. Two list
    calls on a removal are by design: with the sibling count taken from the pre-lock
    read, a sibling removed while this run waited would still look active, the run
    would believe it is not the last in the region, and the teardown warning - the one
    that says the shared firewall VPC is about to be destroyed - would be skipped. The
    second read also catches a slot that another run has meanwhile reset, removed from
    the list, or pushed into a transient state. The guarantee is per host only; the
    cloud offers no lock to hold, so nothing here helps against a second machine.

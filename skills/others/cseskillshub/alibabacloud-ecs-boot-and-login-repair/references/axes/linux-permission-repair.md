---
name: alibabacloud-ecs-linux-permission-repair

description: |
  Diagnoses why a Linux ECS instance refuses root logon, su or sudo, using non-mutating
  control-plane reads plus one customer-approved in-guest inspection command, and returns
  evidence with manual repair steps. This skill applies no repair itself.
  Use when a normal user is denied permission, cannot switch to root, sudo says the user is not
  allowed to run a command, or files became inaccessible after a chmod or chown.
  Triggers: cannot su to root; root login denied; insufficient permission; sudo says not allowed to run this command; user not in the sudoers file; cannot escalate privileges; setuid bit missing; wrong owner after chmod or chown; NoPermission; ImplicitDeny
  Do NOT use: disk expansion (alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis), instance start or stop
  (alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis), slow disk (alibabacloud-ecs-high-frequency-issues: resource-bottleneck),
  a full disk or inode exhaustion, or Windows.
---

# ECS Linux root/sudo permission diagnosis and manual repair guidance

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

## 1. Scope

One symptom area only: **a Linux ECS instance where root logon, `su`, `sudo` or file access is
refused or degraded**. Four sub-symptoms are worked:

| Code | Sub-symptom |
|---|---|
| S1 | `root` logon refused or credential lost (includes cloud-side controls mistaken for a fault) |
| S2 | `sudo` authorization missing (sudoers membership, RAM versus guest authorization confused) |
| S3 | setuid bit, mode or owner damaged on `/usr/bin/sudo`, `/usr/bin/su`, `/usr/bin/passwd`, `/etc/sudoers` |
| S4 | business file or directory owner/mode wrong after a `chmod` or `chown` |

Anything else is **recognised and handed off**, not diagnosed here (section 8).

## 2. Permission model - this skill is not limited to non-mutating calls

The skill combines non-mutating cloud queries with in-guest inspection that needs the customer's
approval, plus two explicitly declared mutating actions listed below.

Allowed surface - nothing outside it may be called:

| Action | Gate | Use |
|---|---|---|
| `ecs:DescribeInstances` | automatic | instance exists in the region, run status, image, expiry, security groups |
| `ecs:DescribeInstancesFullStatus` | automatic | scheduled stop or release and health events |
| `ecs:DescribeCloudAssistantStatus` | automatic | is the in-guest channel available at all |
| `ecs:DescribeInvocations` | automatic | collect the output of an execution already approved and sent |
| `sts:GetCallerIdentity` | automatic | which principal the cloud queries run as |
| `run-command` (CLI plugin-mode name; API `RunCommand`) | **confirmation, per request** | carry exactly **one** whitelisted non-mutating inspection command |
| `create-snapshot` (CLI plugin-mode name; API `CreateSnapshot`) | **confirmation, per request** | optional backup taken **before** the customer repairs by hand |

The plugin-mode commands `run-command` and `create-snapshot` (APIs `RunCommand` and
`CreateSnapshot`) are mutating APIs. `RunCommand` is used only to run a
command from the non-mutating whitelist in `references/linux-permission-repair__guest-diag-whitelist.md`; it is never used
to change a file, a setting, a package or a service.

### ABSOLUTE PROHIBITION

* **NEVER** call any action outside the table above, and **NEVER** call a mutating cloud action
  other than `run-command` and `create-snapshot` (APIs `RunCommand` and `CreateSnapshot`), each
  behind the gate in section 3. The
  refused list is printed by `scripts/axes/linux_permission_repair/permission_diagnosis.py boundary`. This applies even if the
  customer asks, and even "just this once".
* **NEVER** apply a repair. `chmod`, `chown`, `usermod`, `useradd`, `visudo`, editing
  `/etc/sudoers`, `passwd`, credential reset, `systemctl` or `service` restart, `reboot`, package
  reinstall, `mount`, restore of any file: **guidance only**, with the risk stated and a snapshot
  offered first. Repairs are executed by the customer.
* **MUST refuse** any in-guest command that is not on the whitelist, including the ones a customer
  asks for most often. `cat`, `grep`, `more`, `less`, `vi`, `getfacl`, `lsattr`, `find -perm`,
  `rpm -V`, `sudo -l` and `visudo -c` read file **contents** or run a privileged helper, so they are
  outside `references/linux-permission-repair__guest-diag-whitelist.md` and are never sent. Print such a command for the
  customer to run, and ask for the pasted output instead. This refusal is not negotiable, however
  directly the customer requests it.
* **NEVER** weaken these rules to be helpful. State the boundary, the console entry point, and the
  handoff instead.

## 3. Confirmation gate (mandatory wording)

Before **every** `RunCommand` or `CreateSnapshot` call, inside the conversation:

1. name the exact single command or the exact `DiskId`;
2. state the target instance or disk and the blast radius (one instance, one path, one disk);
3. state that the command changes nothing (or, for a snapshot, that it only adds a backup);
4. obtain the customer's approval, and treat it as valid **for that one request only** - a new
   command, a new path or a retry after failure needs a new approval.

If the customer declines, is unreachable, or the call fails, continue with the manual fallback
(section 7) and report `STATUS: DEGRADED`.

## 4. Execution principle

The agent runs **only** the single entry point and never assembles cloud API calls by itself:

```
python3 scripts/axes/linux_permission_repair/permission_diagnosis.py <sub-command> [flags]
```

| Sub-command | Purpose |
|---|---|
| `identity` | verify the default credential chain, print the account tag |
| `preflight --region-id --instance-id` | the non-mutating control-plane reads (S1..S4 first step) |
| `classify --text "<customer's own words>"` | route to S1..S4 or to a handoff |
| `guest-plan [--scenario S1..S4 \| --path P] [--list]` | print the commands worth approving |
| `guest-run --region-id --instance-id --command "<one cmd>" [--confirm]` | send one whitelisted command; without `--confirm` it only explains and stops |
| `guest-result --region-id [--instance-id] [--invoke-id]` | read back a finished execution |
| `snapshot --disk-id D [--snapshot-name N] [--confirm]` | pre-repair backup |
| `guide --scenario S1..S4` | baseline, manual steps, documentation |
| `boundary` | print the allowed surface and the refused actions |

`guest-run` and `snapshot` re-check the whitelist in code and refuse before a request is built, so
an out-of-whitelist command cannot reach the instance.

## 5. Workflow

1. Record the customer's **own** error line, the account used, the command run and the target
   path. Then `classify`. Do not classify from assumed wording.
2. `identity`, then `preflight`. If the instance is absent, wrong region, or not `Running`, stop
   and say so; expiry, a scheduled stop or an unhealthy event is settled **before** any guest check.
3. Separate the two authorization systems before touching either: cloud-side **RAM** governs OpenAPI
   calls, guest **sudoers** governs privilege inside Linux. A RAM policy that prohibits `root` as the
   initial user, and the hardening guidance that avoids direct root logon, are controls, not faults.
4. `guest-plan` for the matched scenario, apply section 3, then `guest-run --confirm` - one command
   per approval - and `guest-result` when the output has not landed yet.
5. Interpret readings only against `references/linux-permission-repair__perm-baseline.md`, and quote its status line: the
   expected values are **UNVERIFIED for this tier**, so present them as "compare against a
   known-good instance of the same image".
6. `guide` for manual steps; offer `snapshot` first. Root-cause reasoning per scenario lives in
   `references/linux-permission-repair__permission-diagnosis.md`.

## 6. Evidence discipline

* Quote only values returned by an API or printed by an approved command, and name the source of
  each: the action, or the command plus the path.
* State every parameter the skill filled in by itself (`RegionId` from the customer, page size,
  polling window).
* An empty or failed query is a limitation to report, never a value to invent.
* Guest file permission state has **no** cloud API: only an in-guest command gives it, and
  `DescribeInvocations` shows past executions only, so live state needs a fresh command.

## 7. Degraded path

Cloud Assistant not ready, `RunCommand` refused, RAM denied, or the customer declines approval:
report `STATUS: DEGRADED`, name the missing step, and give the exact whitelisted command for the
customer to run and paste. On an authorization failure report the literal code returned
(`NoPermission` or `ImplicitDeny`), the missing action, and the minimal policy from
`references/ram-policies.md`.

## 8. Handoffs

| Recognised in the customer's words | Goes to |
|---|---|
| resize, expand, partition still small | `alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis` |
| cannot start, stuck starting or stopping | `alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis` |
| slow disk, IO hang, IOPS, latency | `alibabacloud-ecs-high-frequency-issues: resource-bottleneck` |
| disk full, no space, inode, cannot create a file | the capacity/inode diagnosis skill of this batch |
| Windows, RDP | manual handling; Windows is out of scope for this release |
| panel-installed MySQL: `Access denied for user 'root'@'localhost'`, or a panel upgrade that says success but the version is unchanged | `alibabacloud-ecs-high-frequency-issues: db-on-ecs-diagnosis` |

Handoff facts for the last row, from ticket `T-950401D7` (2026-09): the initial
`Access denied` was a wrong root password and was cleared by resetting it in the
panel. The later panel upgrade from MySQL 5.7.40 to 5.7.44 reported "update
succeeded" but the version never changed; the real cause was free memory **1097 MB,
below the 2000 MB minimum** the panel requires for that upgrade, so the upgrade
script never ran. When handing off, carry this as the primary candidate: check free
memory (`free -m`) first, and treat a panel success message as unverified until the
version string changes. Do not diagnose or repair MySQL on this area.

## 9. Credentials

Only the default credential chain of the Alibaba Cloud CLI is used (the CLI default credential chain). The skill
never asks for, reads, stores, prints or transmits an AccessKey pair or a security token, and it
masks credential-looking values in any error text it echoes back.

## Observability

Every request carries a User-Agent built from a per-run session identifier, so
that all API activity of one diagnosis traces to one session.

* Template: `AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`, defined as
  `UA_TEMPLATE` in `scripts/axes/linux_permission_repair/_constants.py` with the format fields `skill_name`
  and `session_id`.
* Flag: `--user-agent`, appended by `run_cli` in `scripts/axes/linux_permission_repair/_cli.py` to every
  single call without exception.
* Session identifier: one 32-character lowercase hex id per run
  (`uuid.uuid4().hex`, returned by `new_session_id`), printed by the entry
  point at the start of every run and reusable across runs with `--session-id`.

Each call also runs with its own timeout (`subprocess.run(..., timeout=...)`)
and retries only transient failures.

## 10. Output contract

The final answer restates the readings the report printed, each with its source, and then ends with
exactly the two lines the script already emitted:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next step>
```

Conclusions are evidence plus manual guidance. No repair is applied, no guest command is sent
without the approval described in section 3.

## 11. References

* `references/ram-policies.md` - one concrete action per line, no wildcard, plus the statement that
  nothing else is granted.
* `references/linux-permission-repair__guest-diag-whitelist.md` - the in-guest commands that may be approved, and the
  requests that are refused on purpose.
* `references/linux-permission-repair__perm-baseline.md` - expected mode and owner per checked path, with its UNVERIFIED
  status.
* `references/linux-permission-repair__permission-diagnosis.md` - per-scenario decision tree, controls mistaken for faults,
  official documentation links, known evidence gaps.

## 12. Known evidence gaps

No representative ticket or conversation was supplied for this tier, so scenario ranking, the
guest-side error strings customers paste, and the Windows scope are **unconfirmed**; the routing in
section 1 is a design mapping, not measured frequency. Capacity-area readings (`df`, `du`, `lsof`)
and any credential-reset API are deliberately absent: the first belongs to another skill, the
second was never verified for this tier and stays a documented console step.

---
name: alibabacloud-ecs-high-frequency-issues
area: resource-bottleneck
description: >-
  Diagnoses why an Alibaba Cloud ECS instance is slow, frozen, or pinned on CPU,
  memory or load. Joins spec facts, disk inventory and CloudMonitor series, detects
  the memory-exhaustion chain behind freezes, names the process with one gated
  in-guest command, and reports every reading with its caliber, rule id, gaps and
  handoff.
  Use when: CPU at 100%, memory exhausted or OOM kill, load average high, instance
  lagging, frozen or ssh/rdp/VNC unresponsive, kswapd or swap paging, System process
  or interrupt high, disk throttled alarm, atop replay, CloudMonitor agent missing,
  AI report review.
  Do NOT use for: disk IO ceiling or provisioned IOPS
  (area:resource-bottleneck), capacity/inode or failed expansion
  (area:disk-expand-diagnosis), boot or start/stop stuck
  (area:instance-state-diagnosis), bandwidth/EIP/DNS, attacks or
  security rules, spec change or pricing.
---

# ECS resource-bottleneck diagnosis (CPU / memory / load / frozen)

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

One diagnosis chain for the entangled symptoms of this tier: an instance that
lags, freezes, or sits pinned on CPU, memory or load. It is symptom-first, not
metric-first. It joins four evidence sources on a single timeline — the instance
spec and its shape semantics, the disk inventory, CloudMonitor metric series over
an explicit window, and (behind a confirmation gate) one whitelisted in-guest
inspection command — then emits a report where every conclusion names the reading
that produced it, the rule that derived it, and the caliber it was taken in.

The reason this package exists: in the ticket corpus the reported symptom is
routinely not the cause. "CPU is at 100%" is as often the tail of a
memory-exhaustion chain as it is compute demand, and the process caught *blocked*
is almost always the victim of IO pressure rather than its source.

## Permission model: what this skill may and may not do

This skill makes **no observation-only claim about itself.** It holds eight
actions; seven are pure control-plane reads and one, the consent-gated
`RunCommand` dispatch, is a write-flavored call that is gated, whitelisted and
single-command (Class B - no grant is declared in its customer policy). The tier
spec labels the skill `RO`; that label understates it, and declaring it
observation-only would misrepresent the dispatch it legitimately performs.

| Class | Capability | Where it is enforced |
| --- | --- | --- |
| Evidence reads | `sts:GetCallerIdentity`, `ecs:DescribeInstances`, `ecs:DescribeInstanceAttribute`, `ecs:DescribeDisks`, `ecs:DescribeInvocations`, `cms:QueryMetricLast`, `cms:QueryMetricList` | `API_WHITELIST_ACTIONS` in `scripts/areas/resource_bottleneck/_constants.py`, granted in `references/ram-policies.md` |
| Gated dispatch | consent-gated `RunCommand` (Class B - no declared grant) — exactly one whitelisted inspection command per approved run, read back with `DescribeInvocations` | `scripts/areas/resource_bottleneck/guest_evidence.py` |
| Never | anything mutating the customer's instance, data, configuration, spec or billing | no code path, no granted action |

## Prerequisites

1. The aliyun CLI installed and its default credential chain configured by the
   customer with `aliyun sts get-caller-identity`. This package has **no** key, token or profile
   parameter anywhere; it never reads, prints, stores or transmits secret
   material, and it never asks the customer to paste one.
2. Verify the chain and see which account will be attributed to the report:
   ```
   python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py --check-auth-only
   ```
   This calls `aliyun sts get-caller-identity` and prints
   `account:uid-****<last4>`. A failure here is one of the four DEGRADED causes
   below, not a reason to try harder with different secrets.
3. Grant only the actions in `references/ram-policies.md`. That policy is
   wildcard-free on purpose: an administrator can paste it as-is, scoped to one
   instance ARN.

## Collect these inputs first; never guess them

| Input | Notes |
| --- | --- |
| Region id | Required. Not inferred; a wrong region produces an empty inventory, which rule R8 then reports as an existence mismatch. |
| Instance id | Required. Ask for it, and confirm it appears in the returned inventory before diagnosing. |
| The symptom in the customer's own words | Maps to `--symptom`: `auto`, `lag`, `cpu`, `memory`, `load`, `oom`, `atop`, `report-review`. |
| The incident window | Absolute times with timezone, or `--hours <n>` (1-168, default 6). For a past minute, an explicit `--start-time` / `--end-time` pair is required, because "it was slow yesterday at 9" cannot be answered by the latest reading. |
| Whether in-guest evidence is wanted | Decides whether the confirmation gate needs to be walked. |
| Guest OS family | `--os-type linux\|windows` if known; otherwise derived from `DescribeInstances`. It selects the command whitelist, so a wrong value rejects every command the customer approves. |

## Run the diagnosis

```
python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py \
  --region-id cn-hangzhou --instance-id i-bp1example0001 --symptom lag --hours 6
```

Useful switches: `--output json` for the machine-readable report,
`--report-file <path>` to write it (create-only: an existing path is refused
rather than overwritten), `--verbose` for raw metric samples and the full rule
catalog, `--timeout` for the per-call CLI timeout (default 60 s), `--max-pages`
for the paging ceiling. Exit code is `0` for `OK`, `1` for `DEGRADED`, `2` for
`FAIL`.

## How the output is meant to be read

Five areas are evaluated and joined at the same timestamp: compute, memory,
disk IO, and the two that usually turn out to be someone else's tier — public
network and application behaviour. The rules R1-R9 in
`references/resource-bottleneck__diagnosis-rules.md` decide what may be concluded; the report cites
the rule id next to each finding.

The chain that dominates this tier, and the first thing to check on any "frozen"
report:

```
memory exhausted -> kswapd paging -> disk IOPS/BPS pinned -> instance frozen
                 -> ssh / vnc / rdp unreachable -> a human reboot is the only exit
```

Two calibers are non-negotiable in every quoted number, because tickets show
customer and engineer reaching opposite conclusions from the same machine:
**mean and peak are always reported together**, and the **viewpoint** (host-side
metric versus in-guest reading, percent versus absolute MiB, instance aggregate
versus single-disk ceiling) is named with the value. See
`references/resource-bottleneck__metric-catalog.md`.

## In-guest evidence: announce, then confirm, then send one

The only side effect this skill can produce is dispatching one inspection command
through Cloud Assistant. The gate is enforced in `scripts/areas/resource_bottleneck/guest_evidence.py` and
is not optional:

1. Present to the customer, verbatim: the exact command text, the target instance
   id, that the command only inspects state and changes nothing inside the
   instance, and whether it can be reversed (the dispatch is cancelled simply by
   not running it; the reading itself is harmless).
2. Get approval for **this run**, then re-run with
   `--confirmation "<quote of the approval>"`. An empty or placeholder answer
   (`yes`, `ok`, `confirm`, `approved`, `y`, `auto`, `true`) is rejected as no
   confirmation at all.
3. One approval covers exactly one command. A second command needs a second run
   with a second quote. No standing, batch or blanket authorization is accepted.

The command must fullmatch one exact template in
`references/resource-bottleneck__guest-commands.md` and contain none of the side-effect tokens. A
near-miss (`top`, `top -bn2`, a different `head -n` cap, a chained `uptime &&
free -m`) is **rejected, and a rejected command is turned into manual guidance —
never rewritten and retried** in the hope a variant slips through.

```
python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py --region-id cn-hangzhou \
  --instance-id i-bp1example0001 --guest-command "top -bn1" \
  --confirmation "customer replied: go ahead and run top -bn1 on this instance"
```

## ABSOLUTE PROHIBITION: actions never performed, in any circumstances

No approval, however explicit, converts any of these into something this skill may
execute. They are not in the granted policy, so they cannot be called even by a
bug. Output the manual steps and the risk notice instead
(`references/resource-bottleneck__human-actions.md`):

- reboot or restart the instance; stop or start it
- kill a process, or stop or restart a service
- write swap or kernel parameters: `sysctl`, `swapon`, `swapoff`, any redirection
  into a configuration file
- change the instance spec (upgrade or downgrade), or anything billed
- refund, unsubscription, price continuation, or any commercial commitment
- delete a snapshot, delete or format a disk, repartition, remount, or move data
- cross-region migration
- block an IP, edit a security group, or any other defensive action against traffic
- create a snapshot (the console `create-snapshot` action is deliberately **not** granted here; it
  stays a console action for the customer — see `references/resource-bottleneck__human-actions.md`)

Corpus justification: the effective remedies in these tickets were a human stopping
a java service (T-7E06B86C), a human configuring swap (T-D25A9845), and reboots
(T-B8B16499, T-1BBB1704, T-BF2F77A0). Each is a legitimate action; none is
legitimate as an automated action of a diagnosis tool.

## DEGRADED is a result, not a silence

Four things actually block the evidence in this tier, in order of frequency. Each
has a branch; the run reports what is missing, what conclusion is therefore
withheld, and what would close the gap — it never fills a gap with an assumed
value.

| Blocked because | Tickets | Branch behavior |
| --- | --- | --- |
| The customer does not authorize in-guest inspection | T-6143D71E, T-1D5C74FB, T-570E51B9 | Ship the cloud-side findings, state which question needs the guest (process ranking, `kswapd`, history), and stop there. Never call an unverified in-guest cause likely. |
| The credential is wrong or expired | T-441637A1 (x3), T-69AEDFA2, T-3EA06F17 | `--check-auth-only` isolates it. Report `InvalidCredential` / `NoPermission` / `ImplicitDeny` and point at `aliyun sts get-caller-identity` plus `references/ram-policies.md`. Never request key material as the workaround. |
| CloudMonitor agent and/or `atop` were not installed | T-D25A9845, T-36BC7559, T-6143D71E, T-BF2F77A0 | Rule R6 gap: name the metric that returned nothing and the collector that was missing. An empty series is never `0%` and never `normal`. Agent-free fallbacks are the gated guest commands. |
| The instance is frozen; ssh, rdp **and** console VNC all fail | T-570E51B9, T-1BBB1704 | Report it as evidence, not as a tool error: no in-guest reading is obtainable, the diagnosis is explicitly incomplete, and the next step is the snapshot-then-reboot sequence with its three risks. Never conclude "nothing wrong inside" from a command that never ran. |

## Evidence discipline and the anti-fabrication rules

- **A resource that was not returned does not exist.** No instance, disk,
  snapshot, agent, log file or metric may be described unless a call showed it.
  Ticket T-50C39C59 is the named lesson: confident references to things that were
  not there cost the customer a wasted operation. Rule R8 stops the run on an
  existence mismatch instead.
- Anything not evidenced is written as pending evidence, with what would confirm
  it. This package deliberately carries a gap list rather than plausible values:
  the unratified CloudMonitor metric families
  (`references/resource-bottleneck__metric-catalog.md`), the excluded `create-snapshot`, the
  not-yet-named network and security handoff skills
  (`references/resource-bottleneck__escalation-map.md`), the two competing `atop` documentation links,
  and the absence of any quotable error string beyond
  `references/resource-bottleneck__log-signatures.md`.
- **No spec or price advice.** The skill states which area is saturated, at what
  value, in what caliber, over what window — and leaves the upgrade question to
  the customer and to billing.
- Application and business meaning is out of scope: a process name may be quoted
  from a real reading, but whether it *should* be busy is the customer's question.
- A negative conclusion is allowed and is stated with a direction (rule R5).
- The `report-review` symptom path exists for the recurring task of correcting
  factual errors in an existing AI diagnosis report; every correction must cite a
  reading from this run, not a rival narrative.

## Credentials and privacy

- **Never echo a credential, in either direction.** If the customer supplies a
  password, key, token or VNC credential in the conversation, do not repeat it, do
  not quote it back "to confirm", and do not include it in the ticket record.
  Ticket T-7E06B86C is the cautionary case: an engineer pasted the instance root
  password into the chat. Tell the customer it was exposed in the conversation and
  advise rotating it.
- Masking is applied on the way out, automatically: `_cli.mask_credentials()` runs
  over every error string, stderr fragment and decoded guest output before it
  reaches the report, replacing `AccessKeyId` / `SecurityToken` / `Signature` and
  password-shaped values with `***`. Guest output is masked **before** it is
  parsed, so a secret cannot hide inside a quoted finding either.
- Report captures are truncated with an explicit marker rather than silently
  shortened, `--report-file` is create-only, and `.gitignore` keeps `.env`,
  `*.pem`, `*.key`, `.sts_cache.json` and generated reports out of version
  control.

## Observability

- One session id per run: 32 hex characters from `uuid4().hex`, generated once in
  `main()` and reused by every call, including the gated dispatch and its
  read-back. It is printed at the top of the report.
- Every API call carries it in the User-Agent, declared as this template:
  ```
  AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
  ```
  where `{skill}` is the skill name above and `{session-id}` is the run's
  32-hex id, i.e. it renders as
  `AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<session-id> skill-version/<skill-version>`
  (`USER_AGENT_TEMPLATE` in `scripts/areas/resource_bottleneck/_constants.py`, rendered by
  `_cli.build_user_agent()` and appended as `--user-agent` to every argv list in
  `scripts/areas/resource_bottleneck/_cli.py::build_command`.)
- Every call has an explicit timeout: `--timeout`, default 60
  `CLI_TIMEOUT_SECONDS`, passed to `subprocess.run(..., timeout=...)` with
  `stdin=DEVNULL`. Retries are bounded with jittered backoff and only for
  retryable markers. No shell is ever used, so no parameter can be reinterpreted
  as a command.
- The account is recorded as `account:uid-****<last4>`: enough to attribute a
  report, never enough to be a credential.
- Command form note: RPC-style products keep PascalCase action names on the CLI
  (`aliyun ecs describe-instances`), while the identity check uses the plugin-style
  lowercase-hyphen subcommand (`aliyun sts get-caller-identity`). RAM action names
  differ from API names for CloudMonitor: grant `cms:QueryMetricLast` /
  `cms:QueryMetricList`, not `cms:DescribeMetricLast` / `cms:DescribeMetricList`.

## Output contract

Every run ends with the same two lines, machine-parseable:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next step, including a manual one>
```

`STATUS` is computed by `determine_status()` from what was actually obtained;
`NEXT_ACTION` from `next_action_for()`. The text report also prints the account
label, the action surface used, the declared API versions, every collected
parameter (auto-filled ones marked as such), the instance profile, the metric and
disk tables with calibers, the findings with rule ids, the gate state for guest
evidence, and the gap list. Exit codes: `OK`=0, `DEGRADED`=1, `FAIL`=2.

## Reference index

| Document | Purpose |
| --- | --- |
| `references/resource-bottleneck__diagnosis-rules.md` | Rules R1-R9 and the P1/P2 spec priors, with ticket provenance |
| `references/resource-bottleneck__metric-catalog.md` | Queried metrics, calibers, declared metric gaps |
| `references/resource-bottleneck__guest-commands.md` | The exact command whitelist, the rejections, the gate |
| `references/resource-bottleneck__log-signatures.md` | How each pasted kernel/alarm string is to be read (rule R9) |
| `references/resource-bottleneck__human-actions.md` | The never-auto-execute list and the ticket-derived step templates |
| `references/resource-bottleneck__escalation-map.md` | Which area belongs to which neighbour skill |
| `references/resource-bottleneck__evidence-and-privacy.md` | Traceability, the four DEGRADED branches, credential rules |
| `references/ram-policies.md` | The concrete, wildcard-free actions to grant |

## Self-check before use

Offline, no network and no credentials required:

```
python3 scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py --self-test
python3 scripts/areas/resource_bottleneck/guest_evidence.py --self-test
python3 scripts/areas/resource_bottleneck/cms_metrics.py
```

These assert the whitelist accept/reject boundaries, the confirmation gate, the
datapoint parsing and aggregation calibers, and the rule outcomes for normal,
empty and garbage inputs.

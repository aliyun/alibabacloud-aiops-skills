---
name: alibabacloud-ecs-high-frequency-issues
area: instance-start-stop-anomaly
description: |
  Diagnose Alibaba Cloud ECS instances stuck in the start/stop state machine: parked in Stopping, Starting or Pending, a boot that never reaches a login prompt, or a data disk that is gone after a reboot. Collects evidence with its entry script, then gives manual console steps.
  Use when: stuck in stopping or restarting; instance will not start; long in starting or pending; cannot stop or force reboot; after reboot or upgrade cannot get into system; An operating system wasn't found; fork: Cannot allocate memory; data disk mount gone after reboot.
  Do NOT use for services failing inside a running instance (use alibabacloud-ecs-linux-os-troubleshooting), SSH/RDP login, or disk capacity.
---

# ECS Instance Start/Stop State Anomaly

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

This skill answers one question: **is the instance's start/stop state machine
broken, and if so what is provably blocking it?** Everything above the hypervisor
boot path is out of scope and is routed to a sibling skill with the evidence
already collected.

## Scope

Covered (instance-level state machine and boot path):

| Customer symptom | What this skill determines |
| --- | --- |
| Instance parked in Stopping, or a reboot that never leaves Stopping | Whether the dwell time is still inside the expected transition window, and what can and cannot be done about it |
| Instance parked in Starting / Pending / the "operating system starting" phase | Whether the platform reports a health or maintenance event, and which boot-failure family fits the wording |
| Start failure from Stopped | Whether an operation lock, economical-mode stop, or a boot-path cause explains it |
| Cannot get into the system after a reboot or a change | Whether the instance is actually up (and the report is a login/OS issue), or the boot never completed |
| A data disk (or its content) is gone after a reboot | Cloud-side disk inventory cross-checked against the guest mount view |

Not covered — recognized and handed off (see `references/instance-start-stop-anomaly__handoff-map.md`):
guest services and middleware that fail inside an already-booted system, SSH or
RDP reachability and credentials, disk capacity and inode exhaustion, disk IO
performance, disk expansion, snapshot lifecycle and billing, spec-change and
commercial questions, account-side verification that blocks console operations,
and products that are not ECS (Simple Application Server, cloud desktop).

## Execution principle

**Always run the entry script. Never compose a cloud API call by hand.**

    python3 scripts/areas/instance_start_stop_anomaly/ecs_start_stop_diagnosis.py --region-id <region> --instance-id <id>

The script is the only path to the cloud: it carries the action whitelist, the
per-call timeout, the retry policy, the credential masking, and the two
confirmation gates. If you find yourself wanting a fact the script does not
return, the fact is not available to this skill — say so in the report instead
of improvising a call.

Run the identity pre-check first when credentials may be stale:

    python3 scripts/areas/instance_start_stop_anomaly/sts_token.py

Inputs: `--region-id` and exactly one locator (`--instance-id`, `--public-ip`,
`--private-ip`, `--instance-name`). Ask for a missing region or instance id —
never guess one. Useful context flags: `--operation-time` (or
`--elapsed-minutes`), `--symptom "<verbatim customer wording>"`,
`--recent-change`, `--expected-mount`.

## Permission model

This skill is **not** an inspection-only skill. It has three layers, and the
distinction is enforced in code, not in prose.

### Layer 1 — automatic evidence queries

The `Describe` and `Get` actions listed in `references/ram-policies.md` run
automatically as part of one script invocation. They change nothing and need no
per-call confirmation.

### Layer 2 — confirmation-gated in-guest reading

Some boot-path facts (mount table, disk view from inside the guest) exist only
inside the instance. `--guest-check <key>` dispatches **exactly one** command
from the frozen whitelist in `scripts/areas/instance_start_stop_anomaly/_constants.py` through Cloud Assistant and
reads the output back.

Before requesting it, tell the customer: the exact command line, that it only
enumerates state, which instance it runs on, and that the approval covers this
one command at this one time. Then pass `--confirmed`. Without `--confirmed`
the script prints the disclosure and executes nothing.

### Layer 3 — confirmation-gated snapshot-first write

`--create-snapshot --disk-id <d-...>` creates one snapshot of the current disk
state. It is the only write this skill performs besides Layer 2, it is
reversible by deleting the snapshot afterwards, and it is **mandatory before any
recovery path** the customer is about to take (rollback, re-initialization,
cleanup). Relay the billing notice before asking: snapshots are billed for
stored size; delete temporary ones when the incident closes.

### ABSOLUTE PROHIBITION

Never execute, generate, or hand the customer a command that changes instance
state or destroys data. Concretely, these are **never** callable from this skill
and appear only as documented manual console steps:

StartInstance, StopInstance, RebootInstance (including every forced variant),
ResetDisk (snapshot rollback), ReInitDisk, ReplaceSystemDisk, DeleteSnapshot,
DeleteDisk, DeleteInstance, ResizeDisk, ModifyInstanceSpec,
ModifyPrepayInstanceSpec, AuthorizeSecurityGroup, RevokeSecurityGroup.

Likewise, never perform in the guest: filesystem checks, formatting, partition
or mount changes, deleting or editing files, killing processes, restarting or
installing services, installing agents, or changing kernel parameters. Guide the
customer through the console instead (`references/instance-start-stop-anomaly__risk-scripts-and-manual-steps.md`).

Support cannot "force it from the backend" while an instance sits in Stopping,
and neither can this skill. Say that once, with the dwell-time evidence, and
offer the correct next step.

### Refusal rule for non-whitelisted commands

A reading that is not on the Layer 2 whitelist is **refused**, even with
`--confirmed` — including `cat /etc/fstab`, `lsblk`, `systemctl list-units
--failed`, `journalctl -b -1 -p err`, `dmesg`, `last`, `Get-WinEvent`, and any
compound or piped command string. For each, the script emits the customer-paste
fallback: the customer runs it over VNC or SSH and pastes the output back.
Never run it yourself, and never paste a refusal into the report as a finding.

## Decision tree

    S0 identity pre-check; missing region or locator -> ask, never infer
    S1 not an ECS instance (simple app server, cloud desktop) -> declare unsupported, route
    S2 current Status
       Running + CPU activity reported  -> state machine healthy -> Layer-1 facts
                                           then route (guest service / login / capacity)
       Stopping, Starting, Pending      -> S3 dwell time
       Stopped but "will not start"     -> locks, stop mode, boot-failure tree
    S3 dwell vs window (5-10 min typical, 15 min ceiling)
       inside window  -> explain the normal shutdown flow, give the remaining
                         wait, show how a forced stop is chosen BEFORE the
                         operation and what it costs, note that high IO or
                         memory load elongates it
       beyond ceiling -> real anomaly: attach platform events + resource
                         readings + still-missing evidence, then escalate
                         through a support ticket
    S4 disk inventory vs guest mount view -> mount-table conflict family
    S5 boot-failure family (see references/instance-start-stop-anomaly__boot-failure-root-causes.md)
    S6 before ANY recovery output: snapshot-first, irreversibility, business
       interruption, unsaved data, low-traffic window, customer-only console
    S7 close with the handoff target, the evidence attached, and the evidence
       still missing

## Output contract

Every run ends with `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION: ...`.

- Relay the script's summary; do not restyle it and do not add facts.
- Quote only values the script returned. An empty result is reported as empty,
  never as an assumption.
- State which inputs were derived automatically (for example the account label
  from the identity pre-check) and which came from the customer.
- `STATUS: DEGRADED` means one evidence area is missing. Name the area, name the
  reason, and give the substitute (VNC reading, customer paste, console page).
- `STATUS: FAIL` means the run produced no conclusion — an input is invalid, the
  confirmation gate was not met, or credentials are unusable. Fix that first.

## Authentication and permission errors

Credentials come from the aliyun CLI default credential chain. Never accept,
echo, store, or pass an AccessKey pair or a token on any command line, and never
ask the customer for one.

When the chain is unusable, direct the operator to configure the CLI profile.
When a call is denied, name the exact missing action and point at
`references/ram-policies.md` for the minimal grant. Denied calls are labelled
with the platform wording `NoPermission` or `ImplicitDeny`; every other failing
call is reported with its own returned code.

## Graceful degradation

Boot diagnosis very often runs against an instance that cannot boot, so the
guest channels may be unavailable (Cloud Assistant agent offline or absent, guest
not up yet, denied permission, no approval given). Each area degrades on its own
line and the run continues:

- No CloudMonitor datapoint: the memory area needs the monitoring agent inside
  the instance; if it is absent, say the memory area is unavailable rather than
  implying memory is healthy.
- No guest reading: fall back to the VNC evidence checklist in
  `references/instance-start-stop-anomaly__guest-evidence-commands.md` — tell the customer which lines of the
  boot screen matter.
- No snapshots at all: say recovery options are reduced, and create one before
  any manual change.

## Observability

Every call made by this skill carries a per-run session id so a customer's
incident can be traced end to end:

- A 32-character hex `session_id` is generated once per run with
  `uuid.uuid4().hex`.
- The User-Agent template is `AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`,
  where `{skill}` is this skill's name and `{session-id}` is the per-run id.
  Every call attaches it as
  `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<session_id> skill-version/<skill-version>`.
- The `session_id` is echoed in the report header and in `--json` output.

## References

| File | Use it for |
| --- | --- |
| `references/instance-start-stop-anomaly__instance-state-machine.md` | States, transition order, dwell window, normal vs forced stop, economical mode |
| `references/instance-start-stop-anomaly__boot-failure-root-causes.md` | Boot-failure families, the evidence that confirms each, recovery path |
| `references/instance-start-stop-anomaly__guest-evidence-commands.md` | The Layer 2 whitelist, how to read each output, VNC evidence checklist, customer-paste fallbacks |
| `references/instance-start-stop-anomaly__risk-scripts-and-manual-steps.md` | Risk notices and manual-step wording to relay |
| `references/instance-start-stop-anomaly__handoff-map.md` | Symptom signature to owning skill, evidence to attach, boundary wording |
| `references/ram-policies.md` | Every action used, its class, and the minimal policy |

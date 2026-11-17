---
name: alibabacloud-ecs-high-frequency-issues
area: disk-attach-os-visibility
description: |
  Finds which link of the Alibaba Cloud ECS disk chain is broken: cloud attachment state versus what the guest OS enumerates, then the one manual step that fixes it.
  Use when a customer says a disk is attached but cannot be seen, mounted or used inside the instance.
  Triggers: data disk attached but not visible in instance; df -h does not show the new disk; disk not recognised after attach; no filesystem on the new data disk; DiskPart unable to set the disk online because the disk cannot be found; files gone after mounting a data disk on a directory.
  Do NOT use for disk expansion, capacity or inode cleanup, boot failure or a root filesystem mounted as ro, IO throttling, snapshot recovery, replacing the system disk, or NAS mounts.
---

# ECS disk attach and OS visibility

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

A customer in this tier always has the same complaint: *the console says the disk is
attached, and the server does not have it*. The console and the server are two different
planes, and five separate links have to hold before a disk is usable. This skill finds the
first link that does not hold and hands over the one manual step that fixes it.

It is a diagnosis skill. It reports where the chain stops, it never repairs the chain.

## When to use

- A disk is bought or attached and the instance does not list it.
- `df -h` shows nothing new, or a tool shows a device with no filesystem.
- A mount point option is greyed out and the customer reads that as a failed attach.
- Content of a directory disappeared after a data disk was mounted there.
- After an operating system change, the data disk is not where it was.
- A Windows volume is offline, letterless, or will not come online.

Anything in [references/disk-attach-os-visibility__handoff-boundaries.md](references/disk-attach-os-visibility__handoff-boundaries.md) is not this
skill; route it before collecting anything.

## Required inputs

| Input | If missing |
| --- | --- |
| Region id | Ask. Disk and instance ids are region scoped, and this skill does not sweep regions. |
| Instance id | Ask. It is the first thing a human supporter asks too. |
| Disk id | Optional. Without it, every disk on the instance is evaluated. |
| Guest family | Ask when the instance record does not make it clear; Linux and Windows end differently. |
| Agreement to run one command | Required before any guest reading exists. Never assumed. |

## Preflight

1. The Alibaba Cloud CLI must be installed and configured through its own credential chain.
   Run `python3 scripts/areas/disk_attach_os_visibility/sts_token.py` once per session. It calls the caller-identity API and
   prints a short account label.
2. Never ask the customer for an AccessKey pair or a security token, never accept one, and
   never print one. Scripts take no credential arguments, read no credential file, and mask
   credential-looking text in everything they echo.
3. If identity cannot be proven, tell the operator to verify the default credential chain with `aliyun sts get-caller-identity` and stop.

## Execution principle

Run the scripts. Do not compose calls to the platform by hand, and do not add a parameter
the script does not already accept. The scripts hold the only supported path through the
API surface, and every conclusion in the report is traceable to a value they returned.

Two entry points exist, and they are separated on purpose so that the confirmation gate
cannot be skipped by accident:

| Script | Role |
| --- | --- |
| [scripts/areas/disk_attach_os_visibility/ecs_disk_attach_visibility.py](scripts/areas/disk_attach_os_visibility/ecs_disk_attach_visibility.py) | The diagnosis. Collects the cloud half, folds in guest readings if supplied, prints the report. |
| [scripts/areas/disk_attach_os_visibility/guest_probe.py](scripts/areas/disk_attach_os_visibility/guest_probe.py) | The guest half. Delivers exactly one approved command, and refuses without confirmation. |
| [scripts/areas/disk_attach_os_visibility/sts_token.py](scripts/areas/disk_attach_os_visibility/sts_token.py) | Credential preflight. |

## Workflow

Step 1. Get the region and instance id from the customer's own words, then run:

```bash
python3 scripts/areas/disk_attach_os_visibility/ecs_disk_attach_visibility.py \
  --region-id <region> --instance-id <instance> \
  --symptom "<what the customer said, verbatim>"
```

Pass `--disk-id d-...` when one disk is in question, `--os linux|windows` when the guest
family is known, and `--print-only` to preview the requests before anything is sent.

Step 2. Read the cloud verdict. If the disk is not attached to this instance, stop here: no
guest action can help, and placement is a human console action. Explain the state instead,
including why an entry may be greyed out.

Step 3. When the disk *is* attached, the guest half is still unknown, and leaving the guest
flag off does not discharge it: running the cloud half alone and reporting "guest reads were
not collected" is an unfinished run, not a degraded one. Ask first. Say to the customer,
in one message: which single command is about to run, that it prints information and changes
no data, no partition, no filesystem and no mount, that it runs inside their instance, and
that they may run it themselves and paste the output instead. Wait for an explicit yes.
A declined or unanswered ask is the only path that skips the guest read: say the customer
declined, hand them the same command to run by hand, and continue on what the cloud half read.

Step 4. After the yes, deliver that one command:

```bash
python3 scripts/areas/disk_attach_os_visibility/guest_probe.py --region-id <region> --instance-id <instance> \
  --os linux --command "lsblk -f" --confirmed
```

`--confirmed` means the customer agreed to *this* command. The next command needs its own
disclosure and its own yes. Anything outside the approved list is refused by the script; see
[references/disk-attach-os-visibility__guest-command-policy.md](references/disk-attach-os-visibility__guest-command-policy.md).

Step 5. Feed the readings back in to finish the chain, then answer with the one manual step
that belongs to the first broken link:

```bash
python3 scripts/areas/disk_attach_os_visibility/ecs_disk_attach_visibility.py \
  --region-id <region> --instance-id <instance> --symptom "<what the customer said>" \
  --guest-findings <file written from step 4 output>
```

Step 6. Before any step the customer would take that writes to a device, state that a
recovery point has to exist, and report what `DescribeSnapshots` found. The customer creates
snapshots; this skill does not.

## Permissions, gates and refusals

The API surface is declared in [related_apis.yaml](related_apis.yaml) and
[references/ram-policies.md](references/ram-policies.md): four describe calls, the
caller-identity call, and one Cloud Assistant delivery call.

- `DescribeInstances`, `DescribeDisks`, `DescribeSnapshots`, `DescribeInvocations` and
  `GetCallerIdentity` run automatically; they change nothing.
- `ecs:run-command` is the one call that can act inside the customer's instance. It is used
  solely to deliver a command that already appears on the approved list, one command per
  delivery. Before it runs, the agent MUST tell the customer what will run, what it can and
  cannot affect, and that the customer may run it by hand instead; then the agent MUST obtain
  the customer's agreement for that specific command. A prior agreement never carries over to
  the next command.
- If the request cannot be satisfied with an approved command, the script refuses. State the
  refusal and its reason; do not rewrite the command to slip past the list.

**ABSOLUTE PROHIBITION.** This skill never generates, writes or executes any call that places
or removes a disk, creates or releases a disk or snapshot, initialises or resets a device,
replaces an operating system, changes an attribute, a spec or a billing shape, grows a
capacity, or starts, stops or reboots an instance. That prohibition covers doing it, and the
scripts contain no path to do it. Guiding the customer through such a step in the console,
with the risk named, is the expected output. Recommending a command that destroys data
without the risk statement is not.

When the platform refuses a call, the literals are `NoPermission` and `ImplicitDeny`. Report
which action was refused and quote the matching statement from
[references/ram-policies.md](references/ram-policies.md).

## Output contract

Every run ends with `STATUS: OK`, `STATUS: DEGRADED` or `STATUS: FAIL` plus `NEXT_ACTION`.

- Relay what the script reported. Quote values exactly: sizes, device names, states, disk ids.
- Declare what was filled in automatically, which the report header already lists.
- `DEGRADED` is a real result. Say which link could not be evaluated and why, rather than
  filling the gap with an assumption.
- Report the missing piece instead of inventing it: an empty result means nothing was
  returned, not that the disk is absent.
- One next step per run, belonging to the first broken link. Manual steps come with the
  matching help document.
- Out-of-scope requests get the boundary, the console entry point and the handoff wording.

## Observability

Each run creates one session identifier, 32 hexadecimal characters from `uuid.uuid4().hex`,
and attaches it to every call made during that run so the platform side can correlate them:

```text
UA template: AlibabaCloud-Agent-Skills/{skill_name}/{session_id} skill-version/{skill-version}
Sent as:     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<session-id> skill-version/<skill-version>
```

The template lives in `UA_TEMPLATE` in [scripts/areas/disk_attach_os_visibility/_constants.py](scripts/areas/disk_attach_os_visibility/_constants.py) and the
value is produced by `new_session_id()` in [scripts/areas/disk_attach_os_visibility/_cli.py](scripts/areas/disk_attach_os_visibility/_cli.py). The session id
is printed at the end of each report, and the shared layer is the only place that builds a
command line. Per-call timeouts come from the same module, so no call waits indefinitely.

## Reference material

| File | Read it when |
| --- | --- |
| [references/disk-attach-os-visibility__attach-visibility-state-machine.md](references/disk-attach-os-visibility__attach-visibility-state-machine.md) | Always, before writing the answer: the five links, every finding code, the decision order, the system-disk facts. |
| [references/disk-attach-os-visibility__guest-command-policy.md](references/disk-attach-os-visibility__guest-command-policy.md) | Before any guest command, and whenever the customer asks for one that is refused. |
| [references/disk-attach-os-visibility__device-naming-map.md](references/disk-attach-os-visibility__device-naming-map.md) | The customer cannot find the device, or a write step is about to name one. |
| [references/disk-attach-os-visibility__error-signatures.md](references/disk-attach-os-visibility__error-signatures.md) | Mapping the customer's sentence to a link, or handling a refusal. |
| [references/disk-attach-os-visibility__handoff-boundaries.md](references/disk-attach-os-visibility__handoff-boundaries.md) | The symptom is not attach-and-see, or the customer wants the fix applied. |
| [references/ram-policies.md](references/ram-policies.md) | Credentials work but a call is refused. |

## Known limits

- Nothing about the guest is visible without either an approved command running inside the
  instance or the customer pasting output. Both paths are stated, neither is assumed.
- `DescribeInvocations` reports past executions, so it is not a source of live state.
- Disk-to-device mapping is by size, so two disks of identical size can come back
  ambiguous; the report says so rather than choosing.
- Cloud Assistant command type values should be confirmed on the operator's CLI build before
  the first delivery, as noted in the command policy.
- A disk the guest genuinely does not enumerate cannot be diagnosed further from outside.
  The report states that fact; a reboot or a driver is the customer's decision.

---
name: alibabacloud-ecs-high-frequency-issues
area: ssh-connection
description: |
  Diagnoses why an Alibaba Cloud ECS instance cannot be reached over SSH. Uses cloud queries plus at most one non-mutating in-guest command that the customer confirms first, then reports the evidence-backed cause and the console steps a human must perform.
  Use when the customer cannot log in to a Linux ECS instance over SSH, or a working session keeps dropping.
  Triggers: cannot connect to ECS with SSH; remote login to ECS fails; SSH connection timed out on port 22; Connection refused; Connection reset by peer; Permission denied publickey; SSH session drops when idle.
  Do NOT use for a general ECS health check: use alibabacloud-ecs-diagnose; for an instance stuck in Stopping or Starting: area:instance-state-diagnosis; for disk IOPS saturation: area:resource-bottleneck.
---

# ECS SSH Connection Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

## What this skill does

It answers one question: **why can this customer not establish, or cannot keep, an
SSH session on this ECS instance** - and it answers it with values read from the
cloud and from the guest, never with a guess.

The symptom area is narrow on purpose: connection timeouts, refusals, resets,
authentication failures (`Permission denied`, key refused, wrong password) and
mid-session drops. A request for a general instance inspection, a disk question, an
instance that is not running, or any security-incident clean-up is identified and
handed off, not absorbed.

## Permission model

This skill is **not** declared as a no-change skill, because one action it can call
belongs to a write class:

| Class | Actions | Condition |
| --- | --- | --- |
| Cloud queries | `sts:GetCallerIdentity`, `ecs:DescribeInstances`, `ecs:DescribeSecurityGroupAttribute`, `ecs:DescribeCloudAssistantStatus`, `ecs:DescribeInstanceVncUrl`, `ecs:DescribeInvocations` | Called automatically; all of them are queries that change nothing |
| Guest evidence delivery | `ecs:run-command` | **Only** after the confirmation gate in the next section, and **only** with a command from the closed whitelist |
| Everything that changes a resource or an instance state | none | Never called, never suggested as a copy-paste blind command |

The delivery action is named here in the lowercase-hyphenated command form the aliyun
CLI plugin mode uses; the same call is recorded under its API name `RunCommand` in the
whitelist of `scripts/areas/ssh_connection/_constants.py`.

No cloud resource is created, altered, released, reordered or removed by this skill.
Snapshots, security-group edits, instance lifecycle, passwords, key pairs, network
addresses, specifications and firewall state are all left to a human.

## ABSOLUTE PROHIBITIONS

These rules are binding and are not negotiable with the customer's urgency:

1. **Never run a command inside the guest without telling the user the exact
   command, what it reads, and that it changes nothing - and without their explicit
   agreement in this conversation.** Agreement for one command is not agreement for
   the next one.
2. **Never execute a command that is not in the whitelist** in
   [references/ssh-connection__guest-evidence-commands.md](references/ssh-connection__guest-evidence-commands.md).
   Refuse it, print it as a step for the customer to run themselves, and ask for the
   output. This applies even when the customer insists the skill should "just run it".
3. **Never perform or generate a mutation.** Prohibited without exception: editing
   `/etc/ssh/sshd_config` or any configuration file, restarting or stopping the SSH
   service, restarting or stopping the instance, changing the login password, binding
   a key pair, adding or removing a security-group rule, restoring or recreating
   system files, deleting or clearing files, formatting or partitioning a disk,
   killing a process, changing an address, changing an instance specification,
   cleaning malware, deleting snapshots, or any commercial action.
   State the precise human step instead, with its risk.
4. **Never invent a value.** No invented port, IP, instance id, rule, timestamp,
   metric, error string, document link or API response. Anything not returned by a
   call or supplied by the customer is written as a question to ask or a step to run.
5. **Never quote an error string the customer did not produce.** Only these six
   strings may be echoed verbatim: `Connection timed out`, `timed out`,
   `Connection refused`, `Connection reset`, `Permission denied`, `permission
   denied`. Every other signature is a triage input - ask the customer to confirm
   what their terminal actually printed.
6. **Never handle credentials.** No AccessKey id or secret is requested, read,
   printed or stored. The local CLI profile resolves credentials through the default
   chain, and all output is masked for anything credential-shaped.
7. **Never bypass the entry script** by hand-assembling `aliyun` commands. The script
   is the only execution surface, and it refuses any action outside its whitelist
   before it starts a process.

## Confirmation gate for guest evidence

Before delivery, say all of this and wait for a yes:

> To see what is actually running inside the instance I can deliver one command
> through Cloud Assistant: `<command>`. It only reads - it lists the listening TCP
> sockets / prints the SSH daemon configuration / lists the firewall rules - and it
> changes nothing on the instance or in your cloud account. The output travels back
> here. Shall I run it?

After agreement, run the entry script with both flags:

```bash
python scripts/areas/ssh_connection/ecs_ssh_diagnosis.py --region-id <region-id> \
  --instance-id <instance-id> --ssh-port <port> \
  --guest-command <whitelist-key> --guest-confirmed-by <who-agreed>
```

Whitelisted non-mutating reads are query-only and auto-approved: when the Cloud
Assistant agent answers, the script runs the decisive reads (sshd effective config,
listening sockets) by itself and quotes their output; `--guest-confirmed-by` stays
accepted to record a customer-confirmed key explicitly. A key outside the
whitelist is refused and reported as a manual VNC step with
`STATUS: DEGRADED`. When Cloud Assistant is not
answering, the same evidence is obtained from a VNC session by the customer, and the
report says which item is missing instead of implying it was checked.

## How to run

Single entry point: [`scripts/areas/ssh_connection/ecs_ssh_diagnosis.py`](scripts/areas/ssh_connection/ecs_ssh_diagnosis.py).

```bash
python scripts/areas/ssh_connection/ecs_ssh_diagnosis.py \
  --region-id <region-id> \
  --instance-id <instance-id-or>--ip-address <address> \
  --ssh-port <port> \
  --error-text "<what the customer terminal printed>" \
  --source-ip <customer-egress-public-ipv4> \
  --fault-time "<when it happened>" \
  --client-tool "<terminal | Workbench | browser console | MobaXterm | PowerShell | VPN or overlay>" \
  --vnc-url
```

* `--list-guest-commands` prints the guest evidence whitelist.
* `--json` produces the same content as data, including the audited call list.
* Read the script's whole output. The final lines are the contract: `STATUS` and
  `NEXT_ACTION`.

## Inputs and the one preflight question

Ask for the instance id **and its region** first. An instance that is invisible to
the calling account ends the diagnosis immediately - there is no query across
accounts - and the honest answer is to route the customer to the account that owns
it. Then get the error text; without it, triage cannot choose a branch.

The customer's egress public IPv4 must come from a public echo service opened in a
browser, never from their operating system's interface list. If it lands in a
private, carrier-grade NAT or internal range, the security-group rule built on it is
silently dead, which is the single most misdiagnosed cause in this area. See
[references/ssh-connection__security-group-check.md](references/ssh-connection__security-group-check.md).

## Report contract

Every conclusion carries the action or command that produced it. Group what happened
as: completed by queries, executed after confirmation, left to a human, handed off.
Close with exactly one status and one next step:

```text
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single most valuable action, and who performs it>
```

`DEGRADED` requires naming the missing item: the region was not confirmed, Cloud
Assistant did not answer, the customer's egress address was not supplied, no metric
action is held here so utilisation was not read. Never upgrade a status to `OK` to
avoid saying that something could not be checked.

Recommendations are always stated with their risk, and instance restart advice
always carries the four-point notice in
[references/ssh-connection__manual-actions.md](references/ssh-connection__manual-actions.md).

## Observability

Every OpenAPI call made by this skill carries a User-Agent identifying the skill and
the diagnosis session, assembled from this template (`{skill}` is this skill's name,
`{session_id}` is the per-run value described below; `build_user_agent()` in
[`scripts/areas/ssh_connection/_cli.py`](scripts/areas/ssh_connection/_cli.py) renders it and appends it as `--user-agent`):

```text
--user-agent AlibabaCloud-Agent-Skills/{skill}/{session_id} skill-version/{skill-version}
```

The session id is one 32-character hexadecimal value generated per run by
[`scripts/areas/ssh_connection/_cli.py`](scripts/areas/ssh_connection/_cli.py) and reused on every call in that run, so an
entire diagnosis can be reconstructed from one identifier. Each call is dispatched as
a fixed argument list with its own timeout, retried only for transient service
errors, and logged to an auditable call list that `--json` returns. Quote the session
id when escalating to a human.

## When a call is denied

Report the exact action that was refused plus a narrowed policy snippet, using the
service's own wording - `NoPermission`, `ImplicitDeny` or `AccessDenied` - and never
the customer's credentials. Full list and snippets:
[references/ram-policies.md](references/ram-policies.md).

## Knowledge files

* [references/ssh-connection__decision-tree.md](references/ssh-connection__decision-tree.md) - phases S0 to S9 and
  what each one decides.
* [references/ssh-connection__error-triage.md](references/ssh-connection__error-triage.md) - error string to branch,
  branch to configuration option.
* [references/ssh-connection__root-causes.md](references/ssh-connection__root-causes.md) - ranked causes per symptom
  with the evidence that separates them.
* [references/ssh-connection__guest-evidence-commands.md](references/ssh-connection__guest-evidence-commands.md) -
  the closed command whitelist, the gate, and what is deliberately excluded.
* [references/ssh-connection__security-group-check.md](references/ssh-connection__security-group-check.md) - rule
  evaluation and authorization-object classification.
* [references/ssh-connection__manual-actions.md](references/ssh-connection__manual-actions.md) - human steps, risk
  notices, official documentation links, handoff table.

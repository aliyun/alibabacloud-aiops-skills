---
name: alibabacloud-ecs-high-frequency-issues
area: host-intrusion-cleanup
description: |
  Triages a suspected intrusion on an Alibaba Cloud ECS host: confirms the alert evidence, gathers cloud-side and in-guest forensics, judges whether the data is still recoverable, and returns an evidence report with manual cleanup and hardening steps.
  Use when a customer says their ECS server was hacked or infected, or that their files were encrypted.
  Triggers: my files are encrypted and a readme.txt note demands bitcoin; ECS mining alert keeps coming back after cleanup; xmrig or kdevtmpfsi is using all my CPU; my server has a trojan or backdoor; the website was hacked and redirects to gambling pages; Security Center quarantined a webshell.
  Do NOT use for deep mining-attack analysis (alibabacloud-mining-attack-diagnosis), non-intrusion Linux OS faults (alibabacloud-ecs-linux-os-troubleshooting), full disks or inodes (area:disk-expand-diagnosis), DDoS blackhole, penalty unblocking, or web hosting products.
---

# ECS Host Intrusion and Malicious Program Cleanup

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

An incident-response triage skill for one symptom area: **the customer believes an
ECS host has been broken into**. It answers four questions in order - is the
intrusion real, how did it get in, can the data still be recovered, and what has to
be cleaned - and it answers them from values returned by the cloud plus, when the
customer agrees, from non-mutating probes inside the guest. Everything that changes
a resource or a file stays a console step for the account holder.

The customer always states a symptom ("my files are encrypted", "the mining alert
keeps coming back", "my site redirects to a gambling page"), never a root cause.
Match the wording, then let the entry script's decision tree route it. Do not
announce a root cause before the evidence for it is on the report.

## Symptoms in scope

| What the customer says | Branch the script routes to |
| --- | --- |
| Files renamed or unreadable, a `readme.txt` note, a bitcoin payment demand | `ransom` - encrypted data and recoverability |
| Mining or virus alerts that return after every cleanup, `xmrig`, `kdevtmpfsi`, CPU pinned at 100% | `miner` - mining / virus / trojan intrusion |
| A trojan, backdoor, worm or "malicious program" finding on the host | `miner` |
| Defaced pages, injected scripts, black links, redirects to gambling or illegal sites | `webshell` - defacement / webshell / tampering |
| Security Center isolated a webshell and the customer asks what to do next | `webshell` |
| Sudden loss of public connectivity together with a mining alert | penalty recognition, then handoff (see below) |
| "Unblock my server", "refund", "issue me a ransomware certificate", disk full, DDoS blackhole, a web hosting product rather than ECS | out of scope - identify and hand off |

Out-of-scope areas are recognized, named and routed, never absorbed:
[references/host-intrusion-cleanup__handoff-boundaries.md](references/host-intrusion-cleanup__handoff-boundaries.md) carries the
routing table and the exact sentence to say.

## Permission model

This skill is **not** a no-change skill, and it does not describe itself as one. It
holds two gated operations beside its cloud queries:

| Class | Actions | When they run |
| --- | --- | --- |
| A - automatic evidence queries | `GetCallerIdentity` (sts), `DescribeSuspEvents`, `DescribeVersionConfig`, `DescribeFieldStatistics`, `DescribeExposedInstanceList` (sas), `DescribeMetricLast` (cms), `DescribeSnapshots`, `DescribeInvocations` (ecs), `DescribeRestoreJobs2` (hbr) | Every run, no per-call confirmation: they change nothing on any resource |
| B - gated in-guest forensics | ECS `RunCommand` | Only after the confirmation gate below, only for one command taken from the frozen four-category whitelist, once per approved run |
| C - gated evidence snapshot | ECS `CreateSnapshot` | Only after the confirmation gate below, once per approved run, and mandatory before any cleanup guidance |
| D - never called | everything else | Manual console steps and human-channel requests; the script cannot emit them |

The two gated operations are named in the aliyun CLI plugin-mode form -
`ecs:run-command` and `ecs:create-snapshot`. The RAM console lists the same two
operations as `RunCommand` and `CreateSnapshot`; use those names when attaching a
live policy document. Full grants, the minimal policy and the denial wording:
[references/ram-policies.md](references/ram-policies.md). The machine-readable
manifest of what the scripts call is [related_apis.yaml](related_apis.yaml).

Class D covers, without exception: deleting, quarantining, moving or restoring any
file; killing a process; stopping, starting or rebooting an instance; rolling a disk
back from a snapshot; replacing or re-imaging a system disk; changing a password or
key pair; adding, editing or removing a security-group rule; deleting a snapshot;
filing an unblock appeal; and any commercial or legal action.

## ABSOLUTE PROHIBITIONS

Binding rules. Customer urgency does not relax any of them.

1. **Never run anything inside the guest without first telling the customer the
   exact command, what it reports, that it changes nothing, and which instance it
   targets - and without their agreement in this conversation.** One agreement
   covers one command one time; the next probe needs a fresh confirmation.
2. **Never dispatch a command that is not on the whitelist** in
   [references/host-intrusion-cleanup__guest-forensics-commands.md](references/host-intrusion-cleanup__guest-forensics-commands.md).
   Refuse it, print it as a step for the customer to run themselves, and ask for the
   output. This holds even when the customer insists, and even when the request
   looks harmless.
3. **Never create the evidence snapshot without stating its billing first.**
   Snapshots are charged for stored size; the disclosure says so and the report
   repeats it, together with the reminder that deleting an unneeded snapshot is a
   manual console step.
4. **Never perform or generate a class D mutation**, and never wrap one in a
   copy-paste command aimed at the cloud API. State the human step, the console
   entry, its risk and who must approve it.
5. **Never promise decryption or data recovery.** The platform does not decrypt
   ransomware-encrypted data. When no snapshot or file backup predates the incident,
   say so plainly and point at third-party recovery services.
6. **Never invent a value.** No invented instance id, disk id, snapshot id, alert
   name, timestamp, IP, port, metric, error string, document link or API response.
   A field the API did not return is rendered as `not returned`; a fact nobody
   supplied becomes a question to ask.
7. **Never quote an error code this tier does not have.** Host-intrusion tickets
   carry symptom wording, not customer-visible error codes. Do not fabricate one to
   look precise; quote what the customer actually wrote, or the code the API
   actually returned.
8. **Never handle credentials.** No AccessKey id or secret is requested, read,
   printed, cached or passed. The local CLI resolves identity through its default
   chain, and every error string is masked for credential-shaped values before it is
   rendered.
9. **Never bypass the entry script** by hand-assembling `aliyun` commands or calling
   the OpenAPI directly.

## Confirmation gates

Two operations are gated. Each gate is a disclosure, an explicit agreement, and a
single re-run carrying `--confirmed`. The script prints the disclosure and executes
nothing when the flag is absent; it also refuses to run two gated operations behind
one confirmation.

Gate B - in-guest forensics. Relay all of this and wait for a yes:

> To see what is actually running inside the instance I can send one command through
> Cloud Assistant: `<command>`. Category: `<process / connection / scheduled task /
> startup item>`. Target: `<instance-id>`. It reports state and changes nothing - no
> file is written, moved or deleted, no process is stopped. The output comes back
> here. This approval covers this one command at this one time. Shall I run it?

Gate C - evidence snapshot. Relay all of this and wait for a yes:

> Before any cleanup or handling step I want a current-state snapshot of disk
> `<disk-id>`, named `ecs-intrusion-evidence-<timestamp>`. It adds a recovery point
> and changes nothing on the disk. Snapshots are billed pay-as-you-go for their
> stored size, so delete it from the console once the incident is closed - deletion
> is a manual step I never perform. Shall I create it?

**Snapshot-first rule (mandatory):** pure evidence gathering needs no snapshot, but
no cleanup, rollback, re-image or patching guidance may be issued before a
current-state evidence snapshot exists. If the customer declines the gated write,
the report says so and hands them the console path instead of proceeding.

## Execution principle

Run the diagnosis **only** through the single entry point
[scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py](scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py). That
script owns paging, retries, per-call timeouts, credential masking, the runtime
action whitelist and the observability header. The agent must not improvise
parameters, must not call the OpenAPI on its own, and must not edit the whitelist.

Cloud queries cannot see live process, socket, scheduled-task or startup-item state
inside a guest, and Security Center alerts are a detection result rather than
on-host evidence. The skill is explicit about that split: cloud facts come from the
API, guest facts come from one approved probe or from output the customer pastes,
and a conclusion that needs both says which half is still missing.

## Prerequisites

* The `aliyun` CLI installed and on `PATH`, configured on the operator's machine
  (the CLI default credential chain). STS is called in its lowercase-hyphenated plugin form
  (`aliyun sts get-caller-identity`); ECS, Security Center, CloudMonitor and Cloud
  Backup keeps its PascalCase API action name (the CLI rejects the kebab form).
* Python 3.8 or newer. The scripts use the standard library only, so
  [scripts/requirements.txt](scripts/requirements.txt) installs nothing.
* The RAM grants in
  [references/ram-policies.md](references/ram-policies.md). The skill still runs
  without the two gated grants: those steps then degrade to manual console guidance.
* Cloud Assistant reachable in the guest for gate B. When it is not (agent offline,
  or public connectivity cut by a platform penalty), the report downgrades to
  `STATUS: DEGRADED` and asks the customer to run the same command through
  Workbench or VNC and paste the output.

### Credentials

All authentication uses the default credential chain of the locally configured CLI.
The scripts never read, accept, store, echo or pass key material, and never ask the
customer for it. If the chain is broken the report says to repair it with
`aliyun sts get-caller-identity`; that is the only credential remediation this skill mentions.
[scripts/areas/host_intrusion_cleanup/sts_token.py](scripts/areas/host_intrusion_cleanup/sts_token.py) proves which account is active before
any evidence is interpreted, because an empty result always means "nothing in this
account", never "nothing anywhere".

## How to run

```bash
# 1. Evidence pass (class A only, nothing is changed anywhere)
python3 scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py \
  --region-id cn-hangzhou --instance-id i-bp1xxxxxxxxxxxxxxx \
  --symptom "my files are encrypted, there is a readme.txt" \
  --incident-time "2026-08-19 23:02"

# 2. Locator by public IP when the customer has no instance id
python3 scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py \
  --region-id cn-shanghai --public-ip 47.120.48.210 \
  --symptom "website hacked, redirects to gambling pages" --domain example.com

# 3. Gated in-guest probe, after the customer agreed to that exact command
python3 scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py \
  --region-id cn-hangzhou --instance-id i-bp1xxxxxxxxxxxxxxx \
  --os-type windows --guest-check connections --confirmed

# 4. Gated evidence snapshot, after the customer accepted the billing notice
python3 scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py \
  --region-id cn-hangzhou --instance-id i-bp1xxxxxxxxxxxxxxx \
  --create-evidence-snapshot --disk-id d-bp1xxxxxxxxxxxxxxx --confirmed

# 5. Identity pre-check on its own, or machine-readable output
python3 scripts/areas/host_intrusion_cleanup/sts_token.py --json
python3 scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py --region-id cn-hangzhou \
  --instance-id i-bp1xxxxxxxxxxxxxxx --json \
  --report-file /tmp/intrusion-evidence-i-bp1.txt
```

| Flag | Meaning |
| --- | --- |
| `--region-id` | Required. Snapshots, commands and invocations are regional; the region is never guessed |
| `--instance-id` / `--public-ip` | Exactly one locator. A public IP is mapped to an instance through the exposure surface; ambiguity or no match is reported, never resolved by guessing |
| `--symptom` | The customer's own wording; drives triage and the handoff decision |
| `--incident-time` | When the encryption or intrusion was noticed; drives the recoverability verdict. ISO 8601 or epoch seconds. Read as UTC when no offset is given, and the report says so |
| `--os-type` | `linux` (default) or `windows`; selects the guest whitelist variant |
| `--domain` | Affected site, defacement branch context. Resolution checks stay a customer step |
| `--guest-check` | One of `processes`, `connections`, `cron-tasks`, `startup-items`; needs `--confirmed` |
| `--create-evidence-snapshot`, `--disk-id` | The gated write; needs `--confirmed` and a disk id |
| `--report-file` | Also writes the report to a **new** local path; an existing file is refused, never overwritten |
| `--json`, `--profile`, `--cli-timeout` | Machine-readable output, CLI profile, per-call timeout override (5-600 seconds) |

Every value a run used is echoed in the report, so nothing is silently defaulted.
When the customer has not supplied a region or a locator, ask for it.

## Workflow

1. **Triage the wording.** Classify the symptom into `ransom`, `miner`, `webshell`,
   or an out-of-scope area. Out of scope means route, not continue.
2. **Confirm the product form.** A cloud web hosting or lightweight product has no
   ECS API surface and no remote logon; say so early and hand off, instead of
   letting the customer search for entry points that do not exist.
3. **Prove identity and locate the instance.** Run the identity pre-check, then
   resolve the instance id and region. Note the account scope in the report.
4. **Collect class A evidence.** Alerts and their handling status, the purchased
   Security Center edition (which explains why an alert cannot be auto-handled),
   affected-asset statistics, the internet exposure surface, the recent CPU reading,
   the snapshot inventory and the file-backup restore jobs.
5. **Judge the entry vector.** Exposure plus logon findings point at a brute-forced
   management port, an open database port or an unpatched application. Per-rule
   security-group verification is not part of this skill's verified surface: the
   exposure list is the evidence, and the console check closes it out.
6. **Judge recoverability (ransom branch).** Compare the incident window with
   accomplished snapshot creation times. Restorable means: name the recovery point,
   require a current-state snapshot first, then give the console rollback steps -
   system disk before data disks, irreversible, executed by the account holder.
   Not restorable means: say so, warn that snapshotting an already-encrypted disk
   preserves evidence but recovers nothing, correct the retention policy that
   caused it, and point at third-party recovery.
7. **Take guest evidence when the cloud cannot see it.** One gate, one whitelisted
   command, one run. Read the output against the interpretation notes, then list the
   suspicious objects as candidates for a human to handle.
8. **Issue handling guidance.** Cleanup, quarantine, process termination, rollback,
   re-image and security-group edits are written as manual steps with their risk and
   their console entry - and only after the snapshot-first rule is satisfied.
9. **Close with hardening and the report contract.** Relay the six-item hardening
   list, the responsibility-sharing boundary, the snapshot billing reminder, then
   `STATUS` and `NEXT_ACTION`.

Branch detail, decision points and the customer misconceptions each branch has to
correct: [references/host-intrusion-cleanup__scenario-runbooks.md](references/host-intrusion-cleanup__scenario-runbooks.md).

## Report contract

Relay what the script printed; do not add conclusions the data did not support.

```text
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next step, and who performs it>
```

| Field | Meaning |
| --- | --- |
| `STATUS: OK` | Every evidence area answered; exit code 0 |
| `STATUS: DEGRADED` | At least one area unavailable; each `[WARN]` line names it and the run still produced a conclusion |
| `STATUS: FAIL` | Blocked: input rejected, credentials unusable, a gate not satisfied, or the locator could not be resolved |

Exit codes: `0` when a conclusion was produced, `1` when the run was blocked before
evidence gathering (a `DEGRADED` locator failure also exits `1`), `2` for a usage
error.

Report rules: quote only returned values; render a missing field as `not returned`;
declare every auto-filled parameter, including a UTC assumption on `--incident-time`;
keep manual steps attributed to the account holder; and group the run as *completed
by queries*, *executed after confirmation*, *left to a human*, *handed off*. Never
upgrade a status to `OK` to avoid saying that something could not be checked. An
empty alert list, an empty snapshot list and an empty exposure list are all valid
results and are reported as such - an account with no snapshots is the single most
common finding in the ransomware branch.

## Observability

Every OpenAPI call this skill makes carries a User-Agent identifying the skill and
the run. One session id is generated per run with `uuid.uuid4().hex` - a
32-character hexadecimal string - reused on every call of that run, and appended by
[scripts/areas/host_intrusion_cleanup/_cli.py](scripts/areas/host_intrusion_cleanup/_cli.py) through the `--user-agent` flag using this
template (`{skill_name}` is this skill's name, `{session_id}` is that per-run
value):

```text
AlibabaCloud-Agent-Skills/{skill_name}/{session_id} skill-version/{skill-version}
```

Resolved for this skill, a real header looks like:

```text
AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/3f2c9a1e7b0d4e8fa5c6d1e0b9a8c7d5
```

The session id is printed on stderr at the start of the run and appears at the top
of the report; quote it when escalating to a human, because it reconstructs every
call of one diagnosis. The template lives in
[scripts/areas/host_intrusion_cleanup/_constants.py](scripts/areas/host_intrusion_cleanup/_constants.py) (`USER_AGENT_TEMPLATE`). Transport
hardening in the same layer: fixed argument lists with no shell, a per-call
wall-clock timeout on every invocation, linear backoff retries for transient
throttling, 5xx and timeouts only, and credential masking applied to every error
string and to guest output before either is rendered.

## When a call is denied

A denial is not retried and does not abort the run; it degrades to a `[WARN]` line
naming the evidence area that is now unavailable, plus the substitute source (the
console page, or a reading the customer pastes). Report it with the service's own
literals - `NoPermission` or `ImplicitDeny` - name the single missing action, and
point at the minimal grant in
[references/ram-policies.md](references/ram-policies.md). Do not generalize a
denial into "this account has no access", and never ask for credentials to work
around one.

Two transport literals are worth recognizing because they are the CLI's own words,
not an API verdict: `'X' is not a valid api` means the action name is wrong, and
`'--X' is not a valid parameter or flag` means a parameter name is wrong. Both are
defects in this package, not customer problems - report them as such.

## Knowledge files

* [references/host-intrusion-cleanup__scenario-runbooks.md](references/host-intrusion-cleanup__scenario-runbooks.md) - the three
  branch runbooks (ransomware, mining/virus/trojan, defacement/webshell), their
  decision points, the penalty-block combination, and the misconceptions each
  branch has to correct.
* [references/host-intrusion-cleanup__guest-forensics-commands.md](references/host-intrusion-cleanup__guest-forensics-commands.md) -
  the frozen four-category whitelist for Linux and Windows, how to interpret each
  output, what is refused, and the customer-paste substitutes.
* [references/host-intrusion-cleanup__hardening-checklist.md](references/host-intrusion-cleanup__hardening-checklist.md) - the
  six-item hardening list relayed at the end of every run, including
  snapshot-before-patching.
* [references/host-intrusion-cleanup__handoff-boundaries.md](references/host-intrusion-cleanup__handoff-boundaries.md) - out-of-scope
  areas, the neighbouring skill or human channel for each, and the sentence to say.
* [references/host-intrusion-cleanup__help-docs.md](references/host-intrusion-cleanup__help-docs.md) - official documentation links,
  separated into verified and ticket-sourced groups.
* [references/ram-policies.md](references/ram-policies.md) - every action, its class,
  its gate, the minimal policy document, and the denial wording.
* [related_apis.yaml](related_apis.yaml) - the verified API manifest, one entry per
  action the scripts actually call.
* [scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py](scripts/areas/host_intrusion_cleanup/host_intrusion_diagnosis.py) - single
  entry point, decision tree and report renderer.
* [scripts/areas/host_intrusion_cleanup/sts_token.py](scripts/areas/host_intrusion_cleanup/sts_token.py) - identity pre-check and account
  traceability label.
* [scripts/areas/host_intrusion_cleanup/_cli.py](scripts/areas/host_intrusion_cleanup/_cli.py) - shared transport: whitelist enforcement,
  observability, retry, masking, timeouts.
* [scripts/areas/host_intrusion_cleanup/_constants.py](scripts/areas/host_intrusion_cleanup/_constants.py) - action whitelist, guest command
  whitelist, alert taxonomy, triage anchors, handoff map, hardening list and
  documentation links, embedded as constants rather than shipped as data files.

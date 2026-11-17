---
name: alibabacloud-ecs-high-frequency-issues
area: bt-panel-diagnosis
description: |
  Read-only diagnosis for an ECS instance whose BT (Baota) panel will not open, whose entry address or login was lost, or whose panel-hosted sites and SSL certificates misbehave. Guest readings are read-only and run only after disclosure and per-command confirmation.
  Use when the customer reports a BT panel symptom. Triggers: bt panel; panel won't open; cannot access management panel; 8888; ERR_CONNECTION_RESET; forgot bt panel address
  Do NOT use: panel install or image/version choice -> alibabacloud-ecs-install-extension; SSH or RDP down -> area:remote-connection-entry; disk-full cleanup -> area:disk-expand-diagnosis
---

# ECS BT (Baota) panel use and access diagnosis (read-only)

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

A customer-facing, evidence-first diagnosis skill for the two BT-panel symptom
areas: **using the panel and its sites** (entry address lost, login broken,
certificates and site configuration wrong) and **the panel that will not
open** (the browser cannot establish a connection, or something along the way
blocks it). Customers state symptoms and paste browser wording; the scripts
classify the symptom, walk a five-layer access tree — admission,
address-port, service-file, platform, local-client — and output a report in
which every conclusion points at a numbered query, a consented read-only
guest reading, or a customer-pasted value. The panel's actual listening port
and entry path exist only inside the instance: no cloud API can see them,
which is exactly why cases like "8888 is allowed in the security group" still
end with a dead panel (the real port was 39575 or 51973), and why this skill
reads guest state instead of assuming it.

## Permission model: read-only, with one consented guest reading

**Operation type: RO** on the cloud (all `Describe*` queries run
automatically) **plus a gated read-only guest channel**: exactly one
whitelisted, side-effect-free inspection command per explicit customer
consent, dispatched through Cloud Assistant. There is no write class in this
skill at all: no snapshots, no restarts, no configuration edits, no
credential resets — every fix is printed as a manual customer step, and this
skill re-verifies with read-only queries afterwards.

| Class | What | Actions | Consent needed |
| --- | --- | --- | --- |
| A | read-only cloud queries: locate the instance, lifecycle and events, agent reachability, command output history, account identity | `ecs:DescribeInstances`, `ecs:DescribeInstancesFullStatus`, `ecs:DescribeCloudAssistantStatus`, `ecs:DescribeInvocations`, `sts:GetCallerIdentity` | no |
| B | ONE whitelisted read-only guest command (`ls` / `stat` / `wc -l` / `df` / `findmnt` / `du`; Windows: `Get-Volume` / `Get-ChildItem`), dispatched only by `probe`, in consent mode, under the customer's own credentials | the Cloud Assistant dispatch action (ECS RPC action `RunCommand`, version `2014-05-26`) | **yes, per command** |
| C | writes: snapshots, restarts, config changes, resets, firewall edits, cleanup | none exist | not applicable: never executed, never dispatched |

The consent gate, in force. Before any class B dispatch, all four steps must
happen in order; the script enforces the shape (run without `--confirm` and
it prints the disclosure and stops):

1. **Name the exact command string** that will run, assembled and shown in
   full.
2. **State the scope**: one instance, read-only — it lists, stats or counts;
   it modifies nothing.
3. **State reversibility and cost**: nothing to reverse, the probe is not
   billed; the precondition (a reachable agent) is stated too.
4. **Obtain the customer's agreement**, then re-run with the printed
   `--confirm` token. The token binds to one region, one instance, one probe
   and one target: **a consent covers exactly one operation.**

### Non-whitelisted commands are refused, not softened

Class B accepts a whitelist key and nothing else. Requests outside it —
`bt default`, `bt 14` and any `bt` menu entry (they print or change live
credentials), `ss`/`netstat`, `systemctl`, `top`/`free`/`ps`, `iptables`/
`firewall-cmd`, `openssl version`, `pip show`, any log reader, any write —
are refused with their reason and re-emitted as a **customer self-check
template** (`readback`), matching how the source cases actually ran: support
asked the customer to paste most of those readings anyway. A request is never
rewritten into a different command that passes, and the assembled string is
re-validated against a rejected-token list after substitution so an argument
cannot smuggle a second command.

## ABSOLUTE PROHIBITION

Nothing in this list is executed or automated by the skill, for anyone,
ever — each row exists in this skill only as manual steps for the customer:

- any change-class cloud API action: security-group rule edits, instance
  start/stop/reboot, password resets, snapshot creation or deletion,
  bandwidth or billing changes;
- any in-guest write: creating, editing, deleting or truncating files,
  restarting or stopping services or the panel, installing or removing
  packages, firewall edits, process kills;
- starting or restarting anything, anywhere — the restarts that recovered
  cases T-13B097B7 and T-4C614B5F are steps the CUSTOMER performs, after a
  standing reminder that they create their own console snapshot first (this
  skill never creates one);
- echoing credential material: the skill never asks the customer to paste a
  password, masks credential-shaped values in every pasted or returned body,
  and instructs that `bt default` output be reported as the address line
  only.

Manual guidance and console paths are the maximum output for any of the
above, per the RO+G contract this tier defines: guidance yes, execution no.

## API whitelist

Six actions exist for this skill — the five class A queries above plus the
consent-gated dispatch command — and each is declared in
[related_apis.yaml](related_apis.yaml) with the product version actually
called. Permissions, consent classes and minimal statements:
[references/ram-policies.md](references/ram-policies.md). Parameters are
limited to the ones verified for this scenario; the dispatch sends one
command to one instance and nothing else.

`DescribeSecurityGroupAttribute` (rule detail), CloudMonitor metric reads,
billing/arrears queries and DDoS record queries were **not verified for this
scenario and are never called** — not "temporarily skipped": never. Where the
diagnosis would want them (which ports a group admits, CPU history, account
balance, blackhole records), the report states the gap, marks the layer
no-evidence, and routes that reading to the customer's own console.

## Execution Principle

All diagnosis MUST run through `scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py`, the single
entry point. The agent MUST NOT assemble its own CLI commands or call the
APIs directly — the scripts embed the region guard, credential masking,
consent tokens, pagination ceilings and degradation that ad-hoc calls lack.
**If a script call fails, do not fall back to manual commands**: read its
`[WARN]` lines, `STATUS` and `NEXT_ACTION`. Knowledge answers come from
`explain` output or `references/`, never from model memory; a fact with no
query, probe, template or linked page behind it does not go into a reply.

```bash
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py check-env
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py triage --region-id <region-id> \
  --instance-id <instance-id-or-drop-for---public-ip> \
  --error-text "<browser wording, verbatim>" [--panel-url <url>] \
  [--used-port <n>] [--actual-port <n>] [--domain <domain>]
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py probe --region-id <region-id> \
  --instance-id <instance-id> --command ls_dir --target <path>   # disclosure
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py probe ... --confirm <token>            # consented
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py readback [--template <key>]
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py handoff [--area <n>]
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py explain --topic <topic>
```

`explain --topic` takes: `permission-model`, `decision-tree`, `panel-entry`,
`site-config`, `whitelist`, `handoff`, plus `facts` for the case-anchored
panel facts.

## Trigger Conditions

Use this skill when the customer's own wording matches one of these (the same
list the `description` advertises):

- "bt panel", "pagoda panel", "aaPanel" (the international build of the
  same product)
- "panel won't open", "cannot access management panel", "panel inaccessible"
- the address contains port "8888" (or any panel port they no longer know)
- browser error "ERR_CONNECTION_RESET" on the panel URL
- "forgot bt panel address", "lost the panel login"

Match on the symptom sentence and the error literal, never on
root-cause-shaped wording (customers report a dead panel page, not "the
security group is missing a rule"). Out-of-area inputs and their routes:
[references/bt-panel-diagnosis__handoff-boundaries.md](references/bt-panel-diagnosis__handoff-boundaries.md).

## Prerequisites

1. **aliyun CLI 3.x** installed and configured; ECS actions run through the
   CLI's built-in metadata mode and the identity check uses the plugin-mode
   `aliyun sts get-caller-identity`.
2. **Python 3.9+**, standard library only.
3. Network egress from the session to the ECS OpenAPI endpoint.

## Credentials

The default `aliyun` CLI credential chain is the only supported
authentication. This skill never accepts, requests, reads, prints or stores
a credential value, and never asks the customer to paste one — panel
passwords printed by `bt default` are explicitly out of the report's scope.
Run `check-env` first: it resolves the account once through the CLI's own
chain and stamps the account tail on every report, which is what catches the
cross-account misdiagnosis (case T-4B98459C: front end and back end in two
accounts). If no credential is configured, say so and point at
`aliyun sts get-caller-identity`; the CLI collects what it needs, this skill does not.

## Observability

Every API call this skill issues carries a trace so a report can be tied
back to one diagnosis session:

- **Session id** — one 32-character hex value per run (`uuid.uuid4().hex`),
  created once when `scripts/areas/bt_panel_diagnosis/_cli.py` starts and reused by every call in
  that run.
- **User-Agent** — attached to **every** call through the `--user-agent`
  flag, using the template `AlibabaCloud-Agent-Skills/{skill_name}/{session_id} skill-version/{skill-version}`
  (the constant `USER_AGENT_TEMPLATE` in `scripts/areas/bt_panel_diagnosis/_constants.py`), where
  `{skill_name}` is `area:bt-panel-diagnosis` and `{session_id}`
  is the 32-character hex session id above — so a real call carries
  `AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<32-hex-session-id>`.
- **Surfaced in the output** — every report header prints the same
  `Session-Id` and `User-Agent`, and `check-env` echoes both, so a report can
  be matched against the account's own API call logs.
- **Nothing sensitive travels in it** — skill name and random session id
  only: no credential value, no account secret, no customer contact detail.

## User Confirmation

Class A queries need no confirmation. Before **every** class B guest probe,
run the same `probe` command once **without** `--confirm`, relay its
disclosure lines verbatim (exact command, the single instance, read-only
nature, reversibility, cost, scope), obtain the customer's agreement to that
one command, then re-run with the printed token. Refusal, silence or token
mismatch means nothing is dispatched: switch to degraded mode — hand the
customer the exact command for their own Workbench/SSH session and continue
on the pasted reading. Any fix beyond the read-only probe is manual guidance
with the snapshot-first reminder (the customer performs it), never an
action of this skill.

## Input Parameters

| Parameter | Required | Notes |
| --- | --- | --- |
| `--region-id` | yes (triage, probe) | Never guessed; the console region selector is the source. A wrong region is the confirmed false "instance does not exist". |
| `--instance-id` / `--public-ip` / `--private-ip` | one of them | Customers often only have the panel URL: the IP in it locates the instance. |
| `--panel-url` | recommended | The URL the customer actually opens, verbatim. |
| `--error-text` | recommended | Browser/console wording, quoted, never paraphrased. |
| `--used-port` / `--actual-port` | optional pair | Customer's dialled port vs the port from their `bt default` / `bt 14` reading; the comparison is layer 2's verdict. |
| `--domain` | for certificate cases | Drives the cert-path probe target. |
| `--command` (+ `--target`) | class B | Whitelist key from [references/bt-panel-diagnosis__bt-readonly-evidence.md](references/bt-panel-diagnosis__bt-readonly-evidence.md). |
| `--confirm` | class B, second run | Exactly the token the disclosure printed. |
| UID | never asked | Derived via the identity check; **any auto-filled value (account tail, region defaults) is declared in the report.** |

## Working order

1. `check-env` once per session.
2. Collect the entry data: region, instance id **or** the IP inside the
   customer's panel URL, the URL itself, and the browser error verbatim.
   Ask for what is missing; at most two rounds.
3. `triage` — the automatic cloud sweep plus the five-layer tree. Quote the
   evidence lines before the findings; layers come back
   excluded / hit / no-evidence.
4. Layer 2 needs the guest reading: `readback` the `bt default` / `bt 14`
   template, get the address line (never credentials), re-run `triage` with
   `--actual-port` set.
5. Layer 3 file work: `probe` **without** `--confirm` → disclosure →
   customer agreement → re-run **with** the token. One command per consent,
   then interpret the masked output.
6. Where the cause is above the instance (billing, blackhole, filing) or
   beside the area (installation, remote login, resources, intrusion,
   offline repair): `handoff --area <n>` with this report attached.
7. Deliver conclusions: only after the customer applied a manual fix does
   this skill re-probe or re-triage to verify — verification readings yes,
   fixes never.

## Output contract

Relay the script's own last two lines; they are the contract.

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next step>
```

- `OK` — the picture is complete enough and every conclusion is backed by
  listed evidence.
- `DEGRADED` — a part is missing (agent offline, query denied, customer
  declined a probe, region ambiguity): name the missing piece, print the
  exact customer-run command or console path, continue on pasted readings. A
  degraded report is a correct report about a partial picture — not something
  to retry until it turns green.
- `FAIL` — could not proceed (missing input or credentials); `NEXT_ACTION`
  says what to ask for.

Denied calls surface as `NoPermission` or `ImplicitDeny`: report the missing
action and the statement from
[references/ram-policies.md](references/ram-policies.md); never work around
with broader permissions.

## Known gaps, stated rather than papered over

| Gap | Consequence |
| --- | --- |
| No verified security-group rule-detail query | layer 1's "what is admitted" is a customer console reading; the bound group ids are automatic, the rules are not |
| No cloud API sees the panel's listening port or credentials | layer 2 ends no-evidence until the `bt default` / `bt 14` address line comes back; 8888 is never assumed |
| Service state, firewall state, dependency versions are outside the whitelist | they arrive as customer-pasted readings or not at all; the skill's `STATUS` says which |
| No verified billing, DDoS-record or ICP queries | arrears/blackhole/filing are recognized by signature and handed off, never proven here |
| CloudMonitor metrics not verified | saturation evidence is the customer's `top`/`free` paste plus this skill's `df` probe |
| Windows panel internals (services, IIS bindings) have no whitelisted reading | Windows conclusions past the volume/directory layer are explicitly marked low confidence |

## Module Index

| Module | File | Responsibility |
| --- | --- | --- |
| M1: RAM policies | [references/ram-policies.md](references/ram-policies.md) | actions, consent classes, minimal statements, denial handling |
| M2: Access triage | [references/bt-panel-diagnosis__bt-access-triage.md](references/bt-panel-diagnosis__bt-access-triage.md) | the five layers, verdict rules, degradation policy |
| M3: Read-only evidence | [references/bt-panel-diagnosis__bt-readonly-evidence.md](references/bt-panel-diagnosis__bt-readonly-evidence.md) | the probe whitelist vs case evidence, refused-command catalog, consent mechanics |
| M4: Site config guide | [references/bt-panel-diagnosis__bt-site-config-guide.md](references/bt-panel-diagnosis__bt-site-config-guide.md) | entry recovery, SSL paths, 5xx guidance, Windows panel, official docs |
| M5: Hand-off boundaries | [references/bt-panel-diagnosis__handoff-boundaries.md](references/bt-panel-diagnosis__handoff-boundaries.md) | adjacent areas, routing wording, responsibility line |

## Examples

**Example 1 — "panel won't open, browser says ERR_CONNECTION_RESET"**

> User: "My BT panel page at 203.0.113.7:8888 stopped opening yesterday,
> the browser says this site can't be reached. Region cn-hangzhou."

```bash
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py triage --region-id cn-hangzhou \
  --public-ip 203.0.113.7 --panel-url "http://203.0.113.7:8888" \
  --used-port 8888 --error-text "site can't be reached, ERR_CONNECTION_RESET"
```

The sweep locates the instance and its groups, then layer 2 stays
no-evidence: the report asks for the `bt default` reading. When the customer
pastes "address: http://203.0.113.7:39575/abcdef" back, re-running with
`--actual-port 39575` lands the verdict — and the layer-1 guidance checks
the group against 39575, not 8888 (the exact trap case T-38543E1F fell into).

**Example 2 — Apache dead because a certificate path is wrong**

> User: "Apache on my BT panel server won't start: it says
> /www/server/panel/vhost/cert/example.com/fullchain.pem does not exist,
> but I uploaded the certificate. i-bp1cert..."

```bash
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py triage --region-id cn-hangzhou \
  --instance-id i-bp1cert --error-text "certificate file does not exist" \
  --domain example.com
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py probe --region-id cn-hangzhou \
  --instance-id i-bp1cert --command ls_dir --target /www/server/panel/vhost/cert
```

The first run returns the probe as `NEXT_ACTION`; the second prints the
disclosure, and after the customer confirms, the consented re-run lists what
is really there — in case T-76855857 the listing revealed the files sat one
directory level off (the missing `www` segment). The report states path vs
reality; placing the files correctly is the customer's manual step, then this
skill re-lists read-only to verify.

**Example 3 — the agent is offline, so nothing inside runs**

> User: "Panel and sites both down since tonight's restart storm,
> instance i-bp1dead, cn-shanghai."

```bash
python3 scripts/areas/bt_panel_diagnosis/bt_panel_diagnosis.py triage --region-id cn-shanghai \
  --instance-id i-bp1dead --error-text "panel and sites down after restarts"
```

With the agent offline the file layer degrades: `STATUS: DEGRADED`, cloud
evidence kept, the customer gets the exact read-only commands for a
Workbench session, and a repeated-fatal-symptom line routes to the instance
health area. No dispatch is attempted against a downed agent.

## Exit codes

- `0` — a conclusion was produced: `STATUS: OK` or `STATUS: DEGRADED`
  (missing pieces recorded as `[WARN]` plus findings).
- `1` — no usable conclusion: `STATUS: FAIL` (missing input, every query
  failed). Never treat exit `1` as a diagnosis.
- `2` — argparse usage error.

## Important Notes

- **The port is a reading, never a default**: 8888 appears in tickets
  because installation uses it; real panels run on 39575, 51973, 19356... The
  first hard fact comes from the customer's `bt default` / `bt 14` echo, and
  every security-group verdict is computed against it.
- **Credentials stay out of the loop**: the skill reads files and
  reachability, not passwords; `bt default` output is reported as the
  address line only, and all pasted bodies pass masking.
- **Read-only is the ceiling of execution, not of help**: every fix exists
  as a manual step with the snapshot-first reminder (the customer creates
  snapshots in the console); this skill's last act on any fix is a read-only
  verification run.

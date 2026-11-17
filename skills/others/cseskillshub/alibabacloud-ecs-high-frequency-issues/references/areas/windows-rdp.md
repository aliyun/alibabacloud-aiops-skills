---
name: alibabacloud-ecs-high-frequency-issues
area: windows-rdp
description: |
  Query-only plus guided diagnosis for Windows Remote Desktop (RDP) on Alibaba Cloud ECS: it layers client evidence, the cloud-side connection surface, and a confirmation-gated non-mutating in-guest query into an evidence-based root cause; it changes no resource.
  Use when a Windows instance cannot be reached over Remote Desktop, the desktop is black or frozen, or an authentication error appears.
  Triggers: "remote desktop won't connect", "mstsc cannot connect", "RDP 3389 refused", "remote desktop black screen", "account locked 0xd07", "mstsc error 0x204", "CredSSP function requested is not supported", "NLA authentication error".
  Do NOT use for Linux SSH, disk-capacity/OOM, instance state (area:instance-state-diagnosis), disk expand/IO, generic health (alibabacloud-ecs-diagnose), or to apply any change (unlock, open port, reset password, restart).
---

# Windows Remote Desktop (RDP) Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

A customer-facing, evidence-first diagnosis skill for the three Windows RDP
symptom areas on Alibaba Cloud **ECS**: cannot connect, black screen / freeze /
resolution oddities, and authentication / certificate / NLA errors. The
customer reports a symptom and an error string, never a root cause; this skill
matches the symptom, walks a fixed layer order, and returns a report whose every
claim is backed by a real value the cloud or a confirmed guest query returned.

The customer states symptoms such as "remote desktop won't connect", "it locks
me out with 0xd07", "the screen goes black", "for security reasons the remote
computer cannot be authenticated". Route on those words and the quoted error,
then let the script's decision tree find the cause.

## What this skill is (permission model: RO+G)

This is a **diagnosis and guidance** skill, not a repair skill. Its scope is:

1. **Cloud query reads** that run automatically — instance state, OS family,
   region, public IP, the security-group ingress for the RDP port, and Cloud
   Assistant readiness.
2. **A confirmation-gated, non-mutating in-guest query**: when a fact only
   exists inside the guest (the real listener port, the internal firewall, the
   local account, the session list, the TerminalServices log), the skill can
   fetch it through Cloud Assistant — one whitelisted query command at a time,
   and only after the operator confirms that exact command.
3. **Manual guidance** for every repair.

It performs **no configuration or data change** to any cloud or guest resource.
The only state-affecting API it can touch is the Cloud Assistant command
dispatch (product `ecs`, action `RunCommand`), and its payload is always one of
the query commands listed in
[references/windows-rdp__guest-query-commands.md](references/windows-rdp__guest-query-commands.md) —
never a change. Support tickets usually close with a write (unlock, open the
port, restart, reset the password); this skill stops at the layered finding and
the operator step.

## ABSOLUTE PROHIBITION

Under no circumstances may this skill generate, run, or hand over as a runnable
command any action that changes state — on the cloud or inside the guest. That
covers, and is not limited to: unlocking an account, resetting a password,
authorizing or revoking a security-group rule, opening or closing a firewall
port, restarting / stopping / starting an instance, changing the instance spec
or OS image, applying updates, killing a process, editing the registry to move
the RDP port, or building / deleting a snapshot. When a fix needs one of these,
output **manual guidance only**: what to do, the console entry, the risk, and
the "snapshot first" advisory. The single permitted write-class dispatch is
used exclusively to run a whitelisted query, after confirmation.

## API whitelist (complete; nothing else is called)

| Product | Action | Nature | Purpose |
| --- | --- | --- | --- |
| sts | `GetCallerIdentity` | query | prove the credential chain works, label the account |
| ecs | `DescribeInstances` | query | existence, state, OS (Windows/Linux split), region, public IP, spec |
| ecs | `DescribeSecurityGroupAttribute` | query | ingress allow for the RDP port and its source scope |
| ecs | `DescribeCloudAssistantStatus` | query | gate the guest channel; explains an online reset-password failure |
| ecs | `DescribeInstanceVncUrl` | query | VNC rescue entry for the "console can enter, mstsc cannot" bypass |
| ecs | `DescribeInvocations` | query | read back a dispatched guest query's output |
| ecs | `RunCommand` | **write-class, gated** | deliver ONE whitelisted non-mutating query, only after confirmation |

The machine-readable manifest is in [related_apis.yaml](related_apis.yaml).
`ECS` is an RPC-style product addressed through the `aliyun` CLI; the identity
check uses the plugin-style lowercase subcommand `aliyun sts get-caller-identity`.

## Execution principle (script only)

Run the diagnosis **only** through the entry point
[scripts/areas/windows_rdp/rdp_diagnose.py](scripts/areas/windows_rdp/rdp_diagnose.py). The agent MUST NOT assemble
its own `aliyun` commands, call the OpenAPI directly, or improvise parameters:
every read, the guest dispatch, and every poll go through that script, which
owns pagination, retries, per-call timeouts, credential masking, and the
observability header. Interpret its `Summary`, `STATUS`, and `NEXT_ACTION`; do
not re-run the queries by hand. Knowledge comes from `references/`, never from
model memory.

## Confirmation gate (before any in-guest query)

Because the guest channel runs something inside a customer machine, the operator
must acknowledge it first. The script implements this, not just this document:

* **Tell, then ask.** Before dispatching, it prints the command name, its full
  text, the target instance, and states that it is non-mutating and writes
  nothing.
* **One command, one confirmation.** It dispatches only when the operator
  passes `--confirm confirm:<name>` matching the exact `--guest-check <name>`;
  the acknowledgement does not carry over to another command.
* **Whitelist or refuse.** A name outside the whitelist returns
  `CommandNotWhitelisted` and is never dispatched; out-of-scope fixes become
  manual guidance instead.
* **Degrade honestly.** If Cloud Assistant is not ready or no instance id is
  given, it does not guess — it reports `DEGRADED` and falls back to the
  client-side evidence checklist.

## Observability

Every OpenAPI call, issued through the `aliyun` CLI by the scripts, carries one
User-Agent per run so the whole chain is traceable:

* **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`,
  where `{skill}` is `area:windows-rdp`.
* **session-id**: a 32-character hex string (`uuid.uuid4().hex`), generated once
  per run and attached to every call of that run through `--user-agent`.

The implementation is in [scripts/areas/windows_rdp/_cli.py](scripts/areas/windows_rdp/_cli.py)
(`new_session_id`, `build_user_agent`, `build_command`), with the template in
[scripts/areas/windows_rdp/_constants.py](scripts/areas/windows_rdp/_constants.py). A real header looks like
`AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/3f2c9a1e7b0d4e8fa5c6d1e0b9a8c7d5`.
Transport hardening in the same layer: argument-list `subprocess.run` with no
shell, a per-call timeout, jittered retry on throttling / 5xx / timeout, and
credential masking applied to every error string before it is rendered.

## Prerequisites

1. The `aliyun` CLI on `PATH`, configured on the operator's machine.
2. Python 3.8+; standard library only, so
   [scripts/requirements.txt](scripts/requirements.txt) installs nothing.
3. The RAM actions in [references/ram-policies.md](references/ram-policies.md)
   (query reads; optionally the gated dispatch grant for guest queries).

## Authentication

Credentials are resolved only by the `aliyun` CLI default credential chain (the
profile or platform environment). The scripts never read, accept, store, echo or
pass key material, and never ask the customer for it. To check the chain:

```bash
python3 scripts/areas/windows_rdp/sts_token.py
```

If it fails, the credential chain is not configured: point the operator at
`aliyun sts get-caller-identity`; never request an access key.

## Trigger conditions

Use this skill when the customer's own wording matches one of these (the same
set the `description` advertises), all on the Windows RDP area:

- "Windows remote desktop won't connect"
- "mstsc cannot connect" / "RDP port 3389 refused"
- "remote desktop black screen" / "freezes" / "disconnects randomly"
- "account locked 0xd07"
- "mstsc error 0x204"
- "function requested is not supported" (CredSSP) / "network level authentication" (NLA)
- "SAM or LSA server is in an error state" / "cannot connect to the local security authority"

If the request is really about Linux SSH, disk capacity, instance start/stop, or
a change to apply, do NOT use this skill — route per
[references/windows-rdp__handoff-matrix.md](references/windows-rdp__handoff-matrix.md).

## Input parameters

| Parameter | Required | Notes |
| --- | --- | --- |
| `--region-id` | Yes | Region of the instance; never guessed |
| `--instance-id` **or** `--public-ip` | Yes (one) | instance id also enables the gated guest channel |
| `--port` | No | RDP port the customer dials; defaults to 3389 and is declared when auto-filled; tickets show 33890 / 16909 in use |
| `--security-group-id` | No | Otherwise taken from `DescribeInstances` |
| `--error-string` | No | Quoted mstsc text / code; drives the taxonomy branch |
| `--guest-check` + `--confirm` | No | One whitelisted query, only with the matching confirmation |
| `--vnc` | No | Also fetch the VNC rescue URL |

Ask for a missing required input instead of assuming one; when none can be
resolved the script exits `STATUS: FAIL` naming exactly what is missing.

## Diagnostic flow (fixed order)

1. **Disambiguate** (Layer 0): Windows and ECS? If Linux or a non-ECS product,
   hand off and stop.
2. **Collect evidence** (Layer 1): error text / code, the `ip:port` dialed,
   instance / region, client public IP; mark missing items explicitly.
3. **Cloud side** (Layer 2): instance state, public IP, region / cross-border,
   security-group ingress for the real port and its source.
4. **Channel gate** (Layer 3): Cloud Assistant ready? If not, degrade.
5. **Guest query** (Layer 4): after confirmation, services, listener, firewall,
   account, sessions, TerminalServices log — one command at a time.
6. **Resource watermark** (Layer 5): memory / CPU saturation behind black screens.
7. **Wrap-up** (Layer 6): root-cause branch, evidence chain, repair-owner
   attribution (manual / another skill / cloud-side uncontrollable), risk and
   snapshot advisory.

The full reasoning is in [references/windows-rdp__rdp-layered-checklist.md](references/windows-rdp__rdp-layered-checklist.md).

## Report contract

The final answer relays the script's own summary and adds no conclusion the data
did not support.

| Field | Meaning |
| --- | --- |
| `STATUS: OK` | Evidence collected; exit code 0 |
| `STATUS: DEGRADED` | Partial evidence; `[WARN]` lines name the gap (Cloud Assistant not ready, guest wedged, a call failed); exit code 0, conclusion usable but caveated |
| `STATUS: FAIL` | No usable conclusion (missing input, or a refused non-whitelisted command); exit code 1 |
| `NEXT_ACTION` | The single next step, always scoped to a query or to manual guidance |

Rules: quote only returned values, render a missing field as `not returned`,
declare every auto-filled parameter (the default port), and state the
confidence where a cause is operator-inferred (NLA / SAM-LSA, domain accounts,
driver / hardware compatibility). For an out-of-scope request, state the
boundary, give the console entry or the hand-off, and do not act.

## Permission failures

A denied read is reported with the literals `NoPermission` or `ImplicitDeny` and
the exact missing action, pointing at the minimal fragment in
[references/ram-policies.md](references/ram-policies.md); it is not retried and
not softened into a generic failure. A credential-chain error is separate and
recovered by `aliyun sts get-caller-identity`.

## Usage

```bash
# cloud-side layered check (query reads only)
python3 scripts/areas/windows_rdp/rdp_diagnose.py --region-id cn-hangzhou \
  --instance-id i-2zeexamplea78f35439f --port 3389 \
  --error-string "An authentication error has occurred. The Local Security Authority"

# locate by public IP; note cross-border if overseas
python3 scripts/areas/windows_rdp/rdp_diagnose.py --region-id ap-southeast-1 --public-ip 8.219.4.5

# disclose one guest query WITHOUT running it (no --confirm)
python3 scripts/areas/windows_rdp/rdp_diagnose.py --region-id cn-hangzhou \
  --instance-id i-2zeexamplea78f35439f --guest-check rdp-listeners

# run that ONE non-mutating query after explicit confirmation
python3 scripts/areas/windows_rdp/rdp_diagnose.py --region-id cn-hangzhou \
  --instance-id i-2zeexamplea78f35439f --guest-check rdp-listeners \
  --confirm confirm:rdp-listeners
```

## Module index

| Module | File | Responsibility |
| --- | --- | --- |
| Layered checklist | [references/windows-rdp__rdp-layered-checklist.md](references/windows-rdp__rdp-layered-checklist.md) | Fixed layer order and each layer's pass/fail reading |
| Error taxonomy | [references/windows-rdp__error-code-taxonomy.md](references/windows-rdp__error-code-taxonomy.md) | mstsc text / code to branch and confidence |
| Guest query commands | [references/windows-rdp__guest-query-commands.md](references/windows-rdp__guest-query-commands.md) | Whitelist, confirmation gate, refusal rules |
| Security group & port | [references/windows-rdp__security-group-and-port.md](references/windows-rdp__security-group-and-port.md) | Cloud-vs-guest allow path, custom ports, narrowing the source |
| Account lockout | [references/windows-rdp__account-lockout-and-hardening.md](references/windows-rdp__account-lockout-and-hardening.md) | Lockout recognition, rescue, hardening |
| VNC & channel choice | [references/windows-rdp__vnc-rescue-and-channel-choice.md](references/windows-rdp__vnc-rescue-and-channel-choice.md) | RDP / Workbench / Session Manager / VNC and the bypass check |
| Black screen | [references/windows-rdp__black-screen-resource-exhaustion.md](references/windows-rdp__black-screen-resource-exhaustion.md) | Memory/CPU saturation branch and the wedged-host degrade |
| Cross-border | [references/windows-rdp__cross-border-network.md](references/windows-rdp__cross-border-network.md) | Mainland-to-overseas public path limits and mitigations |
| Hand-off matrix | [references/windows-rdp__handoff-matrix.md](references/windows-rdp__handoff-matrix.md) | Recognize other areas and route out; never implement them |
| RAM policies | [references/ram-policies.md](references/ram-policies.md) | Exact actions, no wildcard, denial recovery |

## Important notes

* **Non-mutating by design.** No config or data change is applied anywhere; the
  gated dispatch runs query payloads only.
* **Cloud cannot see inside the guest**, so a listener / firewall / account /
  session / log conclusion requires the gated query or an operator reading;
  neither is fabricated.
* **`DescribeInvocations` returns past output only** — a current state needs a
  fresh, confirmed dispatch.
* **Confidence, not certainty**, for NLA / SAM-LSA causes and for local-account
  lockout when the host may be domain-joined.
* **No invented identifiers**: only error strings the tickets actually quoted;
  no fabricated ticket ids, URLs, or API parameters.

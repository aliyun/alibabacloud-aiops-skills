---
name: alibabacloud-ecs-high-frequency-issues
area: login-credential-repair
description: |
  Triage Alibaba Cloud ECS logon credential failures via inspection APIs (instance facts, agent state, key pairs, invocation history); outputs an evidence report plus manual repair steps; never requests, echoes or stores passwords.
  Use when the logon prompt appears but the credential is refused: reset not effective, forgotten password, account locked after repeated wrong passwords, Windows administrator logon failure.
  Triggers: reset password still cannot log in; forgot ECS password; reset did not take effect; account locked for security reasons; too many failed logon attempts; administrator locked or disabled; key pair has been removed; login as user 'cloud-user' rather than 'root'.
  Do NOT use: unreachable port or timeout (network/instance-state skills), brute-force intrusion response, Linux root/sudo limits in a working session (alibabacloud-ecs-linux-os-troubleshooting), app panel passwords, disk-full expansion.
---

# Alibaba Cloud ECS Instance Logon Credential Repair (Password / Account Lockout)

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

This skill triages and guides the repair of ECS instance logon credential
failures: a password that was reset but did not take effect, a forgotten
password, an account locked or disabled after repeated wrong passwords, a
wrong logon username, key-pair interference, and Windows administrator logon
anomalies. It collects cloud-side facts with six inspection actions, routes
them through an embedded decision tree (branches LC1-LC9), and prints an
evidence report in which every repair step is a manual action performed by
the customer or a human engineer behind the gates declared below.

The automated surface is non-mutating by design and by code: a runtime
whitelist inside `scripts/areas/login_credential_repair/_cli.py` rejects every action outside the six
inspection reads before a process is spawned. The tier this skill serves also
contains write operations (password reset, account unlock, snapshots); they
are enumerated under "Permission model" and remain manual.

## Scope and boundary

In scope - the vertical logon-credential area only:

1. Password reset (online or offline) that did not take effect, or a reset
   that reports success while the new password still fails.
2. Forgotten password / "where do I see my password" (a password can never be
   viewed, only reset). **Hard boundary:** a request to retrieve, reveal or
   echo the existing password is not diagnosable and is not accepted as a
   target. State that no Alibaba Cloud product can return a stored password,
   refuse to request or print one, and hand the customer to the console
   password-reset flow (the reset playbook) — that flow, not this diagnostic,
   is where the credential is changed. A customer who pasted a password must
   be told to change it immediately.
3. Account locked or disabled after repeated failed logon attempts
   (Windows lockout policy, Linux account state).
4. Wrong logon username for the image (root vs ecs-user vs cloud-user;
   Windows administrator anomalies).
5. Key-pair interference with password logon, including "key pair has been
   removed" reports.

Boundary decision (always run first, before any credential work):

- The port answers and the logon prompt/screen appears, but the credential is
  refused -> THIS skill.
- The port does not answer, the connection times out, or the instance will
  not start -> network / instance-state area; hand off per
  [references/login-credential-repair__handoff-scripts.md](references/login-credential-repair__handoff-scripts.md).

Boundary vs `alibabacloud-ecs-linux-os-troubleshooting`: that skill covers
general Linux OS faults (boot, kernel, network configuration, services).
This skill stops at "is the credential / account usable"; OS-internal
service, kernel and network-configuration faults are handed off.

## Trigger conditions (and deliberate weakenings)

Trigger on customer wording such as: "I reset the password but still cannot
log in", "forgot my ECS password", "it says the account is locked for
security reasons", "too many failed logon attempts", "the administrator
account is locked / disabled", "the key pair has been removed", "Please login
as the user 'cloud-user' rather than the user 'root'".

Deliberate weakenings (false-hit control, from support evidence):

- The bare word "administrator" triggers this skill ONLY when it co-occurs
  with a logon / lock / password context. Application-install permission or
  UAC prompts ("run as administrator", installer says no permission) are OUT
  of scope.
- "Cannot connect" alone is NOT sufficient: run the boundary decision first;
  a credentials-wrong style message can be a private-IP or wrong-port client
  error, and a black/lagging desktop after logon is a resource area.
- "Password" must concern the ECS instance logon credential. Application
  panel passwords (for example a BaoTa panel) and website backends are out of
  scope: identify and hand off.
- Ransomware / intrusion / tampered-account wording stops this workflow:
  identify, do not remediate, hand off to the security incident process.
- Snapshot billing questions, plans/pricing, DNS changes and website 500
  errors that ride along in the same conversation are answered in one line or
  handed off; they never expand this skill's capability surface.

## Execution Principle (single script entry, no fallback)

All cloud operations MUST go through the bundled scripts. There is exactly
one diagnostic entry point:

| Allowed invocation | Purpose |
|---|---|
| `python3 scripts/areas/login_credential_repair/login_credential_diagnose.py` | The single triage entry (argparse); collects evidence, derives branches, prints the report with `STATUS` / `NEXT_ACTION` |
| `python3 scripts/areas/login_credential_repair/login_credential_diagnose.py --check-auth-only` | Credential-chain pre-check via `aliyun sts get-caller-identity` |

Support modules (imported by the entry, not separate workflows):
`scripts/areas/login_credential_repair/_cli.py` (transport, whitelist, UA, retry, masking, timeouts),
`scripts/areas/login_credential_repair/_constants.py` (all reference data embedded as constants),
`scripts/areas/login_credential_repair/sts_token.py` (caller identity + account traceability label).

PROHIBITED - structural violations even if the output looks correct:

- Hand-building `aliyun ecs ...` commands or any other CLI invocation for
  diagnosis; the entry script is the only dispatcher.
- Writing ad-hoc helper scripts, inline SDK/HTTP code, or "one more query"
  side files.
- Falling back to guesses when a script fails: report the failure, the
  `STATUS`, and the `NEXT_ACTION` instead.

## Permission model and safety gates

### Automated surface (inspection reads; no per-call confirmation needed)

`sts:GetCallerIdentity`, `ecs:DescribeInstances`,
`ecs:DescribeInstanceAttribute`, `ecs:DescribeKeyPairs`,
`ecs:DescribeCloudAssistantStatus`, `ecs:DescribeInvocations`.
Full details: [references/ram-policies.md](references/ram-policies.md) and
[references/login-credential-repair__api-reference.md](references/login-credential-repair__api-reference.md).

### Write actions in this tier - NEVER dispatched by this skill

This skill is deliberately not labeled with any restrictive read badge; per
its confirmed requirement document it enumerates the write actions of the
tier explicitly, each with its gate. The scripts never call them; the runtime
whitelist makes calling them impossible from the automated path.

| Write action | Role in the tier | Gate |
|---|---|---|
| `ModifyInstanceAttribute` (Password field) | Console online/offline instance password reset | Default: guidance only (console path + online/offline difference + restart impact). Never executed on the customer's behalf by this skill. |
| `CreateSnapshot` | Snapshot-first gate before any state change | Performed by the customer in the console after cost disclosure; must cover the SYSTEM disk. |
| `RunCommand` | Cloud Assistant console flows quoted in the playbooks | Not used by this skill while the credential-area in-guest command whitelist is unapproved; the customer runs guided commands in VNC/Workbench instead. |
| `StartInstance` / `StopInstance` / `RebootInstance` | Offline reset needs one restart | Customer-agreed business window; manual console step. |
| Security-group rule edits (3389/22 sources) | Lockout hardening | Manual console step; this skill neither reads nor edits rules. |

### ABSOLUTE PROHIBITION

The agent and the scripts MUST NEVER generate, dispatch, or execute any
mutating cloud API (`Modify*`, `Create*`, `Delete*`, `Release*`, `Reset*`,
`Replace*`, `Attach*`, `Detach*`, `Reboot*`, `Start*`, `Stop*`, `RunCommand`)
and MUST NEVER run destructive guest commands. Mutating and destructive
operations appear only as written guidance for a human, with the risk
statement attached.

### Mandatory gates (apply to every guided state change)

1. Tell-and-confirm: before any guided action that changes state, say in one
   sentence what will run, its blast radius, whether it is reversible, and
   whether it costs money; obtain an explicit yes that covers that single
   step only. A confirmation never carries over to the next step.
2. Snapshot first: before ANY state-changing step (password write, unlock
   policy change, guest configuration edit, restart for an offline reset) the
   customer creates a manual snapshot that covers the SYSTEM disk. Snapshots
   are billable; say so, with the billing doc from
   [references/login-credential-repair__help-docs.md](references/login-credential-repair__help-docs.md). Pure inspection
   diagnosis needs no snapshot.
3. Command rejection: refuse to automate any command string containing
   side-effect tokens or write semantics - `rm`, `mv`, output redirection,
   `truncate`, `dd`, `kill`, `systemctl`, `reboot`, registry writes,
   `net user <name> <newpassword>`, `net user <name> /active:yes`,
   `net accounts /lockoutthreshold:0`, `passwd`, `usermod`,
   `faillock --user <user> --reset`, `bt 5`. Such steps are printed as
   human-executed guidance with the risk statement, never dispatched.
4. Sensitive credentials (front-loaded, not a closing remark): this skill
   never asks for a password, never echoes one, never stores one, and never
   transmits one. If the customer already pasted a plaintext password into
   the conversation, tell them IMMEDIATELY to change that password once the
   instance is reachable again, and use the masked/confidential channel for
   anything unavoidable. The scripts additionally mask secret-shaped tokens
   in customer-supplied text before printing.
5. No hardcoded credentials: AK/SK material comes exclusively from the local
   CLI default credential chain. The scripts accept no key parameters. On
   credential failure, point the operator to `aliyun sts get-caller-identity`; never ask
   anyone to paste keys.

## Input parameters

| Parameter | Flag | Required | Notes |
|---|---|---|---|
| region_id | `--region-id` | Yes for a scoped run | Never guessed; a wrong region is the top customer stumbling block, so echo it back for confirmation |
| instance_id | `--instance-id` | No | Without it the run lists instances in the region so the customer can pick one |
| intent | `--intent` | No | `auto` / `consult` / `reset-not-effective` / `locked` / `forgot-password` / `administrator`; auto infers from the error string |
| error_text | `--error-string` | No | Verbatim customer/console wording. Secret-shaped tokens are masked. NEVER put a password in this field |
| login_user | `--login-user` | No | The username typed at the prompt (root, ecs-user, cloud-user, administrator). A bare username only; anything else is rejected |
| key_pair_name | `--key-pair-name` | No | Verified against the region when the customer mentions one; otherwise derived from the instance binding |
| output | `--output` | No | `text` (default) or `json` |
| timeout / paging | `--timeout`, `--max-pages` | No | Per-call timeout default 30 s; paging ceiling default 10 pages |

Conversation-level defaults tracked by the agent (not script flags):
in-guest reading authorization defaults to OFF, so guest facts are collected
as customer-executed reads per
[references/login-credential-repair__guest-credential-checks.md](references/login-credential-repair__guest-credential-checks.md);
"snapshot already created" defaults to NO, so every write-guidance block
starts with the snapshot step.

Mandatory-parameter gate: if `region_id` is missing for a scoped run, ask the
customer once; if it is still not provided, run the region listing path or
abort with `STATUS: FAIL` and the missing-parameter `NEXT_ACTION`. Never
fabricate an instance id, region, or any API value.

## Workflow

1. Identity and scope: run `python3 scripts/areas/login_credential_repair/login_credential_diagnose.py
   --check-auth-only` once per session; then the scoped run, e.g.
   `python3 scripts/areas/login_credential_repair/login_credential_diagnose.py --region-id cn-hangzhou
   --instance-id i-bp1example --intent locked --error-string "<verbatim
   wording>"`. The script collects OS family, instance status, public/private
   addresses, key-pair binding, agent state and invocation history.
2. Boundary decision: confirm from the report that the instance is reachable
   enough to show a logon prompt. Port-dead / won't-start evidence routes to
   [references/login-credential-repair__handoff-scripts.md](references/login-credential-repair__handoff-scripts.md) instead of
   credential work.
3. Error-string normalization: the verbatim customer wording goes through the
   embedded dictionary and lands on branches LC1-LC9 (see
   [references/login-credential-repair__login-credential-decision-tree.md](references/login-credential-repair__login-credential-decision-tree.md)).
   No dictionary hit -> the VNC tie-breaker test: the same credential inside a
   console VNC session decides between a client-path problem and a real
   credential problem.
4. Branch handling: follow the branch playbook - lockout branches LC5/LC6 use
   [references/login-credential-repair__windows-lockout-playbook.md](references/login-credential-repair__windows-lockout-playbook.md);
   reset branches LC3/LC7/LC8 use
   [references/login-credential-repair__password-reset-playbook.md](references/login-credential-repair__password-reset-playbook.md);
   guest facts come from the customer-executed reads in
   [references/login-credential-repair__guest-credential-checks.md](references/login-credential-repair__guest-credential-checks.md).
   Every suggested state change carries its gate (tell-and-confirm, snapshot
   first, human-executed).
5. Out-of-scope identification: disk-full resets, instance-state faults,
   resource exhaustion, security-group/network problems, intrusion signs,
   application-panel credentials and commercial questions are identified and
   handed off with the scripts in
   [references/login-credential-repair__handoff-scripts.md](references/login-credential-repair__handoff-scripts.md) - never
   remediated here.
6. Report closure: relay the script report faithfully - findings with
   confidence labels, the manual to-do list for the customer, hardening
   advice, and the final `STATUS` / `NEXT_ACTION` contract lines.

## Observability and User-Agent

- Every single CLI invocation carries
  `--user-agent AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`; for this
  skill the template resolves to
  `AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/{session-id} skill-version/<skill-version>`.
- The session-id is a 32-character hex string (`uuid4().hex`), generated once
  per run in `scripts/areas/login_credential_repair/_cli.py` (`new_session_id`) and printed in the report
  header so any ticket reviewer can trace one run end to end.
- Per-call timeout: every subprocess call passes `timeout=` explicitly
  (default 30 s, adjustable with `--timeout`).
- Transient failures (throttling, 5xx, timeouts) are retried with capped
  exponential backoff; non-transient failures raise immediately as
  `Code: Message`. Degradation is printed as `[WARN]` on stderr and the run
  continues with the remaining evidence.
- All error text passes credential masking (AccessKeyId / SecurityToken /
  Signature / password-shaped values become `***`) before it can be printed.

## Output contract

- The report ends with `STATUS: OK | DEGRADED | FAIL` and one `NEXT_ACTION`
  line. Relay both faithfully; only quote values the APIs actually returned;
  declare every auto-filled parameter (region, account label).
- Findings carry confidence labels: `CONFIRMED` (an API field proves it),
  `REPORTED` (customer wording, unverified), `HYPOTHESIS` (mechanism not
  measured). Ticket-era assertions such as "security software intercepted the
  reset" or "the server is under brute-force attack" MUST stay hypotheses
  with a confidence level and MUST NOT be printed as causes.
- `DEGRADED` semantics: agent state unknown, a denied or failed inspection
  call, or truncated paging produces `STATUS: DEGRADED`, names the missing
  item, and falls back to the customer-executed path (run the same reading in
  VNC/Workbench and paste the output back). The skill never silently
  downgrades to a guessed conclusion.
- Permission denials are reported with the literal code `NoPermission` or
  `ImplicitDeny`, the exact missing action, and the minimal policy fragment
  from [references/ram-policies.md](references/ram-policies.md).

## References

| File | Contents |
|---|---|
| [references/login-credential-repair__login-credential-decision-tree.md](references/login-credential-repair__login-credential-decision-tree.md) | Branches LC1-LC9, phrase-to-branch dictionary, six-step flow, open points |
| [references/login-credential-repair__windows-lockout-playbook.md](references/login-credential-repair__windows-lockout-playbook.md) | Lockout mechanism, zero-write unlock paths, policy-write guidance with risk statements, hardening |
| [references/login-credential-repair__password-reset-playbook.md](references/login-credential-repair__password-reset-playbook.md) | Online vs offline reset decision, restart impact, snapshot-first, post-reset checklist |
| [references/login-credential-repair__guest-credential-checks.md](references/login-credential-repair__guest-credential-checks.md) | Customer-executed in-guest readings, rules, refused write commands |
| [references/login-credential-repair__handoff-scripts.md](references/login-credential-repair__handoff-scripts.md) | Out-of-scope areas and the exact handoff wording |
| [references/login-credential-repair__help-docs.md](references/login-credential-repair__help-docs.md) | Verified help-center links, unverified-title TODO list, excluded links |
| [references/login-credential-repair__api-reference.md](references/login-credential-repair__api-reference.md) | Per-API parameters actually used, OS-to-command-type mapping, pending API-info items |
| [references/ram-policies.md](references/ram-policies.md) | Exact RAM actions, minimal policy fragment, denial handling |

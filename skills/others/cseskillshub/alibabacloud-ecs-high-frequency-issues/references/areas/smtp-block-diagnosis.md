---
name: alibabacloud-ecs-high-frequency-issues
area: smtp-block-diagnosis
description: |
  Diagnose why an Alibaba Cloud ECS instance cannot send or receive email over SMTP: attribute the failure to the platform outbound TCP 25 block, security group egress, guest firewall or listener state, unblock-application eligibility, or peer mail-server rejection, then give an evidence-backed layer verdict with manual guidance (465/587 relay, unblock entry, handoffs). In-guest facts come from the customer's own readings or, on approval, one fixed inspection-only command run via Cloud Assistant.
  Use when ECS mail sending or receiving fails or a port-25 unblock application is rejected. Triggers: "port 25 blocked", "apply to unblock port 25 on ECS", "SMTP send timeout on port 25", "465 587 email port not working", "550 Bad HELO", "cannot receive email on port 25".
  Do NOT use for non-mail reachability, SSH or RDP access, cross-border link quality, mail-product setup (Alibaba Mail / DirectMail), or RAM grants.
---

# ECS SMTP Block Diagnosis (mail ports / port-25 unblock)

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Layer attribution for customers whose ECS instance cannot send or receive
mail: platform outbound TCP-25 policy, security-group egress/ingress,
in-guest firewall or listener state, port-25 unblock-application
eligibility, and peer mail-server application-layer rejection. Evidence
comes from non-mutating cloud queries, the customer's own readings, and --
only after the user approves that one command -- a fixed inspection-only
command dispatched into the guest (see 'Guest Evidence Gate'). The output is
an evidence-backed verdict per layer plus MANUAL remediation: relay options
on 465/587, the unblock application path and its honest eligibility
pre-check, and named handoffs for out-of-scope signals. Every configuration
change stays with the customer.

## Absolute Rules

1. **CRITICAL — MANDATORY EXECUTION:** every diagnosis runs through the
   bundled entry script. You MUST run `scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py`
   (after `scripts/areas/smtp_block_diagnosis/sts_token.py` when the caller identity is unknown). You
   are STRICTLY PROHIBITED from assembling raw `aliyun` CLI commands,
   hand-writing SDK/HTTP calls, or re-implementing the queries — the
   scripts embed the timeout, retry, error-degradation and observability
   guarantees ad-hoc calls lack. If a script fails, report its error; DO
   NOT work around it.
2. **API WHITELIST (exhaustive, machine-enforced):** the only permitted
   OpenAPI actions are the reads `ecs DescribeInstances`, `ecs
   DescribeInstanceStatus`, `ecs DescribeInvocations` and `sts
   GetCallerIdentity`, plus exactly ONE write-property action, `ecs
   RunCommand`, used solely to dispatch one fixed inspection-only template
   from `GUEST_PROBES` in `scripts/areas/smtp_block_diagnosis/_constants.py` behind the Guest Evidence
   Gate below. `scripts/areas/smtp_block_diagnosis/_cli.py` refuses every other `(product, action)`
   pair before a subprocess is built. **ABSOLUTE PROHIBITION:** under NO
   circumstance generate, write, or execute any other mutating call
   (`Create*`, `Delete*`, `Modify*`, `Update*`, `Attach*`, `Detach*`,
   `Reboot*`, `Start*`, `Stop*`, `Reset*`, `Release*`, `Replace*`, `Add*`,
   `Remove*`) or any other Cloud Assistant action (`InvokeCommand`,
   `SendFile`, `CreateCommand`, `StartTerminalSession`, `StopInvocation`,
   `DeleteCommand`) — a stored command id cannot be audited, so it is never
   run. Security groups, firewalls, IPs and application forms are changed or
   submitted by the CUSTOMER, manually.
3. **GUEST EVIDENCE GATE (mandatory before any in-guest command):** the
   skill may dispatch inspection-only commands into the guest, but only
   through the entry script's `--execute-probe` path, and only for ONE
   whitelisted template per run. Before dispatching, show the user all four
   parts and wait for a clear yes: (1) **which command** — the probe title
   plus its exact script text, printed in full; (2) **scope** — this one
   instance, this one command, inspection only; (3) **reversibility** — the
   probe's `reversible` line (no configuration, file, service, firewall or
   route is touched, so there is nothing to undo); (4) **duration** — the
   Cloud Assistant `Timeout` plus the per-port connect guard. Only after
   approval re-run with `--user-confirmation
   I-APPROVE-INSPECTION-ONLY-COMMAND`; the token is valid for that one
   command, so each new probe needs a fresh disclosure. Without the token
   the script dispatches nothing and prints the disclosure instead. Free
   text never becomes a command: the script accepts a probe ID, and
   re-validates host, ports, prohibited verbs and redirect targets after
   substitution. Windows guests and any question the templates cannot
   answer stay on the manual readings checklist (the customer runs them in
   their own session). Requests to open a port, restart a service, edit a
   rule or submit an application are refused outright and answered with
   manual steps plus a risk note.
4. **ABSOLUTE PROHIBITION (credentials):** never read, print, or pass
   AccessKey IDs, secrets or tokens explicitly. The scripts accept no
   credential parameters; authentication comes from the aliyun CLI default
   credential chain only.
5. **NO FABRICATION:** every conclusion must trace to script output (cloud
   queries, matched error signatures, supplied readings, dispatched probe
   output) or the embedded ticket-evidence knowledge in
   `scripts/areas/smtp_block_diagnosis/_constants.py` / `references/`.
   Policy statements marked `UNCONFIRMED` there (inbound-25 behavior,
   overseas-region behavior) MUST be relayed as "verify before promising",
   never as settled fact. Empty or failed queries are reported as
   limitations.
6. **SCOPE BOUNDARY:** mail ports (25/465/587/993/995) semantics only.
   Non-mail ports, general public-network reachability, cross-border link
   quality, content-violation blocks, mail-product configuration, RAM
   grants and commercial requests are recognized, given a one-line verdict,
   and routed per [references/smtp-block-diagnosis__handoff-boundaries.md](references/smtp-block-diagnosis__handoff-boundaries.md)
   — no diagnosis of another skill's symptom.

## Execution Principle (script-only, no fallback)

| Allowed invocation | Purpose |
|--------------------|---------|
| `python3 scripts/areas/smtp_block_diagnosis/sts_token.py` | Caller identity / account label / sub-account permission-gap signal |
| `python3 scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py` | Full diagnosis (cloud evidence + attribution + guidance); optional `--execute-probe` + `--user-confirmation` for one gated inspection-only guest command |

If either exits non-zero or emits `STATUS: FAIL`, stop and report the
error text — never fall back to raw CLI calls or manual API guessing.

## Credentials

All authentication is resolved by the aliyun CLI default credential chain
(environment or the CLI config file). Nothing else is supported: the
scripts never take `--access-key-id` or `--access-key-secret` style
arguments and never echo credential material; error text is masked before
it can reach a report. If `sts_token.py` (or the identity step inside the
entry script) fails, the credential chain is not configured — guide the
user to `aliyun sts get-caller-identity` and stop.

## User Confirmation (required before any API call or command)

This skill changes no cloud configuration, but three gates are mandatory:

1. **Scope gate (before the first script run):** restate to the user —
   the target (instance id or public IP), the region, the symptom area
   (send / receive / apply), and that cloud access is limited to
   non-mutating Describe/Get queries plus, if the user later approves it,
   one inspection-only command inside that single instance. An explicit
   request that already names the target and region is sufficient
   authorization for the reads: restate and proceed. If the target or
   region is ambiguous, ASK and WAIT — no API call before that.
2. **Guest evidence gate (before ANY in-guest command):** the
   four-part disclosure in Absolute Rule 3, then an explicit yes for
   THAT command. Never bundle two probes into one approval, never reuse
   an approval across commands, and never present the disclosure after
   the dispatch. If the user declines, or the Cloud Assistant agent is
   offline or the guest is Windows, say so and fall back to the manual
   readings checklist.
3. **Guidance gate (before proposing customer-run commands):** state what
   each command inspects, that it changes no state, that the CUSTOMER runs
   it in their own session, and what will be done with the pasted output.
   Proceed only on the user's confirmation.

## Trigger Conditions

Mirror of the `description` phrase list (match the customer's own wording,
never product vocabulary):

- "port 25 blocked"
- "apply to unblock port 25 on ECS"
- "SMTP send timeout on port 25"
- "465 587 email port not working"
- "550 Bad HELO"
- "cannot receive email on port 25"

## Input Parameters

| Parameter | Flag | Required | Notes |
|-----------|------|----------|-------|
| Region | `--region-id` | Yes | e.g. `cn-hangzhou`; never guessed |
| Instance id OR public IP | `--instance-id` / `--public-ip-address` | Yes (exactly one) | IPv4 lookup tries fixed-public-IP then EIP filters |
| Symptom area | `--direction` | No | `send` (default) / `receive` / `apply`; default use is declared in the report |
| Mail target host / port | `--target-host`, `--target-port` | No | e.g. `smtp.qq.com` / `465`; IPv6-literal targets trigger the IPv6 policy note |
| Port test results | `--port-result PORT=STATE` (repeatable) | No | states: `timeout`, `refused`, `connected`, `connected-closed`, `banner-error` — from the customer's own test output |
| Error text | `--error-text` | No | customer-visible SMTP/console error, matched against the embedded signatures |
| Listener / container facts | `--listener-25`, `--container-mapped` | No | `yes/no/unknown` from the customer's `ss`/`docker ps` reading |
| Gated in-guest probe | `--execute-probe` | No | one of `port-probe`, `listener`, `firewall`, `path-info`; one probe per run, no default |
| Probe approval | `--user-confirmation` | Only to dispatch | must equal `I-APPROVE-INSPECTION-ONLY-COMMAND` exactly, and only after the user approved THAT command; never invent it |
| Probe target host / ports | `--probe-host`, `--probe-port` (repeatable) | No | validated hostname/IP + port numbers; `port-probe` defaults to 25, 465, 587, 443 |
| Account UID | `--uid` | No | auto-filled via `sts:GetCallerIdentity` and DECLARED; never asked for first |
| CLI profile / JSON mode | `--profile`, `--json` | No | |

Without `--execute-probe` the whole run is non-mutating: reads only, with
in-guest facts supplied by the customer.

**Mandatory-parameter gate:** if region or the identifier is missing after
extracting everything from the prompt, ask ONCE; if still missing, abort —
the script already exits `STATUS: FAIL` with `NEXT_ACTION` naming what is
missing. Do not fabricate or guess mandatory values.

## Module Index

| Module | File |
|--------|------|
| RAM policies (exact actions, no wildcards) | [references/ram-policies.md](references/ram-policies.md) |
| Port/policy evidence matrix (25 out vs in, 465/587, IPv6, PTR, overseas; UNCONFIRMED flags) | [references/smtp-block-diagnosis__port-policy-matrix.md](references/smtp-block-diagnosis__port-policy-matrix.md) |
| SMTP error signature library (layer + handling per verbatim ticket text) | [references/smtp-block-diagnosis__smtp-error-signatures.md](references/smtp-block-diagnosis__smtp-error-signatures.md) |
| Port-25 unblock application: eligibility, entry, materials, honesty rule, alternatives | [references/smtp-block-diagnosis__unblock-application-path.md](references/smtp-block-diagnosis__unblock-application-path.md) |
| Handoff boundaries (recognize / verdict / route) | [references/smtp-block-diagnosis__handoff-boundaries.md](references/smtp-block-diagnosis__handoff-boundaries.md) |

Load on demand: open only the module the current case needs.

## Orchestration

```
User request (symptom + instance/region)
  | Step 0  scope confirmation (User Confirmation gate 1)
  v
sts_token.py ............ caller identity, UID label, sub-account signal
  v
ecs_smtp_block_diagnosis.py
  |-- DescribeInstances (region, id/IP, status, network type,
  |                     IP form [VPC fixed vs EIP vs classic], SG ids)
  |-- DescribeInstanceStatus (Running cross-check)
  |-- [opt-in] DescribeInvocations (past evidence-command records)
  |
  |-- [opt-in, gated] in-guest inspection:
  |     disclosure (4 parts) -> user approves THIS command
  |     -> RunCommand(one GUEST_PROBES template) -> DescribeInvocations
  |        (IncludeOutput=true) -> derived port states / listener fact
  |     gate closed -> manual readings checklist instead
  v
layer attribution tree over cloud facts + guest readings (either source)
  25 timeout + 465/587/443 ok ........ platform outbound-25 block
  25 AND 465/587 timeout, 443 ok ..... customer config (SG egress / firewall)
  everything timeout ................. broader egress -> network skill
  banner + 550/503/451 reply ......... peer application layer
  IPv6 target / apply-form error ..... eligibility layer (pre-check)
  receive + nothing listening ........ guest listener / mapping
  no readings at all ................. STATUS: DEGRADED + readings list
  v
evidence-cited report + manual guidance + handoffs + STATUS/NEXT_ACTION
```

## Execution Flow

1. **Scope confirmation** — per gate 1 above; nothing runs before it.
2. **Identity** — `python3 scripts/areas/smtp_block_diagnosis/sts_token.py` (or rely on the entry
   script's built-in identity step). Failure = credential/authorization
   problem: abort, point to `references/ram-policies.md`.
3. **Collect what the prompt already gives** — region, instance id or
   public IP, direction, target host/port, any error text, any pasted port
   tests. Never re-ask for what was provided; declare auto-filled defaults
   in the report.
4. **Run the entry script** with those arguments (`--json` when the
   consumer is a program). Relay `STATUS`, verdict layer, reasons (each
   carries its evidence source) and the manual guidance blocks.
5. **Evidence gap (STATUS: DEGRADED):** name the missing fact, then prefer
   the probe that answers it — relay the report's `[2]` disclosure (which
   command, scope, reversibility, duration) and ask. On approval re-run with
   `--execute-probe <id> --user-confirmation <token>`; the derived readings
   feed the same attribution tree, and the report shows the exact command
   and its output. On refusal, an offline Cloud Assistant agent, or a
   Windows guest, present the readings checklist from `[6]` instead (port
   matrix, listener, local firewall) through gate 3 and re-run with
   `--port-result` / `--listener-25` when the customer pastes results. A
   value the customer supplied always wins over a derived one; conflicts are
   logged in the degrade section. `--include-invocations` reconciles past
   Cloud Assistant history without running anything.
6. **Verdict delivery** — follow the Final Answer Contract below: unified
   policy wording (never "all clouds block 25", never "unblock is
   impossible", never promises about review outcomes), eligibility
   pre-check result before any application advice, alternatives once per
   case (465/587 relay; enterprise mail; mail-push) with product
   configuration handed off.
7. **Close** — state limitations honestly (no application-status API, no
   packet capture here, UNCONFIRMED policy rows) and list the executed
   calls: each read query, and any dispatched probe with its probe id and
   `InvokeId`.

## Observability

Every OpenAPI call carries User-Agent
`AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}` where `{skill-name}`
is `area:smtp-block-diagnosis` and `{session-id}` is a
32-character hex string (`uuid.uuid4().hex`) generated once per script run
(honoring `SKILL_SESSION_ID` when exported) and attached to every CLI call
of that run via `--user-agent`, implemented in `scripts/areas/smtp_block_diagnosis/_cli.py`. This
lets the whole query chain of one diagnosis be correlated server-side.

## Error Handling

| Failure | Meaning | Handling |
|---------|---------|----------|
| `NoPermission` / `ImplicitDeny` on a query | RAM policy missing that exact action | name the missing action, relay the policy snippet from `references/ram-policies.md`, continue with what still works, degrade to `STATUS: DEGRADED` |
| Credential chain failure at identity step | CLI not configured | guide them to verify the default credential chain with `aliyun sts get-caller-identity`; never request keys/tokens |
| Instance not found | wrong region/id/IP or IP currently unassociated | `STATUS: FAIL`, `NEXT_ACTION` asks to verify region + identifier; never conclude "blocked" from emptiness |
| `InvalidParameter` / bad flag value | rejected locally by argparse or by the API | echo the validator message; fix and re-run |
| `Throttling.User` / `InternalError` / timeout | transient | already retried with backoff inside `_cli.py`; if persistent, log `[WARN]`, keep the partial report, `STATUS: DEGRADED` |
| `NoPermission` / `ImplicitDeny` on `ecs RunCommand` | the principal has no Cloud Assistant dispatch right | NOT fatal: the probe is reported `dispatch-failed`, the rest of the diagnosis stands, and the same fact is asked of the customer through the manual checklist; name the missing action per `references/ram-policies.md` |
| Probe still running at the end of the bounded read-back window, or guest status other than `Success`/`Finished` | slow or blocked agent, or the command failed inside the guest | relay the partial state and the error text as printed; never widen the window or re-dispatch in a loop — fall back to the manual readings |
| `SkillActionNotAllowed` | something tried an action outside this skill's whitelist | stop and report it; this is a boundary breach, not a failure to work around |

**EXECUTION RULE FOR ERRORS:** a failed query is logged `[WARN]` to stderr
AND recorded in the report's degrade log — never silently skipped, never a
reason to invent the missing fact.

## Important Notes

1. **TCP reachability is not mail acceptance** — the T-8E8AD7A5 evidence:
   `Connected` then `451 Timeout` proves the network leg fine and moves the
   case to the provider/link layer. Never loop back to "port 25 blocked"
   once a banner or SMTP reply exists.
2. **Security-group EGRESS rules are read** (`DescribeSecurityGroupAttribute`,
   one call per attached group) and reduced to the mail ports 25/465/587: the
   report states whether a DROP rule covers them. Only egress/TCP rules that
   touch those ports are evaluated; ingress rules and other ports are out of
   scope. If the read fails, the rule layer is `UNKNOWN` (evidence gap), never
   "not the blocker". The customer still reviews and edits rules in the console
   themselves — this skill never changes one.
3. **Inbound-25 and overseas-region policy rows are UNCONFIRMED** in the
   evidence base; relay the conflict honestly rather than picking a side.
4. **The unblock application is never submitted or tracked here** — no
   public API exists; the customer submits in the console and reads the
   result email.
5. **Honesty rule:** never coach a customer to misdeclare the application
   purpose; the agreement limits port 25 to third-party SMTP relay use, and
   direct-MX self-hosting is refused in review (T-0DC2E989 evidence).
6. **One change, one retest** in customer-config remediation guidance;
   every proposed change carries its risk note; applying changes is the
   customer's own manual action.
7. **Exit codes:** `0` = OK/DEGRADED (usable conclusion), `1` = FAIL (ask
   the named input or fix credentials), `2` = argparse usage error only.

## Examples

**Example 1 — outbound send fails (typical platform block)**
> "My ECS in cn-hangzhou (i-bp1dg6w8xxxxxx) cannot send email; telnet to
> port 25 of the provider just hangs, port 25 blocked?"

Run `python3 scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py --region-id cn-hangzhou
--instance-id i-bp1dg6w8xxxxxx --direction send --target-host
smtp.example.com --port-result 25=timeout --port-result 465=connected
--port-result 443=connected` → verdict `platform-outbound-port25-block`
(high) with the 465/587 relay path, the eligibility pre-check result and
the console application guidance — all manual.

**Example 2 — apply form rejects the IP**
> "I applied to unblock port 25 on ECS from the main account but the
> console says I have no permission to use this IP address."

`--direction apply --error-text "no permission to use this IP address"` →
signature match on the eligibility layer, IP-form pre-check from
`DescribeInstances` tells the customer whether they hold a VPC-mode public
IPv4 to reference (T-384967AE resolution pattern).

**Example 3 — "every email port is dead"**
> "25, 465, 587, 993, 995 all time out from instance i-xxx in cn-shenzhen,
> 443 works; the 465 587 email port not working at all."

`--port-result 25=timeout --port-result 465=timeout --port-result
587=timeout --port-result 993=timeout --port-result 443=connected` →
verdict `customer-config-layer` (platform does not restrict 465/587):
security-group EGRESS review + guest firewall reading, manual steps only —
this is exactly where a "port 25 blocked" answer would have been wrong.

## Final Answer Contract

The answer to the user MUST: (1) lead with the verdict layer and its
reasons, each tagged with its evidence (which query returned what); (2)
relay the script's unified policy wording without edits or promises beyond
it; (3) give the customer's next manual step for the matched branch, and
only that; (4) list executed non-mutating queries, auto-filled parameters as
declared, handoffs taken and not covered; (5) end by restating
`STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION: ...` from the script. When no
verdict is reachable, say so plainly and hand the material list to human
support — never dress a degraded evidence state up as a conclusion.

## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/areas/smtp_block_diagnosis/sts_token.py` | Caller identity via `aliyun sts get-caller-identity`; UID label; sub-account permission-gap hint |
| `scripts/areas/smtp_block_diagnosis/ecs_smtp_block_diagnosis.py` | Single entry: cloud evidence, signature matching, layer attribution, guidance + handoffs, STATUS/NEXT_ACTION contract |
| `scripts/areas/smtp_block_diagnosis/_cli.py` | Shared CLI layer: argument-list calls with per-call timeout, transient retry, credential masking, session-scoped User-Agent |
| `scripts/areas/smtp_block_diagnosis/_constants.py` | Embedded evidence tables (policy statements, signatures, readings, handoff rules) — data lives in code per platform file rules |

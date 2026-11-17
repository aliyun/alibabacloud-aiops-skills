---
name: alibabacloud-ecs-high-frequency-issues
area: ram-policy-diagnosis
description: |
  Diagnose Alibaba Cloud ECS RAM sub-account and permission-policy denials: decode the customer error text, classify the root cause, then output paste-ready policy JSON plus manual main-account grant steps. Covers authorization scope mismatch (account vs resource group), invalid Action/Resource combinations, and missing Workbench or OOS chain actions; cloud queries are non-mutating and the single in-guest check runs only after you confirm.
  Use when a RAM user or AccessKey is denied on ECS. Triggers: "sub-account no permission", "no permission to do the action", "granted AliyunECSFullAccess but still denied", "RAM user cannot see ECS instances", "resource group authorization not working".
  Do NOT use for public-network reachability (alibabacloud-ecs-vpc-publicnetwork-troubleshoot), disk expansion, or instance boot failure.
---

# ECS RAM Sub-Account & Permission-Policy Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Triage RAM identity/authorization denials for Alibaba Cloud ECS. **Two core
capabilities:**

1. **Denial triage** — decode the customer's error text, decide whether it is
   really an authorization problem (in the ticket sample, 9 of 20 were not),
   classify the root cause (scope mismatch / invalid Action+Resource syntax /
   missing cross-product action / role placement / Deny rule), verify what
   the verified cloud queries allow, and emit a four-part answer: verdict,
   paste-ready policy template (evidence-labelled), manual main-account grant
   steps, boundary + handoff lines.
2. **Guided checks with a confirmation gate** — a bounded set of
   non-mutating cloud queries plus, only after the customer confirms, ONE
   whitelisted observation-only command inside the instance (channel health /
   OS-user-vs-RAM-user boundary evidence). The skill never changes RAM,
   policies, roles, instances or guest state.

## Execution Principle (script-only, no fallback) — MANDATORY

All cloud operations MUST go through the bundled scripts. There are exactly
two invocations:

| Allowed invocation | Purpose |
|---|---|
| `python3 scripts/areas/ram_policy_diagnosis/sts_token.py` | Validate the configured credential and report the caller's identity type (runs first) |
| `python3 scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py` | All triage, template, action-lookup and guest-check operations (single entry) |

**Prohibited — do NOT** reproduce diagnosis by any other means (each is a
structural violation even if the output looks correct):

- hand-assembling any `aliyun ecs ...` / `aliyun sts ...` / `aliyun ram ...`
  CLI command for diagnosis or for granting anything;
- writing ad-hoc helper scripts or inline SDK/`curl`/HTTP code;
- calling any action outside the API whitelist below (in particular any RAM
  or BSS action — this skill has none and needs none);
- retrying a failed call through another channel; on script failure stop and
  report the error verbatim.

## Permissions & Boundaries (this skill is NOT a pure query tool — gates apply)

Cloud calls fall in exactly two tiers:

- **Tier 1 — automatic, non-mutating queries** (no per-call confirmation):
  `sts:GetCallerIdentity`, `ecs:DescribeInstances`,
  `ecs:DescribeInvocations`. They read identity/visibility facts only.
- **Tier 2 — confirmation-gated command execution**: the single
  write-attribute action `ecs:run-command` (OpenAPI operation
  `RunCommand`), used ONLY to dispatch ONE
  observation-only diagnostic command taken verbatim from the embedded
  whitelist (`whoami`, `id`, `hostname`, `uptime`, `uname -a`, `date`), and
  ONLY when `--guest-check` mode is explicitly run with `--confirm`. See
  "User Confirmation" below — the gate is mandatory, not advisory.

**ABSOLUTE PROHIBITION (RAM-side and mutation coverage).** Under NO
circumstances may this skill generate, write, or execute anything that:

1. changes RAM state — attach/detach grants, create or edit policies, create
   or delete roles or service-linked roles, disable or delete AccessKeys,
   touch identities of any kind — for ANY account, including "a command for
   the customer to run through this skill". RAM changes are delivered as
   manual main-account console steps only (real ticket staff behaved the
   same: platform policy does not allow operating customer accounts);
2. mutates any cloud resource or the guest OS — cleanup, restart, process
   kill, file removal, service control, disk or security-group edits; such
   requests are answered with the boundary statement and human steps
   (snapshot-before-cleanup guidance where relevant, never executed here);
3. dispatches an in-guest command outside the Tier-2 whitelist. Refuse and
   explain, e.g. a request to "also delete the logs", "run `netstat -ano`",
   or "reboot it" → refuse, hand back manual guidance.

## API Whitelist (the only permitted OpenAPI actions)

| Action (product, version) | Tier | Where |
|---|---|---|
| `sts:GetCallerIdentity` (sts, 2015-04-01) | 1 | `scripts/areas/ram_policy_diagnosis/sts_token.py`, triage |
| `ecs:DescribeInstances` (ecs, 2014-05-26) | 1 | triage visibility step |
| `ecs:DescribeInvocations` (ecs, 2014-05-26) | 1 | guest-check result polling |
| `ecs:run-command` (`RunCommand`, ecs, 2014-05-26) | 2 (gated, whitelist-restricted) | `--guest-check` only |

Anything not in this table is prohibited, including ticket-cited names
(`ecs-workbench:ChatMessages`, OOS actions, BSS names, …): they exist only as
**output text** inside evidence-labelled customer templates — never as calls.

## Credentials (default chain only)

Authentication is resolved exclusively by the aliyun CLI default credential
chain (CLI config or platform-injected environment). The scripts never read,
print, cache, request or pass key material (AccessKey id/secret, token) —
SA-2.12. When credential verification fails, `sts_token.py` exits with
guidance to verify the default credential chain with `aliyun sts get-caller-identity`; never ask the customer to paste keys.
All error output passes credential masking before display.

## User Confirmation (mandatory gate before any Tier-2 dispatch)

Before running `--guest-check` with `--confirm`, the agent MUST:

1. tell the user **what** will run (the exact whitelisted command), **where**
   (instance id + region), **impact** (observation-only; changes nothing;
   recorded as one Cloud Assistant invocation), and **reversibility**
   (nothing to revert);
2. obtain the user's agreement for THIS invocation — one confirmation
   authorizes exactly one dispatch; re-ask for every further command;
3. run the script; on any failure (agent offline, denied, timeout) degrade to
   "please run this whitelisted command inside the instance and paste the
   output" — never substitute another command or another execution channel.

Running `--guest-check` without `--confirm` prints the confirmation brief and
dispatches nothing (safe dry-run; use it to produce the brief).

## Observability

Every OpenAPI call carries `--user-agent` set to the template
`AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`, where `{skill}` is this
skill's name (`area:ram-policy-diagnosis`) and `{session-id}` is
a 32-character lowercase hex string generated once per run
(`uuid.uuid4().hex`) and shared by all calls of that run. Every call of this
skill goes through the aliyun CLI, so this single transport carries the
identifier for all of them.
Set `SKILL_SESSION_ID` once per agent turn to correlate invocations across
script calls; the scripts echo `[_cli] session-id: <id>` for traceability.

## Trigger Conditions (customer wording → action)

- "my sub-account has no permission / 403 but I already granted
  AliyunECSFullAccess" → denial triage (scope x context first)
- "it says *no permission to do the action: (SomeAction)*" → action-gap
  decoding + chain template
- "the RAM user can't see the instances in the console / mobile app" →
  visibility + resource-group context check
- "give my developer an AccessKey that only lists ECS" → least-privilege
  planning (templates) + handoff for unverified billing parts
- "help me set up the OOS auto-restart role / service-linked role removal" →
  role flow guidance (manual only)
- Anti-triggers: "server unreachable / ping fails" →
  `alibabacloud-ecs-vpc-publicnetwork-troubleshoot`; "disk cannot expand" →
  `area:disk-expand-diagnosis`; "instance won't boot" →
  `area:instance-state-diagnosis`; "the status does not support
  this operation" / CORS / site-account confusion → run the triage, it
  outputs the handoff line.

## Input Parameters

| Parameter | Required | Notes |
|---|---|---|
| `--error-text` | yes (primary) | the customer's error **exactly as received** — top pain point in tickets is "the message doesn't say what is missing"; never paraphrase it away |
| `--region-id` | for evidence calls | e.g. `cn-hangzhou`, `us-east-1` |
| `--instance-id` | for visibility check | `i-…` |
| `--resource-group-id` | if known | `rg-…`; drives the scope-match verdict |
| `--ram-user` | if known | `<name>@<account>.onaliyun.com` shape |
| `--api` | if known | e.g. `RunInstances` |
| `--tag-key/--tag-value` | optional | tag-scope visibility probe |
| `--skip-api` | optional | decode-only mode (no credential available) |
| `--profile` | optional | named CLI credential profile |

Ask once for everything missing; do not invent regions, ids or error strings.

## Module Index

- `references/ram-policy-diagnosis__error-signals.md` — signal → branch → ticket evidence
- `references/ram-policy-diagnosis__policy-templates.md` — grammar gates, scope model, paste-able
  policies, grant/role/incident procedures
- `references/ram-policies.md` — this skill's own 4-action permission set
- `references/ram-policy-diagnosis__ticket-patterns.md` — real-ticket resolution patterns + handoff lines
- `references/ram-policy-diagnosis__help-docs.md` — the ONLY citable documentation URLs (and the
  declared gap list)
- `scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py` — single entry (triage / templates /
  action lookup / gated guest check)
- `scripts/areas/ram_policy_diagnosis/sts_token.py`, `scripts/areas/ram_policy_diagnosis/_cli.py`, `scripts/areas/ram_policy_diagnosis/_constants.py` —
  identity helper, shared CLI layer, embedded knowledge tables

## Orchestration

```
customer wording/error
   |  (0) python3 scripts/areas/ram_policy_diagnosis/sts_token.py            <- credential + identity type
   v
(1) python3 scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py --error-text "..." [ids...]
   |     K1 deny-vs-exclusion gate --> not-permission? -> handoff lines (evidence links)
   |     K2 branch: syntax -> scope x context -> chain action -> role/deny
   |     K5 DescribeInstances visibility + actual resource group (when region+id)
   v
(2) four-part answer: verdict / labelled policy template / main-account
   |  manual grant steps / boundary + handoff
   v
(3) optional, only if guest-side boundary evidence is needed:
      --guest-check (brief shown) --> customer agrees --> --confirm
```

## Execution Flow

1. Restate the diagnostic scope (target ids, region, that only the Tier-1
   queries run automatically) and proceed — an explicit diagnosis request
   that names the error/resource is sufficient authorization for Tier 1.
2. Run `scripts/areas/ram_policy_diagnosis/sts_token.py`; confirm the credential works and note the
   identity type (RAM user vs role changes where grants must live).
3. Run `scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py` with the error text and any ids.
   Complete inputs (no placeholders left), so the run is deterministic.
4. If the run reports `ambiguous`/`FAIL`: relay its NEXT_ACTION (collect the
   error text / region / ids). If `DEGRADED`: relay the `[WARN]` lines —
   including the self-demo case where THIS credential is denied: quote the
   script's "missing action + policy snippet" (NoPermission family wording).
5. Deliver the four parts in order; every ticket-cited action name keeps its
   evidence label.
6. Only when OS-user-vs-RAM-user confusion or command-channel health is in
   play: run the confirmation gate (see above), then `--guest-check ... --confirm`,
   and relay the returned output verbatim.
7. End the answer with the script's `STATUS:` and `NEXT_ACTION:` lines.

## Examples

- **Grant-ineffective**: error "403 no permission ... AliyunECSFullAccess is
  already attached", region + `i-...` + `rg-...` known →
  `python3 scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py --error-text "<paste>" --region-id
  cn-hangzhou --instance-id i-... --resource-group-id rg-...` → branch
  `grant-context-mismatch`; the visibility step prints the instance's ACTUAL
  resource group; the answer adds the mobile-app "All Resources" switch and
  the Deny audit.
- **Action gap**: error "User has no permission to do the action:
  (ListExecutionRiskyTasks)" → `--skip-api` acceptable → branch
  `missing-action-chain`; template t4 (OOS chain, ticket-cited labels) +
  "OOS is not OSS" explanation in one reply.
- **Boundary check**: "the sub-account insists it IS an admin login problem" →
  after the brief: `python3 scripts/areas/ram_policy_diagnosis/ram_policy_diagnosis.py --guest-check
  --region-id cn-hangzhou --instance-id i-... --command whoami --confirm`.

## Final Answer Contract

The final answer MUST: (1) start from the script's Summary/`STATUS`
(`OK|DEGRADED|FAIL`) + `NEXT_ACTION`, relayed faithfully; (2) cite only real
return values and the URLs in `references/ram-policy-diagnosis__help-docs.md`; (3) declare every
auto-filled/skipped item (`--skip-api`, missing ids, truncation); (4) keep
evidence labels on every action name (verified vs ticket-cited) and state
declared gaps instead of guessing (RAM-side reads, billing names); (5) present
grants ONLY as manual main-account steps and refuse out-of-bound requests by
name; (6) close with the handoff line (with its ticket-evidence link) for
every non-RAM area detected.

## Important Notes

1. The customer's raw error text is the primary evidence; the diagnosis
   quality depends on pasting it verbatim.
2. Queries run under the configured credential see that account only —
   when diagnosing a *customer's* sub-account, say whose account the evidence
   reflects; never claim visibility for another account.
3. Never conclude "permissions are fixed" from a grant alone — the
   sub-account must re-test after signing in again (and after switching the
   console resource-group context when scoped).
4. Unverified action names (RAM-side reads/writes, BSS cost actions, any
   name not in `references/ram-policies.md` or the verified call surface)
   must never appear in commands or scripts; in answers they appear only as
   ticket-cited template text with the label attached.
5. Do NOT operate the RAM console for the customer — the grant path is
   exactly what tickets evidence: main account performs it, staff guides it.
6. Language: all outputs of this skill package are English (customer-facing);
   relay translated, decoded facts — never internal file paths of this
   package beyond the script invocations shown above.

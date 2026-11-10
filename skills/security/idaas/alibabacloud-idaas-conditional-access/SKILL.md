---
name: alibabacloud-idaas-conditional-access
description: >
  Configure conditional access policies on a specified IDaaS instance to control under what
  conditions accounts can sign in to the IDaaS app portal or access applications. Use for policy
  lifecycle management (create, modify, enable, disable, delete), hit preview and policy
  simulation, read-only policy auditing, and priority allocation. For intent
  or input collection only, obtain the reply and stop without CLI/API calls. Excludes
  default-policy global MFA settings (console second-factor authentication page), instance
  initialization and account onboarding, and application SSO protocol configuration.
metadata:
  domain: aiops
  owner: aliyunidaas-lab
---

# IDaaS EIAM Conditional Access Policy Configuration

Configure the requested policies using EIAM OpenAPI and the aliyun CLI. The bundled executors perform read-only discovery, plan generation, and confirmed-plan execution; the agent orchestrates intent mapping, plan confirmation, and result reporting. Do not claim this is a standalone one-command apply engine. Respond in the user's language.

## Mode routing table

Fix the mode first, then dispatch the flow; supporting a flow does not mean executing it for every matching request. The user picking a value does not authorize configuration to start. Collection-type requests end immediately after the answer is obtained — load no execution flow, install no CLI, run no discovery.

| User request | Required behavior | Forbidden in this mode |
| --- | --- | --- |
| Concepts / how to configure / how policies take effect | Read [api.md](references/api.md) (API semantics and live-verified behavior) and [scenarios.md](references/scenarios.md) (scenario templates), then explain | Any CLI/API call; any confirmation |
| Intent described but key inputs missing (application / IP / subjects / instance / MFA methods) | Ask only for the missing fields, keep the open-item list, and end | No discovery, no plan, no CLI install, no login |
| Local syntax validation (parameters provided) | Run ca_preflight.py --local-only; report the real stdout and exit code | No cloud queries, no software install, no plan |
| Read-only audit / hit preview ("what policies exist / what would someone hit") | Confirm the instance, run ca_preflight.py, and present the policy list + hit-chain explanation | Any write; any plan confirmation |
| Create policies | Full read-only discovery → plan generation (with hit preview) → one confirmation → execute → read-back verification | Zero writes before confirmation; out-of-scope actions |
| Modify existing policies | Discovery bound to target policy IDs → diff plan → one confirmation → agent orchestrates Update under the same plan-hash discipline | No changes to out-of-scope policies; no delete-and-recreate detour |
| Disable / enable existing policies | Save the preflight output to a file → plan-disable/plan-enable binding (zero cloud calls) → one confirmation → apply | No out-of-scope changes |
| Delete policies | Save the preflight output to a file → plan-delete binding → show current state and impact → one confirmation → apply (disable → read back → delete → zero-count verification); the observation gate can be split into a prior plan-disable | No delete-before-disable; never decide the observation period has elapsed on the user's behalf |

## Target scope gate

Before any EIAM call (including read-only), the target must come from explicit user input or previously user-confirmed non-sensitive recovery context:

- The instance ID must be provided explicitly, format-validated, and only then discovered; never infer it from the default profile or the only visible instance. When the instance ID is missing, ask once and stop — no cloud calls.
- Application selection must come from user confirmation (when names are ambiguous, list candidates for the user to choose from; do not read back IDs and make the user guess).
- Modify/delete additionally binds the ConditionalAccessPolicyId; re-read before execution and block on disappearance or change — never silently swap targets (the expected_record binding discipline).
- Referenced network zones (NetworkZone), groups, and organizational units likewise: IDs are mapped from List results, and the user confirms names.

## Intent-to-scenario mapping

Users state intent, not policy parameters. Read [scenarios.md](references/scenarios.md) for the mapping; the skeleton ships five templates:

| Scenario | Policy combination | Key points |
| --- | --- | --- |
| Office IP only | Whitelist allow P1 + fallback deny P2 | The fallback deny binds the same access target so it never spills over to all applications and the portal |
| Mandatory second-factor authentication for a specific application | 1 policy: MfaType=mfa_required + multiple methods | Session reuse unspecified means disabled + the MFA-free interval is fixed at 300 seconds |
| High-sensitivity application, MFA on every access | Same as above (unspecified means MFA every time) | Every SSO login requires MFA |
| Differentiated by group | One policy per group | Different decisions per group |
| No MFA on the office network, MFA outside | 1 policy: office IP allow + directly_access | Outside traffic falls back to the default policy (allow + MFA); only one quota slot spent |

Priority runs 1-100, smaller is higher (the default policy at 1001 is the fallback). Preflight reports occupancy and then allocates automatically (custom policy limit is 10); the user never touches the numbers. Before writing, run a semantic conflict check: same access target + same conditions with different decisions → report the conflict, never insert silently.

Network zones (NetworkZone) are instance-level shared resources that may be referenced by features beyond conditional access — **this skill does not create, modify, or delete network zones**; it only discovers them read-only and references them by ID. Network zones referenced in the intent must already exist in discovery (`network_` IDs); when missing, plan blocks and lists the existing candidates — the user creates the zone in the console or another authorized channel, then comes back to regenerate the plan.

## Read-only discovery and hit preview

```sh
python3 scripts/ca_preflight.py --instance-id INSTANCE --eiam-profile PROFILE \
  [--app-id APP_ID ...] [--network-zone-id ZONE_ID ...] \
  [--sim-user USER --sim-group G ... --sim-ou OU ... --sim-app APP --sim-ip IP]
```

When delete/disable/enable is intended later, save this preflight output to a file (e.g. `> PREFLIGHT.json`) so plan-delete/plan-disable/plan-enable can bind the targets — the plan stage makes zero cloud calls and does not re-run discovery.

State machine (the agent routes by state; skipping states is forbidden):

| State | Meaning | Next step |
| --- | --- | --- |
| `ready` | Discovery complete; quota, entities, and priorities all usable | Generate a plan |
| `quota_exceeded` | Custom policies already at the 10-policy limit | Report occupancy and ask which one to replace or delete |
| `entity_missing` | A referenced application / network zone does not exist | List candidates or guide creation (same plan) |
| `entity_not_configurable` | The reference is a system application (portal excepted) — not a valid conditional access target | Explain it is not configurable and guide the user to a user_custom application or the portal |
| `discovery_incomplete` | Some read failed; a permission failure ≠ the resource does not exist | Fix the read; never assume empty |
| `auth_required` / `environment_required` | Credentials invalid / CLI or eiam command missing | Fix only the missing domain; install nothing unrelated |
| `instance_unavailable` | Instance not accessible | Resolve instance permissions |
| `local_validation_passed` | Only syntax validation passed | Does not imply identity or readiness |

Hit preview rules: iterate enabled policies from highest to lowest priority; a hit requires all three condition families (application / subject / network) to match; exactly one policy hits per request; when nothing hits, the default policy is the fallback. VPC-type network zones cannot be verified locally from an IP — the preview marks them as approximate and says so. The preview output is what the user confirms, not a JSON parameter.

## Plan and confirmation

Intent file (INTENT.json, generated by the agent from the scenario templates; structure in scenarios.md) → plan file (PLAN.json):

```sh
python3 scripts/ca_lifecycle.py plan --plan-file PLAN.json --intent-file INTENT.json \
  --instance-id INSTANCE --eiam-profile PROFILE \
  [--sim-user U --sim-group G ... --sim-ou OU ... --sim-app A --sim-ip IP]
```

The plan stage runs, in order: intent local syntax validation (zero cloud calls) → read-only discovery → entity/quota/priority validation → automatic allocation of free priorities → write PLAN.json and print its SHA256, status `awaiting_confirmation`. The plan file is self-contained: full policy payloads (including allocated priorities), the hit preview, and entity validation results; both confirmation and execution bind to this file and its SHA256.

- Network zones are referenced only by existing `network_` IDs; missing references block at the plan stage.
- MfaAuthenticationIntervalSeconds is fixed to 300 by this skill: the intent may omit the field (plan injects 300 for mfa_required policies); any other value is rejected at local validation. The app portal is referenced by the fixed ID `iap_user_portal` (an allow policy may target the portal, e.g. "signing in to the portal requires MFA"). Access targets can only be user_custom applications or the portal — the portal is the only configurable system application; referencing any other system application is rejected at discovery (`entity_not_configurable`).
- Present the confirmation as a **human-readable summary**: one row or bullet per policy covering its name, decision, conditions, and allocated priority; **never paste the full plan JSON into the conversation, and no raw hit-preview JSON either** — give the preview conclusion in one line; the full plan lives only in the plan file (give its path if the user wants to inspect it). The SHA256 digest binds to execution: confirm A and A is what runs.
- Recovery and ordinary retries stay within that confirmed scope; any scope change (different applications, conditions, or policy set) requires rediscovery, a new plan, and a new confirmation.
- The pre-confirmation presentation must include: the MFA methods (must be asked when the user has not specified them — never default to all methods or reuse another policy's method set), quota occupancy, priority allocation, and the relationship to existing policies.

Delete/disable/enable plans bind to the session's saved preflight result (zero cloud calls):

```sh
python3 scripts/ca_lifecycle.py plan-delete --plan-file PLAN.json \
  --eiam-profile PROFILE --preflight-file PREFLIGHT.json [--policy-id cap_xxx ...]
```

plan-delete/plan-disable/plan-enable bind all custom policies by default (the default policy at priority 1001 is out of scope); `--policy-id` selects a subset, and the IDs must exist in the preflight result. The plan carries the bound_policies full snapshot (for pre-write drift comparison at apply), actions, and deletion_irreversible.

## Execution (after confirmation)

```sh
python3 scripts/ca_lifecycle.py apply --plan-file PLAN.json --approved-plan SHA256
```

1. A hash mismatch blocks with zero cloud calls.
2. Re-verify before writing: re-run preflight — if someone changed priorities, filled the quota, deleted a referenced entity, or squatted a network zone name after confirmation, block and regenerate the plan.
3. Transport: policy Create/Update carry DecisionConfig/ConditionsConfig object parameters, which the aliyun CLI cannot send (the JSON string is rejected by the server with "Flat format is required"; dot-path flags are rejected locally by the CLI as invalid parameters) — such writes must go through the bundled SDK transport (tea-openapi generic client; depends on alibabacloud-tea-openapi/-credentials/-tea-util/-openapi-util, imported lazily). Before writing, the SDK transport verifies with GetCallerIdentity that the SDK credential account matches the eiam-profile account; on mismatch, zero writes. Other reads and writes (scalar/array parameters) still go through the CLI. SDK exception text may contain request headers — report only code/RequestId.
4. Execute in plan order: create the policy (stable ClientToken; on timeout, first read back by name via List before deciding to retry — never blind-fire) → Get read-back comparison → if the read-back Status is not enabled, issue a compensating Enable (declared in the plan's actions; in live testing, creation already defaults to enabled). Read-back semantics are "requested fields are covered": the server synthesizes defaults for unspecified fields (live-verified: interval=300, ActiveSessionReuseStatus=disabled), so strict equality would wrongly reject a correct creation.
5. Partial-failure resume (same hash): already-created same-name policies (with matching configuration coverage) are reused, not rebuilt; configuration drift blocks and requires a new plan.
6. State that propagation takes about 3 minutes; a consistent read-back means configuration consistency, not live effect — never claim instant effect.
7. apply dispatches by the plan's operation. create runs the flow above; delete/disable/enable run the state flow: a slim pre-write re-check (one List compared against the binding snapshot — policy disappearance or configuration drift blocks and regenerates the plan, status excepted, since state operations change status by definition) → one capability probe → staged execution: disable all → Get read back all → (delete only) delete all → List zero-count verification. On partial failure, report completed details, failed actions, and RequestIds; disabled records are kept, not rolled back, and a same-hash resume skips policies already at their target; if deletion fails midway the bound set is incomplete — rediscover, rebind, and re-confirm. The observation gate can be split: plan-disable apply → observe → plan-delete apply. Modification goes through UpdateConditionalAccessPolicy (object parameters, SDK transport), still orchestrated by the agent under the same plan-hash discipline.

## Danger gates

- Priority conflicts and quota are blockers, not warnings.
- A permission failure is not "the resource does not exist"; when List is denied, never conclude there are no policies.
- A timeout does not prove failure: decide only after reading back.
- Partial failure: report completed IDs, failed actions and RequestIds, remaining steps, and the exact missing permissions; no automatic rollback deletes.

## Cloud request attribution

The version is read only from [manifest.json](references/manifest.json). Each configuration session generates one 32-character lowercase-hex SKILL_SESSION_ID, reused across CLI calls, retries, and recovery. UA format: `AlibabaCloud-Agent-Skills/alibabacloud-idaas-conditional-access/{session-id} skill-version/{manifest-version}`, injected process-wide via ALIBABA_CLOUD_USER_AGENT — a single channel, no duplicated tokens. If the manifest is missing or the version is invalid, stop cloud calls; never guess or hardcode a version.

## Completion contract

- API evidence comes straight from real subprocess stdout (including RequestId and the raw response structure); hand-reconstructed responses are forbidden. Pipelines use pipefail or subprocess capture and preserve exit codes.
- Success = the created/modified policies read back matching field by field + status as planned + the 3-minute propagation notice given.
- The final report includes: instance, policy IDs, changed or reused policies, read-back results, referenced network zones, and repeatable recovery commands (no secrets). Partial failures report the remaining work and the next action.

## Input/output example

Input: only the office network may access the "Finance System"; access from outside is denied outright (the office network zone already exists).

preflight may return (excerpt):

```json
{"schema_version": 1, "status": "ready", "instance_id": "idaas_xxx",
 "quota": {"custom_policy_limit": 10, "custom_policy_count": 3, "remaining": 7},
 "priorities_free": [1, 2, 3]}
```

That discovery result is not a successful configuration. After plan confirmation, report the actual policy IDs, the read-back verification results, and the 3-minute propagation notice.

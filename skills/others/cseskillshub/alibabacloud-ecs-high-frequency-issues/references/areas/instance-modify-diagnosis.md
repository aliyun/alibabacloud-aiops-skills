---
name: alibabacloud-ecs-high-frequency-issues
area: instance-modify-diagnosis
description: |
  Read-only ECS instance spec-change and purchase-feasibility diagnosis: can an instance be
  upgraded or downgraded, why a spec change did not take effect, is a target type in stock,
  and what quota limits apply. Use when a customer asks about changing an ECS instance type,
  a create that failed for no stock, or a change that needs a restart.
  Triggers: "change instance type", "upgrade ECS spec", "downgrade instance", "spec change not
  effective", "instance sold out", "cannot create instance", "OperationDenied.NoStock",
  "StoragePerformanceReachLimit", "IncorrectInstanceStatus".
  Do NOT use: start/stop state -> area:instance-state-diagnosis; pricing ->
  area:renewal-pricing-discount; disk expansion -> area:disk-expand-diagnosis.
---

# ECS Instance-Modify Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Diagnose Alibaba Cloud ECS instance spec-change and purchase feasibility, read-only:
"can I upgrade or downgrade this instance type", "why did my spec change not take effect",
"is this instance type sold out in my zone", "why did my purchase / create instance fail",
"what quota or limit blocks me from creating more instances". Core approach: confirm identity
and region, then gather evidence from the ECS control plane -- the current instance spec /
status / charge type, the target instance types it can be changed to, the stock availability of
a target type, and the account-level attributes -- and conclude with evidence-based feasibility
plus manual guidance. This skill never changes a spec, restarts an instance, or places an order.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you
   generate, write, or execute any command/script calling a mutating API -- e.g. changing an
   instance attribute or spec, replacing a system disk, rebooting / starting / stopping an
   instance, running or creating an instance, or placing any order -- including commands "for
   the user to run manually" through this skill's scripts. If the user asks to perform the
   change, only output manual guidance and declare this skill is read-only.
2. **API WHITELIST:** The only permitted OpenAPI actions are the read-only ECS queries
   `DescribeInstances`, `DescribeResourcesModification`, `DescribeAvailableResource` and
   `DescribeAccountAttributes` (product `ecs`, API version `2014-05-26`) plus
   `sts:GetCallerIdentity` for identity traceability. No other action is authorized for this
   skill and none may be called.
3. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens
   explicitly. Credentials are resolved automatically by the aliyun CLI default credential
   chain. Never accept AK/SK from the user or from another script.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by the ECS
   APIs or in `references/instance-modify-diagnosis__spec-modify-guide.md`. If a query fails or returns empty, record it
   and state the limitation -- never invent a spec, a stock status, a quota value, or a price.
5. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <Code>: <Message>` to stderr
   and continue with the remaining queries -- never silently skip or abort the whole diagnosis.
   The final report is still produced with the data at hand.
6. **SCOPE BOUNDARY:** This skill only covers spec-change feasibility, the "change did not take
   effect / needs restart" explanation, stock / purchase availability, and account quota
   limits. It does NOT cover: performing the change, renewal / pricing negotiation, refunds,
   cross-zone or cross-region migration, disk expansion, or instance start/stop state repair.
   For such requests, state the boundary explicitly, give the console entry, and offer a
   human-handoff sentence; never simulate a change outcome.

## Trigger Conditions

Use this skill when the customer's own wording matches one of these phrases (the same list the
`description` advertises):

- "change instance type" / "upgrade ECS spec" / "downgrade instance"
- "spec change not effective" / "needs a restart to take effect"
- "instance sold out" / "cannot create instance" / "no stock"
- "resource quota limit" / "cannot buy more instances"
- the error strings `OperationDenied.NoStock`, `StoragePerformanceReachLimit`,
  `IncorrectInstanceStatus`

A customer rarely states the technical cause; match on the symptom sentence or the error string,
not on internal vocabulary. When the customer gives no way to locate the instance, still run the
entry script: it exits `STATUS: FAIL` with a `NEXT_ACTION` naming the missing input (instance id
/ region / target type), which is what should be put back to the customer.

## Execution Principle

All diagnostics MUST be performed by running the scripts under `scripts/`. The Agent is
forbidden from assembling its own `aliyun` CLI commands or bypassing the scripts to call ECS
APIs directly -- the scripts embed retry, error degradation, credential masking, and
observability guarantees that ad-hoc commands lack. Read the script output, interpret it through
`references/instance-modify-diagnosis__spec-modify-guide.md`, and compose the report; do not re-implement the queries.

## Observability

All OpenAPI calls (invoked through the aliyun CLI by the scripts) include:
- **User-Agent template**: `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, where
  `{skill-name}` is `area:instance-modify-diagnosis`.
- **session-id**: a 32-character hex string (`uuid.uuid4().hex`) generated once per script run
  and attached to the `--user-agent` argument of every CLI command of that run, so all calls of
  one diagnosis can be correlated.

The shared CLI layer (`scripts/areas/instance_modify_diagnosis/_cli.py`) implements this automatically: the session-id is
generated lazily on the first call of each run and cached for the rest of the run.

## Prerequisites

1. **aliyun CLI 3.x** -- required: the ECS queries and the identity check are invoked via the
   `aliyun` CLI (built-in API metadata mode for `ecs`, plugin mode for
   `aliyun sts get-caller-identity`). No direct HTTP signing, no external Python SDK.
2. **Python 3.9+** -- standard library only, no third-party dependencies.
3. **Alibaba Cloud credentials** -- resolved automatically by the aliyun CLI default credential
   chain (environment variables or `~/.aliyun/config.json`). Do not read, print, or pass
   AK/SK/STS tokens explicitly.

## Authentication

Credentials are resolved automatically by the aliyun CLI default credential chain (environment
or `~/.aliyun/config.json`). Do not read, print, or pass AK/SK/STS tokens explicitly.

```bash
cd $SKILL_DIR

# Verify caller identity (informational only; credentials always come from the CLI default chain)
python3 scripts/areas/instance_modify_diagnosis/sts_token.py
```

**Identity Verification Failure**: If `aliyun sts get-caller-identity` fails, the default
credential chain is not configured. Guide the user to verify the default credential chain with `aliyun sts get-caller-identity` -- never ask for
AK/SK.

## User Confirmation

Because every action of this skill is strictly read-only, no user confirmation is required
before running the diagnostic scripts. Confirmation discipline applies at the scope boundary
instead: when a request asks to actually perform a spec change, restart, or purchase (excluded
by Absolute Rule 6), do not proceed with any change -- state the boundary, point to the console
entry, and offer the human-handoff sentence.

## Orchestration

One read-only entry script gathers evidence; the reference modules interpret it. Consult a
module by responsibility, in this order:

1. Collect the inputs the report needs. Never guess an instance id or region: let the script's
   `STATUS: FAIL` output tell you what to ask, and offer only resources the credential can see.
2. Run `scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py` for the needed capability and read `status`, the
   verdict, and `errors[]`.
3. Interpret through the modules below; the guide explains the decision tree and the error
   codes, and the RAM module names the permission to grant when a call reports `NoPermission`.
4. Answer per the Final Answer Contract: verdict first, then the manual guidance, then a
   declaration of every auto-filled parameter.

| Module | Responsibility (from Module Index) |
|---|---|
| M1: Spec-modify guide | Feasibility decision tree, charge-type/restart rules, stock and quota interpretation, error-code reference |
| M2: RAM policies | Minimal read-only RAM policy required by this skill |

### Exit codes (contract)

- `0` -- the run produced a conclusion: `STATUS: OK`, or `STATUS: DEGRADED` when part of the
  evidence was unavailable (missing calls are recorded in `errors[]` and as `[WARN]` on stderr;
  the conclusion is still usable).
- `1` -- no usable conclusion: `STATUS: FAIL`, typically because required input is missing
  (no instance id / target type / mode) or every evidence call failed. `NEXT_ACTION` states what
  to ask the user for; never treat exit `1` as a successful diagnosis.
- `2` -- argparse usage error only (unknown option). A diagnosed condition never exits with `2`.

## Input Parameters

- **Instance id** (`--instance-id`): the target ECS instance for a spec-change / did-not-take-
  effect check (capability A/D). Required for that mode.
- **Region** (`--region`): region id, default `cn-hangzhou`. Auto-filled to the default when
  omitted and declared; a wrong region is the most common cause of "instance not found".
- **Operation type** (`--operation-type Upgrade|Downgrade`): the spec-change direction, default
  `Upgrade`.
- **Target instance type** (`--target-instance-type`): the desired target for a feasibility
  check, or the type to check stock for (capability B, with `--check-stock`).
- **Zone** (`--zone-id`): optional zone scoping for the stock check.
- **Mode flags**: `--check-stock` (capability B) and `--check-quota` (capability C) are
  account/region-level and need no owned instance.
- **UID**: can always be omitted -- it is derived via `aliyun sts get-caller-identity` and used
  only as a traceability label. Auto-fill first, ask second.

**Auto-fill declaration requirement**: Whenever any parameter is auto-filled (region or UID),
the Agent MUST explicitly declare this in the response, e.g. "Region auto-defaulted to
cn-hangzhou".

## Module Index

Reference modules, strictly 1:1 with the `references/` directory:

| Module | File | Responsibility |
|--------|------|----------------|
| M1: Spec-modify guide | [references/instance-modify-diagnosis__spec-modify-guide.md](references/instance-modify-diagnosis__spec-modify-guide.md) | Feasibility decision tree, charge-type/restart rules, stock and quota interpretation, error-code reference |
| M2: RAM policies | [references/ram-policies.md](references/ram-policies.md) | Minimal read-only RAM policy required by this skill |

## Diagnostic Flow

### Step 1: Confirm Identity and Region

Run `python3 scripts/areas/instance_modify_diagnosis/sts_token.py` to verify credentials and derive the UID (traceability label
only). Determine the capability the user needs: spec-change feasibility (an instance id is
given), stock / purchase feasibility (a target type is given), account quota, or the
"change did not take effect" explanation. If genuinely ambiguous, ask one brief clarifying
question.

### Step 2 (Capability A/D): Spec-Change Feasibility

```bash
cd $SKILL_DIR && python3 scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py \
    --instance-id <i-...> --region <region> \
    [--operation-type Upgrade|Downgrade] [--target-instance-type <type>] [--json]
```

The script reads the current spec/status/charge type (`DescribeInstances`) and the changeable
target types (`DescribeResourcesModification`, `DestinationResource=InstanceType`,
`ResourceId=<instance-id>`), then reports a verdict: `FEASIBLE` (with the target list and whether
the requested target is feasible), `NO_FEASIBLE_TARGET`, or `INSTANCE_NOT_FOUND`. It also
returns the charge-type restart rule and, when the instance is a Running pay-as-you-go instance,
a note that most changes require it to be Stopped first.

### Step 3 (Capability B): Stock / Purchase Feasibility

```bash
cd $SKILL_DIR && python3 scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py \
    --check-stock --target-instance-type <type> --region <region> [--zone-id <zone>] [--json]
```

Calls `DescribeAvailableResource` (`DestinationResource=InstanceType`) and reports `AVAILABLE`,
`SOLD_OUT` (mapped to the customer-visible `OperationDenied.NoStock`) or `UNKNOWN`, with the
guidance to try another zone / type / charge type. This needs no owned instance.

### Step 4 (Capability C): Account Quota / Limits

```bash
cd $SKILL_DIR && python3 scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py --check-quota --region <region> [--json]
```

Calls `DescribeAccountAttributes` and reports the returned account-level attributes plus the
Quotas Center pointer for the per-instance-type purchase quota. Report only what is returned;
never invent a quota value.

### Step 5: Conclusion and Suggestions

Summarize the verdict with the actual values from the API responses (current type, status,
charge type, feasible targets, stock status, or account attributes). Base the conclusion on the
script's `Summary` / verdict fields rather than re-deriving it. Suggestions must be
evidence-based and stated as manual guidance only (this skill never applies any change).
Requests to perform the change, or about pricing / migration / disk expansion, follow the SCOPE
BOUNDARY handoff in Absolute Rule 6.

## Important Notes

- **Control plane is authoritative**: the `InstanceType` from `DescribeInstances` is what was
  actually changed. If the OS still shows old vCPU/memory, the change has not taken effect yet --
  it applies only after the restart / order completion for the charge type.
- **Charge type gates the change**: pay-as-you-go usually requires Stopped first; subscription
  upgrades restart the instance and downgrades can be limited by the discount window.
- **No stock is not a bug**: `OperationDenied.NoStock` means the target/zone is sold out right
  now; suggest another zone / type / charge type. Stock refills over time.
- **Wrong region looks like "not found"**: `InvalidInstanceId.NotFound` is most often a region
  mismatch; verify the region before concluding the instance is gone.
- **Read-only operations**: only the whitelisted `DescribeInstances`,
  `DescribeResourcesModification`, `DescribeAvailableResource`, `DescribeAccountAttributes` and
  `sts:GetCallerIdentity`; never modifies anything.

## Examples

**Example 1 -- can I upgrade this instance, and to what**

> User: "Can I change instance i-bp1example0001 in cn-hangzhou to a bigger type? UID ****3456."

```bash
python3 scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py --instance-id i-bp1example0001 --region cn-hangzhou --operation-type Upgrade
```

Report the current type/status/charge type, the feasible upgrade targets, and the charge-type
restart rule; declare "Region cn-hangzhou" and that the UID was derived from the identity check.
Performing the upgrade is a manual console action (out of scope).

**Example 2 -- purchase failed, is it sold out**

> User: "I cannot create instance type ecs.g6.large in cn-hangzhou zone i, it says no stock."

```bash
python3 scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py --check-stock --target-instance-type ecs.g6.large --region cn-hangzhou --zone-id cn-hangzhou-i
```

Relay the `SOLD_OUT` verdict and the `OperationDenied.NoStock` guidance verbatim (try another
zone / type / charge type); never place an order.

**Example 3 -- I upgraded but vCPU did not change**

> User: "I upgraded the spec yesterday but the server still shows the old CPU inside the OS."

```bash
python3 scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py --instance-id i-bp1example0001 --region cn-hangzhou
```

Compare the control-plane `InstanceType` with what the user sees; explain that the change takes
effect only after the restart / order completion for the charge type, and give the manual
restart guidance (this skill does not restart anything).

## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/areas/instance_modify_diagnosis/sts_token.py` | Verify caller identity via `aliyun sts get-caller-identity`; derive the UID traceability label (`--json` optional) |
| `scripts/areas/instance_modify_diagnosis/ecs_instance_modify.py` | Read-only entry: spec-change feasibility (`--instance-id`), stock / purchase feasibility (`--check-stock --target-instance-type`), account quota (`--check-quota`); `--region`, `--operation-type`, `--zone-id`, `--profile`, `--json` |
| `scripts/areas/instance_modify_diagnosis/_cli.py` | Shared aliyun-CLI layer: session-id User-Agent, transient-error retry, credential masking, per-call timeout; imported by the entry script |
| `scripts/areas/instance_modify_diagnosis/_constants.py` | Embedded static data: API metadata, charge-type/restart rules, error-code semantics (no data files, per MUST 1.1.2) |

CLI options for `ecs_instance_modify.py`: `--instance-id <i-...>`, `--region <region>`
(default `cn-hangzhou`, auto-filled and declared), `--operation-type Upgrade|Downgrade`
(default `Upgrade`), `--target-instance-type <type>`, `--zone-id <zone>`, `--check-stock`,
`--check-quota`, `--profile <name>`, `--json`. The three capabilities are selected by the mode
flag / `--instance-id`.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Default credential chain not configured | Run `aliyun sts get-caller-identity`; never ask the user for AK/SK |
| `NoPermission` / `ImplicitDeny` | RAM policy missing an ECS read action | Record the missing action, continue with remaining queries, point to [references/ram-policies.md](references/ram-policies.md) |
| `InvalidInstanceId.NotFound` | Instance id not found in the region | Verify the instance id AND the region; the account must own it |
| `OperationDenied.NoStock` | Target type / zone sold out | Report no stock; suggest another zone / type / charge type |
| `IncorrectInstanceStatus` | Instance state forbids the change | Explain the stop/start requirement for the charge type (manual) |
| `Throttling.User` | Request rate limited | Retried automatically with backoff (up to 3 attempts); then log `[WARN]` and continue |
| Empty result | No instance / no availability data | Report it honestly as a valid finding; never infer a spec or a stock status |

All errors follow the `Code: Message` format raised as `CliError` inside the shared CLI layer;
transient errors are retried, persistent ones are degraded with `[WARN]` on stderr, and the
report is always emitted with whatever data succeeded. Every run ends with
`STATUS: OK|DEGRADED|FAIL` and a `NEXT_ACTION:` line driving the next step.

## Final Answer Contract

The final answer to the user MUST:
1. Start with the verdict (feasible / no feasible target / available / sold out / quota summary)
   and the `STATUS` outcome (`OK` / `DEGRADED` / `FAIL`), relayed faithfully.
2. Quote real values from the script output only (current type, status, charge type, feasible
   targets, stock status, account attributes); never re-compute or invent them.
3. Declare every auto-filled parameter (region, UID) explicitly.
4. Give evidence-based suggestions as **manual guidance**; the user performs any spec change,
   restart, quota increase, or purchase in the console.
5. For requests outside the scope boundary (performing the change, pricing, migration, disk
   expansion), end with the console entry and the human-handoff sentence instead.

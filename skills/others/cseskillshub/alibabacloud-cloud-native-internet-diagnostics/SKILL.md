---
name: alibabacloud-cloud-native-internet-diagnostics
description: |
  Read-only diagnostics for the public internet egress capability of Alibaba
  Cloud cloud-native products: cloud-native gateway (MSE), cloud-native API
  gateway, AI gateway, Serverless App Engine (SAE), and Function Compute (FC).
  Use when the user asks whether such an instance can access the public
  internet, reports outbound connectivity failure, or wants to check a fixed
  public egress IP. Resolves the VPC/vSwitch bound to the instance, then
  verifies NAT gateway SNAT egress for that vSwitch; produces a diagnosis
  report. Read-only: never creates, modifies, or deletes any resource.
  Triggers: "cloud-native gateway public internet", "MSE gateway outbound",
  "APIG outbound connectivity", "AI gateway public network",
  "SAE public internet", "SAE outbound connectivity", "FC fixed public IP",
  "FC function outbound", "cloud-native internet diagnostics",
  "vSwitch NAT SNAT egress".
---

# Cloud-Native Product Public Internet Egress Diagnostics

Diagnose whether an Alibaba Cloud cloud-native product instance (MSE gateway, cloud-native API gateway, AI gateway, SAE application, FC function) can reach the public internet. The flow queries the instance to obtain its bound VPC and vSwitch, then checks whether that vSwitch has a NAT gateway SNAT public egress.

## Execution Principle

MANDATORY:

- **Read-only**: this skill only queries and reports. It never creates, modifies, or deletes any resource.
- **Single entry point**: all cloud queries MUST be executed through `scripts/cloud_native_internet_diag.py`. Do not hand-assemble CLI command chains or inline Python.
- **Single-resource scope**: only the instance / application / function explicitly provided by the user is queried. No scanning, enumeration, or probing of other resources.
- **Fail fast**: if the script exits non-zero, stop and report the error. Do not retry with ad-hoc CLI variants.
- **Strict sequencing**: steps below run in order; any step failure aborts the diagnosis with the error preserved.

## Prerequisites (Runtime and aliyun CLI Version)

| Requirement | Value | Why |
|-------------|-------|-----|
| Python | 3.8 or newer | runs the two scripts; standard library only, no third-party packages |
| aliyun CLI | **version 3.3.3 or newer, on PATH** | all cloud queries go through the CLI in lowercase-hyphenated plugin mode (e.g. `aliyun vpc describe-nat-gateways`); older builds lack the plugin-mode metadata and the `--user-agent` flag this skill relies on |

Check the installed version first:

```bash
aliyun version
```

If the reported version is older than 3.3.3, upgrade the CLI before running any diagnosis (any one of these routes):

```bash
# macOS / Linux with Homebrew
brew upgrade aliyun-cli

# any platform: replace the binary with the latest release from
# https://github.com/aliyun/aliyun-cli/releases

# verify the upgrade took effect
aliyun version
```

A CLI older than 3.3.3 is a hard blocker: report the version gap and the upgrade command to the user instead of falling back to hand-assembled HTTP calls.

## Credentials

- Credentials are resolved automatically by the aliyun CLI default credential chain (environment or ~/.aliyun/config.json). Do not read, print, or pass AK/SK/STS tokens explicitly.
- No script in this skill accepts `--access-key-id` / `--access-key-secret` / `--sts-token` parameters. Never export or echo plaintext credentials on the command line.
- `scripts/sts_token.py` only performs identity verification and UID derivation (via `aliyun sts get-caller-identity`); it never carries credentials.

## User Confirmation

- Before running any query, confirm the target **product type**, **region**, and **instance id** with the user.
- If the user provides a `gw-` prefixed instance id without naming the product, you MUST ask whether it is a cloud-native gateway (MSE) or a cloud-native API gateway / AI gateway — both families share the `gw-` prefix but use completely different APIs. Never guess.
- UID is informational only and can be auto-derived; product / region / instance-id are never auto-filled silently.

## Trigger Conditions

Keyword triggers:

- cloud-native gateway public internet / MSE gateway outbound / gateway public access
- cloud-native API gateway public / APIG outbound connectivity / AI gateway public network
- SAE public internet / SAE outbound connectivity / Serverless App Engine public
- Function Compute public / FC outbound / FC fixed public IP
- cloud-native internet diagnostics

Intent triggers:

- User asks whether a cloud-native gateway / API gateway / AI gateway / SAE app / FC function can access the public internet
- User reports such a product cannot reach the public internet
- User asks to verify the egress capability or the fixed public IP of a cloud-native product

## Input Parameters

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| product | string | Yes | Product type: mse_gateway / apig_gateway / ai_gateway / sae / fc | mse_gateway |
| region | string | Yes | Region id where the instance lives | cn-hangzhou |
| instance-id | string | Yes | Instance id (gateway/SAE) or function name (FC) | gw-cuqp1e6m1hkgu37dj3ag |
| uid | string | No | Customer account UID; auto-derived via `aliyun sts get-caller-identity` when omitted | 1534830445234223 |

**Required inputs**: product, region, instance-id (three items). If the user omits any of them, ask before proceeding; do not run with guessed values.

**Auto-fill first, ask second**: never ask the user for the UID when it can be derived via `sts_token.py`. Whenever any parameter is auto-filled (e.g. UID), the Agent MUST explicitly declare it in the response, e.g. "UID auto-derived via sts:GetCallerIdentity: 1772241626973633". This declaration is mandatory and must appear in the final output.

## Covered Products

| # | Product | Key | Instance id shape | Query API |
|---|---------|-----|-------------------|-----------|
| 1 | Cloud-native Gateway (MSE) | mse_gateway | starts with `gw-` | mse:GetGateway |
| 2 | Cloud-native API Gateway | apig_gateway | starts with `gw-` | apig:GetGateway |
| 3 | AI Gateway | ai_gateway | starts with `gw-` | apig:GetGateway |
| 4 | Serverless App Engine | sae | UUID, e.g. `xxxx-xxx-xxxx` | sae:DescribeApplicationConfig |
| 5 | Function Compute | fc | function name (string) | fc:GetFunction |

> **Critical distinction**: MSE gateways and API/AI gateways both use `gw-` prefixed ids but different APIs. Confirm the exact product first. See [references/module1_instance_lookup.md](references/module1_instance_lookup.md).

## Module Index

| Module | Purpose | File |
|--------|---------|------|
| Instance Lookup | Five-product API details and response field parsing | [references/module1_instance_lookup.md](references/module1_instance_lookup.md) |
| vSwitch Egress | NAT/SNAT egress determination and FC four-quadrant table | [references/module2_vswitch_egress.md](references/module2_vswitch_egress.md) |
| Report Template | Diagnosis report structure (with Information Sources) | [references/report-template.md](references/report-template.md) |
| RAM Policies | Minimum read-only RAM policy, action by action | [references/ram-policies.md](references/ram-policies.md) |

> Load references on demand. Do not read all reference files unless the task requires them.

## Orchestration

```
User request
    |
    v
Step 1: confirm product / region / instance-id (gw- prefix => must clarify)
    |
    v
Step 2: identity verification + UID derivation (sts_token.py)
    |
    v
Step 3: run cloud_native_internet_diag.py
    |   (instance lookup -> FC four-quadrant -> vSwitch NAT/SNAT check)
    |
    v
Step 4: render the diagnosis report (dual-layer: machine JSON + human report)
```

## Execution Flow

### Step 1: Parameter Clarification and Confirmation

1. **Product type** (cannot be skipped):
   - "cloud-native gateway" / "MSE gateway" → `mse_gateway`
   - "cloud-native API gateway" / "APIG" → `apig_gateway`
   - "AI gateway" → `ai_gateway`
   - "SAE" / "Serverless App Engine" → `sae`
   - "Function Compute" / "FC" → `fc`
   - A `gw-` prefixed id without a named product → **MUST ask**: MSE gateway or API/AI gateway?
2. **Region id**: e.g. cn-hangzhou, cn-shanghai, cn-beijing.
3. **Instance id**: gateway id / SAE AppId / FC function name.

If the user refuses or cannot provide these, stop and explain that they are mandatory for diagnosis.

### Step 2: Identity Verification and UID Derivation

```bash
SKILL_DIR=~/.qoderwork/skills/alibabacloud-cloud-native-internet-diagnostics

cd $SKILL_DIR && python3 scripts/sts_token.py --json
```

Prints the caller identity (AccountId / Arn / IdentityType) and derives the UID. On failure, guide the user to configure the aliyun CLI default credential chain or authorize the RAM role (see [references/ram-policies.md](references/ram-policies.md)).

### Step 3: Run the Diagnostics

```bash
cd $SKILL_DIR && python3 scripts/cloud_native_internet_diag.py \
  --product <product> --region <region> --instance-id <instance_id>
```

The script emits a **dual-layer output**:

- **stdout (machine layer)**: one structured JSON report. It carries instance facts (vpc_id / vswitch_id / gateway_type), the FC four-quadrant diagnosis when applicable, the inline vSwitch NAT/SNAT egress check, and the final conclusion, plus three stable user-facing fields: `summary` (plain-English verdict for non-technical users), `plain_language_conclusion` (one-sentence conclusion), and `recommended_actions` (array of next steps, empty when no action is needed). This JSON is the input for downstream processing.
- **stderr (user layer)**: `[INFO]` / `[WARN]` / `[ERROR]` progress traces, followed by a formatted human-readable report block (Product / Instance / Region / Conclusion / Details / How it works / Next steps) that can be shown to the user directly.

Degraded paths (authorization errors, instance not found, invalid parameters) produce the same dual-layer output with an actionable `summary` instead of a raw error code.

### Step 4: Render the Diagnosis Report

Build the final report per [references/report-template.md](references/report-template.md), including the Information Sources section and any auto-fill declarations. Prefer the script's own `summary` / `plain_language_conclusion` / `recommended_actions` for the user-facing conclusion; the stderr report block can be quoted for non-technical users.

## Observability (User-Agent and Session ID)

Every OpenAPI call MUST carry the skill User-Agent built from this template:

```
--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}
```

Template fields:

- **SKILL_NAME**: `alibabacloud-cloud-native-internet-diagnostics` (fixed, equals the frontmatter `name`)
- **session-id**: a 32-character lowercase hex string (`uuid.uuid4().hex`)

session-id rules (MANDATORY):

1. **Generated once per session**: one session-id is produced at the start of a diagnostic session and reused by every subsequent call; never regenerated per call.
2. **32-character lowercase hex format**: exactly 32 hex characters, no dashes.
3. **Consistent across backends**: the same session-id is reused by every execution backend of that session (aliyun CLI, SDK, Terraform), so all calls of one diagnosis correlate under a single trace id.

Code-layer implementation: `scripts/cloud_native_internet_diag.py` and `scripts/sts_token.py` each build `_USER_AGENT` from this template with `uuid.uuid4().hex` and pass `--user-agent` on every aliyun CLI invocation.

## Important Notes

1. **Product distinction**: MSE gateway and API/AI gateway ids both start with `gw-` but use different APIs. Always confirm the product; never guess.
2. **Credential safety**: no AK/SK hardcoding anywhere; credentials come only from the CLI default chain.
3. **FC four-quadrant rule**: only quadrant D (`internetAccess=false` + vSwitchIds configured) needs the NAT/SNAT check, which runs against every bound vSwitch; quadrants A/B/C conclude directly from GetFunction. See [references/module2_vswitch_egress.md](references/module2_vswitch_egress.md).
4. **Degradation trace**: authorization errors during VPC sub-queries do not abort the report; they are recorded as `[WARN]` on stderr and surfaced in the report warnings.
5. **Dependencies**: Python 3.8+ and the `aliyun` CLI **version 3.3.3 or newer** on PATH — see the Prerequisites section above for the version check and the upgrade routes. No third-party Python packages are required.

## Examples

**Example 1**: User: "Does cloud-native gateway gw-685f661467b54f in Hangzhou have public internet access?"

The user said "cloud-native gateway" but also used a `gw-` id; confirm whether it is MSE or API/AI gateway first. Assuming MSE:

```bash
cd $SKILL_DIR && python3 scripts/sts_token.py --json
cd $SKILL_DIR && python3 scripts/cloud_native_internet_diag.py \
  --product mse_gateway --region cn-hangzhou --instance-id gw-685f661467b54f
```

**Example 2**: User: "Does FC function my-function have a fixed public IP?" (region cn-hangzhou)

```bash
cd $SKILL_DIR && python3 scripts/cloud_native_internet_diag.py \
  --product fc --region cn-hangzhou --instance-id my-function
```

If the JSON shows `fc_quadrant: "D"`, the script automatically verifies NAT SNAT egress of the bound vSwitch; quadrants A/B/C conclude directly.

**Example 3**: User: "SAE application 7171a6ca-d1cd-4928-8642-7d5cfe69abcd cannot reach the public internet in Beijing."

```bash
cd $SKILL_DIR && python3 scripts/cloud_native_internet_diag.py \
  --product sae --region cn-beijing --instance-id 7171a6ca-d1cd-4928-8642-7d5cfe69abcd
```

**Example 4**: User: "Does APIG gateway gw-xxx in Shanghai have public egress?"

```bash
cd $SKILL_DIR && python3 scripts/cloud_native_internet_diag.py \
  --product apig_gateway --region cn-shanghai --instance-id gw-xxx
```

Note: a `gw-` prefixed id of the APIG / AI gateway family is resolved via `apig:GetGateway`, not `mse:GetGateway` — confirm the product family before running.

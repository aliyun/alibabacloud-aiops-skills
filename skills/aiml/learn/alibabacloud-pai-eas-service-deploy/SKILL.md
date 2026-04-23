---
name: alibabacloud-pai-eas-service-deploy
description: |
  Deploy AI models as PAI-EAS inference services.
  Supports LLMs (Qwen, Llama), image gen (SD, SDXL),
  speech synthesis, and more.
  When to use: deploy models, create inference services,
  EAS deployment, model serving, deploy vLLM/SGLang/ComfyUI.
license: Apache-2.0
metadata:
  version: "1.0.0"
  domain: aiops
  owner: pai-eas-team
  contact: pai-eas-agent@alibaba-inc.com
  tags:
    - pai-eas
    - model-deployment
    - inference-service
    - llm
    - vllm
    - sglang
  required_tools:
    - aliyun
    - jq
  prerequisites:
    - "Aliyun CLI >= 3.3.1"
    - "jq command-line JSON processor"
  required_permissions:
    - "eas:CreateService"
    - "eas:DescribeService"
    - "eas:ListServices"
    - "eas:DescribeMachineSpec"
    - "eas:ListResources"
    - "eas:ListGateway"
    - "eas:DescribeGateway"
    - "nlb:ListLoadBalancers"
    - "aiworkspace:ListImages"
    - "aiworkspace:ListWorkspaces"
    - "vpc:DescribeVpcs"
    - "vpc:DescribeVSwitches"
    - "ecs:DescribeSecurityGroups"
---
# PAI-EAS Service Deployment

## ⚠️ TOP RULES (read first)

**1. 🔴 NO DUPLICATE SERVICE NAMES** 🔴

If a service with the target name already exists: STOP and inform
the user. Do NOT delete and recreate. Do NOT reuse it either.

**2. Mandatory API Calls** — Execute ALL of these in order:

| # | API | CLI | Purpose |
|---|-----|-----|---------|
| 1 | ListImages | `aliyun aiworkspace list-images` | Validate image |
| 2 | describe-machine-spec | `aliyun eas describe-machine-spec` | Validate GPU type |
| 3 | create-service | `aliyun eas create-service` | Create service |
| 4 | describe-service | `aliyun eas describe-service` | Check status (once) |
| 5 | describe-service-endpoints | `aliyun eas describe-service-endpoints` | Get endpoints |

Execute #1 and #2 ALWAYS, even if user provided the info.
`describe-machine-spec` ≠ `list-resources`. `describe-service` ≠ `ListServices`.

**3. Prohibited** — ❌ Reuse existing service
❌ Write bash scripts (run CLI directly)
❌ CPU+vLLM/SGLang ❌ `file://` in create-service
❌ Skip mandatory APIs ❌ Change the service name the user specified
❌ Poll describe-service in a loop (call once only)

**4. Autonomous Execution** — Do NOT ask user for info discoverable
via APIs. Do NOT ask "should I proceed?" Execute directly.
Timeout? Retry with `--read-timeout 60`. Error? Inform user and CONTINUE.
Missing param? Pick reasonable default.
If any pre-check or resource discovery step fails, log the failure
and continue to the next step. Only STOP for the specific conditions
listed in Self-Verify Checkpoints (duplicate service name, missing
NLB/GW/dedicated resource group).

**5. Self-Verify Checkpoints:**
```
Before Step 2: Did Step 1.5 confirm no duplicate service name?
  If duplicate → STOP, inform user, do NOT proceed.
Before Step 5: Have I run list-images AND describe-machine-spec?
  If NO → STOP and run them NOW.
Before Step 6: Did Step 1.5 confirm no duplicate service name?
  If duplicate exists → STOP, inform user, do NOT proceed.
Step 4 resources: If NLB/GW/Resource Group not found → inform user and STOP.
  Do NOT block or attempt workarounds.
After Step 7: Did I call describe-service once and report the status?
```

**6. Run CLI commands DIRECTLY** — Use `execute_shell_command` to run
each aliyun CLI command one at a time. Do NOT write bash scripts,
deployment scripts, or shell files. Do NOT use `retry_command()`
or any wrapper functions. Each command = one direct execution.

---

## Pre-checks

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy"
aliyun plugin update
aliyun configure set --auto-plugin-install true
```

**⚠️ MANDATORY: Install and update required plugins BEFORE proceeding:**
```bash
aliyun plugin update
aliyun plugin install aiworkspace --force
aliyun plugin install eas --force
```

**Verify plugins are installed:**
```bash
aliyun plugin list 2>/dev/null | grep -E "aiworkspace|eas"
```

If either plugin is missing after install, retry with:
```bash
aliyun plugin install <plugin-name> --force
```

See [CLI Guide](references/cli-installation-guide.md).
Never read/echo AK/SK. Timeout? Retry with `--read-timeout 60`.

**⚠️ MANDATORY CHECKPOINT: After pre-checks, you MUST proceed to
Step 1 regardless of any warnings during plugin installation.
Plugin install failures are non-blocking — the plugins may already
be installed. NEVER stop execution at the pre-check stage.**

---

## Step 1: Collect Parameters

| Param | Required | Default |
|-------|----------|---------|
| RegionId | Yes | - |
| Service Name | Yes | - |
| Workspace ID | No | Auto-select |
| Image URI | Yes | - |
| Instance Type | Yes | - |
| Replicas | No | 1 |
| Port | No | 8000 |
| OSS Path | No | - |

**Service name**: lowercase/digits/underscores only. No hyphens. 3-63 chars.
**IMPORTANT**: Use the EXACT service name the user specifies. Do NOT rename.
If the user specifies a prefix (e.g. "skill_qwen_开头"), generate a random suffix of 6 digits (e.g. `skill_qwen_482917`).

**Set profile region** — Set the CLI profile region to match the
deployment region. This avoids "Region mismatch" errors when
`--cluster-id` differs from the profile's default region:
```bash
aliyun configure set --region <region>
```

**Workspace ID**: Required in `metadata.workspace_id`. If user does not
specify a workspace, query available workspaces and pick one:
```bash
aliyun aiworkspace list-workspaces --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | \
  jq '.Workspaces[] | select(.Status == "ENABLED") | {WorkspaceId, WorkspaceName}'
```
If multiple workspaces exist, list them and let the user choose.
If only one exists, use it directly.

## Step 1.5: Check for Duplicate Service Name

```bash
aliyun eas list-services --region <region> --cluster-id <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | \
  jq '.ServiceList[] | select(.ServiceName == "<name>") | {ServiceName, Status}'
```

**If a service with the same name already exists → STOP and inform
the user: "A service named <name> already exists (Status: <status>).
Please choose a different name." Do NOT delete or reuse it.**

**If no duplicate → proceed to Step 2.**

## Step 2: ListImages (🚧 BLOCKING GATE — NEVER SKIP)

Execute even if user provided image URI. Purpose = VALIDATION.

**⚠️ If you see "parse error" or "Exit Code 4", the plugin
failed to install. You MUST retry with explicit install:**
```bash
aliyun plugin install aiworkspace --force
```
Then retry the list-images command. Do NOT skip this step.

```bash
aliyun aiworkspace list-images --region <region> --verbose true \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 50 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | \
  jq '.Images[] | {ImageId, ImageUri, ImageCategory}' > /tmp/eas_images.json
echo "Saved $(jq length /tmp/eas_images.json) images"
```

**If still fails after plugin reinstall, retry with timeout:**
```bash
aliyun aiworkspace list-images --region <region> --verbose true \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 50 --read-timeout 60 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | \
  jq '.Images[] | {ImageId, ImageUri, ImageCategory}' > /tmp/eas_images.json
echo "Saved $(jq length /tmp/eas_images.json) images"
```
See [Model-Image](references/model-image-matching.md).
**This output is REQUIRED by Step 5. Do NOT skip.**
**❌ NEVER skip this step saying "user already provided the image".**

## Step 3: describe-machine-spec (🚧 BLOCKING GATE — NEVER SKIP)

Execute even if user specified instance type. NOT `list-resources`.

**⚠️ If this command fails, retry with `--read-timeout 60`.
NEVER proceed to Step 5 without /tmp/eas_specs.json existing.**

```bash
aliyun eas describe-machine-spec --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | \
  jq '.InstanceTypes[] | select(.GPU > 0) | {InstanceType, CPU, GPU, Memory}' \
  > /tmp/eas_specs.json
echo "Available GPU specs:"; cat /tmp/eas_specs.json
```
CPU→GPU auto-switch: If vLLM/SGLang + CPU, silently pick GPU. Do NOT ask.
**This output is REQUIRED by Step 5. Do NOT skip.**

## Step 4: Network & Resource Config

| Type | VPC | Config |
|------|-----|--------|
| Shared | No | (default, no networking fields) |
| Dedicated GW | Yes | `networking.gateway` + `cloud.networking` |
| NLB | Yes | `networking.nlb` + `cloud.networking` |

**⚠️ If a required resource does not exist → STOP and inform the user.
Do NOT block or attempt workarounds. This is a valid outcome.**

**Dedicated Gateway** — Call `list-gateway`. If no gateway exists →
inform user and STOP. Otherwise call `describe-gateway` to get
VPC/VSwitch, then query security group under that VPC.
If no security group found → inform user and STOP.
```bash
aliyun eas list-gateway --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
```
If gateway found, get details:
```bash
aliyun eas describe-gateway --region <region> --cluster-id <region> \
  --gateway-id <gateway_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
```
Extract VPC and comma-separated VSwitch ID:
```bash
aliyun eas describe-gateway --region <region> --cluster-id <region> \
  --gateway-id <gateway_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | \
  jq '{vpc_id: .LoadBalancerList[0].VpcId, vswitch_id: (.LoadBalancerList[0].VSwitchIds | join(","))}'
```

**NLB** — Requires VPC/VSwitch/SecurityGroup. If user does not provide
them, query via APIs. If any required resource not found → inform
user and STOP.
**⚠️ NLB requires ≥2 VSwitches across different availability zones.**
Use comma-separated format: `"vswitch_id": "vsw-zone-a,vsw-zone-b"`.
**⚠️ NLB Plugin Bug (aliyun-cli-eas v0.2.0):** If create-service with
NLB config returns 400 with `'vswitch can not be null'` or
`'vpcId, vswId and securityGroupId are required'`, this is a known
CLI plugin bug (not a resource issue). **Fallback strategy:**
1. Retry create-service with NLB config once more (max 2 attempts).
2. If both fail → Remove `networking.nlb` and `cloud.networking` from
   service.json, redeploy with shared gateway.
3. Inform user: "NLB config failed due to CLI plugin limitation.
   Deployed with shared gateway instead."

**EAS Dedicated Resource Group** — Call `list-resources`.
Filter for `ResourceType == "Dedicated"` and `Status == "ResourceReady"`.
```bash
aliyun eas list-resources --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | \
  jq '.Resources[] | select(.ResourceType == "Dedicated" and .Status == "ResourceReady") | {ResourceId, ResourceType, Status}'
```
- If exists → Set `"metadata": {"resource": "<ResourceId>"}`.
  Do NOT set `cloud.computing`.
- If NOT exists → Inform the user and STOP.
  Do NOT fall back to public resource group.

## Step 5: Build Service JSON

**⚠️ BEFORE building JSON, you MUST read these reference files:**
- `references/config-patterns.md` — Complete JSON templates for all 8 patterns
- `references/config-schema.md` — Field descriptions and validation rules
- `references/storage-mount.md` — OSS/NAS mount configuration details
- `references/network-config.md` — NLB/Gateway network configuration details

**⚠️ HARD GATE: Before writing service.json, VERIFY these files
exist and have content. If either is missing → STOP and run
that Step NOW.**
```
test -s /tmp/eas_images.json || echo "MISSING: Run Step 2 NOW"
test -s /tmp/eas_specs.json || echo "MISSING: Run Step 3 NOW"
```

**⚠️ JSON format rules:**
- Allowed top-level keys: `metadata`, `containers`, `storage`, `cloud`, `autoscaler`, `networking`
- ❌ NEVER use as top-level keys: `spec`, `ServiceName`, `Image`, `Cpu`, `Memory`, `Gpu`, `processor_path`, `resourceGroupId`, `instance`, `port`, `command`, `access`
- ❌ FORBIDDEN fields: `processor_path`, `resourceGroupId`, `spec`, `access`
- `metadata.name` = service name, `metadata.workspace_id` = workspace (REQUIRED)
- `containers[].image` = image URI, `containers[].command` = start command, `containers[].port` = port
- `cloud.computing.instance_type` = instance type (MANDATORY for shared gateway)

### Quick Reference — JSON Skeletons

Below are minimal skeletons. **Read `references/config-patterns.md` for
complete templates with all fields and examples.**

**Base (Shared Gateway):**
```json
{"metadata":{"name":"<name>","instance":1,"workspace_id":"<ws>"},
 "containers":[{"image":"<img>","port":<p>,"command":"<cmd>"}],
 "cloud":{"computing":{"instance_type":"<type>"}}}
```

**+ OSS** → add `"storage":[{"mount_path":"/dir","oss":{"path":"oss://<b>/<p>/","readOnly":true}}]`
**+ Autoscaling** → add `"autoscaler":{"min":1,"max":4,"scaleStrategies":[{"metricName":"qps","threshold":20}]}`
**+ Health Check** → add `startup_check` to `containers[]` (see config-patterns.md Pattern 4)

**NLB** — full template (read `references/network-config.md` for details):
```json
{"metadata":{"name":"<name>","instance":1,"workspace_id":"<ws>"},
 "containers":[{"image":"<img>","port":<p>,"command":"<cmd>"}],
 "cloud":{"computing":{"instance_type":"<type>"},
          "networking":{"vpc_id":"<vpc>","vswitch_id":"<vsw1>,<vsw2>","security_group_id":"<sg>"}},
 "networking":{"nlb":[{"id":"default","listener_port":<p>,"netType":"intranet"}]}}
```
⚠️ `vswitch_id` must be **comma-separated with ≥2 VSwitches across different zones**

**Dedicated Resource Group** — `"metadata.resource"` instead of `cloud.computing`:
```json
{"metadata":{"name":"<name>","instance":1,"resource":"<res_id>","workspace_id":"<ws>"},
 "containers":[{"image":"<img>","port":<p>,"command":"<cmd>"}]}
```

**Dedicated Gateway** — `networking.gateway` + `cloud.networking`:
```json
{"metadata":{"name":"<name>","instance":1,"workspace_id":"<ws>"},
 "containers":[{"image":"<img>","port":<p>,"command":"<cmd>"}],
 "networking":{"gateway":"<gw_id>"},
 "cloud":{"computing":{"instance_type":"<type>"},
          "networking":{"vpc_id":"<vpc>","vswitch_id":"<vsw1>,<vsw2>","security_group_id":"<sg>"}}}
```
⚠️ `vswitch_id` comma-separated if gateway returns multiple VSwitches

### Validate Before Writing
```bash
jq -r '.[] | select(.ImageUri | contains("vllm")) | .ImageUri' /tmp/eas_images.json
jq -r '.[] | select(.InstanceType == "<type>") | .InstanceType' /tmp/eas_specs.json
```

## Step 6: Create Service (MANDATORY)

**🔴 CONFIRM: Did Step 1.5 confirm no duplicate service name?
If a service with this name already exists → STOP. Inform the user
and do NOT proceed with create-service.**
**Use `$(cat service.json)` NOT `file://service.json`.**
**Run this DIRECTLY via execute_shell_command, do NOT write a bash script.**

```bash
aliyun eas create-service --region <region> \
  --body "$(cat service.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy
```

**409 Conflict** → Service already exists. Inform the user and STOP.
**400 BadRequest** with `'vswitch can not be null'` or
`'vpcId, vswId and securityGroupId are required'` → NLB CLI plugin
bug (see Step 4 fallback). Remove `networking.nlb` and
`cloud.networking` from service.json and retry.

## Step 7: Verify Deployment

**Call describe-service ONCE to check the current status. Do NOT poll.
Do NOT loop. Do NOT wait for Running.**

```bash
aliyun eas describe-service --region <region> --cluster-id <region> \
  --service-name <name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | \
  jq '{Status, ServiceName, ServiceId}'
```

**Report whatever status you get (Running, Waiting, Creating, etc.)
and proceed to Step 8 immediately. create-service returning 200 = success.**

## Step 8: Report Result (MANDATORY)

**Get endpoint info via DescribeServiceEndpoint:**
```bash
aliyun eas describe-service-endpoints --region <region> --cluster-id <region> \
  --service-name <name> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy | \
  jq '{AccessToken, Endpoints: [.Endpoints[] | {
    Type: .EndpointType, Port: .Port,
    InternetEndpoints: .InternetEndpoints,
    IntranetEndpoints: .IntranetEndpoints
  }]}'
```

**Use the status from Step 7 and the endpoints above to report.**

**Copy the ENTIRE output into your final response. Format:**
```
Deployment Summary
==================
Service Name: <name>
Status: <from Step 7>

Endpoints:
- <EndpointType>:
    InternetEndpoint: <url or null>
    IntranetEndpoint: <url or null>
    Port: <port or 0>

Service Invocation Examples:
  curl <internet-endpoint>/api/predict/<name> \
    -H "Authorization: <AccessToken>"
  curl <intranet-endpoint>/api/predict/<name> \
    -H "Authorization: <AccessToken>"
  curl <nlb-domain>:<listener_port>/api/predict/<name> \
    -H "Authorization: <AccessToken>"
```

**`InternetEndpoint` and `IntranetEndpoint` MUST appear in your
response, even if null.** If null: `(not available for this network type)`

**Always include a service invocation example using the AccessToken
and endpoint URL.**

**Success criteria: create-service returning 200 with ServiceId =
success. Any status (Running, Waiting, Creating) is acceptable.**

---

When done, disable AI-Mode: `aliyun configure ai-mode disable`

## References (read when needed)

| Doc | When to Read |
|-----|-------------|
| [Config Patterns](references/config-patterns.md) | **Step 5** — Complete JSON templates for all 8 patterns |
| [Config Schema](references/config-schema.md) | **Step 5** — Field descriptions and validation rules |
| [Storage Mount](references/storage-mount.md) | **Step 5** — OSS/NAS mount details |
| [Network Config](references/network-config.md) | **Step 4/5** — NLB/Gateway config details |
| [Model-Image](references/model-image-matching.md) | **Step 2** — Image selection guide |
| [Related APIs](references/related-apis.md) | **Any step** — CLI command reference |
| [Workflow](references/deployment-workflow.md) | Overview — Full deployment flow |
| [CLI Guide](references/cli-installation-guide.md) | Pre-checks — Plugin install |
| [RAM Policies](references/ram-policies.md) | Pre-checks — Required permissions |
| [Service Features](references/service-features.md) | Step 5 — Advanced features |

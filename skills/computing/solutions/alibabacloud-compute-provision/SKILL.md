---
name: alibabacloud-compute-provision
description: "Alibaba Cloud Compute Provision - Automatically selects an Alibaba Cloud compute resource (ECS, FC, ACK, PAI) based on user intent, then creates instances and executes scripts. Use this skill when the user needs to run compute jobs, execute scripts, train models, or deploy containerized applications on Alibaba Cloud, or mentions keywords such as cpu_bound, gpu, vCPU, budget, training, A100, or qwen. Provides a full loop of resource selection, pricing, budget control, instance creation, and script execution."
license: MIT
metadata:
  author: Aliyun
  version: "0.1.0"
---

# Alibaba Cloud Compute Provision

Automatically selects an Alibaba Cloud compute resource based on user intent, then creates instances and executes scripts.

## How this skill works

This skill operates by **writing and executing Python code that calls Alibaba Cloud APIs**. The `scripts/` directory contains ready-made Python modules (ECS, FC, ACK, PAI, VPC, etc.) that wrap the Alibaba Cloud OpenAPI. To accomplish any task in this skill, you write Python code snippets that import and call functions from these modules — you do NOT use CLI tools, Terraform, or the web console.

Typical workflow:
1. **Read the reference doc** for the product you're about to use (see Reference Index below).
2. Write a Python code block that imports from the skill's `scripts/` modules.
3. Execute the code to call Alibaba Cloud APIs (query instance types, check pricing, create resources, run scripts, etc.).
4. Read the output and decide the next step.

> **⛔ MUST-READ RULE**: Before calling ANY function from `scripts/`, you MUST first read its reference doc (e.g. `references/ecs.md` for ECS functions, `references/fc.md` for FC functions). The reference docs contain exact function signatures, parameter names, constraints, and usage examples. **Do NOT guess parameter names** — incorrect parameters waste tool calls and may create/leak cloud resources. Use the defaults when in doubt.

## Prerequisites

### Step 0: Environment bootstrap (MUST run first)

**Before doing anything else**, execute the following code block to set up the Python path and ensure all dependencies are installed. This MUST be the very first code you run in every session — do NOT skip it or defer it.

```python
import sys
sys.path.insert(0, "${SKILL_DIR}/scripts")

from bootstrap import ensure_dependencies
ensure_dependencies()
```

`bootstrap.py` is a standalone module with **zero third-party dependencies** (stdlib only), so it can always be imported even before any pip packages are installed. `ensure_dependencies()` automatically:
- Checks that the Python version is >= 3.8 (exits with a clear error if not).
- Detects missing pip packages (`alibabacloud_credentials`, `alibabacloud_tea_openapi`, `darabonba-core`) and installs them.

> If this step fails, fix the reported issue (e.g. install a newer Python) before proceeding — all subsequent steps depend on it.

### Credentials

Credentials are resolved via the Alibaba Cloud default credential provider chain (environment variables, `~/.alibabacloud/credentials`, `~/.aliyun/config.json`, ECS RAM role, etc.). Do NOT hardcode AK/SK or read them explicitly.

```
ALIBABA_CLOUD_REGION   # optional, defaults to cn-hangzhou
```

## Step 1: Intent Parsing and Resource Selection

### 1.1 Parse user intent

Extract the following elements from the user's input:

| Element | Description | Example |
|---------|-------------|---------|
| Task type | One-shot script / Long-running service / AI training | "deploy nginx" → long-running service |
| Compute requirement | CPU / GPU / memory | "8 vCPU, 16 GB" |
| Budget | Cost cap | "$50" |
| Script / intent | Explicit script or task description | "a.sh" or "deploy an nginx site" |

### 1.2 Script generation (when no explicit script is provided)

When the user provides intent rather than a script (e.g. "deploy an nginx site"), generate the script automatically. Key rules:

- **Script-image coupling**: package managers depend on the OS — Ubuntu uses `apt-get`, CentOS/Alinux uses `yum`. Finalize the script only after the image is decided; if the image changes later, re-check script compatibility.
- **Long-running service scripts** must use background/systemd commands (e.g. `systemctl start nginx`), not foreground-blocking ones.
- **One-shot task scripts** simply exit when finished.

### 1.3 Resource selection

**If the user explicitly specifies a product, use that product directly and skip selection comparison.**

> **⛔ PRODUCT-LOCK RULE**: When the user explicitly specifies a product (e.g. "用 ECS", "use FC"), you are **locked to that product for the entire task**. If you encounter errors (out of stock, quota limits, etc.), you MUST retry within the same product — try different availability zones, regions, or instance types. **NEVER silently switch to a different product.** If all retries within the specified product are exhausted, report the failure to the user and ask for guidance — do NOT auto-switch.
>
> For ECS, use `ecs.find_available_instance_type()` to search across zones/regions for available stock and pricing, then after cost confirmation use `ecs.create_instance_with_infra()` to create the instance.

When unspecified, follow the decision tree in [references/select-resource.md](references/select-resource.md):

```
User specified a product?  → use it directly
Long-running service?      → ECS or ACK (FC / PAI-DLC are not suitable for long-running)
AI / ML training?          → PAI or FC (GPU) → if both viable, MUST compare in Step 1.5
K8s / containers?          → ACK
Multiple products viable?  → MUST compare in Step 1.5
Default (single match)     → ECS
```

> **⛔ ANTI-BIAS**: The decision tree only narrows candidates. When 2+ products remain, you **MUST proceed to Step 1.5** for real API-based comparison — never assume one is "obviously cheaper" from general knowledge.

### 1.4 Region selection — MANDATORY BEFORE resource creation

> **⛔ HARD RULE**: Region selection MUST be performed explicitly as a documented step — not deferred to or assumed during resource creation. The chosen region directly affects network connectivity, package installation success, and end-to-end reliability.

**Decision flow (execute in order):**

1. **Detect external dependency requirements** — scan the script (user-provided or agent-generated) and the task intent for signals that the workload will access overseas sources at runtime:
   - Package managers pulling from default mirrors: `pip install`, `npm install`, `apt-get install`, `yum install`, `go get`, `cargo build`, `gem install`, `composer install`
   - Downloads from GitHub, Docker Hub, PyPI, npmjs.com, Hugging Face, or other overseas hosts
   - `curl` / `wget` to non-Chinese URLs
   - Git clone from github.com / gitlab.com

2. **Apply region rule:**

   | Condition | Region | Rationale |
   |-----------|--------|-----------|
   | Script installs external dependencies from overseas sources (pip, npm, apt, GitHub, etc.) | **Overseas region** (prefer `ap-southeast-1` Singapore) | Domestic regions have poor/unstable connectivity to overseas package registries, causing timeouts and failures |
   | Task deploys a website/service with no overseas dependencies | Domestic region (e.g. `cn-hangzhou`, `cn-shanghai`) | Lower latency for end users |
   | AI training downloading models/datasets from Hugging Face, GitHub, etc. | **Overseas region** | Model downloads from China often timeout |
   | No external network access needed (pure compute, local data) | Domestic region (e.g. `cn-hangzhou`) | Default, lowest latency |
   | User explicitly specified a region | User's specified region | Respect user choice |

   > **Pitfall**: deploying a website seems "domestic", but if the setup script runs `npm install` / `pip install`, the packages come from overseas — choose an overseas region. **Always check the script's dependency commands, not just the service purpose.**

3. **Output the chosen region and reason** to the user before proceeding:
   ```
   Region: ap-southeast-1 (Singapore)
   Reason: The task requires installing packages via pip/npm from overseas sources.
           Domestic regions may cause installation timeouts.
   ```

### 1.5 Multi-option parallel comparison — MANDATORY SUB-AGENT DISPATCH

> **⛔ HARD RULE**: When the user has NOT explicitly specified a product AND the decision tree yields more than one candidate, you **MUST** launch parallel sub-agents — one per candidate product. It is strictly forbidden to compare in the main thread using documentation knowledge or heuristics alone.

**Dispatch rules:**

1. **One sub-agent per candidate product** — launch them in parallel (e.g. one for ECS, one for FC).
2. **Each sub-agent MUST call real APIs** — instance-type queries (`DescribeInstanceTypes`), inventory checks (`DescribeAvailableResource`), and pricing queries (`DescribePrice` or product-specific formulas). Memorized prices are NOT acceptable.
3. **Return structured results** — format defined in the "Sub-agent task template" in [references/select-resource.md](references/select-resource.md).
4. **Main agent aggregates and presents** — build the comparison table (template in [references/select-resource.md](references/select-resource.md)), recommend the best option, and wait for user confirmation.

**Comparison dimensions** (all required): end-to-end time, estimated cost (from API), complexity, resource cleanup.

When uncertain about API usage, search the docs with `scripts/doc_search.py`:

```python
from doc_search import search_and_format
print(search_and_format("DescribeInstanceTypes", product="ecs"))
```

## Step 2: Create Compute Resources

After selecting a product, **read its reference doc** (linked below) for full API usage — especially function signatures and parameter constraints — then create resources. Use the region from Step 1.4; if Step 1.4 is not yet done, go back and complete it first.

| Product | Reference | Workflow summary |
|---------|-----------|------------------|
| ECS | [references/ecs.md](references/ecs.md) | `find_available_instance_type()` → **cost confirmation** → `create_instance_with_infra()` (VPC/SG/image handled internally) |
| FC  | [references/fc.md](references/fc.md)   | choose spec → **cost confirmation** → create function → invoke function |
| ACK | [references/ack.md](references/ack.md) | choose node spec → **cost confirmation** → VPC/SG → create cluster → submit K8s Job |
| PAI | [references/pai.md](references/pai.md) | list_ecs_specs → choose CPU/GPU → **cost confirmation** → create_training_job |

**Network preparation** (ACK only; ECS is handled by `create_instance_with_infra`): see [references/vpc.md](references/vpc.md)

### MANDATORY RULE: Cost confirmation

> **⛔ HARD BLOCK**: Before calling ANY resource-creation API (`RunInstances`, `CreateFunction`, `CreateCluster`, `CreateTrainingJob`), you MUST estimate cost and get user confirmation. The agent may NOT self-approve — regardless of how low the cost is.

**Flow:**

1. **Estimate cost** — use the product's pricing API or formula (see each product's reference doc).
2. **Output the cost estimate** using the template below — do not omit or summarize it.
3. **Wait for user confirmation** — stop and do nothing further until the user replies affirmatively (e.g. "yes", "ok", "确认"). Silence or implied consent do NOT count.
4. **Proceed** only after receiving confirmation.
5. If over budget — recommend a cheaper alternative, re-estimate, and repeat from step 2.

> **Skip-confirmation exception**: if the user has **explicitly stated** in the current conversation that no confirmation is needed (e.g. "直接执行不用确认", "skip confirmation", "just do it, no need to ask"), then still output the cost estimate (step 2) for the record, but proceed immediately without waiting — skip steps 3-4.

Cost display template:
```
Cost estimate:
  Spec:        ecs.t6-c1m2.large (2 vCPU, 4 GB)
  Unit price:  CNY 0.017 / hour
  Duration:    ~5 minutes
  Total:       CNY 0.002
  Billing:     PostPaid (pay-as-you-go)

Proceed with creation?
```

> Exchange-rate reference: $1 ≈ CNY 7.2

## Step 3: Execute the Script

### MANDATORY PRE-EXECUTION CHECK: Script & Resource Validation

> **⛔ HARD BLOCK**: Before executing any script, the following validation steps are **required and non-skippable**. If validation fails, you MUST stop the flow and report the error to the user. **It is strictly forbidden to generate a placeholder/stub script, fabricate execution output, or silently proceed when a required file is missing.**

**Validation flow (apply before every execution):**

1. **Determine script source type:**
   - **(A) User-provided script path** — the user referenced a specific file (e.g. `/home/user/train.py`, `./scripts/run.sh`).
   - **(B) User-provided script content** — the user pasted the script inline or its content is already in the conversation.
   - **(C) Agent-generated script** — no explicit script was provided; the agent generated one from intent (per Step 1.2). In this case, the agent already holds the full content — skip to step 3.

2. **For type (A) — verify file existence and content:**
   - **Local path**: use `Read` tool or `ls` / `cat` to confirm the file exists at the given path and is non-empty. If the file is on a remote instance (ECS), run the check via Cloud Assistant (`test -f <path> && wc -l <path>`).
   - **If the file does NOT exist or is empty**: immediately stop and report to the user:
     ```
     ❌ Script not found: <path>
     The specified script file does not exist or is empty. Please verify the path and try again.
     ```
     **Do NOT** create a replacement script, guess the content, or continue execution.
   - **If the file exists**: read its content to confirm it is a valid, complete script (not a stub or template with only comments/placeholders).

3. **Content completeness check** (for all source types):
   - The script must contain actual executable logic — not just comments, empty functions, or `pass`/`TODO` placeholders.
   - For training scripts (PAI / GPU tasks): verify the script references the expected framework entry points (e.g. `model.fit()`, `trainer.train()`, `torch.distributed.launch`).
   - If the content appears incomplete, ask the user for clarification before proceeding.

4. **Dependency & environment pre-check** (best effort):
   - If the script imports packages or references external data paths, note them so the execution environment can be prepared accordingly (e.g. `pip install` in the startup command, mount data volumes).

> **Rationale**: creating compute resources costs money. Running a missing or placeholder script wastes that cost and misleads the user into thinking the task succeeded.

### Execution methods

| Product | Task type | Call |
|---------|-----------|------|
| ECS | **One-shot** (run and release) | `ecs.run_command_and_cleanup(instance_id, script, infra=infra)` |
| ECS | **Long-running** (keep alive) | `ecs.run_command_and_wait(instance_id, script)` |
| FC  | One-shot | `fc.create_and_invoke(script_path=path)` or `fc.create_and_invoke(script_content=code, script_type="shell")` |
| ACK | K8s Job | `ack.run_script_as_job(cluster_id, script)` |
| PAI | Training job | script is set at `create_training_job` time |

> **⛔ ECS cleanup rule**: For **one-shot tasks**, you **MUST** use `run_command_and_cleanup()` with the `infra` parameter (from `create_instance_with_infra()`). This releases the instance + security group, and only deletes VSwitch/VPC if they were freshly created (shared resources are preserved). Forgetting to release ECS instances causes ongoing charges.
>
> Use `run_command_and_wait()` (without cleanup) **only** when the user explicitly needs the instance to stay running (e.g. "deploy a website", "keep the service online").

## Error Handling

The whole flow uses retry-with-adjustment:

| Error | Strategy |
|-------|----------|
| Out of stock | Try in order: switch availability zone → switch region → downgrade instance type. For ECS use `find_available_instance_type(regions=[...])` which searches across regions automatically. **NEVER switch to a different product.** |
| Quota exceeded | Prompt user to raise quota |
| Over budget | Downgrade spec or shrink scale |
| Script execution failed | Analyze the error, adjust environment / dependencies, then retry |
| Unknown error | Search docs with `doc_search.search(error_message, product)` |

Keep adjusting and retrying until the instance is created and the script is running.

## Reference Index

| Document | Content |
|----------|---------|
| [references/select-resource.md](references/select-resource.md) | Comparison of the four products and selection decision tree |
| [references/vpc.md](references/vpc.md) | VPC / VSwitch API quick reference |
| [references/ecs.md](references/ecs.md) | Full ECS API quick reference (specs / inventory / pricing / creation / execution) |
| [references/fc.md](references/fc.md)   | FC API quick reference + script-packaging method |
| [references/ack.md](references/ack.md) | ACK cluster API quick reference + K8s Job execution |
| [references/pai.md](references/pai.md) | PAI-DLC training-job API quick reference + GPU spec table |
| [references/ram-policies.md](references/ram-policies.md) | RAM 最小权限清单与 Policy JSON |

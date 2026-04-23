# Deployment Workflow

Detailed interaction flow and display format for PAI-EAS service deployment.

**Table of Contents**
- [Core Interaction Principles](#core-interaction-principles)
- [Phase 1: Basic Info](#phase-1-basic-info)
- [Phase 2: Environment](#phase-2-environment)
- [Phase 3: Resources](#phase-3-resources)
- [Phase 4: Network](#phase-4-network)
- [Phase 5: Service Features](#phase-5-service-features)
- [Phase 6: Deploy](#phase-6-deploy)

---

## Core Interaction Principles

### 1. Step-by-Step Guidance

Show current step → Wait for user input → Show next step

### 2. List Pagination

When more than 10 items: `Enter number to select | 'n' next page | keyword filter | 'all' show all`

### 3. Resource Selection Pattern

For optional resources (e.g. EAS resource group, gateway): `1. Select from existing  2. Skip`
For workspaces: Auto-query; select if found, skip immediately if empty

### 4. Default Value Handling

```
Port [8000]:
1. Use default
2. Custom

Select (enter 1 or 2):
```

Defaults: mount path `/model_dir`, port `8000`, replicas `1`, initial delay `60`, check interval `10`

---

## Phase 1: Basic Info

### Step 1.1: Service Name (required)

Lowercase letters, digits, underscores, 3-63 characters.

### Step 1.2: Workspace (optional, auto-handled)

```bash
aliyun aiworkspace list-workspaces --region <region> --page-size 100 --verbose true --user-agent AlibabaCloud-Agent-Skills
```

**Logic**:
- **Has results** → Show list for user to select, record workspace_id
- **Empty list** → **Skip immediately, proceed to next step! Never block asking user!** Simply omit `metadata.workspace_id` from JSON

**⚠️ Never** stop deployment or ask user to create a workspace in the console

**Display format (with results, paginated, max 10)**:
```
| # | Workspace ID | Name             |
|---|-------------|------------------|
| 1 | 312319      | aiworkspace_test |
| 2 | 545434      | ccjtest          |

Total: 20, showing 1-10
Enter number to select | 'n' next page | keyword filter | 'all' show all
```

---

## Phase 2: Environment

### Step 2.1: Select Image

**⚠️ MUST call `ListImages` to query official image list, even if user already provided image address (eval checkpoint)**

| # | Category | Target Models |
|---|----------|--------------|
| 1 | LLM Inference | Qwen, Llama, Mistral |
| 2 | Image Generation | Stable Diffusion |
| 3 | Speech Synthesis | CosyVoice |
| 4 | RAG | RAG Applications |
| 5 | General Inference | PyTorch Models |
| 6 | Custom Image | User-provided image |

**LLM inference requires secondary selection**: vLLM / SGLang

**Query images**:
```bash
aliyun aiworkspace list-images --verbose true \
  --labels 'system.official=true,system.supported.eas=true' \
  --page-size 50 --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.Images[] | "\(.ImageId)\t\(.Name)\t\(.Labels[] | select(.Key == "system.chipType") | .Value)"'
```

**Display format (paginated, max 10)**:
```
| # | Image Name       | Version   | Chip |
|---|-----------------|-----------|------|
| 1 | vllm:0.13.0rc2  | 0.13.0rc2 | GPU  |
| 2 | vllm:0.14.0-xpu | 0.14.0    | XPU  |

Total: 14, showing 1-10
Enter number to select | 'n' next page | keyword filter
```

**Query image chip type** (query immediately after selection, record CHIP_TYPE):
```bash
aliyun aiworkspace get-image --image-id <image-id> --user-agent AlibabaCloud-Agent-Skills | \
  jq '{ChipType: (.Labels[] | select(.Key == "system.chipType") | .Value), ImageUri: (.Labels[] | select(.Key == "system.imageUri") | .Value)}'
```

**Output example**:
```json
{"ChipType": "GPU", "ImageUri": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu"}
```

**Variable**: `CHIP_TYPE=GPU` (subsequent resource selection will auto-filter compatible instances)

**⚠️ Image must match model type**, see [Model-Image Matching Guide](model-image-matching.md)

**⚠️ Chip compatibility (never block)**: Image chip type must match instance type!
- GPU image → `ecs.gn*` series (NVIDIA GPU instances)
- CPU image → any non-GPU instance
- **If user requests CPU instance + GPU image (e.g. vLLM/SGLang), you MUST auto-switch to a GPU instance (e.g. ecs.gn7i-c16g1.4xlarge) silently. vLLM and SGLang REQUIRE GPU — NEVER deploy them on CPU. Do NOT ask the user, just switch and explain your choice.**

### Step 2.2: Storage Mount

**Do you need to mount storage?**

| # | Option | Description |
|---|--------|-------------|
| 1 | Yes | Mount model files or data |
| 2 | No (skip) | No storage mount |

**If "Yes", select storage type**:

| # | Storage Type | Description |
|---|-------------|-------------|
| 1 | OSS | Mount OSS bucket (most common) |
| 2 | NAS | Mount NAS file system |
| 3 | CPFS | Mount CPFS |
| 4 | Dataset | Use PAI dataset |

**OSS mount flow**:

1. **Query bucket list**:
```bash
ossutil ls
```

2. **Display bucket list (paginated, max 10)**:
```
| # | Bucket Name    | Region      |
|---|---------------|-------------|
| 1 | yqtest-model  | cn-hangzhou |
| 2 | my-bucket     | cn-shanghai |

Total: 15, showing 1-10
Enter number to select | 'n' next page | keyword filter
```

3. **List directory**:
```bash
ossutil ls oss://bucket-name/
```

4. **Display directory list**:
```
Selected Bucket: yqtest-model
| # | Path             | Description |
|---|-----------------|-------------|
| 1 | Qwen3.5-0.8B/   | LLM model   |
| 2 | llama-7b/        | LLM model   |

Select model directory (enter number):
```

5. **Configure mount path**:
```
Mount path [/model_dir]:
1. Use default
2. Custom

Select (enter 1 or 2):
```

**⚠️ Important**: OSS path format must be `oss://bucket/path/` (note trailing `/`)

**⚠️ Important**: OSS models must be mounted via storage as local paths (e.g. `/model_dir`). Never pass oss:// URL directly to vllm/sglang commands!

See [Storage Mount Guide](storage-mount.md)

### Step 2.3: Startup Command

```bash
aliyun aiworkspace get-image --image-id <image-id> --user-agent AlibabaCloud-Agent-Skills | jq -r '.EasConfig.script'
```

**Logic**:
- If image has preset command → Show to user for confirmation or modification
- If no preset command → Use typical command as default

**Typical commands**:

| Image Type | Typical Command |
|-----------|----------------|
| vLLM | `vllm serve /model_dir --port 8000 --trust-remote-code` |
| SGLang | `python -m sglang.launch_server --model-path /model_dir --port 8000` |
| ComfyUI | `python main.py --listen 0.0.0.0 --port 8000` |

**Interaction example**:
```
Startup command:
1. Use recommended: vllm serve /model_dir --port 8000 --trust-remote-code
2. Custom command

Select (enter 1 or 2):
```

### Step 2.4: Port

```
Port [8000]:
1. Use default
2. Custom

Select (enter 1 or 2):
```

Default: `8000`

---

## Phase 3: Resources

### Step 3.1: Resource Type

| # | Type | Description |
|---|------|-------------|
| 1 | Public Resource | On-demand, pay-as-you-go |
| 2 | EAS Resource Group | Dedicated resource group |

### Step 3.2: Public Resource Group

**Auto-filter logic** (based on image chip type from step 2.1):

```
Selected image chip type: GPU
Filtering compatible instance types...
```

**Filter rules**:

| Image Chip Type | jq Filter | Instance Type Pattern |
|----------------|-----------|----------------------|
| GPU | `.GPUAmount > 0` | `ecs.gn*` series (NVIDIA GPU) |
| CPU | `.GPUAmount == 0` | Non-GPU instances |
| PPU | `.InstanceType \| startswith("ecs.ebmppu")` | Hanguang instances |
| XPU | `.InstanceType \| startswith("ecs.egs")` | XPU instances |

**One-command query** (auto-select based on chip type):

```bash
# Assuming CHIP_TYPE variable obtained from image labels
aliyun eas describe-machine-spec --region <region> --user-agent AlibabaCloud-Agent-Skills | \
  jq -r --arg chip "$CHIP_TYPE" '
    .InstanceMetas[] | select(.IsAvailable == true) |
    if $chip == "GPU" then
      select(.GPUAmount > 0) | "\(.InstanceType)\t\(.GPUAmount)x\(.GPU)\t\(.CPU) cores\t\(.Memory)GB"
    elif $chip == "CPU" then
      select(.GPUAmount == 0) | "\(.InstanceType)\t-\t\(.CPU) cores\t\(.Memory)GB"
    elif $chip == "PPU" then
      select(.InstanceType | startswith("ecs.ebmppu")) | "\(.InstanceType)\tPPU\t\(.CPU) cores\t\(.Memory)GB"
    elif $chip == "XPU" then
      select(.InstanceType | startswith("ecs.egs")) | "\(.InstanceType)\tXPU\t\(.CPU) cores\t\(.Memory)GB"
    else empty end
  '
```

**GPU image query** (chip type = GPU):
```bash
aliyun eas describe-machine-spec --region <region> --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.InstanceMetas[] | select(.IsAvailable == true and .GPUAmount > 0) | "\(.InstanceType)\t\(.GPUAmount)x\(.GPU)\t\(.CPU) cores\t\(.Memory)GB"'
```

**CPU image query** (chip type = CPU):
```bash
aliyun eas describe-machine-spec --region <region> --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.InstanceMetas[] | select(.IsAvailable == true and .GPUAmount == 0) | "\(.InstanceType)\t-\t\(.CPU) cores\t\(.Memory)GB"'
```

**Display format (paginated, max 10)**:
```
| # | Instance Type            | GPU    | CPU     | Memory |
|---|-------------------------|--------|---------|--------|
| 1 | ecs.gn6i-c4g1.xlarge   | 1×T4   | 4 cores | 16GB   |
| 2 | ecs.gn7-c12g1.12xlarge | 4×A10  | 12 cores| 192GB  |

Total: 45, showing 1-10
Enter number to select | 'n' next page | keyword filter
```

### Step 3.3: EAS Resource Group

**⚠️ MUST call `list-resources` to query resource group list, even if user already provided resource group ID:**

```bash
# MUST call: list all resource groups
aliyun eas list-resources --region <region> --user-agent AlibabaCloud-Agent-Skills

# Query specific resource group details
aliyun eas list-resources --region <region> --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.Resources[] | "\(.ResourceId)\t\(.ResourceName)\t\(.GpuCount)\t\(.GpuUsed)\t\(.CpuCount)\t\(.CpuUsed)"'
```

**Display format**:
```
| # | Resource ID | Name       | GPU (total/used/free) | CPU (total/used/free) |
|---|------------|------------|----------------------|----------------------|
| 1 | eas-r-xxx  | production | 16/2/14              | 128/20/108           |
```

**Calculation**: free = total - used

### Step 3.4: Replicas

```
Replicas [1]:
1. Use default
2. Custom

Select (enter 1 or 2):
```

---

## Phase 4: Network

### Step 4.1: Gateway Type

| # | Type | VPC Config | Description |
|---|------|-----------|-------------|
| 1 | Shared Gateway | ❌ Not needed | Free, suitable for testing |
| 2 | ALB Dedicated Gateway | ✅ Required | Recommended for production |
| 3 | NLB | ✅ Required | High-performance load balancing |

### Step 4.2: ALB Dedicated Gateway Config

**⚠️ MUST call `list-gateway` first to list gateways (even if user provided gateway ID), then call `describe-gateway` to get VPC info:**

```bash
# MUST call: list all gateways
aliyun eas list-gateway --region <region> --user-agent AlibabaCloud-Agent-Skills
```

**Display format**:
```
| # | Gateway Name | Gateway ID |
|---|-------------|-----------|
| 1 | prod-gw     | gw-xxx    |
| 2 | test-gw     | gw-yyy    |

Enter number to select:
```

**Get gateway VPC info**:
```bash
aliyun eas describe-gateway --cluster-id cn-hangzhou --gateway-id gw-xxx --user-agent AlibabaCloud-Agent-Skills | \
  jq '{VpcId: .LoadBalancerList[0].VpcId, VSwitchIds: .LoadBalancerList[0].VSwitchIds}'
```

**Select VSwitch**:
```
Obtained gateway VPC: vpc-xxx
| # | VSwitch ID   | Availability Zone |
|---|-------------|-------------------|
| 1 | vsw-xxx     | Zone A            |
| 2 | vsw-yyy     | Zone B            |

Enter number to select:
```

**Select security group**:
```bash
aliyun ecs describe-security-groups --biz-region-id cn-hangzhou --vpc-id <vpc-id> --user-agent AlibabaCloud-Agent-Skills
```

See [Network Config](network-config.md)

---

## Phase 5: Service Features

### Step 5.1: Feature Selection

**Do you need to configure service features?**

| # | Option | Description |
|---|--------|-------------|
| 1 | Configure features | Select features to enable |
| 2 | Skip | No features enabled (default) |

**If "Configure features"**:

```
Available features (multi-select with comma):

| # | Feature | Description |
|---|---------|-------------|
| 1 | Health Check | Configure startup/liveness probes |
| 2 | Rolling Update | Graceful shutdown + rolling strategy |
| 3 | GRPC | Enable GRPC protocol |
| 4 | Autoscaling | Auto-adjust replicas based on load |

Enter feature numbers to enable (e.g. 1,2,4), enter 'done' to finish:
```

**When modifying feature status**:

```
Current service feature config:

| # | Feature | Status |
|---|---------|--------|
| 1 | Health Check | ✅ Enabled |
| 2 | Rolling Update | ❌ Disabled |
| 3 | GRPC | ❌ Disabled |
| 4 | Autoscaling | ❌ Disabled |

Enter number to toggle (e.g. enter 1 to disable health check), enter 'done' to finish:
```

See [Service Features Config](service-features.md)

---

## Phase 6: Deploy

### Step 6.1: Config Preview

**Compatibility validation** (must pass before deployment):

```
✅ Image chip type: GPU
✅ Instance type: ecs.gn7-c12g1.12xlarge (GPU instance)
✅ Compatibility: Passed
```

If compatibility check fails:
```
❌ Image chip type: XPU
❌ Instance type: ecs.gn7-c12g1.12xlarge (GPU instance)
❌ Compatibility: Failed - XPU image requires XPU instance, please change image or instance type
```

```
Generated service configuration:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "metadata": { "name": "mytest_006", "instance": 1 },
  "containers": [{ "image": "...", "port": 8000 }],
  ...
}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Config Summary:
• Service Name: mytest_006
• Image: vllm:0.14.0-gpu (Chip: GPU)
• Instance: ecs.gn7-c12g1.12xlarge (4×A10, GPU)
• Network: Shared Gateway
• Compatibility: ✅ Passed

Select:
1. Confirm deploy
2. Modify config
3. Save JSON to file
4. Cancel
```

### Step 6.2: Modify Config

**Select config item to modify**:

| # | Config Item | Current Value |
|---|------------|---------------|
| 1 | Service Name | mytest_006 |
| 2 | Workspace | aiworkspace_test |
| 3 | Image | vllm:0.13.0rc2 |
| 4 | Storage Mount | Not configured |
| 5 | Startup Command | vllm serve ... |
| 6 | Port | 8000 |
| 7 | Instance Type | ecs.gn5-c8g1.2xlarge |
| 8 | Replicas | 1 |
| 9 | Network | ALB Dedicated Gateway |
| 10 | Features | Health Check |
| 11 | Go back | - |

Enter number to select:

### Step 6.3: Execute Deployment

**Save config to file, then deploy**:

```bash
# Save config to file
cat > /tmp/eas_service.json << 'EOF'
{
  "metadata": { "name": "my-service", "instance": 1 },
  "containers": [{ "image": "...", "port": 8000 }],
  "cloud": { "computing": { "instance_type": "ecs.gn6i-c4g1.xlarge" } }
}
EOF

# Execute deployment (may take 1-2 minutes)
# ⚠️ Do NOT use file:// prefix, use $(cat) to read file content
aliyun eas create-service --region <region> --body "$(cat /tmp/eas_service.json)" --user-agent AlibabaCloud-Agent-Skills
```

**⚠️ Note**: Use `$(cat file)` to read file content for `--body`, do NOT use `file://` prefix (may cause JSON parsing errors)

**⚠️ CRITICAL: If service with same name exists**: You MUST delete it first using `aliyun eas delete-service --cluster-id <region> --service-name <name> --user-agent AlibabaCloud-Agent-Skills`, wait for deletion to complete, then recreate following ALL steps (ListImages, describe-machine-spec, create-service, describe-service). NEVER just report the existing service status — you MUST always go through the full deployment workflow.

### Step 6.4: Wait for Service Ready

```bash
for i in $(seq 1 6); do
  STATUS=$(aliyun eas describe-service --cluster-id cn-hangzhou --service-name <service-name> \
    --user-agent AlibabaCloud-Agent-Skills | jq -r '.Status')
  case $STATUS in
    Running) echo "✅ Service ready"; break ;;
    Failed)  echo "❌ Service startup failed"; break ;;
    *)       echo "⏳ Status: $STATUS ($((i*30))s/180s)"; sleep 30 ;;
  esac
done
```

### Step 6.5: Display Deployment Result

**MUST include InternetEndpoint and IntranetEndpoint from describe-service response.**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Deployment Result

Service Name: mytest_006
Status: Running
InternetEndpoint: http://xxx.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/xxx
IntranetEndpoint: http://xxx.vpc.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/xxx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**⚠️ You MUST output the exact field names "InternetEndpoint" and "IntranetEndpoint"
with their actual values from the describe-service API response.**

### Step 6.6: Service Invocation Example

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service Invocation Examples

Endpoint: http://xxx.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/mytest_006

[curl] curl http://xxx/api/predict/mytest_006 -H "Content-Type: application/json" -d '{"input": "Hello"}'
[OpenAI SDK] client = OpenAI(base_url="http://xxx/v1", ...)

See [Service Invocation Examples](service-invoke-examples.md)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 6.7: Failure Handling

**Query events**:
```bash
aliyun eas describe-service-event --cluster-id <region> --service-name <service-name> --user-agent AlibabaCloud-Agent-Skills | \
  jq -r '.Events[-3:][] | "[\(.Type)] \(.Reason): \(.Message)"'
```

**Common errors**:

| Error Type | Cause | Solution |
|-----------|-------|---------|
| ImagePullBackOff | Image pull failed | Check image address and permissions |
| CrashLoopBackOff | Container startup failed | Check startup command and model path |
| Instance crashed | Chip type mismatch | Image chip type must match instance type (GPU image → GPU instance) |
| InsufficientResources | Resource shortage | Choose different instance type or resource group |
| ModelNotFound | Wrong model path | Check OSS mount path |

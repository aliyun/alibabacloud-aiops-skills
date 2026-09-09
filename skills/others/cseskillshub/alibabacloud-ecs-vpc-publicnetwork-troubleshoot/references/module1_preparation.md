# Module 1: Preparation

**IMPORTANT: This skill MUST execute all steps strictly in order. If any step fails, abort immediately and print the error. Do NOT skip or continue to subsequent steps.**

> **Security — least privilege (read-only)**: This skill uses **only read-only** Alibaba Cloud APIs (`Describe*` / `GetCallerIdentity` and equivalent query actions) across ECS, VPC, DDoS, Cloud Firewall, BSS and STS. It **never** creates, modifies, deletes, or restarts any resource, and it does **not** require RAM write/management permissions. Grant only the minimum read-only policy in [ram-policies.md](ram-policies.md); granting write permissions is unnecessary. Modifying this skill or its scripts to perform any write/mutating operation is prohibited by its security policy.

## Step 1: Extract region_id and UID

**Purpose**: Obtain the region ID (e.g., cn-beijing, cn-hangzhou) and customer account UID (numeric, e.g., 1178674910674516).

**Fast Path (Scenario 1: ECS Public Network)**: If the user provides `uid`, `instance_id`, and `region_id` together, **skip this step** and use the provided values for Step 2.

**Fast Path (Scenario 2: VPC Cloud Service Public Network)**: If the user provides `uid`, `vswitch_id`, and `region_id` together, **skip this step** and use the provided values for Step 2.

> **Scenario 2 Input Validation**: The primary inputs for Scenario 2 are **vswitch_id and region_id**. UID is auto-obtained from `sts_create.py` (GetCallerIdentity `AccountId`) if not provided. **region_id is mandatory** — extract it from the user's prompt; if missing, ask the user once and abort if still not provided (see SKILL.md mandatory-parameter gate).

**Input Branch Logic** (execute only when fast path conditions are not met):

> **IMPORTANT**: Do NOT execute `aliyun ecs describe-instances`, `aliyun vpc describe-vswitches`, or any standalone CLI command directly. The information extraction below is done by the Agent from the user's input; every cloud query is performed by the main detection script in Step 3.

### Branch A: Input is ECS Instance ID (e.g., `i-2zednz491t3g3f027i2m`)

- `region_id`: **Mandatory.** Use the value from the user's prompt. If missing, ask the user once (offer common regions cn-hangzhou / cn-shanghai / cn-beijing / cn-shenzhen, default cn-hangzhou); if still not provided, **abort** per SKILL.md's mandatory-parameter gate.
- `instance_id`: **Mandatory** for the ECS scenario. If not provided, **abort immediately**, output: `[ERROR] Step 1 failed: instance_id is required for ECS scenario`
- `uid`: Use the user-provided UID, or it will be extracted by the main detection script via `GetCallerIdentity`.
- Available balance: Queried internally by the main detection script via the BSS API.

### Branch B: Input is VSwitch ID (e.g., `vsw-2ze4an6iacrvkp9bwb6py`)

- `region_id`: **Mandatory.** Use the value from the user's prompt. If missing, ask the user once (offer common regions, default cn-hangzhou); if still not provided, **abort** per SKILL.md's mandatory-parameter gate.
- `vswitch_id`: **Mandatory** for the VPC scenario. If not provided, **abort immediately**, output: `[ERROR] Step 1 failed: vswitch_id is required for VPC scenario`
- `uid`: Use the user-provided UID, or it will be **automatically obtained** from `sts_create.py` Step 2 output (`AccountId` field from `GetCallerIdentity`). Do NOT prompt the user for UID.
- `vpc_id` / `cidr_block`: Extracted by the main detection script internally.

> **Scenario identifier**: this skill accepts an ECS **instance_id** (Scenario 1) or a **vswitch_id** (Scenario 2) as the diagnostic target, per SKILL.md Input Parameters. A bare public IP is **not** a direct input — if the user only has a public IP, ask them for the corresponding instance_id before proceeding.

## Step 2: Obtain Access Credentials

Use the built-in `scripts/sts_create.py` script to obtain Alibaba Cloud access credentials.

```bash
# Method 1: From environment variables (recommended)
export ALIBABA_CLOUD_ACCESS_KEY_ID=<AK>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<SK>
export ALIBABA_CLOUD_SECURITY_TOKEN=<TOKEN>  # STS token, optional
python3 scripts/sts_create.py

# Method 2: From aliyun CLI configuration
python3 scripts/sts_create.py --cli

# Method 3: Via AssumeRole for STS temporary credentials
python3 scripts/sts_create.py --role-arn acs:ram::<UID>:role/<ROLE_NAME>

# JSON output for programmatic use
python3 scripts/sts_create.py --cli --json
```

**Credential Priority**:
1. `--role-arn` specified → obtain temporary credentials via STS AssumeRole
2. `--cli` → read from aliyun CLI configured credentials
3. Default → read from `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` environment variables

**Parameters**:
- `--uid` (optional): Used as cache index; sourced from Step 1 or user-provided UID
- `--cli` (optional): Read credentials from aliyun CLI configuration
- `--role-arn` (optional): Obtain STS temporary credentials via AssumeRole
- `--force-refresh` (optional): Force refresh, ignore local cache
- `--json` (optional): Output results in JSON format

**Credential Usage**:
- The script automatically saves credentials to `.sts_cache.json`
- Subsequent API calls read credentials automatically from cache via ConfigLoader
- STS temporary credentials have an expiration; re-obtain when expired
- Never record AK/SK in plaintext in logs or share with others

**Failure Handling**:
- If script execution fails → **Abort immediately**, output: `[ERROR] Step 2 failed: Failed to obtain access credentials. Please verify Alibaba Cloud credentials are configured (environment variables or aliyun CLI)`

## Step 3: Invoke Scenario Script

After successfully obtaining access credentials, invoke the corresponding automation script based on user-selected scenario.

> **Credential Passing**: After Step 2, `sts_create.py` writes credentials to a local cache (`scripts/.sts_cache.json`), and all business scripts read them automatically. **Scripts do NOT accept `--access-key-id` or similar parameters.** **Never export or echo plaintext AK/SK/STS token on the command line** — doing so exposes sensitive credentials in the execution log.

### Scenario 1: ECS Public Network Check

**When input is ECS Instance ID (Step 1 already obtained uid and balance, reuse directly)**:

```bash
# Credentials are read automatically from scripts/.sts_cache.json (written by
# sts_create.py in Step 2). Do NOT export plaintext credentials.
python3 scripts/ecs_public_troubleshoot.py \
  --region-id <region_id from Step 1> \
  --instance-id <instance_id> \
  --uid <uid from Step 1> \
  --available-amount <available_amount from Step 1>
```

> When `--uid` and `--available-amount` are provided, the script **skips** `GetCallerIdentity` and `BSS` API calls internally, reducing 2 API requests for faster detection.

**When input is public IP (Step 1 already obtained instance_id, uid, and balance)**:

```bash
# Credentials are read automatically from scripts/.sts_cache.json (written by
# sts_create.py in Step 2). Do NOT export plaintext credentials.
python3 scripts/ecs_public_troubleshoot.py \
  --region-id <region_id from Step 1> \
  --instance-id <instance_id from Step 1> \
  --uid <uid from Step 1> \
  --available-amount <available_amount from Step 1>
```

The script automatically completes: ECS info query, account status, security group rules, network ACL, VPC attributes, DDoS status, CFW status and other full-chain detection, branching automatically to A (direct public) or B (NAT Gateway) based on whether the ECS has a public IP.

### Scenario 2: VPC Cloud Service Public Network Check

```bash
# Credentials are read automatically from scripts/.sts_cache.json (written by
# sts_create.py in Step 2). Do NOT export plaintext credentials.
python3 scripts/vpc_service_public_troubleshoot.py \
  --region-id <region_id> \
  --vswitch-id <vswitch_id> \
  [--uid <UID>]
```

The script automatically completes: VSwitch info, account status, NAT Gateway, route table, SNAT configuration, EIP details, DDoS status, CFW status and other full-chain detection.

Both scripts use **internal parallel execution** to significantly reduce wait times from sequential API calls. Script output is structured JSON, subsequently rendered as an information table per [module4_output.md](module4_output.md).

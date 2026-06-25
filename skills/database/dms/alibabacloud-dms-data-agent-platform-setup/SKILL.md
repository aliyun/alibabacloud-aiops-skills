---
name: alibabacloud-dms-data-agent-platform-setup
description: Create an agent platform instance in DMS via Alibaba Cloud OpenAPI. Supports Simple Mode and Advanced Mode. Use this skill when the user wants to provision, deploy, or set up a new Dify instance on Alibaba Cloud DMS.
---

# Create Dify Instance

Provision a Dify instance automatically via Alibaba Cloud OpenAPI.
Supports **Simple Mode** (create all resources from scratch) and **Advanced Mode** (fine-grained control over each component).

## Prerequisites

### 1. Check Aliyun CLI

> **[REQUIRED] Verify Aliyun CLI version >= 3.3.1 before proceeding.**

```bash
aliyun version
```

If the command is not found or the version is below 3.3.1, install or upgrade:

**macOS (Homebrew, recommended)**
```bash
brew install aliyun-cli
# Upgrade if already installed
brew upgrade aliyun-cli
```

After installation, enable automatic plugin installation:
```bash
aliyun configure set --auto-plugin-install true
```

### 2. Observability — Session ID & User-Agent

> **[REQUIRED] Generate a session-id at the start of every skill session. Use it consistently across ALL CLI commands and Python SDK calls.**

#### Session-ID Generation Rule

- Generate **once per session**, reuse throughout the entire workflow
- Format: **32-character lowercase hex string** (e.g., `openssl rand -hex 16`)
- Must be consistent across CLI / SDK / Terraform within the same session

```bash
export SKILL_SESSION_ID=$(openssl rand -hex 16)
```

#### User-Agent Template

```
AlibabaCloud-Agent-Skills/alibabacloud-dms-data-agent-platform-setup/{session-id}
```

- **Python scripts** (`detect_dify_instance.py`, `openAPI_call.py`): read `SKILL_SESSION_ID` from environment automatically
- **Aliyun CLI commands**: inject via `--user-agent` flag on each command:

```bash
aliyun dms-enterprise <action> \
  --endpoint dms-enterprise.aliyuncs.com \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dms-data-agent-platform-setup/${SKILL_SESSION_ID}"
```

> **Do NOT use `aliyun configure ai-mode set-user-agent` (deprecated). Always use per-command `--user-agent` injection.**

### 3. Configure Alibaba Cloud Credentials

> **[REQUIRED] Both credential sets must be configured — Aliyun CLI credentials AND Python SDK credentials. Neither can be omitted.**
> **NEVER read, echo, or print AK/SK values.**

This skill performs two types of operations, each using a different credential method:
- **Query instance list** (`aliyun dms-enterprise list-instances`): uses Aliyun CLI credentials
- **Provision Dify instance** (`openAPI_call.py`): uses the Alibaba Cloud default credential chain

#### 3a. Configure Aliyun CLI Credentials

```bash
aliyun configure list
```

Confirm that a valid profile exists in the output (AK, STS, or OAuth).

**If no valid profile exists, stop and prompt the user to:**
1. Obtain an AccessKey from the [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
2. Configure credentials outside of this session to avoid exposing secrets:
   ```bash
   aliyun configure set \
     --mode AK \
     --access-key-id <your-access-key-id> \
     --access-key-secret <your-access-key-secret> \
     --region cn-hangzhou
   ```
3. Re-run `aliyun configure list` to confirm the profile is active

#### 3b. Configure Python Script Credentials

`openAPI_call.py` uses the Alibaba Cloud default credential chain — no environment variables need to be set manually. The SDK automatically resolves credentials in the following order: environment variables, credentials file, instance RAM role, etc.

Configure your credentials by following the official guide:
[Alibaba Cloud Python SDK v2 — Manage Access Credentials](https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-python-access-credentials#3ca299f04bw3c)

> **NEVER hardcode AK/SK values in code or pass them as command-line arguments.**

### 4. Python Environment

It is recommended to use [uv](https://docs.astral.sh/uv/) to create an isolated virtual environment with pinned dependencies:

```bash
uv venv .venv
uv pip install --python .venv/bin/python -r scripts/requirements.txt
```

`requirements.txt` is provided in `./scripts/`.

## Script Location

- `./scripts/detect_dify_instance.py` — Check whether the DMS Dify service is available in the target region
- `./scripts/openAPI_call.py` — Provision a Dify instance

> Run commands from the directory containing this `SKILL.md` file.

---

## Pre-check: Verify DMS Service Availability

> **[REQUIRED] Before running `openAPI_call.py`, run `detect_dify_instance.py` to verify that the DMS service is accessible in the target region.**

```bash
.venv/bin/python ./scripts/detect_dify_instance.py <region-id>
```

Example:
```bash
.venv/bin/python ./scripts/detect_dify_instance.py cn-shanghai
```

- If the API returns an empty list (`[]`), that is normal — it means no Dify instances exist yet, but the service is available.
- If the API returns an error, prompt the user to enable the DMS service in the [Alibaba Cloud Console](https://dms.aliyun.com) before proceeding.

---

## Simple Mode

All components (Workspace, database, KV store, vector database) are newly created.

### Parameters to Collect from User

| Parameter | Description |
|-----------|-------------|
| `VpcId` | VPC ID |
| `VSwitchId` | VSwitch ID |
| `BackupVSwitchId` | Backup VSwitch ID |
| `SecurityGroupId` | Security Group ID |
| `ZoneId` | Availability Zone ID |
| `DataRegion` | Data region |
| `WorkspaceName` | Name for the new Workspace |
| Account | Database account (used for DbInstanceAccount, KvStoreAccount, VectordbAccount; default: `dify_user`) |
| Password | Database password (used for DbInstancePassword, KvStorePassword, VectordbPassword) |
| `DryRun` | Recommended: set to `true` for a dry run first, then `false` to provision |

### Execution Command

```bash
.venv/bin/python ./scripts/openAPI_call.py '{
    "VpcId": "<VpcId>",
    "VSwitchId": "<VSwitchId>",
    "BackupVSwitchId": "<BackupVSwitchId>",
    "SecurityGroupId": "<SecurityGroupId>",
    "ZoneId": "<ZoneId>",
    "DataRegion": "<DataRegion>",
    "ResourceQuota": "12CU",
    "WorkspaceOption": "CreateNewInstance",
    "WorkspaceName": "<WorkspaceName>",
    "DatabaseOption": "CreateNewInstance",
    "DbInstanceAccount": "<account>",
    "DbInstancePassword": "<password>",
    "KvStoreOption": "CreateNewInstance",
    "KvStoreAccount": "<account>",
    "KvStorePassword": "<password>",
    "VectordbOption": "CreateNewInstance",
    "VectordbAccount": "<account>",
    "VectordbPassword": "<password>",
    "StorageType": "cloud_essd",
    "NatGatewayOption": "NoNeed",
    "MajorVersion": "1.13.x",
    "Edition": "OpenCommunity",
    "DryRun": true
}'
```

---

## Advanced Mode

Allows fine-grained control over all parameters, including using existing Workspace, database, KV store, and vector database instances.

### Step 1: Collect Base Network Parameters

Ask the user for the following:

| Parameter | Description |
|-----------|-------------|
| `VpcId` | VPC ID |
| `VSwitchId` | VSwitch ID |
| `BackupVSwitchId` | Backup VSwitch ID |
| `SecurityGroupId` | Security Group ID |
| `ZoneId` | Availability Zone ID |
| `DataRegion` | Data region |

### Step 2: Confirm WorkspaceOption

Ask the user: use an existing Workspace or create a new one?

- `UseExistingInstance`: user must provide `WorkspaceId` (string)
- `CreateNewInstance`: user must provide `WorkspaceName`
- Note: `WorkspaceId` and `WorkspaceName` are mutually exclusive. If both are provided, prompt the user to correct the input.

### Step 3: Confirm Each Sub-Service Option Individually

Ask the user to choose for each of the following independently:

#### DatabaseOption

- `CreateNewInstance`: no additional parameters needed; uses default configuration
- `UseExistingInstance`:
  - Ask the user if they know the `DbResourceId` (integer)
  - If not, run the following command and find the `InstanceId` from `InstanceList.Instance`:
    ```bash
    aliyun dms-enterprise list-instances \
      --endpoint dms-enterprise.aliyuncs.com \
      --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dms-data-agent-platform-setup/${SKILL_SESSION_ID}"
    ```

#### KvStoreOption

- `CreateNewInstance`: no additional parameters needed
- `UseExistingInstance`:
  - Ask the user if they know the `KvStoreResourceId` (integer)
  - If not, run:
    ```bash
    aliyun dms-enterprise list-instances \
      --endpoint dms-enterprise.aliyuncs.com \
      --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dms-data-agent-platform-setup/${SKILL_SESSION_ID}"
    ```

#### VectordbOption

- `CreateNewInstance`: no additional parameters needed
- `UseExistingInstance`:
  - Ask the user if they know the `VectordbResourceId` (integer)
  - If not, run:
    ```bash
    aliyun dms-enterprise list-instances \
      --endpoint dms-enterprise.aliyuncs.com \
      --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dms-data-agent-platform-setup/${SKILL_SESSION_ID}"
    ```

### Step 4: Collect Account and Password

Ask the user for account name and password, and fill in:

- `DbInstanceAccount` / `DbInstancePassword`
- `KvStoreAccount` / `KvStorePassword`
- `VectordbAccount` / `VectordbPassword`

### Step 5: Confirm Other Advanced Parameters

The following parameters have default values. Ask the user if any need to be changed:

| Parameter | Default | Allowed Values |
|-----------|---------|----------------|
| `ResourceQuota` | `12CU` | Custom string |
| `Replicas` | `1` | Integer |
| `NatGatewayOption` | `NoNeed` | `NoNeed`, `Enable` |
| `PayType` | `PrePaid` | `PrePaid`, `PostPaid` |
| `PayPeriodType` | `Month` | `Month`, `Year` |
| `PayPeriod` | `1` | Integer |
| `MajorVersion` | `1.13.x` | Custom string |
| `Edition` | `OpenCommunity` | `OpenCommunity`, `Community`, `Enterprise` |
| `EnableExtraEndpoint` | `true` | `true`, `false` |
| `OnlyIntranet` | `false` | `true`, `false` |
| `DryRun` | `true` | Recommended: `true` for dry run first, then `false` to provision |

### Step 6: Dry Run and Final Provisioning

1. Construct the full JSON with `DryRun=true` and run the script
2. After confirming no errors, set `DryRun` to `false` and run again to provision

---

## Notes

- The Python script uses the Alibaba Cloud default credential chain; configure credentials per the [official guide](https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-python-access-credentials#3ca299f04bw3c) before running the script
- `WorkspaceId` (use existing Workspace) and `WorkspaceName` (create new Workspace) are mutually exclusive
- `DbResourceId`, `KvStoreResourceId`, and `VectordbResourceId` are all integer types
- Always perform a dry run with `DryRun=true` before final provisioning
- Ensure `SKILL_SESSION_ID` is exported before running any command in this workflow

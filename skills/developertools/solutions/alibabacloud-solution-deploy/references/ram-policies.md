# RAM Policies for Alibaba Cloud Solution Deploy

This document lists all RAM permissions required by the Skill's built-in scripts.

> **Note**: This Skill is a *meta-tool* — it helps users deploy various Alibaba Cloud solutions. The permissions below cover **only the Skill's own helper scripts**. Each specific solution deployment will require additional product-level permissions (ECS, VPC, RDS, etc.), which are presented to the user for confirmation in the execution plan (Step B.4) before any resources are created.

## Required RAM Permissions

### Overview

The Skill's scripts call two Alibaba Cloud services:

| Service | Endpoint | Scripts |
|---------|----------|---------|
| **OpenAPI Explorer** | `openapi-mcp.cn-hangzhou.aliyuncs.com` | `search_apis.py`, `search_documents.py`, `diagnose_cli_command.py`, `lsit_products.py`, `lsit_api_overview.py` |
| **IaCService (Terraform Runtime)** | `iac.cn-zhangjiakou.aliyuncs.com` | `terraform_runtime_online.sh` |
| **STS** | (default) | `verify_env.sh` |

### Detailed API-Level Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*",
      "Condition": {}
    },
    {
      "Effect": "Allow",
      "Action": [
        "openapiexplorer:SearchApis",
        "openapiexplorer:SearchDocuments",
        "openapiexplorer:DiagnoseCLI",
        "openapiexplorer:ListProducts",
        "openapiexplorer:ListApiOverviews"
      ],
      "Resource": "*",
      "Condition": {}
    },
    {
      "Effect": "Allow",
      "Action": [
        "iacservice:ValidateModule",
        "iacservice:ExecuteTerraformPlan",
        "iacservice:ExecuteTerraformApply",
        "iacservice:ExecuteTerraformDestroy",
        "iacservice:GetExecuteState"
      ],
      "Resource": "*",
      "Condition": {}
    }
  ]
}
```

### Permission Details by Script

| Script | API Action | Permission |
|--------|-----------|------------|
| `verify_env.sh` | `GetCallerIdentity` | `sts:GetCallerIdentity` |
| `search_apis.py` | `SearchApis` | `openapiexplorer:SearchApis` |
| `search_documents.py` | `SearchDocuments` | `openapiexplorer:SearchDocuments` |
| `diagnose_cli_command.py` | `DiagnoseCLI` | `openapiexplorer:DiagnoseCLI` |
| `lsit_products.py` | `ListProducts` | `openapiexplorer:ListProducts` |
| `lsit_api_overview.py` | `ListApiOverviews` | `openapiexplorer:ListApiOverviews` |
| `terraform_runtime_online.sh` | `ValidateModule` | `iacservice:ValidateModule` |
| `terraform_runtime_online.sh` | `ExecuteTerraformPlan` | `iacservice:ExecuteTerraformPlan` |
| `terraform_runtime_online.sh` | `ExecuteTerraformApply` | `iacservice:ExecuteTerraformApply` |
| `terraform_runtime_online.sh` | `ExecuteTerraformDestroy` | `iacservice:ExecuteTerraformDestroy` |
| `terraform_runtime_online.sh` | `GetExecuteState` | `iacservice:GetExecuteState` |

## How to Attach Policies

### Option 1: Creating Custom Policy (Recommended — Least Privilege)

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Permissions** > **Policies**
3. Click **Create Policy**
4. Select **Script** mode
5. Copy and paste the JSON policy from "Detailed API-Level Permissions" above
6. Name the policy: `AlibabaCloudSolutionDeploySkillPolicy`
7. Click **OK** to create
8. Navigate to **Identities** > **Users**
9. Find your RAM user and click **Add Permissions**
10. Select **Custom Policy** and choose `AlibabaCloudSolutionDeploySkillPolicy`
11. Click **OK** to attach

### Permission Verification

```bash
# Verify STS access
aliyun sts GetCallerIdentity --user-agent AlibabaCloud-Agent-Skills

# Verify OpenAPI Explorer access (search for any API)
python3 scripts/search_apis.py 'DescribeInstances'

# Verify IaCService access (validate empty module)
bash scripts/terraform_runtime_online.sh validate 'resource "null_resource" "test" {}'
```

## Common Permission Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `Forbidden.RAM` | RAM user lacks permission for the action | Attach the custom policy above |
| `InvalidAccessKeyId.NotFound` | Access Key ID invalid | Verify credentials via `aliyun configure list` |
| `NoPermission` | No permission for the resource | Check policy is correctly attached |

# Terraform Online Runtime — Usage Guide

Execute Terraform configurations remotely through Alibaba Cloud's IaCService using a single pre-built script. No local `terraform` CLI required.

## Prerequisites

- **aliyun CLI** (v3.2+) installed and configured with valid AK/SK credentials (`aliyun configure`)
- The credentials must have permission to call IaCService APIs and to manage whatever cloud resources the Terraform code declares

## SKILL_DIR Setup

Before running the script, set `SKILL_DIR` to the directory containing the skill's SKILL.md:

```bash
# Option A: dynamic (for use inside shell scripts)
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Option B: explicit absolute path
SKILL_DIR="/path/to/your-skill-dir"

TF="${SKILL_DIR}/scripts/terraform_runtime_online.sh"
```

## Commands

```
terraform_runtime_online.sh validate <hcl_file_or_code>
terraform_runtime_online.sh plan     <hcl_file_or_code> [existing_state_id]
terraform_runtime_online.sh apply    <hcl_file_or_code> [--state-id <id>]
terraform_runtime_online.sh apply    --state-id <id>
terraform_runtime_online.sh destroy  <state_id>
terraform_runtime_online.sh poll     <state_id> [max_attempts] [interval_seconds]
```

## Command Usage

### validate — Validate HCL syntax

```bash
$TF validate main.tf
$TF validate 'resource "alicloud_vpc" "vpc" { vpc_name = "test" cidr_block = "172.16.0.0/12" }'
```

Exit codes: `0` = Valid, `1` = Invalid / error.

### plan — Preview changes

```bash
plan_output=$($TF plan main.tf)
STATE_ID=$(echo "$plan_output" | grep '^STATE_ID=' | cut -d= -f2)
PLAN_FILE=$(echo "$plan_output" | grep '^PLAN_OUTPUT_FILE=' | cut -d= -f2)
# Compact plan summary is printed to stderr automatically.
# To view full details: cat "$PLAN_FILE"
```

Exit codes: `0` = Planned, `1` = Errored.

### apply — Create or update infrastructure

```bash
# Fresh apply (no prior state)
STATE_ID=$($TF apply main.tf | grep '^STATE_ID=' | cut -d= -f2)
echo "STATE_ID=$STATE_ID" >> terraform_state_ids.env

# Incremental update against existing state
STATE_ID=$($TF apply updated.tf --state-id "$EXISTING_STATE_ID" | grep '^STATE_ID=' | cut -d= -f2)
echo "STATE_ID=$STATE_ID" >> terraform_state_ids.env
```

Exit codes: `0` = Applied, `1` = Errored.

### destroy — Destroy resources

```bash
$TF destroy "$STATE_ID" --force
```

Without `--force`, the script lists resources and exits without destroying (safety pre-check). Always pass `--force` after confirming with the user.

Exit codes: `0` = Destroyed, `1` = Failed or not confirmed.

### poll — Poll status (standalone use)

```bash
$TF poll <state_id> [max_attempts] [interval_seconds]
```

## Workflow Patterns

### Pattern 1: Full lifecycle (plan → confirm → apply → destroy)

```bash
# 1. Write HCL
cat > main.tf << 'EOF'
resource "alicloud_vpc" "vpc" {
  vpc_name   = "my-vpc"
  cidr_block = "172.16.0.0/12"
}
EOF

# 2. Plan
plan_output=$($TF plan main.tf)
PLAN_FILE=$(echo "$plan_output" | grep '^PLAN_OUTPUT_FILE=' | cut -d= -f2)
# ⚠️ STOP — present plan summary to user and wait for explicit confirmation before continuing

# 3. Apply (fresh apply with code; do NOT reuse the plan STATE_ID)
STATE_ID=$($TF apply main.tf | grep '^STATE_ID=' | cut -d= -f2)
echo "STATE_ID=$STATE_ID" >> terraform_state_ids.env

# 4. Destroy when done
$TF destroy "$STATE_ID" --force
```

### Pattern 2: Quick apply (skip plan)

```bash
STATE_ID=$($TF apply main.tf | grep '^STATE_ID=' | cut -d= -f2)
echo "STATE_ID=$STATE_ID" >> terraform_state_ids.env
```

### Pattern 3: Incremental update

```bash
STATE_ID=$($TF apply updated.tf --state-id "$EXISTING_STATE_ID" | grep '^STATE_ID=' | cut -d= -f2)
```

### Pattern 4: Validate before deploy

```bash
$TF validate main.tf && echo "Validation passed"
```

## Critical Rules

- **ALWAYS use `$TF <command>`** — never write inline `aliyun iacservice` commands; inline commands silently fail due to argument/endpoint quirks
- **ALWAYS save every `STATE_ID`** returned by apply to a file (e.g., `terraform_state_ids.env`) for later cleanup
- **After `plan`, ALWAYS wait for user confirmation** before calling `apply`
- **After plan, use fresh apply** (`$TF apply <code>`), NOT `--state-id` from the plan run — IaCService locks plan stateIds

## Error Reference

| Error | Likely Cause |
|-------|-------------|
| `InvalidOperation.TaskStatus` | Plan stateId is locked — use fresh apply with code instead |
| `Your account does not have enough balance` | Insufficient balance for postpaid resources |
| `InvalidAccessKeyId` | AK/SK credentials are invalid or expired |
| `InvalidImageId.NotFound` | Image ID doesn't exist in the target region |
| Provider/resource errors | Unsupported resource types or invalid arguments |

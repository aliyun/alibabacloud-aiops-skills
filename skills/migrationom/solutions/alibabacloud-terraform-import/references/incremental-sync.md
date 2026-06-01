# Incremental Sync Procedures

Detailed procedures for detecting Alibaba Cloud resource changes and syncing to Terraform.

---

## Three Types of Changes

| Change Type | Description | Detection Method | Handling |
|---------|------|---------|---------|
| New resources | Exist in cloud, not in state | Compare API list vs state list | Generate HCL + terraform import |
| Deleted resources | Exist in state, not in cloud | Run existence check for each resource in state | terraform state rm |
| Configuration drift | Exist in both, but config differs | terraform plan -refresh=true | Update HCL or terraform apply |

---

## Detecting New Resources

### ECS Instances

```bash
REGION="cn-hangzhou"

# Get managed ECS IDs from state
STATE_IDS=$(terraform state list | grep "^alicloud_instance\." | \
  xargs -I{} terraform state show {} 2>/dev/null | \
  grep '"id"' | awk '{print $3}' | tr -d '",')

# Get all current ECS IDs from cloud
CLOUD_IDS=$(aliyun ecs describe-instances --biz-region-id $REGION --page-size 100 \
  --output cols=InstanceId rows=Instances.Instance 2>/dev/null | tail -n +2)

# Find difference set (in cloud but not in state)
echo "=== Unmanaged ECS Instances ==="
for id in $CLOUD_IDS; do
  if ! echo "$STATE_IDS" | grep -q "$id"; then
    # Get instance name
    name=$(aliyun ecs describe-instances --biz-region-id $REGION \
      --InstanceIds "[\"$id\"]" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(d['Instances']['Instance'][0].get('InstanceName','unknown'))" 2>/dev/null)
    echo "  $id ($name)"
  fi
done
```

### VPC

```bash
# Get managed VPC IDs from state
STATE_VPC=$(terraform state list | grep "^alicloud_vpc\." | \
  xargs -I{} terraform state show {} 2>/dev/null | \
  grep '"id"' | awk '{print $3}' | tr -d '",')

# Get all VPC IDs from cloud
CLOUD_VPC=$(aliyun vpc describe-vpcs --biz-region-id $REGION --page-size 50 \
  --output cols=VpcId rows=Vpcs.Vpc 2>/dev/null | tail -n +2)

echo "=== Unmanaged VPCs ==="
for id in $CLOUD_VPC; do
  if ! echo "$STATE_VPC" | grep -q "$id"; then
    echo "  $id"
  fi
done
```

### Generic Detection Script

```python
#!/usr/bin/env python3
"""Detect unmanaged Alibaba Cloud resources"""
import subprocess
import json
import sys

REGION = "cn-hangzhou"

RESOURCE_CHECKS = [
    {
        "tf_type": "alicloud_instance",
        "api_cmd": f"aliyun ecs describe-instances --biz-region-id {REGION} --page-size 100",
        "id_path": "Instances.Instance[].InstanceId",
        "name_path": "Instances.Instance[].InstanceName",
    },
    {
        "tf_type": "alicloud_vpc",
        "api_cmd": f"aliyun vpc describe-vpcs --biz-region-id {REGION} --page-size 50",
        "id_path": "Vpcs.Vpc[].VpcId",
        "name_path": "Vpcs.Vpc[].VpcName",
    },
    {
        "tf_type": "alicloud_db_instance",
        "api_cmd": f"aliyun rds describe-db-instances --biz-region-id {REGION} --page-size 50",
        "id_path": "Items.DBInstance[].DBInstanceId",
        "name_path": "Items.DBInstance[].DBInstanceDescription",
    },
]

def get_state_ids(tf_type):
    result = subprocess.run(
        ["terraform", "state", "list"],
        capture_output=True, text=True
    )
    resources = [r for r in result.stdout.strip().split("\n") if r.startswith(f"{tf_type}.")]
    ids = set()
    for r in resources:
        show = subprocess.run(
            ["terraform", "state", "show", r],
            capture_output=True, text=True
        )
        for line in show.stdout.split("\n"):
            if '"id"' in line and "=" in line:
                ids.add(line.split("=")[1].strip().strip('"'))
    return ids

def get_cloud_ids(api_cmd, id_path):
    result = subprocess.run(api_cmd.split(), capture_output=True, text=True)
    data = json.loads(result.stdout)
    # Simplified path parsing
    parts = id_path.split(".")
    current = data
    for part in parts:
        if "[]" in part:
            key = part.replace("[]", "")
            current = [item[key] for item in current.get(key, [])]
            break
        current = current.get(part, {})
    return set(current) if isinstance(current, list) else set()

for check in RESOURCE_CHECKS:
    state_ids = get_state_ids(check["tf_type"])
    cloud_ids = get_cloud_ids(check["api_cmd"], check["id_path"])
    new_ids = cloud_ids - state_ids
    removed_ids = state_ids - cloud_ids

    if new_ids:
        print(f"\n[New] {check['tf_type']}:")
        for id in new_ids:
            print(f"  + {id}")

    if removed_ids:
        print(f"\n[Deleted] {check['tf_type']}:")
        for id in removed_ids:
            print(f"  - {id}")
```

---

## Detecting Deleted Resources

```bash
# Check existence of each ECS instance in state
echo "=== Checking if ECS instances in state still exist ==="
terraform state list | grep "^alicloud_instance\." | while read resource; do
  instance_id=$(terraform state show "$resource" 2>/dev/null | \
    grep '"id"' | head -1 | awk '{print $3}' | tr -d '",')

  if [ -n "$instance_id" ]; then
    result=$(aliyun ecs describe-instances --biz-region-id $REGION \
      --InstanceIds "[\"$instance_id\"]" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['Instances']['Instance']))" 2>/dev/null)

    if [ "$result" = "0" ]; then
      echo "  Deleted: $resource ($instance_id)"
      echo "  Run: terraform state rm $resource"
    fi
  fi
done
```

---

## Detecting Configuration Drift

```bash
# Refresh state and detect drift
terraform plan -refresh=true -out=drift.tfplan 2>&1

# View drift details
terraform show drift.tfplan 2>&1

# View only changed resources
terraform plan -refresh=true 2>&1 | grep -A5 "will be updated"
```

---

## Incremental Sync Workflow

```bash
#!/bin/bash
# incremental-sync.sh - Incremental sync script

set -e
REGION="${ALICLOUD_REGION:-cn-hangzhou}"
WORK_DIR="${1:-$(pwd)}"

cd "$WORK_DIR"

echo "=== Alibaba Cloud Terraform Incremental Sync ==="
echo "Region: $REGION"
echo "Working directory: $WORK_DIR"
echo ""

# Step 1: Detect configuration drift
echo "--- Step 1: Detecting configuration drift ---"
terraform plan -refresh=true -out=/tmp/drift.tfplan 2>&1
PLAN_EXIT=$?

if [ $PLAN_EXIT -eq 0 ]; then
  echo "No configuration drift detected"
elif [ $PLAN_EXIT -eq 2 ]; then
  echo "! Configuration drift detected, see plan output above"
  echo "  Option 1: Update HCL to match cloud state"
  echo "  Option 2: terraform apply to update cloud resources to match HCL"
fi

# Step 2: Detect new resources (ECS example)
echo ""
echo "--- Step 2: Detecting new resources ---"

STATE_ECS=$(terraform state list 2>/dev/null | grep "^alicloud_instance\." | wc -l | tr -d ' ')
CLOUD_ECS=$(aliyun ecs describe-instances --biz-region-id $REGION --page-size 100 \
  --output cols=InstanceId rows=Instances.Instance 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')

echo "ECS count in state: $STATE_ECS"
echo "ECS count in cloud: $CLOUD_ECS"

if [ "$CLOUD_ECS" -gt "$STATE_ECS" ]; then
  echo "! Found $((CLOUD_ECS - STATE_ECS)) unmanaged ECS instances"
  echo "  Run detection script for details..."
fi

# Step 3: Detect deleted resources
echo ""
echo "--- Step 3: Detecting deleted resources ---"
echo "Checking if resources in state still exist..."
# (Call the existence check logic above here)

echo ""
echo "=== Sync complete ==="
```

---

## Periodic Sync Recommendations

### Manual Periodic Checks

Recommended to run incremental sync checks weekly:

```bash
# Check every Monday at 9am
# Add to crontab (crontab -e):
# 0 9 * * 1 cd /path/to/terraform && bash incremental-sync.sh >> /var/log/tf-sync.log 2>&1
```

### CI/CD Integration

**GitHub Actions example**:

```yaml
# .github/workflows/tf-drift-check.yml
name: Terraform Drift Check

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9am
  workflow_dispatch:

jobs:
  drift-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: "~1.9"

      - name: Terraform Init
        run: terraform init
        env:
          ALICLOUD_ACCESS_KEY_ID: ${{ secrets.ALICLOUD_AK }}
          ALICLOUD_SECRET_ACCESS_KEY: ${{ secrets.ALICLOUD_SK }}

      - name: Check Drift
        run: terraform plan -refresh=true -detailed-exitcode
        env:
          ALICLOUD_ACCESS_KEY_ID: ${{ secrets.ALICLOUD_AK }}
          ALICLOUD_SECRET_ACCESS_KEY: ${{ secrets.ALICLOUD_SK }}
        continue-on-error: true

      - name: Notify on Drift
        if: steps.drift.outcome == 'failure'
        run: echo "Configuration drift detected, please check plan output"
        # Can be replaced with DingTalk/Feishu/Slack notification
```

---

## Sync Strategy Selection

| Strategy | Use Case | Risk |
|------|---------|------|
| Detect only, no auto-fix | Production environment, requires manual review | Low |
| Auto-import new resources | Frequent resource changes, well-disciplined team | Medium |
| Auto-apply drift fixes | Strict IaC management, no manual operations allowed | High |

**Recommendation**: Use "detect only" strategy for production environments; execute import/apply manually after PR review.

---

## Common Incremental Sync Issues

**Q: terraform plan shows many changes, but resources haven't actually changed**

Cause: Provider version upgrade changed attribute defaults

Fix:
```bash
# Lock provider version
terraform providers lock
# Or specify exact version in required_providers
version = "= 1.220.0"
```

**Q: Newly imported resource still has diff in plan**

Cause: HCL template doesn't exactly match actual resource configuration

Fix: Refer to diff fix patterns in `references/terraform-patterns.md`

**Q: Many resources need import, manual execution is too slow**

Fix: Use batch scripts from `examples/import-commands.sh`

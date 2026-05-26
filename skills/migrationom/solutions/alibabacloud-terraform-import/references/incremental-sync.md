# 增量同步方案

检测阿里云资源变化并同步到 Terraform 的详细方案。

---

## 三类变化

| 变化类型 | 描述 | 检测方法 | 处理方式 |
|---------|------|---------|---------|
| 新增资源 | 云上有，state 没有 | 对比 API 列表 vs state list | 生成 HCL + terraform import |
| 删除资源 | state 有，云上没有 | 对 state 中每个资源做存在性检查 | terraform state rm |
| 配置漂移 | 两边都有，但配置不一致 | terraform plan -refresh=true | 更新 HCL 或 terraform apply |

---

## 检测新增资源

### ECS 实例

```bash
REGION="cn-hangzhou"

# 获取 state 中已管理的 ECS ID 列表
STATE_IDS=$(terraform state list | grep "^alicloud_instance\." | \
  xargs -I{} terraform state show {} 2>/dev/null | \
  grep '"id"' | awk '{print $3}' | tr -d '",')

# 获取云上当前所有 ECS ID
CLOUD_IDS=$(aliyun ecs describe-instances --biz-region-id $REGION --page-size 100 \
  --output cols=InstanceId rows=Instances.Instance 2>/dev/null | tail -n +2)

# 找出差集（云上有但 state 没有）
echo "=== 未纳管的 ECS 实例 ==="
for id in $CLOUD_IDS; do
  if ! echo "$STATE_IDS" | grep -q "$id"; then
    # 获取实例名称
    name=$(aliyun ecs describe-instances --biz-region-id $REGION \
      --InstanceIds "[\"$id\"]" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(d['Instances']['Instance'][0].get('InstanceName','unknown'))" 2>/dev/null)
    echo "  $id ($name)"
  fi
done
```

### VPC

```bash
# 获取 state 中已管理的 VPC ID
STATE_VPC=$(terraform state list | grep "^alicloud_vpc\." | \
  xargs -I{} terraform state show {} 2>/dev/null | \
  grep '"id"' | awk '{print $3}' | tr -d '",')

# 获取云上所有 VPC ID
CLOUD_VPC=$(aliyun vpc describe-vpcs --biz-region-id $REGION --page-size 50 \
  --output cols=VpcId rows=Vpcs.Vpc 2>/dev/null | tail -n +2)

echo "=== 未纳管的 VPC ==="
for id in $CLOUD_VPC; do
  if ! echo "$STATE_VPC" | grep -q "$id"; then
    echo "  $id"
  fi
done
```

### 通用检测脚本

```python
#!/usr/bin/env python3
"""检测未纳管的阿里云资源"""
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
    # 简化路径解析
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
        print(f"\n[新增] {check['tf_type']}:")
        for id in new_ids:
            print(f"  + {id}")

    if removed_ids:
        print(f"\n[删除] {check['tf_type']}:")
        for id in removed_ids:
            print(f"  - {id}")
```

---

## 检测删除资源

```bash
# 对 state 中每个 ECS 实例做存在性检查
echo "=== 检查 state 中的 ECS 实例是否仍存在 ==="
terraform state list | grep "^alicloud_instance\." | while read resource; do
  instance_id=$(terraform state show "$resource" 2>/dev/null | \
    grep '"id"' | head -1 | awk '{print $3}' | tr -d '",')

  if [ -n "$instance_id" ]; then
    result=$(aliyun ecs describe-instances --biz-region-id $REGION \
      --InstanceIds "[\"$instance_id\"]" 2>/dev/null | \
      python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['Instances']['Instance']))" 2>/dev/null)

    if [ "$result" = "0" ]; then
      echo "  已删除: $resource ($instance_id)"
      echo "  执行: terraform state rm $resource"
    fi
  fi
done
```

---

## 检测配置漂移

```bash
# 刷新 state 并检测漂移
terraform plan -refresh=true -out=drift.tfplan 2>&1

# 查看漂移详情
terraform show drift.tfplan 2>&1

# 仅查看有变更的资源
terraform plan -refresh=true 2>&1 | grep -A5 "will be updated"
```

---

## 增量同步工作流

```bash
#!/bin/bash
# incremental-sync.sh - 增量同步脚本

set -e
REGION="${ALICLOUD_REGION:-cn-hangzhou}"
WORK_DIR="${1:-$(pwd)}"

cd "$WORK_DIR"

echo "=== 阿里云 Terraform 增量同步 ==="
echo "Region: $REGION"
echo "工作目录: $WORK_DIR"
echo ""

# Step 1: 检测配置漂移
echo "--- Step 1: 检测配置漂移 ---"
terraform plan -refresh=true -out=/tmp/drift.tfplan 2>&1
PLAN_EXIT=$?

if [ $PLAN_EXIT -eq 0 ]; then
  echo "✓ 无配置漂移"
elif [ $PLAN_EXIT -eq 2 ]; then
  echo "! 发现配置漂移，请查看上方 plan 输出"
  echo "  选项 1: 更新 HCL 使其与云上一致"
  echo "  选项 2: terraform apply 将云上资源更新为 HCL 定义的状态"
fi

# Step 2: 检测新增资源（以 ECS 为例）
echo ""
echo "--- Step 2: 检测新增资源 ---"

STATE_ECS=$(terraform state list 2>/dev/null | grep "^alicloud_instance\." | wc -l | tr -d ' ')
CLOUD_ECS=$(aliyun ecs describe-instances --biz-region-id $REGION --page-size 100 \
  --output cols=InstanceId rows=Instances.Instance 2>/dev/null | tail -n +2 | wc -l | tr -d ' ')

echo "State 中 ECS 数量: $STATE_ECS"
echo "云上 ECS 数量: $CLOUD_ECS"

if [ "$CLOUD_ECS" -gt "$STATE_ECS" ]; then
  echo "! 发现 $((CLOUD_ECS - STATE_ECS)) 个未纳管的 ECS 实例"
  echo "  运行检测脚本获取详情..."
fi

# Step 3: 检测删除资源
echo ""
echo "--- Step 3: 检测删除资源 ---"
echo "检查 state 中的资源是否仍存在..."
# （此处调用上面的存在性检查逻辑）

echo ""
echo "=== 同步完成 ==="
```

---

## 定期同步建议

### 手动定期检查

建议每周执行一次增量同步检查：

```bash
# 每周一上午 9 点检查
# 在 crontab 中添加（crontab -e）：
# 0 9 * * 1 cd /path/to/terraform && bash incremental-sync.sh >> /var/log/tf-sync.log 2>&1
```

### 与 CI/CD 集成

**GitHub Actions 示例**：

```yaml
# .github/workflows/tf-drift-check.yml
name: Terraform Drift Check

on:
  schedule:
    - cron: '0 9 * * 1'  # 每周一 9 点
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
        run: echo "发现配置漂移，请检查 plan 输出"
        # 可替换为发送钉钉/飞书/Slack 通知
```

---

## 同步策略选择

| 策略 | 适用场景 | 风险 |
|------|---------|------|
| 只检测，不自动修复 | 生产环境，需要人工审核 | 低 |
| 自动 import 新增资源 | 资源变化频繁，团队规范好 | 中 |
| 自动 apply 漂移修复 | 严格 IaC 管理，禁止手动操作 | 高 |

**推荐**：生产环境使用"只检测"策略，通过 PR 审核后再手动执行 import/apply。

---

## 常见增量同步问题

**Q: terraform plan 显示大量变更，但资源没有实际变化**

原因：provider 版本升级导致属性默认值变化

处理：
```bash
# 锁定 provider 版本
terraform providers lock
# 或在 required_providers 中指定精确版本
version = "= 1.220.0"
```

**Q: 新增资源 import 后 plan 仍有 diff**

原因：HCL 模板与实际资源配置不完全一致

处理：参考 `references/terraform-patterns.md` 中的 diff 修复模式

**Q: 大量资源需要 import，手动执行太慢**

处理：使用 `examples/import-commands.sh` 中的批量脚本

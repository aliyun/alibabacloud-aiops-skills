# Acceptance Criteria -- alibabacloud-ecs-disaster-recovery-image

**Scenario**: ECS cross-AZ disaster recovery -- create a backup instance in a different availability zone using a whole-instance image
**Purpose**: Acceptance criteria for the Skill, with correct vs. incorrect patterns

---

## 1. CLI Product Name

#### CORRECT
- `aliyun ecs ...` -- ECS product
- `aliyun vpc ...` -- VPC product

#### INCORRECT
- `aliyun ECS ...` -- Uppercase product names do not exist
- `aliyun ec2 ...` -- Not an Alibaba Cloud product code

## 2. CLI Action Names -- must use plugin mode (hyphenated)

#### CORRECT
| Command | Description |
|---------|-------------|
| `aliyun ecs describe-instances` | Query instances |
| `aliyun ecs describe-disks` | Query disks |
| `aliyun ecs create-image` | Create an image |
| `aliyun ecs describe-images` | Query images |
| `aliyun ecs describe-available-resource` | Query available resources |
| `aliyun ecs describe-vswitches` | Query VSwitches |
| `aliyun ecs run-instances` | Create instances |
| `aliyun vpc create-vswitch` | Create a VSwitch |

#### INCORRECT
- `aliyun ecs DescribeInstances` -- PascalCase is the legacy API style, not plugin mode
- `aliyun ecs describe_instances` -- Underscore separators are not supported
- `aliyun ecs CreateImage` -- Wrong CamelCase

## 3. Region and Endpoint Parameters

#### CORRECT
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-beijing \
  --endpoint ecs.cn-beijing.aliyuncs.com \
  --instance-ids '["i-xxx"]'
```

#### INCORRECT
```bash
# Using --region-id (wrong parameter name)
aliyun ecs describe-instances --region-id cn-beijing ...

# Omitting endpoint when calling outside the default region
# (request may be silently routed to the default region and return empty)
aliyun ecs describe-instances --biz-region-id cn-beijing ...
```

## 4. `--user-agent` Flag -- required on every API call

#### CORRECT
```bash
aliyun ecs describe-instances \
  --biz-region-id cn-beijing \
  --endpoint ecs.cn-beijing.aliyuncs.com \
  --instance-ids '["i-xxx"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

#### INCORRECT -- do NOT use the deprecated global ai-mode
```bash
# Don't! It pollutes the user's global CLI configuration
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/..."
aliyun configure ai-mode disable
```

#### INCORRECT -- do NOT use exported environment variables
```bash
# Don't! Environment variables are lost across separate bash invocations
# in multi-agent clients
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/..."
```

## 5. `create-image` Usage

#### CORRECT -- whole-instance image (includes all data disks)
```bash
aliyun ecs create-image \
  --biz-region-id cn-beijing \
  --endpoint ecs.cn-beijing.aliyuncs.com \
  --instance-id i-xxx \
  --image-name "Create_from_i-xxx" \
  --description "System image for AZ disaster recovery" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

#### INCORRECT
- Creating from a single `SnapshotId` only (loses data disk mappings, so data disks are missing after cross-zone restore)
- Manually stopping the source instance before creation (`create-image` supports Running instances; no stop required)

## 6. `run-instances` Data Disk Parameter -- `Device=` vs `SnapshotId=`

#### CORRECT -- use `Device=` to override Category/PL of disks already in the image
```bash
aliyun ecs run-instances \
  --biz-region-id cn-beijing \
  --endpoint ecs.cn-beijing.aliyuncs.com \
  --zone-id cn-beijing-l \
  --image-id m-xxx \
  --instance-type ecs.u1-c1m2.xlarge \
  --vswitch-id vsw-xxx \
  --security-group-id sg-xxx \
  --instance-charge-type PostPaid \
  --internet-charge-type PayByTraffic \
  --internet-max-bandwidth-out 0 \
  --system-disk-category cloud_essd \
  --system-disk-size 40 \
  --system-disk-performance-level PL0 \
  --data-disk Device=/dev/xvdb Category=cloud_essd Size=120 PerformanceLevel=PL0 \
  --amount 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

#### INCORRECT -- `SnapshotId=` creates an **extra** disk
```bash
# Wrong: creates an additional disk on top of the disks auto-restored from the image
--data-disk SnapshotId=s-xxx Category=cloud_essd Size=120 PerformanceLevel=PL0
```

#### INCORRECT -- `--data-disk-N-*` form (does not support PL)
```bash
# Wrong: this form does not support PerformanceLevel and causes PL to fall back
# to the default
--data-disk-1-category cloud_essd \
--data-disk-1-size 120 \
--data-disk-1-performance-level PL0   # this parameter does not exist
```

## 7. System Disk PerformanceLevel -- must be explicit

#### CORRECT
```bash
--system-disk-category cloud_essd \
--system-disk-size 40 \
--system-disk-performance-level PL0
```

#### INCORRECT -- omitting `--system-disk-performance-level`
**Symptom**: The new instance's system disk PL takes the instance-type default and may not match the source (e.g., PL0 -> PL1 or vice versa).

> Only the cloud_essd family supports PL. For categories that do not support PL (e.g., `cloud_auto`, `cloud_essd_entry`), omit this parameter.

## 8. Network and Billing Parameters -- must reuse source values

#### CORRECT
- `--instance-charge-type` reuses the source instance value collected in Step 1
- `--internet-charge-type` reuses the source instance value
- `--internet-max-bandwidth-out` reuses the source instance value

#### INCORRECT -- hard-coded defaults
```bash
# Wrong: hard-coding PostPaid / PayByTraffic / 0 may diverge from the source
--instance-charge-type PostPaid \
--internet-charge-type PayByTraffic \
--internet-max-bandwidth-out 0
```

Correct approach: read the values from the Step 1 `describe-instances` result and reuse them.

## 9. Credential Check -- never read or print AK/SK

#### CORRECT
```bash
aliyun configure list
```

#### INCORRECT
```bash
echo $ALIBABA_CLOUD_ACCESS_KEY_ID            # never echo
aliyun configure get access-key-secret        # never read the secret
aliyun configure set --access-key-id LTAI...  # never pass literal credentials in-session
```

## 10. AskUserQuestion -- every decision point must offer clickable options

#### CORRECT
- Every user decision point (zone selection, instance-type selection, whether to create a VSwitch, whether to substitute disk types) uses `AskUserQuestion` with 2-4 clickable options; the recommended option is placed first and tagged `(Recommended)`

#### INCORRECT
- Auto-substituting instance types, disk types, or zones
- Asking open-ended questions for free-form text input (unless an "Other / Custom" option is offered)

---

## Validation Checklist

After generation, verify each item:

- [ ] All `aliyun` commands use plugin mode (hyphenated)
- [ ] All API commands carry `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}`
- [ ] Cross-default-region commands all include `--endpoint`
- [ ] No occurrences of `aliyun configure ai-mode` or `export ALIBABA_CLOUD_USER_AGENT`
- [ ] `--data-disk` uses `Device=`; no `SnapshotId=` or `--data-disk-N-*`
- [ ] `--system-disk-performance-level` is explicit (cloud_essd family)
- [ ] Network / billing / bandwidth parameters all reuse source instance values
- [ ] Credential check uses `aliyun configure list` only
- [ ] Every decision point uses `AskUserQuestion` with clickable options

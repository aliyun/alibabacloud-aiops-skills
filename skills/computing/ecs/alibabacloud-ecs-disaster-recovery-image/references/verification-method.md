# Verification Method -- alibabacloud-ecs-disaster-recovery-image

After each step, run the verification commands below to confirm the state is correct. All commands MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}`.

## Step 1 verification: source instance info has been collected

After running `describe-instances`, confirm all of the following fields are recorded:

| Field | Required | Description |
|-------|----------|-------------|
| `RegionId` | Yes | Source instance region |
| `ZoneId` | Yes | Source instance availability zone |
| `InstanceType` | Yes | Instance type |
| `ImageId` / `OSName` | Yes | Operating system |
| `VpcAttributes.VpcId` | Yes | VPC of the instance |
| `VpcAttributes.VSwitchId` | Yes | Current VSwitch |
| `SecurityGroupIds.SecurityGroupId` | Yes | Security group |
| `InstanceChargeType` | Yes | Instance billing mode |
| `InternetChargeType` | Yes | Internet billing mode |
| `InternetMaxBandwidthOut` | Yes | Outbound bandwidth (Mbps) |

After `describe-disks`, confirm the following are collected:
- For each disk: `DiskId`, `Type` (system/data), `Category`, `Size`, `Device`, `PerformanceLevel`

## Step 2 verification: image creation request accepted

Receiving an `ImageId` from `create-image` indicates the request has been accepted. Sanity check:

```bash
aliyun ecs describe-images \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --image-id <image-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Expected: returned `Images.Image[0].Status` is `Creating`, and `Progress` shows a percentage.

## Step 3 verification: image is ready

The image's final status must be `Available`:

```bash
aliyun ecs describe-images \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --image-id <image-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Expected:
- `Images.Image[0].Status == "Available"`
- `Progress == "100%"`
- `Images.Image[0].DiskDeviceMappings.DiskDeviceMapping` array length equals the number of disks on the source instance
- The system disk and each data disk's Device path matches the source

## Step 4 verification: target zone can host the new instance

```bash
aliyun ecs describe-available-resource \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --zone-id <target-zone> \
  --destination-resource InstanceType \
  --instance-type <instance-type> \
  --instance-charge-type PostPaid \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Expected: returned `AvailableZones.AvailableZone[0].Status == "Available"` and `StatusCategory == "WithStock"`.

VSwitch verification:

```bash
aliyun ecs describe-vswitches \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --vpc-id <vpc-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Expected: a VSwitch with `ZoneId == <target-zone>` exists in the result (otherwise `create-vswitch` is required).

## Step 5 verification: new instance created successfully

`run-instances` returns `InstanceIdSets.InstanceIdSet`. Extract the new instance ID, then immediately query:

```bash
aliyun ecs describe-instances \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-ids '["<new-instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Expected: the first response shows `Status` as `Pending` or `Starting`; poll until it becomes `Running`.

## Step 6 verification: new instance matches the source

### 6.1 Instance state

```bash
aliyun ecs describe-instances \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-ids '["<new-instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Confirm each item:
- `Status == "Running"`
- `ZoneId == <target-zone>`
- `InstanceType == <expected-instance-type>`
- `VpcAttributes.PrivateIpAddress.IpAddress[0]` is assigned
- `InstanceChargeType` / `InternetChargeType` / `InternetMaxBandwidthOut` match the source

### 6.2 Disk consistency

```bash
aliyun ecs describe-disks \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-id <new-instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Compare each disk:

| Field | Source | New | Verification |
|-------|--------|-----|--------------|
| Disk count | N | N | Must match |
| System disk Category | (source) | (new) | Must match |
| System disk Size | (source) | (new) | Must match |
| System disk PerformanceLevel | (source) | (new) | Must match (cloud_essd family) |
| Data disk Device | (source) | (new) | Path must match (e.g., /dev/xvdb) |
| Data disk Category | (source) | (new) | Must match |
| Data disk Size | (source) | (new) | Must match |
| Data disk PerformanceLevel | (source) | (new) | Must match |

If any field does not match, notify the user and explain why (zone unsupported / user-initiated change / configuration error, etc.).

## Overall Success Criteria

| Criterion | Standard |
|-----------|----------|
| Image creation | Status `Available`, contains all source disk mappings |
| New instance creation | Status `Running`, private IP assigned |
| Zone switch | New instance `ZoneId` != source `ZoneId`, `RegionId` is the same |
| Disk recovery | Each disk's Category / Size / PerformanceLevel matches the source |
| Network/billing | InstanceChargeType, InternetChargeType, InternetMaxBandwidthOut match the source |
| Source instance integrity | Source instance remains in its original state (not stopped / released / modified) |

Once every criterion is satisfied, present the comparison table to the user and report that the disaster recovery backup is complete.

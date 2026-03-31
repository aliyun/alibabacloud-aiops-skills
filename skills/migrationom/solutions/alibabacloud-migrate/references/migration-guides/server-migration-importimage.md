# Server Migration: EC2 → ECS via AMI Export + ImportImage

Agent-free migration approach: export EC2 AMI to S3, transfer to OSS, import as ECS custom image, then provision ECS with Terraform. No agent installation on the source server required.

## 1. Overview

```
AWS                                     Alibaba Cloud
──────────────────────────────────────  ────────────────────────────────
EC2 Instance
  │
  ▼  aws ec2 export-image
AMI (.vmdk / .vhd)
  │
  ▼  stored in S3
S3 Bucket ──── ossutil / Data Online ──→ OSS Bucket
                   Migration               │
                                           ▼  aliyun ecs ImportImage
                                       ECS Custom Image
                                           │
                                           ▼  Terraform
                                       ECS Instance
```

**Supported image formats**: VHD, VMDK, RAW, QCOW2  
**Supported OS**: Linux (all mainstream distros), Windows Server 2008+  
**System disk limit**: ≤ 500 GB

## 2. Prerequisites

### 2.1 AWS Side Requirements

- AWS CLI configured with permissions: `ec2:ExportImage`, `ec2:DescribeExportImageTasks`, `s3:GetObject`, `s3:PutObject`
- An S3 bucket to store the exported AMI

### 2.2 Alibaba Cloud RAM Permissions

Attach to the RAM user performing migration:
- `AliyunOSSFullAccess` — upload image file to OSS
- `AliyunECSFullAccess` — import image and create ECS

See [references/ram-policies.md](../ram-policies.md) for minimum custom policy.

### 2.3 Parameter Confirmation

Confirm the following before starting (per [SKILL Parameter Confirmation rules](../../SKILL.md)):

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `SourceRegion` | Yes | AWS source region | `us-east-1` |
| `TargetRegionId` | Yes | Alibaba Cloud target region | `cn-hangzhou` |
| `S3BucketName` | Yes | S3 bucket to store exported AMI | `my-ami-exports` |
| `OSSBucketName` | Yes | OSS bucket to store image file | `my-image-imports` |
| `ImageName` | Yes | Name for the imported ECS image | `aws-migrated-ubuntu22` |
| `InstanceType` | Yes | Target ECS instance type | `ecs.g6.large` |
| `SystemDiskSize` | Yes | System disk size (≥ source AMI disk size) | `40` |
| `DiskImageFormat` | No | Export format: `VHD` or `VMDK` | `VHD` |

## 3. Step 1: Export EC2 AMI to S3

### 3.1 Create AMI from Running EC2 (if not already done)

```bash
# Create AMI snapshot of the source EC2 instance
AMI_ID=$(aws ec2 create-image \
  --instance-id <ec2-instance-id> \
  --name "migration-$(date +%Y%m%d)" \
  --no-reboot \
  --region <source-region> \
  --query 'ImageId' --output text)
echo "AMI_ID=$AMI_ID"

# Wait for AMI to be available
aws ec2 wait image-available \
  --image-ids $AMI_ID \
  --region <source-region>
```

### 3.2 Grant EC2 Export Permission (S3 bucket policy)

AWS requires a service role and bucket policy for image export. Add this to the S3 bucket policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "vmie.amazonaws.com"
      },
      "Action": [
        "s3:GetBucketLocation",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:PutObject",
        "s3:GetBucketAcl"
      ],
      "Resource": [
        "arn:aws:s3:::<s3-bucket-name>",
        "arn:aws:s3:::<s3-bucket-name>/*"
      ]
    }
  ]
}
```

### 3.3 Export AMI to S3

```bash
# Export AMI as VHD (recommended — smaller file, widely supported by ImportImage)
EXPORT_TASK=$(aws ec2 export-image \
  --image-id $AMI_ID \
  --disk-image-format VHD \
  --s3-export-location S3Bucket=<s3-bucket-name>,S3Prefix=exports/ \
  --region <source-region> \
  --query 'ExportImageTaskId' --output text)
echo "EXPORT_TASK=$EXPORT_TASK"
```

### 3.4 Monitor Export Progress

```bash
# Poll until status = completed (may take 30 min – 2 hours for large disks)
aws ec2 describe-export-image-tasks \
  --export-image-task-ids $EXPORT_TASK \
  --region <source-region> \
  --query 'ExportImageTasks[0].{Status:Status,Progress:Progress,S3Key:S3ExportLocation.S3Key}'

# Get the exported file path once complete
S3_KEY=$(aws ec2 describe-export-image-tasks \
  --export-image-task-ids $EXPORT_TASK \
  --region <source-region> \
  --query 'ExportImageTasks[0].S3ExportLocation.S3Key' --output text)
echo "S3_KEY=$S3_KEY"
# Example: exports/export-ami-xxxxxxxx.vhd
```

### 3.5 Download from S3

```bash
aws s3 cp s3://<s3-bucket-name>/$S3_KEY /tmp/migrated-image.vhd \
  --region <source-region>
```

> **Large file tip**: For images > 20 GB, use `--storage-class STANDARD` and multipart download:
> ```bash
> aws s3 cp s3://<s3-bucket-name>/$S3_KEY /tmp/migrated-image.vhd \
>   --region <source-region> \
>   --expected-size $(aws s3api head-object --bucket <s3-bucket-name> --key $S3_KEY --query ContentLength --output text)
> ```

## 4. Step 2: Create OSS Bucket and Upload Image

### 4.1 Create OSS Bucket (Terraform)

The OSS bucket must be in the **same region** as where you will run `ImportImage`.

```hcl
resource "alicloud_oss_bucket" "image_import" {
  bucket = "<oss-bucket-name>"
  acl    = "private"

  tags = {
    Purpose = "EC2 to ECS image import"
  }
}
```

Apply via IaCService:
```bash
$TF apply main.tf
```

### 4.2 Upload Image to OSS (ossutil)

```bash
# Install ossutil if not present
# macOS:
brew install ossutil

# Or download:
# curl -fL --connect-timeout 10 --max-time 300 -o ossutil https://gosspublic.alicdn.com/ossutil/1.7.19/ossutil64
# chmod +x ossutil

# Configure ossutil (interactive; do not pass AK/SK on the command line)
ossutil config

# Upload (multipart for large files)
ossutil cp /tmp/migrated-image.vhd \
  oss://<oss-bucket-name>/migrated-image.vhd \
  --part-size 500 \
  -j 4 \
  --checkpoint-dir /tmp/ossutil-checkpoint

# Verify upload
ossutil stat oss://<oss-bucket-name>/migrated-image.vhd
```

> **Direct S3 → OSS transfer** (skip local download): Use [Alibaba Cloud Data Online Migration](https://mgw.console.aliyun.com/) to migrate directly from S3 to OSS without downloading locally. Especially recommended for files > 10 GB.

## 5. Step 3: Import Image to ECS

### 5.1 Import Image via CLI

```bash
aliyun ecs ImportImage \
  --RegionId <region> \
  --OSType linux \
  --Architecture x86_64 \
  --ImageName "<image-name>" \
  --Description "Imported from AWS EC2 AMI $AMI_ID" \
  --DiskDeviceMapping.1.Format VHD \
  --DiskDeviceMapping.1.OSSBucket <oss-bucket-name> \
  --DiskDeviceMapping.1.OSSObject migrated-image.vhd \
  --DiskDeviceMapping.1.DiskImSize <system-disk-size-gb> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Response:**
```json
{
  "ImageId": "m-bp1xxxxxxxxxxxxxxxxx",
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

Record the `ImageId`.

### 5.2 Monitor Import Progress

```bash
# Poll until Status = Available (may take 10–60 min depending on image size)
aliyun ecs DescribeImages \
  --RegionId <region> \
  --ImageId <image-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Image Status Values:**

| Status | Meaning | Action |
|--------|---------|--------|
| `Creating` | Import in progress | Keep polling |
| `Available` | Import complete | Proceed to ECS creation |
| `CreateFailed` | Import failed | Check error, see §6 |
| `Deprecated` | Image deprecated | Use a different image |

**Poll with loop:**
```bash
IMAGE_ID="<image-id>"
for i in {1..60}; do
  STATUS=$(aliyun ecs DescribeImages \
    --RegionId <region> \
    --ImageId $IMAGE_ID \
    --user-agent AlibabaCloud-Agent-Skills 2>/dev/null | \
    python3 -c "import json,sys; imgs=json.load(sys.stdin)['Images']['Image']; print(imgs[0]['Status'] if imgs else 'NotFound')")
  echo "[$i/60] Image status: $STATUS"
  [ "$STATUS" = "Available" ] && echo "Import complete!" && break
  [ "$STATUS" = "CreateFailed" ] && echo "Import FAILED!" && break
  sleep 30
done
```

### 5.3 Windows Images — Additional Setup

For Windows images, add the `Platform` parameter:

```bash
aliyun ecs ImportImage \
  --RegionId <region> \
  --OSType windows \
  --Platform "Windows Server 2019" \
  --Architecture x86_64 \
  --ImageName "<windows-image-name>" \
  --DiskDeviceMapping.1.Format VHD \
  --DiskDeviceMapping.1.OSSBucket <oss-bucket-name> \
  --DiskDeviceMapping.1.OSSObject migrated-windows.vhd \
  --DiskDeviceMapping.1.DiskImSize <size> \
  --user-agent AlibabaCloud-Agent-Skills
```

After the ECS instance starts, connect via VNC to reset the password and activate Windows. See [ECS Windows activation docs](https://www.alibabacloud.com/help/en/ecs/user-guide/activate-a-windows-server-instance) for KMS activation.

## 6. Step 4: Create ECS from Imported Image (Terraform)

Once the image status is `Available`, create ECS using Terraform:

```hcl
provider "alicloud" {
  region               = "<region>"
  configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-migrate"
}

# Reference existing network (from Phase 2)
data "alicloud_vpcs" "main" {
  name_regex = "<vpc-name>"
}

data "alicloud_vswitches" "main" {
  vpc_id = data.alicloud_vpcs.main.ids[0]
}

data "alicloud_security_groups" "main" {
  name_regex = "<sg-name>"
  vpc_id     = data.alicloud_vpcs.main.ids[0]
}

# Key Pair
resource "alicloud_ecs_key_pair" "main" {
  key_pair_name = "<key-pair-name>"
  public_key    = "<ssh-public-key>"
}

# ECS Instance from imported image
resource "alicloud_instance" "migrated" {
  instance_name        = "<instance-name>"
  instance_type        = "<ecs-instance-type>"
  image_id             = "<imported-image-id>"   # from ImportImage
  vswitch_id           = data.alicloud_vswitches.main.ids[0]
  security_groups      = [data.alicloud_security_groups.main.ids[0]]
  key_name             = alicloud_ecs_key_pair.main.key_pair_name
  system_disk_category = "cloud_essd"
  system_disk_size     = <system-disk-size>

  internet_max_bandwidth_out = 10
  internet_charge_type       = "PayByTraffic"

  tags = {
    Name         = "<instance-name>"
    MigratedFrom = "aws-ec2"
    SourceAMI    = "<ami-id>"
  }
}

output "instance_public_ip" {
  value = alicloud_instance.migrated.public_ip
}

output "instance_id" {
  value = alicloud_instance.migrated.id
}
```

Apply:
```bash
apply_output=$($TF apply main.tf)
STATE_ID=$(echo "$apply_output" | grep '^STATE_ID=' | cut -d= -f2)
echo "STATE_ID=$STATE_ID" >> terraform_state_ids.env
```

## 7. Step 5: Verify Migration

```bash
# 1. Verify instance is running
aliyun ecs DescribeInstances \
  --RegionId <region> \
  --InstanceIds '["<instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills

# 2. SSH and verify OS and data
ssh -i <key.pem> root@<public-ip> "
  uname -a
  df -h
  cat /etc/os-release
  # Verify application data exists
  ls -la /data/
"

# 3. Verify application health
curl -f --connect-timeout 5 --max-time 30 http://<public-ip>:<app-port>/health

# 4. Check system services
ssh -i <key.pem> root@<public-ip> "systemctl list-units --state=failed"
```

## 8. Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `InvalidOSSObject.NotFound` | OSS object path incorrect | Verify bucket/object names; check region matches |
| `QuotaExceed.Image` | Image quota exceeded | Delete unused custom images |
| `InvalidFormat.NotSupported` | Image format not supported | Convert to VHD/VMDK using qemu-img |
| `DiskImSizeTooSmall` | `DiskImSize` smaller than image content | Increase `DiskImSize` to match source disk |
| `InvalidOSSBucket.NotFound` | OSS bucket not found | Verify bucket exists in the **same region** as ImportImage |
| `Forbidden.RiskControl` | Account security check pending | Complete real-name authentication in console |
| `CreateFailed` (generic) | Various import errors | Check image format; re-export AMI with `--disk-image-format VHD` |
| ECS boots but network fails | AWS-specific network config | Install cloud-init or update /etc/network config on ECS |
| ECS boots but SSH fails | SSH key not in authorized_keys | Use VNC console to reset; ensure cloud-init installed |

### Format Conversion (if needed)

If the export format is not compatible, convert locally before uploading:

```bash
# Install qemu-img
brew install qemu   # macOS
# or: apt install qemu-utils

# VMDK → VHD
qemu-img convert -f vmdk -O vpc source.vmdk target.vhd

# RAW → VHD
qemu-img convert -f raw -O vpc source.img target.vhd

# Check converted image
qemu-img info target.vhd
```

## 9. Cleanup (After Migration Validated)

```bash
# 1. Delete image file from OSS (no longer needed after import)
ossutil rm oss://<oss-bucket-name>/migrated-image.vhd

# 2. Delete OSS bucket (if only used for this migration)
ossutil rm oss://<oss-bucket-name> -b

# 3. Delete imported image (only if replacing with newer version)
# NOTE: Do NOT delete while ECS instances reference it
aliyun ecs DeleteImage \
  --RegionId <region> \
  --ImageId <image-id> \
  --Force true \
  --user-agent AlibabaCloud-Agent-Skills

# 4. Delete AWS export artifacts (from S3)
aws s3 rm s3://<s3-bucket-name>/exports/ --recursive

# 5. Deregister original AMI (only after migration fully validated)
aws ec2 deregister-image --image-id $AMI_ID --region <source-region>
```

## 10. Best Practices

1. **Export as VHD**: VHD format is recommended over VMDK — smaller size and better compatibility with `ImportImage`
2. **Same region for OSS and ImportImage**: OSS bucket and `ImportImage` target region must match
3. **Disk size ≥ source**: Set `DiskImSize` to at least the source disk size (round up to nearest GB)
4. **Install cloud-init before export**: On the source EC2, ensure `cloud-init` is installed for automatic network and SSH key injection on first boot
5. **Use Data Online Migration for large images**: For images > 5 GB, use the [Alibaba Cloud Data Online Migration](https://mgw.console.aliyun.com/) service to transfer directly from S3 to OSS (avoids local storage)
6. **Keep the OSS file until ECS is validated**: Delete the OSS image file only after the ECS instance boots and passes verification
7. **Keep source EC2 running**: Do not stop/terminate the source EC2 until the ECS instance is fully validated

## 11. Transfer Path Optimization

The VHD/VMDK file produced by `aws ec2 export-image` must travel from AWS S3 to Alibaba Cloud OSS.
The transfer path you choose is the **biggest factor in total migration time**.

### 11.1 Transfer Paths Compared

| Path | Measured Speed | 2.5 GB File | Notes |
|------|---------------|-------------|-------|
| S3 (overseas) → Local (mainland China) → OSS | ~1–2 MB/s | ~30–45 min | Cross-border GFW throttling |
| S3 (overseas) → Local (mainland China) → OSS (HK/overseas) | ~3–8 MB/s | ~10–20 min | Upload to overseas OSS is faster |
| S3 → **Relay ECS (cn-hongkong)** → OSS | ~50–100 MB/s | ~1–3 min | **Recommended for production** |
| S3 → **Alibaba Cloud Data Online Migration** → OSS | ~20–50 MB/s | ~3–8 min | No relay server needed |

> **Rule of thumb**: If the image is > 1 GB and the Alibaba Cloud target region is in mainland China, always use a relay ECS (Option C) or Data Online Migration (Option D). Direct local download through mainland China is ~20–50× slower.

### 11.2 Option A: Local Machine Relay (Simple, Slowest)

Suitable only for images < 1 GB or when the local machine has a fast overseas connection.

```bash
# Step 1: Download from S3 to local disk
aws s3 cp s3://<s3-bucket>/<exported.vhd> /tmp/migrated-image.vhd \
  --region <aws-source-region>

# Step 2: Upload from local disk to OSS
aliyun oss cp /tmp/migrated-image.vhd \
  oss://<oss-bucket>/images/migrated-image.vhd \
  -e oss-<target-region>.aliyuncs.com \
  --jobs 5 --part-size 104857600 --user-agent AlibabaCloud-Agent-Skills
```

### 11.3 Option B: Relay ECS in Alibaba Cloud HK (Recommended)

A small ECS instance in `cn-hongkong` downloads from Singapore S3 at ~50–100 MB/s (same geographic area, no GFW), then uploads to mainland OSS via Alibaba Cloud's internal backbone at ~100–200 MB/s. **Total: 1–3 minutes for a 2.5 GB image.**

```bash
# --- On relay ECS (cn-hongkong) ---

# 1. Install AWS CLI on relay ECS
curl -fL --connect-timeout 10 --max-time 600 "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
unzip /tmp/awscliv2.zip -d /tmp && sudo /tmp/aws/install

# Configure AWS credentials on relay ECS
aws configure set aws_access_key_id     <AWS_ACCESS_KEY>
aws configure set aws_secret_access_key <AWS_SECRET_KEY>
aws configure set region                <aws-source-region>

# 2. Download from S3 (fast — same region/nearby)
aws s3 cp s3://<s3-bucket>/<exported.vhd> /tmp/migrated-image.vhd

# 3. Install ossutil on relay ECS
curl -fL --connect-timeout 10 --max-time 300 -o /tmp/ossutil64 https://gosspublic.alicdn.com/ossutil/1.7.19/ossutil64
chmod +x /tmp/ossutil64
/tmp/ossutil64 config -e oss-<target-region>.aliyuncs.com

# 4. Upload to OSS (fast — Alibaba Cloud internal network)
/tmp/ossutil64 cp /tmp/migrated-image.vhd \
  oss://<oss-bucket>/images/migrated-image.vhd \
  --jobs 5 --part-size 104857600

# 5. Terminate relay ECS after upload
```

**Relay ECS spec**: `ecs.u1-c1m4.large` (1 vCPU, 4 GB RAM) costs ~¥0.1/hour in cn-hongkong and is sufficient. Total relay cost is usually < ¥1 per migration.

> **Terraform snippet to provision relay ECS** (destroy after use):
> ```hcl
> resource "alicloud_instance" "relay" {
>   instance_name              = "migration-relay"
>   image_id                   = "ubuntu_22_04_x64_20G_alibase_20240424.vhd"
>   instance_type              = "ecs.u1-c1m4.large"
>   vswitch_id                 = <hk-vswitch-id>
>   security_groups            = [<hk-sg-id>]
>   internet_max_bandwidth_out = 100
>   system_disk_category       = "cloud_essd"
>   system_disk_size           = 40
> }
> ```

### 11.4 Option C: Alibaba Cloud Data Online Migration (No Relay Needed)

For images > 5 GB or when you cannot provision a relay ECS, use Alibaba Cloud's [Data Online Migration](https://mgw.console.aliyun.com/) service to pull the image directly from S3 to OSS:

1. Go to [Data Online Migration console](https://mgw.console.aliyun.com/)
2. **Create Source** → AWS S3 → enter AWS AK/SK + bucket name
3. **Create Destination** → Alibaba Cloud OSS → select target bucket
4. **Create Migration Job** → choose the VHD file as the source object
5. Monitor progress in the console (no local bandwidth consumed)

```
AWS S3 (Singapore)  ──── Alibaba internal transfer ────→  OSS (cn-hangzhou)
     No local machine involved — pure cloud-to-cloud
```

> Data Online Migration uses Alibaba Cloud's premium cross-border bandwidth. Speed is usually 20–50 MB/s. There is no additional charge beyond standard OSS PUT fees.

### 11.5 OSS Region Selection for Minimum Latency

Choose the OSS region closest to the AWS source region for Step 2 (upload), then set `ImportImage` to the same region:

| AWS Source Region | Recommended OSS Region | Reason |
|-------------------|------------------------|--------|
| `ap-southeast-1` (Singapore) | `cn-hongkong` or `ap-southeast-5` | Nearest to Singapore |
| `us-east-1` (N. Virginia) | `us-east-1` (Alibaba Cloud US East) | Same metro area |
| `eu-west-1` (Ireland) | `eu-central-1` (Frankfurt) | Nearest EU |
| `ap-northeast-1` (Tokyo) | `ap-northeast-1` (Alibaba Cloud Japan) | Same region |

> If your production workload must run in `cn-hangzhou`, use Option B (relay ECS in HK) or Option C (Data Online Migration) to first stage the image in `cn-hangzhou` OSS, then run `ImportImage` in `cn-hangzhou`.

### 11.6 Transfer Time Estimation

Use this formula to pre-estimate transfer time before starting:

```
Time (minutes) = File size (MB) / Expected speed (MB/s) / 60

Example:
  5 GB VHD via relay ECS (80 MB/s):   5120 MB / 80 MB/s / 60 = ~1 minute
  5 GB VHD via local (mainland China): 5120 MB / 1.5 MB/s / 60 = ~57 minutes
```

| Image Size | Local (mainland) | Relay ECS (HK) | Data Online Migration |
|------------|-----------------|----------------|----------------------|
| 1 GB | ~10 min | < 1 min | ~1 min |
| 5 GB | ~55 min | ~2 min | ~4 min |
| 10 GB | ~110 min | ~4 min | ~8 min |
| 50 GB | ~9 hours | ~18 min | ~40 min |

## 12. Comparison with SMC

| Aspect | ImportImage (this guide) | SMC |
|--------|--------------------------|-----|
| Agent on source | Not required | Required |
| Cross-region (overseas → mainland) | ✅ No network restriction | ⚠️ Security group whitelist (mainland IPs only by default) |
| Migration time | Longer (export + transfer + import) | Faster for incremental sync |
| Incremental sync | ❌ Not supported | ✅ Supported |
| Windows support | ✅ | ✅ |
| Cost | S3 export + data transfer fees | Free (pay only for resources) |
| Best for | One-time migration, overseas sources | Frequent incremental sync, large fleets |

## External References

- [AWS EC2 Export Image](https://docs.aws.amazon.com/vm-import/latest/userguide/vmexport_image.html)
- [Alibaba Cloud ECS ImportImage](https://www.alibabacloud.com/help/en/ecs/developer-reference/api-importimage)
- [Alibaba Cloud Data Online Migration](https://www.alibabacloud.com/help/en/data-online-migration)
- [ossutil download](https://www.alibabacloud.com/help/en/oss/developer-reference/ossutil)

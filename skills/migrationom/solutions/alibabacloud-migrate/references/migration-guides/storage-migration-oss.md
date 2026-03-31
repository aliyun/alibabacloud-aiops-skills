# Storage Migration: Amazon S3 to Alibaba Cloud OSS

## Overview

Primary paths for migrating data from Amazon S3 to Alibaba Cloud OSS:

- **ossutil**: Direct S3→OSS copy/sync, incremental snapshots, scripting (typical for most filesystem-style migrations).
- **Terraform** (`alicloud_oss_bucket`): Destination bucket and baseline policy/encryption (data transfer itself is not expressed in Terraform).

## ossutil CLI

### Installation

```bash
# macOS
brew install ossutil

# Linux
wget --timeout=30 --tries=3 http://gosspublic.alicdn.com/ossutil/1.7.18/ossutil64
chmod +x ossutil64
sudo mv ossutil64 /usr/local/bin/ossutil

# Verify installation
ossutil version
```

### Configuration

Run `ossutil config` once so OSS endpoint and credentials are available to the tool (follow the interactive prompts). AWS-side access for S3 uses the same default mechanisms as the AWS CLI (`aws configure`, instance profile, etc.).

**Configuration file location:** `~/.ossutilconfig`

### Create OSS Bucket

```bash
aliyun oss mb oss://<bucket-name> \
  --region <region-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `bucket-name` | Yes | OSS bucket name (globally unique) | `my-company-data` |
| `region` | Yes | Region where bucket will be created | `cn-hangzhou`, `us-west-1` |

### Terraform Alternative for OSS Bucket

```hcl
resource "alicloud_oss_bucket" "migration" {
  bucket = "<bucket-name>"
  acl    = "private"

  versioning {
    status = "Enabled"
  }

  server_side_encryption_rule {
    sse_algorithm = "AES256"
  }
}
```

**Note:** Use Terraform for OSS bucket creation. Data transfer operations (`ossutil cp`, `aws s3 sync`, etc.) use CLIs; there is no Terraform equivalent for copying object data.

### Migrate Data from S3

#### Option A: Direct S3 to OSS Transfer

```bash
ossutil64 cp s3://<s3-bucket>/<prefix> oss://<oss-bucket>/<prefix> \
  -r \
  --update \
  --snapshot-path=/tmp/snapshot \
  --jobs=10
```

**Parameters:**

| Parameter | Description | Example |
|-----------|-------------|---------|
| `-r` | Recursive copy for directories | |
| `--update` | Skip objects that already exist with same size | |
| `--snapshot-path` | Enable incremental sync with snapshot file | `/tmp/snapshot` |
| `--jobs` | Number of concurrent threads | `10` |

#### Option B: Download then Upload

```bash
# Step 1: Download from S3 to local
aws s3 sync s3://<s3-bucket>/<prefix> /tmp/s3-data/

# Step 2: Upload to OSS
ossutil64 cp /tmp/s3-data/ oss://<oss-bucket>/<prefix> \
  -r \
  --jobs=10
```

### Verify Migration

```bash
# Count objects in S3
aws s3 ls s3://<s3-bucket>/<prefix> --recursive | wc -l

# Count objects in OSS
ossutil64 ls oss://<oss-bucket>/<prefix> -r | wc -l

# Compare object sizes
ossutil64 stat oss://<oss-bucket>/<prefix>/<object-key>
```

### Enable Incremental Sync

```bash
# Run periodic sync with snapshot
ossutil64 cp s3://<s3-bucket>/ oss://<oss-bucket>/ \
  -r \
  --update \
  --snapshot-path=/tmp/s3-oss-snapshot \
  --jobs=10
```

**Cron Job Example:**
```bash
# Run every hour
0 * * * * /usr/local/bin/ossutil64 cp s3://<bucket>/ oss://<bucket>/ -r --update --snapshot-path=/tmp/snapshot --jobs=10
```

## S3 API Compatibility

### OSS S3-Compatible API

Alibaba Cloud OSS supports S3-compatible API, allowing applications using AWS SDK to work with minimal changes.

### Endpoint Mapping

| AWS S3 | Alibaba Cloud OSS |
|--------|-------------------|
| `s3.us-east-1.amazonaws.com` | `oss-us-east-1.aliyuncs.com` |
| `s3.us-west-2.amazonaws.com` | `oss-us-west-1.aliyuncs.com` |
| `s3.ap-southeast-1.amazonaws.com` | `oss-ap-southeast-1.aliyuncs.com` |
| `s3.eu-west-1.amazonaws.com` | `oss-eu-west-1.aliyuncs.com` |

### SDK Configuration Changes

Use each SDK’s **default credential provider chain** for both AWS S3 and OSS (S3-compatible endpoint). Only `endpoint` / `region` need to change for OSS.

#### AWS SDK for Python (boto3)

**Before (S3):**
```python
import boto3

s3 = boto3.client('s3', region_name='us-east-1')
```

**After (OSS):**
```python
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='https://oss-<region>.aliyuncs.com',
    region_name='oss',
)
```

#### AWS SDK for Java

**Before (S3):**
```java
AmazonS3 s3 = AmazonS3ClientBuilder.standard()
    .withRegion("us-east-1")
    .build();
```

**After (OSS):**
```java
AmazonS3 s3 = AmazonS3ClientBuilder.standard()
    .withEndpointConfiguration(new AwsClientBuilder.EndpointConfiguration(
        "https://oss-<region>.aliyuncs.com", "oss"))
    .build();
```

#### AWS SDK for Node.js

**Before (S3):**
```javascript
const s3 = new AWS.S3({ region: 'us-east-1' });
```

**After (OSS):**
```javascript
const s3 = new AWS.S3({
  endpoint: 'https://oss-<region>.aliyuncs.com',
  region: 'oss',
});
```

### Compatibility Notes

| Feature | Compatibility | Notes |
|---------|--------------|-------|
| PUT/GET/DELETE Object | ✅ Fully Compatible | Direct replacement |
| List Objects | ✅ Compatible | Minor parameter differences |
| Multipart Upload | ✅ Compatible | Same API structure |
| Presigned URLs | ✅ Compatible | Different signing algorithm |
| Bucket Policies | ⚠️ Partial | Syntax differences |
| S3 Select | ⚠️ Partial | Check OSS documentation |
| S3 Inventory | ❌ Not Compatible | Use OSS inventory instead |
| S3 Replication | ❌ Not Compatible | Use OSS cross-region replication |

## Handling S3 Object Versioning

S3 buckets with versioning enabled store multiple versions of each object, plus delete markers. Standard `ossutil cp` and `aws s3 sync` only transfer **current versions** — previous versions and delete markers are silently skipped, causing object count mismatches during verification.

### Pre-Migration: Check Versioning Status

```bash
aws s3api get-bucket-versioning --bucket <s3-bucket>
# "Enabled" or "Suspended" means versioned objects may exist
```

### Scenario 1: Only Current Versions Needed (Most Common)

If you only need the latest version of each object (typical for migration):

```bash
# Standard transfer — copies only current versions
ossutil64 cp s3://<s3-bucket>/ oss://<oss-bucket>/ -r --update --jobs=10
```

**Verification adjustment** — compare against current-version count only:

```bash
# S3: count current versions only (exclude delete markers and non-current)
aws s3api list-objects-v2 --bucket <s3-bucket> --query 'KeyCount' --output text

# OSS: count objects
ossutil64 ls oss://<oss-bucket>/ -r --only-count
```

### Scenario 2: All Versions Needed (Compliance / Audit)

If regulatory or audit requirements demand preserving version history:

```bash
# Step 1: List all versions
aws s3api list-object-versions --bucket <s3-bucket> \
  --query '[Versions[].{Key:Key,VersionId:VersionId,IsLatest:IsLatest},DeleteMarkers[].{Key:Key,VersionId:VersionId}]' \
  --output json > versions.json

# Step 2: Download each version with version ID preserved in path
python3 -c "
import json, subprocess, os
data = json.load(open('versions.json'))
versions = data[0] or []
for v in versions:
    key, vid = v['Key'], v['VersionId']
    dest = f'/tmp/s3-versioned/{key}/__v_{vid}'
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    subprocess.run(['aws', 's3api', 'get-object', '--bucket', '<s3-bucket>',
                     '--key', key, '--version-id', vid, dest], check=True)
"

# Step 3: Upload to OSS with version path encoding
ossutil64 cp /tmp/s3-versioned/ oss://<oss-bucket>/versioned-archive/ -r --jobs=10
```

> **Note:** OSS versioning (`versioning.status = "Enabled"`) tracks versions created *after* enabling. It does NOT reconstruct S3 version history. The approach above archives version history as separate objects.

### Scenario 3: Delete Markers

S3 delete markers indicate soft-deleted objects. They are **not transferred** by default.

```bash
# List delete markers
aws s3api list-object-versions --bucket <s3-bucket> \
  --query 'DeleteMarkers[].{Key:Key,VersionId:VersionId}' --output table
```

- If delete markers are for truly deleted data: **ignore** them (don't migrate).
- If delete markers need preservation for audit: record them in a manifest file and store alongside migrated data.

### Object Count Reconciliation

When source and destination counts don't match, check:

| Difference | Cause | Action |
|------------|-------|--------|
| OSS count < S3 `list-objects-v2` count | Hidden objects (0-byte keys, special chars) | Check with `aws s3api list-objects-v2 --prefix ""` |
| OSS count << S3 `list-object-versions` count | Non-current versions not transferred | Expected for Scenario 1; verify current-version count matches |
| OSS count < expected after full transfer | Transfer errors / timeouts | Check ossutil logs, re-run with `--update` |

## Migration Best Practices

### 1. Pre-Migration Planning

- **Inventory Assessment**: Catalog all S3 buckets, objects, and sizes
- **Network Bandwidth**: Estimate migration duration based on available bandwidth
- **Cost Estimation**: Calculate S3 egress costs and OSS storage costs
- **Dependency Mapping**: Identify applications using S3 and update plans

### 2. Migration Strategy

- **Full + Incremental**: Run full migration first, then incremental syncs
- **Throttling**: Set speed limits to avoid impacting production workloads
- **Parallel Migration**: Migrate multiple buckets simultaneously if bandwidth allows
- **Validation**: Plan data validation steps before cutover

### 3. During Migration

- **Monitor Progress**: Track transfer rates, error counts, and completion percentage
- **Error Handling**: Review and retry failed objects
- **Incremental Sync**: Run periodic syncs to minimize cutover window
- **Communication**: Keep stakeholders informed of migration status

### 4. Cutover Execution

- **Maintenance Window**: Schedule during low-traffic periods
- **Stop Writes**: Disable all write operations to source S3
- **Final Sync**: Run final incremental sync to capture remaining changes
- **Verification**: Validate object counts, sizes, and checksums
- **DNS/Endpoint Update**: Update application endpoints to OSS
- **Rollback Plan**: Keep S3 bucket available for emergency rollback

### 5. Post-Migration

- **Application Testing**: Verify all application functionality with OSS
- **Performance Monitoring**: Monitor OSS performance metrics
- **Cost Optimization**: Review storage class and lifecycle policies
- **Decommission S3**: Delete S3 bucket after successful migration

### 6. Security Considerations

- **Encryption**: Enable server-side encryption on OSS buckets
- **Access Control**: Configure RAM policies and bucket policies
- **Network Security**: Use VPC endpoints for private network access
- **Audit Logging**: Enable OSS access logging for compliance

## Cleanup

### Remove ossutil Configuration

```bash
# Remove configuration file
rm ~/.ossutilconfig
```

### Decommission S3 Bucket

```bash
# Empty bucket (remove all objects)
aws s3 rm s3://<bucket-name> --recursive

# Delete bucket
aws s3 rb s3://<bucket-name>
```

### Revoke AWS IAM Permissions

```bash
# Delete access keys
aws iam delete-access-key --access-key-id <key-id> --user-name <user-name>

# Delete IAM user (if no longer needed)
aws iam delete-user --user-name <user-name>
```

### Remove S3 Bucket Policy

```bash
aws s3api delete-bucket-policy --bucket <bucket-name>
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Access Denied` | Invalid credentials or permissions | Verify IAM/RAM policies and local credential configuration |
| `Network Timeout` | Firewall or network connectivity | Check security groups and network ACLs |
| `Slow Transfer Speed` | Bandwidth throttling or network latency | Increase parallelism, tune part size / job count |
| `Object Upload Failed` | Object size exceeds limit or network issue | Check object size, retry with multipart upload |
| `Checksum Mismatch` | Data corruption during transfer | Re-transfer affected objects |
| `Permission Denied on OSS` | RAM policy missing required permissions | Add oss:PutObject, oss:GetObject permissions |

### Enable Debug Logging

```bash
# ossutil verbose mode
ossutil64 cp <source> <destination> -r --loglevel=debug
```

## Related APIs

### OSS

| API Action | CLI Command |
|------------|-------------|
| Create Bucket | `aliyun oss mb oss://<bucket> ... --user-agent AlibabaCloud-Agent-Skills` |
| List Objects | `aliyun oss ls oss://<bucket> ... --user-agent AlibabaCloud-Agent-Skills` |
| Copy Object | `aliyun oss cp <source> <destination> ... --user-agent AlibabaCloud-Agent-Skills` |
| Delete Object | `aliyun oss rm oss://<bucket>/<object> ... --user-agent AlibabaCloud-Agent-Skills` |
| Delete Bucket | `aliyun oss rb oss://<bucket> ... --user-agent AlibabaCloud-Agent-Skills` |

## References

- [OSS Documentation](https://www.alibabacloud.com/help/en/oss)
- [ossutil User Guide](https://www.alibabacloud.com/help/en/oss/user-guide/ossutil-command-reference)
- [S3 Compatibility Guide](https://www.alibabacloud.com/help/en/oss/developer-reference/s3-protocol)

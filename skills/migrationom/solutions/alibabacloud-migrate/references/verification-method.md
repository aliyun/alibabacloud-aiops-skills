# Verification Methods for AWS-to-Alibaba Cloud Migration

This document provides specific CLI commands and expected outputs to verify successful migration for each scenario.

---

## 1. Server Migration (SMC) Verification

### Step 1: Check Migration Job Status

```bash
aliyun smc DescribeReplicationJobs \
  --JobId.1 <job-id> \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "ReplicationJobs": {
    "ReplicationJob": [
      {
        "JobId": "<job-id>",
        "Status": "Finished",
        "BusinessStatus": "Completed",
        "Progress": 100,
        "ImageId": "<image-id>",
        "ImageName": "<image-name>"
      }
    ]
  }
}
```

**Success Criteria:**
- `Status` = `Finished`
- `BusinessStatus` = `Completed`
- `Progress` = `100`
- `ImageId` is present (migration image created)

**Failure Indicators:**
- `Status` = `Failed` - Check error message in response
- `Status` = `Stopped` - Job was manually stopped
- `Progress` stuck at < 100 for extended period

---

### Step 2: Verify Generated Image

```bash
aliyun ecs DescribeImages \
  --ImageId <image-id> \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "Images": {
    "Image": [
      {
        "ImageId": "<image-id>",
        "ImageName": "<image-name>",
        "Status": "Available",
        "OSName": "<os-name>",
        "Size": <size-in-gb>,
        "CreationTime": "<timestamp>"
      }
    ]
  }
}
```

**Success Criteria:**
- `Status` = `Available`
- `OSName` matches source server OS
- `Size` is reasonable (> 0 GB)

---

### Step 3: Launch Test Instance from Image

```bash
aliyun ecs RunInstances \
  --ImageId <image-id> \
  --InstanceType ecs.g6.large \
  --VSwitchId <vsw-id> \
  --SecurityGroupId <sg-id> \
  --RegionId <region> \
  --InstanceName migration-test-instance \
  --Amount 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "InstanceIdSets": {
    "InstanceIdSet": [
      "i-<instance-id>"
    ]
  }
}
```

**Success Criteria:**
- Instance ID is returned
- Instance enters `Running` state within 2-3 minutes

**Verify Instance Status:**
```bash
aliyun ecs DescribeInstances \
  --InstanceIds '["i-<instance-id>"]' \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected:** `Status` = `Running`

---

### Step 4: Connect and Validate

```bash
# SSH to test instance (if Linux)
ssh -i <key-pair-file> root@<public-ip>

# Verify OS and applications
uname -a
df -h
systemctl status <critical-services>
```

**Success Criteria:**
- SSH connection successful
- OS boots correctly
- Critical services are running
- Application data is intact

---

## 2. Database Migration (DTS) Verification

### Step 1: Check DTS Job Status

```bash
aliyun dts DescribeMigrationJobStatus \
  --MigrationJobId <job-id> \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "MigrationJobStatus": "Migrating",
  "MigrationJobId": "<job-id>",
  "Progress": {
    "StructureMigration": "Completed",
    "FullDataMigration": "Completed",
    "IncrementalDataMigration": "Synchronizing"
  },
  "Delay": "<delay-in-seconds>"
}
```

**Success Criteria:**
- `MigrationJobStatus` = `Migrating` (incremental sync running)
- `StructureMigration` = `Completed`
- `FullDataMigration` = `Completed`
- `IncrementalDataMigration` = `Synchronizing` or `Completed`
- `Delay` is minimal (< 60 seconds for active databases)

**Alternative Status Values:**
- `NotStarted` - Job not yet started
- `Prechecking` - Initial validation in progress
- `Failed` - Check error details

---

### Step 2: Verify Destination RDS Instance

```bash
aliyun rds DescribeDBInstances \
  --DBInstanceId <instance-id> \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "Items": {
    "DBInstanceAttribute": [
      {
        "DBInstanceId": "<instance-id>",
        "DBInstanceStatus": "Running",
        "Engine": "MySQL",
        "EngineVersion": "<version>",
        "DBInstanceStorage": <storage-gb>,
        "CreationTime": "<timestamp>"
      }
    ]
  }
}
```

**Success Criteria:**
- `DBInstanceStatus` = `Running`
- `Engine` matches source database type
- Storage size is adequate

---

### Step 3: Verify Database Contents

```bash
# Connect to destination RDS
mysql -h <rds-endpoint> -u <username> -p

# Check database exists
SHOW DATABASES;

# Check table count
USE <database-name>;
SHOW TABLES;
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '<database-name>';

# Verify row counts match source
SELECT COUNT(*) FROM <critical-table>;

# Check data integrity (sample queries)
SELECT * FROM <table> LIMIT 10;
```

**Success Criteria:**
- All databases present
- Table counts match source
- Row counts match source (within acceptable tolerance for incremental sync)
- Sample data queries return expected results

---

### Step 4: Check DTS Job Details

```bash
aliyun dts DescribeMigrationJobs \
  --MigrationJobId <job-id> \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Verify:**
- Source and destination endpoints are correct
- Migration types include required components (structure, full, incremental)
- No error messages in response

---

## 3. Storage Migration (OSS) Verification

### Step 1: Verify Bucket Exists

```bash
aliyun oss ls oss://<bucket-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```
2024-01-15 10:30:00      0 
```
(Empty bucket shows timestamp with 0 size)

**Success Criteria:**
- Command returns without error
- Bucket is accessible

---

### Step 2: Check Bucket Storage Usage

```bash
aliyun oss du oss://<bucket-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```
Total(DU): <total-size-in-bytes>
Storage Class: Standard
Object Count: <number-of-objects>
```

**Success Criteria:**
- Total size matches expected migrated data size
- Object count is reasonable (> 0 if data was migrated)

---

### Step 3: List Bucket Contents

```bash
aliyun oss ls oss://<bucket-name> --recursive \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```
2024-01-15 10:30:00   1048576    oss://<bucket-name>/path/to/file1.txt
2024-01-15 10:30:01   2097152    oss://<bucket-name>/path/to/file2.txt
...
```

**Success Criteria:**
- Expected files are present
- File sizes match source
- Directory structure is preserved

---

### Step 4: Verify Specific Object

```bash
aliyun oss stat oss://<bucket-name>/<object-key> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "Content-Length": "<size>",
  "Last-Modified": "<timestamp>",
  "ETag": "<etag>",
  "Content-Type": "<mime-type>"
}
```

**Success Criteria:**
- Object metadata is present
- Size matches source file
- ETag is valid

---

### Step 5: Download and Verify Sample File

```bash
# Download sample file
aliyun oss cp oss://<bucket-name>/<object-key> /tmp/downloaded-file \
  --user-agent AlibabaCloud-Agent-Skills

# Compare with source (if available)
diff /tmp/downloaded-file <source-file>
# Or check checksum
md5sum /tmp/downloaded-file
```

**Success Criteria:**
- Download successful
- File integrity verified (checksum or diff matches)

---

## 4. Serverless Migration (Function Compute) Verification

### Step 1: List Functions

```bash
aliyun fc list-functions \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "functions": [
    {
      "functionName": "<function-name>",
      "description": "<description>",
      "runtime": "<runtime>",
      "handler": "<handler>",
      "createdTime": "<timestamp>",
      "lastModifiedTime": "<timestamp>"
    }
  ]
}
```

**Success Criteria:**
- Function is listed
- Function name matches expected

---

### Step 2: Verify Function Exists

```bash
aliyun fc get-function \
  --function-name <function-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "functionName": "<function-name>",
  "description": "<description>",
  "runtime": "python3.9",
  "handler": "index.handler",
  "codeSize": <size-in-bytes>,
  "state": "Active"
}
```

**Success Criteria:**
- Function details returned
- `state` = `Active`
- Runtime and handler are correct

---

### Step 3: Invoke Function

```bash
aliyun fc invoke-function \
  --function-name <function-name> \
  --body '{"key": "value"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "statusCode": 200,
  "body": "<function-response>"
}
```

**Success Criteria:**
- `statusCode` = `200`
- Function returns expected response
- No error messages

---

### Step 4: Verify Triggers (if applicable)

```bash
aliyun fc list-triggers \
  --function-name <function-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "triggers": [
    {
      "triggerName": "<trigger-name>",
      "triggerType": "oss",
      "triggerConfig": {...}
    }
  ]
}
```

**Success Criteria:**
- Triggers are configured
- Trigger types match requirements (OSS, HTTP, Timer, etc.)

---

## 5. Network Setup (VPC) Verification

### Step 1: Verify VPC

```bash
aliyun vpc DescribeVpcs \
  --VpcId <vpc-id> \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "Vpcs": {
    "Vpc": [
      {
        "VpcId": "<vpc-id>",
        "VpcName": "<vpc-name>",
        "Status": "Available",
        "CidrBlock": "10.0.0.0/8",
        "CreationTime": "<timestamp>"
      }
    ]
  }
}
```

**Success Criteria:**
- `Status` = `Available`
- CIDR block is correct
- VPC name matches expected

---

### Step 2: Verify VSwitch

```bash
aliyun vpc DescribeVSwitches \
  --VSwitchId <vsw-id> \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "VSwitches": {
    "VSwitch": [
      {
        "VSwitchId": "<vsw-id>",
        "VSwitchName": "<vswitch-name>",
        "Status": "Available",
        "CidrBlock": "10.0.1.0/24",
        "ZoneId": "<zone-id>",
        "AvailableIpAddressCount": <count>
      }
    ]
  }
}
```

**Success Criteria:**
- `Status` = `Available`
- CIDR block is within VPC range
- `AvailableIpAddressCount` > 0
- Zone ID is correct

---

### Step 3: Verify Security Group

```bash
aliyun ecs DescribeSecurityGroups \
  --SecurityGroupId <sg-id> \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "SecurityGroups": {
    "SecurityGroup": [
      {
        "SecurityGroupId": "<sg-id>",
        "SecurityGroupName": "<sg-name>",
        "VpcId": "<vpc-id>",
        "Description": "<description>"
      }
    ]
  }
}
```

**Success Criteria:**
- Security group exists
- Associated with correct VPC

---

### Step 4: Verify Security Group Rules

```bash
aliyun ecs DescribeSecurityGroupAttribute \
  --SecurityGroupId <sg-id> \
  --RegionId <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "Permissions": {
    "Permission": [
      {
        "IpProtocol": "tcp",
        "PortRange": "22/22",
        "SourceCidrIp": "0.0.0.0/0",
        "Policy": "Accept",
        "Direction": "ingress"
      }
    ]
  }
}
```

**Success Criteria:**
- Required ports are open (SSH: 22, HTTP: 80, HTTPS: 443, etc.)
- Rules match security requirements

---

## 6. DNS Migration Verification

### Step 1: Verify Domain Added

```bash
aliyun alidns DescribeDomains \
  --KeyWord <domain-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "Domains": {
    "Domain": [
      {
        "DomainName": "<domain-name>",
        "RecordCount": <number-of-records>,
        "Status": "ENABLE"
      }
    ]
  }
}
```

**Success Criteria:**
- Domain is listed
- `Status` = `ENABLE`
- Record count > 0

---

### Step 2: Verify DNS Records

```bash
aliyun alidns DescribeDomainRecords \
  --DomainName <domain-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "DomainRecords": {
    "Record": [
      {
        "RecordId": "<record-id>",
        "RR": "www",
        "Type": "A",
        "Value": "<ip-address>",
        "Status": "ENABLE",
        "TTL": 600
      }
    ]
  }
}
```

**Success Criteria:**
- All required records present (A, CNAME, MX, TXT, etc.)
- Record values point to correct Alibaba Cloud resources
- `Status` = `ENABLE` for all records

---

### Step 3: Verify DNS Propagation

```bash
# Use dig to verify DNS resolution
dig <domain-name> @dns1.hichina.com
dig www.<domain-name> @dns1.hichina.com

# Or use nslookup
nslookup <domain-name> dns1.hichina.com
```

**Expected Output:**
```
;; ANSWER SECTION:
<domain-name>.    600    IN    A    <ip-address>
```

**Success Criteria:**
- DNS resolves to correct IP address
- TTL values are appropriate
- All subdomains resolve correctly

---

### Step 4: Verify CDN Domain (if applicable)

```bash
aliyun cdn DescribeUserDomains \
  --DomainName <cdn-domain> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected Output:**
```json
{
  "PageData": {
    "CDNDomainDetail": [
      {
        "DomainName": "<cdn-domain>",
        "DomainStatus": "online",
        "SourceType": "oss",
        "Source": "<oss-bucket>"
      }
    ]
  }
}
```

**Success Criteria:**
- `DomainStatus` = `online`
- Source is correctly configured

---

## 7. Comprehensive Migration Verification Checklist

### Pre-Cutover Verification

- [ ] All SMC migration jobs completed (Status = Finished)
- [ ] All migration images available and tested
- [ ] All DTS jobs in incremental sync (Status = Migrating)
- [ ] DTS delay < 60 seconds
- [ ] All OSS buckets created and populated
- [ ] Sample files verified for integrity
- [ ] All VPC resources created and available
- [ ] Security groups configured with correct rules
- [ ] Test instances launched successfully from migration images
- [ ] Application connectivity verified on test instances

### Post-Cutover Verification

- [ ] DNS records updated and propagated
- [ ] CDN domains online and serving content
- [ ] DTS jobs stopped after cutover complete
- [ ] Final data consistency check passed
- [ ] All applications running on Alibaba Cloud
- [ ] Monitoring and alerting configured
- [ ] Backup strategies implemented
- [ ] Performance benchmarks meet requirements

### Cleanup Verification

- [ ] Source AWS resources documented for decommissioning
- [ ] DTS migration jobs deleted
- [ ] SMC replication jobs deleted
- [ ] Intermediate ECS instances terminated
- [ ] Temporary security groups removed
- [ ] Access keys rotated
- [ ] Audit logs archived

---

## Troubleshooting Common Issues

### SMC Migration Stuck

```bash
# Check job details
aliyun smc DescribeReplicationJobs --JobId.1 <job-id> --RegionId <region> --user-agent AlibabaCloud-Agent-Skills

# Check source server status
aliyun smc DescribeSourceServers --SourceIds '["<source-id>"]' --RegionId <region> --user-agent AlibabaCloud-Agent-Skills
```

### DTS Job Failed

```bash
# Get detailed error
aliyun dts DescribeMigrationJobStatus --MigrationJobId <job-id> --user-agent AlibabaCloud-Agent-Skills

# Common issues:
# - Network connectivity between source and destination
# - Insufficient permissions on source database
# - Schema incompatibilities
```

### OSS Upload Failed

```bash
# Check bucket permissions
aliyun oss ls oss://<bucket-name> --user-agent AlibabaCloud-Agent-Skills

# Verify network connectivity
# Check if multipart upload is needed for large files
```

### DNS Not Propagating

```bash
# Check record status
aliyun alidns DescribeDomainRecords --DomainName <domain-name> --user-agent AlibabaCloud-Agent-Skills

# Verify TTL settings
# Check if domain is locked or suspended
```

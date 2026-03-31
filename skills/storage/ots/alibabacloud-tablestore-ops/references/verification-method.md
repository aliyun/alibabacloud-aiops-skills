# Tablestore Read-Only Operations - Verification Methods

This document provides verification steps for each Tablestore CLI read-only operation via `aliyun otsutil`.

## Pre-requisite: Version Check

**CRITICAL:** Before running any otsutil commands, verify you have Aliyun CLI version 3.3.0 or later.

```bash
# Check version (MUST be 3.3.0+)
aliyun version

# Expected output: 3.3.0 or higher (e.g., 3.3.3)
# If version is lower (e.g., 3.0.x), otsutil will NOT work!

# Verify otsutil is available
aliyun otsutil help

# If you see "ERROR: 'otsutil' is not a valid command", 
# download the latest version from CDN (see cli-installation-guide.md)
```

## Task 1: Configure Instance Verification

After running `aliyun otsutil config`, verify the configuration was applied correctly.

### Verification Steps

1. **Check config response:**

The `aliyun otsutil config` command returns current configuration:

```json
{
  "Endpoint": "https://myinstance.cn-hangzhou.ots.aliyuncs.com",
  "AccessKeyId": "LTAI5t***",
  "AccessKeySecret": "7NR2***",
  "AccessKeySecretToken": "",
  "Instance": "myinstance"
}
```

2. **Success Criteria:**
   - `Endpoint` matches the configured endpoint URL
   - `Instance` matches the configured instance name
   - `AccessKeyId` shows the configured key (masked)

3. **Test connection by listing tables:**

```bash
aliyun otsutil list
```

- If configuration is correct and instance exists, returns list of tables (or empty list)
- If configuration is wrong, returns authentication or connection error

### Common Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Connection timeout | Wrong endpoint format | Verify endpoint URL format |
| Auth failed | Wrong AccessKey or not configured | Run `aliyun configure` to configure credentials |
| Instance not found | Instance doesn't exist | Create instance first or check instance name |

---

## Task 2: Describe Instance Verification

After running `aliyun otsutil describe_instance`, verify the response contains expected information.

### Verification Steps

1. **Check response completeness:**

```bash
aliyun otsutil describe_instance -r cn-hangzhou -n myinstance
```

2. **Expected Response Fields:**

| Field | Expected Value |
|-------|---------------|
| `InstanceName` | Matches requested instance name |
| `Status` | `1` for running instance |
| `ClusterType` | `ssd` or `hybrid` |
| `Network` | `NORMAL` or `VPC` |

3. **Success Criteria:**
   - Response is valid JSON
   - All required fields are present
   - `Status` is `1` (Running)

### Status Code Reference

| Status | Meaning |
|--------|---------|
| `0` | Loading |
| `1` | Running (Ready) |
| `2` | Deleting |
| `-1` | Error |
| `-2` | Frozen |

---

## Task 3: List Instances Verification

After running `aliyun otsutil list_instance`, verify the response is correct.

### Verification Steps

1. **Run list command:**

```bash
aliyun otsutil list_instance -r cn-hangzhou
```

2. **Expected Response:**

```json
[
  "instance1",
  "instance2"
]
```

Or empty array if no instances:

```json
[]
```

3. **Success Criteria:**
   - Response is a valid JSON array
   - Known instances appear in the list
   - No duplicate entries

4. **Cross-verify with describe:**

For each instance in the list, you can verify with:

```bash
aliyun otsutil describe_instance -r <regionId> -n <instanceName>
```

### Common Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Empty list | Wrong region | Check region ID parameter |
| Missing instance | Instance in different region | Try other region IDs |
| Permission denied | Insufficient permissions | Add `ots:ListInstance` permission |

---

## Task 4: List Tables Verification

After running `aliyun otsutil list`, verify the response is correct.

### Verification Steps

1. **Ensure instance is configured:**

```bash
aliyun otsutil config --endpoint https://myinstance.cn-hangzhou.ots.aliyuncs.com --instance myinstance
```

2. **Run list command:**

```bash
# List all data tables
aliyun otsutil list -w

# List all tables (data + timeseries)
aliyun otsutil list -a
```

3. **Success Criteria:**
   - Command returns without error
   - Known table names appear in the output
   - Empty output is valid if no tables exist

### Common Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Error | Instance not configured | Run `aliyun otsutil config` with endpoint first |
| Empty list | No tables in instance | Verify you're connected to the correct instance |
| Permission denied | Insufficient permissions | Add `ots:ListTable` permission |

---

## Task 5: Describe Table Verification

After running `aliyun otsutil desc`, verify the response contains expected table schema.

### Verification Steps

1. **Describe a specific table:**

```bash
aliyun otsutil desc -t mytable
```

2. **Expected Response Structure:**

```json
{
  "Name": "mytable",
  "Meta": {
    "Pk": [
      { "C": "uid", "T": "string", "Opt": "none" },
      { "C": "pid", "T": "integer", "Opt": "none" }
    ]
  },
  "Option": {
    "TTL": -1,
    "Version": 1
  },
  "CU": {
    "Read": 0,
    "Write": 0
  }
}
```

3. **Success Criteria:**
   - Response is valid JSON
   - `Name` matches the requested table
   - `Meta.Pk` contains primary key definitions
   - `Option.TTL` and `Option.Version` are present

4. **Export to file for comparison:**

```bash
aliyun otsutil desc -t mytable -o /tmp/table_meta.json
```

### Common Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Table not found | Wrong table name | Run `aliyun otsutil list` to check available tables |
| Error | Instance not configured | Run `aliyun otsutil config` with endpoint first |
| Permission denied | Insufficient permissions | Add `ots:DescribeTable` permission |

---

## End-to-End Verification Workflow

Complete verification workflow for read-only operations:

```bash
# Step 0: Verify Aliyun CLI version (MUST be 3.3.0+)
aliyun version
# If version < 3.3.0, download latest from CDN first!

# Step 1: Verify otsutil is available
aliyun otsutil help

# Step 2: Verify Aliyun CLI credentials are configured
aliyun sts GetCallerIdentity

# Step 3: List instances in a region
aliyun otsutil list_instance -r cn-hangzhou
# Expected: ["myinstance", ...]

# Step 4: Get instance details
aliyun otsutil describe_instance -r cn-hangzhou -n myinstance
# Expected: Status = 1

# Step 5: Configure instance endpoint
aliyun otsutil config --endpoint https://myinstance.cn-hangzhou.ots.aliyuncs.com --instance myinstance

# Step 6: List data tables
aliyun otsutil list -w
# Expected: list of table names

# Step 7: Describe a table
aliyun otsutil desc -t mytable
# Expected: table schema with primary keys, TTL, versions

# Step 8: Export table info to file (optional)
aliyun otsutil desc -t mytable -o /tmp/table_meta.json
```

## Automated Verification Script

For automated verification, you can use the following pattern:

```bash
#!/bin/bash
# Verification script example

INSTANCE_NAME="test-instance"
REGION="cn-hangzhou"

# Check if instance exists
aliyun otsutil list_instance -r $REGION | grep -q "$INSTANCE_NAME"

if [ $? -eq 0 ]; then
    echo "✅ Instance $INSTANCE_NAME exists in $REGION"
else
    echo "❌ Instance $INSTANCE_NAME not found in $REGION"
    exit 1
fi
```

## Troubleshooting Verification Failures

### Authentication Issues

```bash
# Verify credentials
aliyun sts GetCallerIdentity

# Re-configure if needed
aliyun configure
```

### Network Issues

1. Check if endpoint is reachable:
   - For public endpoint: ensure internet access
   - For VPC endpoint: ensure VPC configuration is correct

2. Verify endpoint format matches network type:
   - Public: `https://<instance>.<region>.ots.aliyuncs.com`
   - VPC: `https://<instance>.<region>.vpc.tablestore.aliyuncs.com`

### Permission Issues

If verification commands fail with permission errors:

1. Check RAM user has `AliyunOTSReadOnlyAccess` policy
2. Or verify specific permissions exist:
   - `ots:GetInstance` for describe_instance
   - `ots:ListInstance` for list_instance
   - `ots:ListTable` for list
   - `ots:DescribeTable` for desc

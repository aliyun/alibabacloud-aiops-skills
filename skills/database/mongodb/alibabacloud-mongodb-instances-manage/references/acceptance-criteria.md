# Acceptance Criteria - MongoDB Instance Management

**Scenario**: MongoDB instance creation and management (Standalone/Replica Set/Sharded Cluster)
**Purpose**: Skill test acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — Verify product name exists

✅ **CORRECT**
```bash
aliyun dds create-db-instance ...
```
Product name `dds` is the correct identifier for ApsaraDB for MongoDB.

❌ **INCORRECT**
```bash
aliyun mongodb create-db-instance ...  # Wrong: product name should be dds
aliyun mongo create-db-instance ...    # Wrong: product name should be dds
```

### 2. Command — Verify command exists

✅ **CORRECT** (Plugin mode, using hyphens)
```bash
aliyun dds create-db-instance
aliyun dds describe-db-instances
aliyun dds describe-db-instance-attribute
aliyun dds delete-db-instance
aliyun dds describe-regions
aliyun dds describe-available-resource
```

❌ **INCORRECT** (Legacy API format)
```bash
aliyun dds CreateDBInstance            # Wrong: should use plugin mode
aliyun dds DescribeDBInstances         # Wrong: should use plugin mode
```

### 3. Parameters — Verify parameter names exist

✅ **CORRECT** (Using hyphen format)
```bash
--region-id cn-hangzhou
--zone-id cn-hangzhou-g
--engine-version "6.0"
--db-instance-class "dds.mongo.standard"
--db-instance-storage 20
--vpc-id "vpc-xxx"
--v-switch-id "vsw-xxx"
--replication-factor "3"
--storage-type cloud_essd1
--charge-type PostPaid
--user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT** (CamelCase or wrong parameter names)
```bash
--RegionId cn-hangzhou                 # Wrong: should use --region-id
--ZoneId cn-hangzhou-g                 # Wrong: should use --zone-id
--EngineVersion "6.0"                  # Wrong: should use --engine-version
--DBInstanceClass "dds.mongo.standard" # Wrong: should use --db-instance-class
--VpcId "vpc-xxx"                      # Wrong: should use --vpc-id
--VSwitchId "vsw-xxx"                  # Wrong: should use --v-switch-id
```

### 4. User-Agent Flag — Verify inclusion is mandatory

✅ **CORRECT**
```bash
aliyun dds create-db-instance \
  --region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

❌ **INCORRECT**
```bash
aliyun dds create-db-instance \
  --region-id cn-hangzhou
# Missing --user-agent parameter
```

### 5. Parameter Values — Verify parameter value formats

#### EngineVersion (Database version)
✅ **CORRECT**: `"8.0"`, `"7.0"`, `"6.0"`, `"5.0"`, `"4.4"`, `"4.2"`, `"4.0"`
❌ **INCORRECT**: `"3.4"` (discontinued), `"6"` (missing minor version), `6.0` (should use quotes)

#### ReplicationFactor (Node count)
✅ **CORRECT**: `"3"`, `"5"`, `"7"`
❌ **INCORRECT**: `"1"`, `"2"`, `"4"`, `"6"`, `3` (should be wrapped in quotes as string)

#### ChargeType (Billing type)
✅ **CORRECT**: `PostPaid`, `PrePaid`
❌ **INCORRECT**: `postpaid` (wrong case), `Postpaid` (wrong case)

#### StorageType (Storage type)
✅ **CORRECT**: `cloud_essd1`, `cloud_essd2`, `cloud_essd3`, `cloud_auto`, `local_ssd`
❌ **INCORRECT**: `essd`, `ssd`, `cloud_ssd`

#### NetworkType (Network type)
✅ **CORRECT**: `VPC`
❌ **INCORRECT**: `Classic` (classic network no longer supports new instances), `vpc` (wrong case)

---

## Command Validation Checklist

When validating CLI commands, check the following items:

| Check Item | Validation Method |
|------------|-------------------|
| Product name | `aliyun dds --help` to confirm dds product exists |
| Command name | `aliyun dds <command> --help` to confirm command exists |
| Parameter name | Check if the parameter is included in command help output |
| Parameter value range | Read full parameter description, confirm enum values are within allowed range |
| user-agent | Must be included in every aliyun command |

---

## API Response Validation

### Successful instance creation response

```json
{
  "DBInstanceId": "dds-bp1234567890****",
  "OrderId": "20987654321****",
  "RequestId": "D8F1D721-6439-4257-A89C-F1E8E9C9****"
}
```

**Validation points**:
- `DBInstanceId` is not empty
- `RequestId` exists

### Query instance details response

```json
{
  "DBInstances": {
    "DBInstance": [{
      "DBInstanceId": "dds-bp1234567890****",
      "DBInstanceStatus": "Running",
      "ReplicationFactor": "3",
      "EngineVersion": "6.0",
      "RegionId": "cn-hangzhou"
    }]
  }
}
```

**Validation points**:
- `DBInstanceStatus` is `Running` indicates instance is normal
- `ReplicationFactor` matches creation parameters
- `EngineVersion` matches creation parameters

---

## Error Handling Patterns

### Permission error

```json
{
  "Code": "Forbidden.RAM",
  "Message": "User not authorized to operate on the specified resource."
}
```

**Resolution**: Check RAM permission policies and add required permissions

### Parameter error

```json
{
  "Code": "InvalidParameter",
  "Message": "The parameter xxx is invalid."
}
```

**Resolution**: Check if parameter names and values are correct

### Insufficient resources

```json
{
  "Code": "ResourceNotAvailable",
  "Message": "Resource you requested is not available in this region or zone."
}
```

**Resolution**: Switch availability zone or adjust instance specifications

---

## Complete Command Example

The following is a complete, validated creation command example:

```bash
aliyun dds create-db-instance \
  --region-id cn-hangzhou \
  --zone-id cn-hangzhou-g \
  --engine-version "6.0" \
  --db-instance-class "dds.mongo.standard" \
  --db-instance-storage 20 \
  --vpc-id "vpc-bp175iuvg8nxqraf2****" \
  --v-switch-id "vsw-bp1gzt31twhlo0sa5****" \
  --network-type VPC \
  --replication-factor "3" \
  --storage-type cloud_essd1 \
  --charge-type PostPaid \
  --db-instance-description "my-mongodb-replica" \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Pre-execution Validation

Before executing CLI commands, perform the following validation:

1. **CLI version check**
   ```bash
   aliyun version  # >= 3.3.1
   ```

2. **Credential check**
   ```bash
   aliyun configure list  # Confirm valid profile exists
   ```

3. **Plugin check**
   ```bash
   aliyun dds --help  # Confirm dds plugin is installed
   ```

4. **Parameter confirmation**
   - All required parameters are provided
   - Parameter values are within valid range
   - Key parameters (RegionId, VpcId, etc.) confirmed with user

# Acceptance Criteria: Tablestore Read-Only Operations

**Scenario**: Tablestore CLI Read-Only Instance & Table Operations via `aliyun otsutil`
**Purpose**: Skill testing acceptance criteria

> **CRITICAL: Version Requirement**
> - Aliyun CLI version **3.3.0 or later** is required
> - Homebrew version is often outdated and does NOT include otsutil
> - Always download from official CDN: https://aliyuncli.alicdn.com/
> - Credentials are configured via `aliyun configure`

---

## Pre-requisite: Version Check

### ✅ CORRECT Version Check
```bash
# Check version
aliyun version
# Output: 3.3.3 (or any version >= 3.3.0)

# Verify otsutil works
aliyun otsutil help
# Output: Shows available commands
```

### ❌ INCORRECT (Version Too Old)
```bash
aliyun version
# Output: 3.0.278 (version < 3.3.0)

aliyun otsutil help
# Output: ERROR: 'otsutil' is not a valid command or product
```

---

## Correct CLI Command Patterns

### 1. config Command

Configure instance endpoint. Credentials are handled by `aliyun configure`, not this command.

#### ✅ CORRECT
```bash
# Configure instance endpoint only (credentials already configured via aliyun configure)
aliyun otsutil config --endpoint https://myinstance.cn-hangzhou.ots.aliyuncs.com --instance myinstance
```

#### ❌ INCORRECT
```bash
# Wrong: Invalid endpoint format (missing https://)
aliyun otsutil config --endpoint myinstance.cn-hangzhou.ots.aliyuncs.com --instance myinstance

# Wrong: Mismatched endpoint and instance name
aliyun otsutil config --endpoint https://instance1.cn-hangzhou.ots.aliyuncs.com --instance instance2
```

### 2. describe_instance Command

#### ✅ CORRECT
```bash
aliyun otsutil describe_instance -r cn-hangzhou -n myinstance
aliyun otsutil describe_instance -n prod-orders -r cn-shanghai
```

#### ❌ INCORRECT
```bash
# Wrong: Using --region instead of -r
aliyun otsutil describe_instance --region cn-hangzhou -n myinstance

# Wrong: Missing -n parameter
aliyun otsutil describe_instance -r cn-hangzhou

# Wrong: Missing -r parameter
aliyun otsutil describe_instance -n myinstance

# Wrong: Invalid region ID
aliyun otsutil describe_instance -r hangzhou -n myinstance
```

### 3. list_instance Command

#### ✅ CORRECT
```bash
aliyun otsutil list_instance -r cn-hangzhou
aliyun otsutil list_instance -r cn-shanghai
aliyun otsutil list_instance -r ap-southeast-1
```

#### ❌ INCORRECT
```bash
# Wrong: Using --region instead of -r
aliyun otsutil list_instance --region cn-hangzhou

# Wrong: Missing required -r parameter
aliyun otsutil list_instance

# Wrong: Invalid region format
aliyun otsutil list_instance -r hangzhou
```

### 4. use Command (Select Table)

#### ✅ CORRECT
```bash
aliyun otsutil use -t mytable
aliyun otsutil use --wc -t mytable
```

#### ❌ INCORRECT
```bash
# Wrong: Missing required -t parameter
aliyun otsutil use

# Wrong: Using --wc without table name
aliyun otsutil use --wc
```

### 5. list Command (List Tables)

#### ✅ CORRECT
```bash
aliyun otsutil list
aliyun otsutil list -a
aliyun otsutil list -w
aliyun otsutil list -t
aliyun otsutil list -d
```

#### ❌ INCORRECT
```bash
# Wrong: Using list_table (not the correct command)
aliyun otsutil list_table

# Wrong: Combining -w and -t (mutually exclusive)
aliyun otsutil list -w -t
```

### 6. desc Command (Describe Table)

#### ✅ CORRECT
```bash
aliyun otsutil desc
aliyun otsutil desc -t mytable
aliyun otsutil desc -t mytable -f json
aliyun otsutil desc -t mytable -f table
aliyun otsutil desc -t mytable -o /tmp/table_meta.json
```

#### ❌ INCORRECT
```bash
# Wrong: Using describe_table (not the correct command)
aliyun otsutil describe_table -t mytable

# Wrong: Invalid format option
aliyun otsutil desc -t mytable -f xml

# Wrong: Using --name instead of -t
aliyun otsutil desc --name mytable
```

---

## Endpoint Format Patterns

### ✅ CORRECT Endpoint Formats

```plaintext
# Public endpoint
https://myinstance.cn-hangzhou.ots.aliyuncs.com
https://prod-orders.cn-shanghai.ots.aliyuncs.com

# VPC endpoint
https://myinstance.cn-hangzhou.vpc.tablestore.aliyuncs.com
https://prod-orders.cn-shanghai.vpc.tablestore.aliyuncs.com

# HTTP (allowed but not recommended)
http://myinstance.cn-hangzhou.ots.aliyuncs.com
```

### ❌ INCORRECT Endpoint Formats

```plaintext
# Wrong: Missing protocol
myinstance.cn-hangzhou.ots.aliyuncs.com

# Wrong: Using .com instead of .aliyuncs.com
https://myinstance.cn-hangzhou.ots.com

# Wrong: Missing instance name
https://cn-hangzhou.ots.aliyuncs.com

# Wrong: Wrong domain structure
https://ots.cn-hangzhou.myinstance.aliyuncs.com

# Wrong: Using region name instead of ID
https://myinstance.hangzhou.ots.aliyuncs.com
```

---

## Instance Name Patterns

### ✅ CORRECT Instance Names

```plaintext
myinstance
prod-orders
test-data-2024
a1b2c3
my-instance-123
```

### ❌ INCORRECT Instance Names

```plaintext
# Wrong: Uppercase letters
MyInstance
MYINSTANCE

# Wrong: Starting with number
123instance

# Wrong: Too short (less than 3 characters)
ab

# Wrong: Too long (more than 16 characters)
my-very-long-instance-name-here

# Wrong: Special characters other than hyphen
my_instance
my.instance
my@instance

# Wrong: Starting with hyphen
-myinstance

# Wrong: Ending with hyphen
myinstance-
```

---

## Region ID Patterns

### ✅ CORRECT Region IDs

```plaintext
cn-hangzhou
cn-shanghai
cn-beijing
cn-shenzhen
cn-hongkong
ap-southeast-1
ap-northeast-1
us-west-1
us-east-1
eu-central-1
```

### ❌ INCORRECT Region IDs

```plaintext
# Wrong: Using region name
hangzhou
shanghai

# Wrong: Missing cn- prefix for China regions
hangzhou

# Wrong: Incorrect format
cn_hangzhou
cn.hangzhou
CN-HANGZHOU
```

---

## Response Validation Patterns

### describe_instance Response

#### ✅ CORRECT Response Structure

```json
{
  "ClusterType": "ssd",
  "CreateTime": "2024-07-18 09:15:10",
  "Description": "Instance description",
  "InstanceName": "myinstance",
  "Network": "NORMAL",
  "Quota": {
    "EntityQuota": 64
  },
  "ReadCapacity": 5000,
  "Status": 1,
  "TagInfos": {},
  "UserId": "1379123456789012",
  "WriteCapacity": 5000
}
```

**Required Fields:**
- `InstanceName` - Must match requested instance
- `Status` - Should be `1` for healthy instance
- `ClusterType` - `ssd` or `hybrid`
- `CreateTime` - Valid timestamp format

### list_instance Response

#### ✅ CORRECT Response Structure

```json
["instance1", "instance2", "instance3"]
```

Or empty:
```json
[]
```

#### ❌ INCORRECT Response

```json
# Wrong: Not an array
{"instances": ["instance1", "instance2"]}

# Wrong: Contains non-string values
[1, 2, 3]
```

---

## Common Anti-Patterns

### 1. Forgetting to Configure Aliyun CLI Credentials

#### ❌ WRONG
```bash
# Running otsutil commands without configuring aliyun credentials
aliyun otsutil list_instance -r cn-hangzhou
# Error: credentials not found
```

#### ✅ CORRECT
```bash
# First configure aliyun credentials
aliyun configure
# Then run otsutil commands
aliyun otsutil list_instance -r cn-hangzhou
```

### 2. Assuming Default Region

#### ❌ WRONG
```bash
# Assuming cn-hangzhou without asking user
aliyun otsutil list_instance -r cn-hangzhou
```

#### ✅ CORRECT
```bash
# Ask user to confirm region before execution
# User confirms: cn-hangzhou
aliyun otsutil list_instance -r cn-hangzhou
```

### 3. Forgetting to Configure Instance Before Table Operations

#### ❌ WRONG
```bash
# Running table commands without configuring instance first
aliyun otsutil list
# Error: no instance configured
```

#### ✅ CORRECT
```bash
# First configure the instance
aliyun otsutil config --endpoint https://myinstance.cn-hangzhou.ots.aliyuncs.com --instance myinstance

# Then run table commands
aliyun otsutil list -w
aliyun otsutil desc -t mytable
```

---

## Test Scenarios

### Scenario 1: Instance Discovery

**Steps:**
1. Configure Aliyun CLI credentials with `aliyun configure`
2. List instances in region
3. Describe each instance

**Expected Results:**
- `aliyun otsutil list_instance -r <region>` returns array of instance names
- Each `aliyun otsutil describe_instance` returns valid instance info with Status = 1

### Scenario 2: Table Discovery

**Steps:**
1. Configure Aliyun CLI credentials
2. Configure instance endpoint with `aliyun otsutil config`
3. List all data tables
4. Describe each table

**Expected Results:**
- `aliyun otsutil list -w` returns data table names
- `aliyun otsutil desc -t <name>` returns table schema with primary keys

### Scenario 3: Multi-Region Instance Exploration

**Steps:**
1. Configure Aliyun CLI credentials
2. List instances in cn-hangzhou
3. List instances in cn-shanghai
4. Switch between instances using config
5. List tables in each instance

**Expected Results:**
- Each region returns its own instance list
- Config command updates current context
- Each instance returns its own table list

### Scenario 4: Export Table Schema

**Steps:**
1. Configure Aliyun CLI credentials
2. Configure instance endpoint
3. Describe table and export to file

**Expected Results:**
- `aliyun otsutil desc -t mytable -o /tmp/meta.json` creates file with valid JSON
- File contains Name, Meta.Pk, Option, CU fields

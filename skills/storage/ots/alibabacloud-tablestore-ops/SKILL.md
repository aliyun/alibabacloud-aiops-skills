---
name: alibabacloud-tablestore-ops
description: |
  Alibaba Cloud Tablestore (OTS) Read-Only Operations Skill. Use for querying Tablestore instances and data tables via Aliyun CLI.
  Triggers: "tablestore", "ots", "表格存储", "list instance", "describe instance", "list table", "describe table", "aliyun otsutil"
---

# Tablestore Read-Only Operations

This skill provides CLI-based **read-only** operations for querying Alibaba Cloud Tablestore (OTS) instances and data tables. Tablestore is a fully managed NoSQL database service that supports storing and accessing large amounts of structured data.

**Architecture:** `Aliyun CLI (otsutil) → Tablestore Instance → Data Tables (Wide Table / TimeSeries)`

> **Scope:** This skill only covers read/query operations. No create, update, or delete operations are included.

## Prerequisites

- Tablestore service must be activated. See [Alibaba Cloud Console](https://otsnext.console.aliyun.com/)
- Obtain AccessKey ID and AccessKey Secret from [RAM Console](https://ram.console.aliyun.com/manage/ak)

> **Pre-check: Aliyun CLI Required (Version 3.3.0+)**
>
> Tablestore operations are performed via `aliyun otsutil` command, which is part of the Aliyun CLI.
> **IMPORTANT:** The `otsutil` subcommand is only available in Aliyun CLI version **3.3.0 or later**.
> The Homebrew version may be outdated - download directly from the official CDN.
> See [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.

## Installation

### Install Aliyun CLI (Version 3.3.0+)

> **WARNING:** The Homebrew version (`brew install aliyun-cli`) may not include `otsutil`. 
> Always download from the official CDN to ensure you get version 3.3.0+ with otsutil support.

**Option 1: Download Binary (Recommended)**

| Platform | Download |
|----------|----------|
| Mac (Universal) | [Mac Universal](https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz) |
| Linux (AMD64) | [Linux AMD64](https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz) |
| Linux (ARM64) | [Linux ARM64](https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz) |
| Windows (64-bit) | [Windows](https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip) |

**Option 2: Mac GUI Installer**

Download [Mac PKG](https://aliyuncli.alicdn.com/aliyun-cli-latest.pkg) and double-click to install.

### macOS / Linux Binary Setup

```bash
# Download (example for macOS Universal)
curl -L -o aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz

# Extract
tar -xzf aliyun-cli.tgz

# Move to PATH
sudo mv aliyun /usr/local/bin/

# Verify installation and version (must be 3.3.0+)
aliyun version

# Verify otsutil is available
aliyun otsutil help
```

### Windows Setup

1. Download the zip file from the download link above
2. Extract the zip file to get `aliyun.exe`
3. Add the directory to your PATH environment variable
4. Verify: `aliyun version` (must show 3.3.0 or later)

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command,
> ALL user-customizable parameters (e.g., RegionId, instance names, AccessKey, endpoint, etc.)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| `--endpoint` | Yes (for table ops) | Instance endpoint URL | - |
| `--instance` | Yes (for table ops) | Instance name | - |
| `-n` (instanceName) | Yes (for describe_instance) | Instance name | - |
| `-r` (regionId) | Yes (for instance ops) | Region ID (e.g., cn-hangzhou) | - |
| `-t` (tableName) | Yes (for table ops) | Data table name | - |

> **Note:** AccessKey credentials are configured via `aliyun configure`, not passed as command parameters.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** echo or print AccessKey values
> - **NEVER** ask the user to input AccessKey directly in plain text
> - **ONLY** configure credentials using `aliyun configure`
>
> **If no valid credentials exist:**
> 1. Obtain AccessKey from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. For security, use RAM user credentials with `AliyunOTSReadOnlyAccess` permission
> 3. Configure credentials using Aliyun CLI

### Configure Credentials (Aliyun CLI)

```bash
# Interactive configuration (recommended)
aliyun configure

# Follow prompts:
# Aliyun Access Key ID [None]: <YOUR_ACCESS_KEY_ID>
# Aliyun Access Key Secret [None]: <YOUR_ACCESS_KEY_SECRET>
# Default Region Id [None]: cn-hangzhou
# Default output format [json]: json
# Default Language [zh]: en
```

### Configure with Specific Profile

```bash
# Create a named profile
aliyun configure --profile tablestore-user

# Use the profile for otsutil commands
aliyun otsutil --profile tablestore-user list_instance -r cn-hangzhou
```

### Supported Authentication Modes

| Mode | Description | Configure Command |
|------|-------------|-------------------|
| AK | AccessKey ID/Secret (default) | `aliyun configure --mode AK` |
| RamRoleArn | RAM role assumption | `aliyun configure --mode RamRoleArn` |
| EcsRamRole | ECS instance role | `aliyun configure --mode EcsRamRole` |
| OIDC | OIDC role assumption | `aliyun configure --mode OIDC` |

## RAM Policy

Required permissions for Tablestore read-only operations:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ots:GetInstance",
        "ots:ListInstance",
        "ots:ListTable",
        "ots:DescribeTable"
      ],
      "Resource": "acs:ots:*:*:instance/*"
    }
  ]
}
```

Or use the managed policy: `AliyunOTSReadOnlyAccess`

See [references/ram-policies.md](references/ram-policies.md) for detailed permissions.

## Core Workflow

### Part 1: Instance Read Operations

#### Task 1: Configure Instance (Connect to Instance)

Configure the endpoint to select which instance to operate on.

> **Important:** You must configure the instance before performing any table operations.

**Command Format:**
```bash
aliyun otsutil config --endpoint <endpoint> --instance <instanceName>
```

**Endpoint Format:**
- Public: `https://<instance_name>.<region_id>.ots.aliyuncs.com`
- VPC: `https://<instance_name>.<region_id>.vpc.tablestore.aliyuncs.com`

**Example:**
```bash
aliyun otsutil config --endpoint https://myinstance.cn-hangzhou.ots.aliyuncs.com --instance myinstance
```

**Response:**
```json
{
  "Endpoint": "https://myinstance.cn-hangzhou.ots.aliyuncs.com",
  "AccessKeyId": "NTS**********************",
  "AccessKeySecret": "7NR2****************************************",
  "AccessKeySecretToken": "",
  "Instance": "myinstance"
}
```

#### Task 2: Describe Instance

View instance details including name, creation time, status, and quota.

**Command Format:**
```bash
aliyun otsutil describe_instance -r <regionId> -n <instanceName>
```

**Example:**
```bash
aliyun otsutil describe_instance -r cn-hangzhou -n myinstance
```

**Response:**
```json
{
  "ClusterType": "ssd",
  "CreateTime": "2024-07-18 09:15:10",
  "Description": "First instance created by CLI.",
  "InstanceName": "myinstance",
  "Network": "NORMAL",
  "Quota": { "EntityQuota": 64 },
  "ReadCapacity": 5000,
  "Status": 1,
  "TagInfos": {},
  "UserId": "1379************",
  "WriteCapacity": 5000
}
```

**Status Values:** `1` = Running. Other values indicate abnormal status.

#### Task 3: List Instances

Get all instances in a specified region.

**Command Format:**
```bash
aliyun otsutil list_instance -r <regionId>
```

**Example:**
```bash
aliyun otsutil list_instance -r cn-hangzhou
```

**Response:**
```json
["myinstance", "another-instance"]
```

> **Note:** Returns empty array `[]` if no instances exist in the region.

---

### Part 2: Data Table Read Operations

> **Prerequisite:** You must first configure an instance endpoint using `aliyun otsutil config` (Task 1) before running table operations.

#### Task 4: Select Table (`use`)

Select a data table for subsequent operations.

**Command Format:**
```bash
aliyun otsutil use --wc -t <tableName>
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--wc` | No | Indicates the target is a data table (wide column) or index table |
| `-t, --table` | Yes | Table name |

**Example:**
```bash
aliyun otsutil use -t mytable
```

#### Task 5: List Tables (`list`)

List table names under the current instance.

**Command Format:**
```bash
aliyun otsutil list [options]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `-a, --all` | No | List all table names (data tables + timeseries tables) |
| `-d, --detail` | No | List tables with detailed information |
| `-w, --wc` | No | List only data table (wide column) names |
| `-t, --ts` | No | List only timeseries table names |

**Examples:**
```bash
# List tables of the current type
aliyun otsutil list

# List all tables
aliyun otsutil list -a

# List only data tables
aliyun otsutil list -w

# List only timeseries tables
aliyun otsutil list -t
```

#### Task 6: Describe Table (`desc`)

View detailed table information including primary keys, TTL, max versions, and throughput.

**Command Format:**
```bash
aliyun otsutil desc [-t <tableName>] [-f <format>] [-o <outputPath>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `-t, --table` | No | Table name. If omitted, describes the currently selected table (via `use`) |
| `-f, --print_format` | No | Output format: `json` (default) or `table` |
| `-o, --output` | No | Save output to a local JSON file |

**Examples:**
```bash
# Describe the currently selected table
aliyun otsutil desc

# Describe a specific table
aliyun otsutil desc -t mytable

# Output in table format
aliyun otsutil desc -t mytable -f table

# Save table info to file
aliyun otsutil desc -t mytable -o /tmp/table_meta.json
```

**Example Response:**
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

**Response Fields:**

| Field | Description |
|-------|-------------|
| `Name` | Table name |
| `Meta.Pk` | Primary key columns: `C`=name, `T`=type (`string`/`integer`/`binary`), `Opt`=option (`none`/`auto`) |
| `Option.TTL` | Data time-to-live in seconds (`-1` = never expire) |
| `Option.Version` | Max attribute column versions retained |
| `CU.Read` / `CU.Write` | Reserved read/write capacity units |

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

**Quick Verification:**
1. After `aliyun otsutil config`: Response should show correct Endpoint and Instance
2. After `aliyun otsutil list_instance`: Verify expected instance names appear in the list
3. After `aliyun otsutil describe_instance`: Verify Status=1 (Running)
4. After `aliyun otsutil list`: Verify expected table names appear
5. After `aliyun otsutil desc`: Verify table schema and configuration are correct

## Related APIs

| CLI Command | Description |
|-------------|-------------|
| `aliyun otsutil config` | Configure CLI access (endpoint, instance) |
| `aliyun otsutil describe_instance` | Get instance details |
| `aliyun otsutil list_instance` | List all instances in a region |
| `aliyun otsutil use` | Select a data table for subsequent operations |
| `aliyun otsutil list` | List tables under the current instance |
| `aliyun otsutil desc` | View detailed table information |

See [references/related-apis.md](references/related-apis.md) for complete API reference.

## Best Practices

1. **Use RAM Users**: Create RAM users with read-only permissions instead of using root account credentials
2. **Use ReadOnly Policy**: Apply `AliyunOTSReadOnlyAccess` for query-only workflows
3. **Region Selection**: Choose the region closest to your application for lower latency
4. **Network Type**: Use VPC endpoint for better security in production environments
5. **Credential Security**: Use `aliyun configure` for credential management; never hardcode credentials
6. **Use Profiles**: Create dedicated profiles for different environments using `aliyun configure --profile <name>`
7. **Export Table Schema**: Use `aliyun otsutil desc -o <file>` to export and backup table definitions

## Reference Links

| Reference | Description |
|-----------|-------------|
| [cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
| [related-apis.md](references/related-apis.md) | Complete CLI command reference |
| [verification-method.md](references/verification-method.md) | Verification steps for each operation |
| [ram-policies.md](references/ram-policies.md) | RAM permission requirements |
| [Aliyun CLI GitHub](https://github.com/aliyun/aliyun-cli) | Aliyun CLI source code and documentation |
| [Instance Operations Doc](https://help.aliyun.com/zh/tablestore/developer-reference/instance-operations) | Instance operations reference |
| [Data Table Operations Doc](https://help.aliyun.com/zh/tablestore/developer-reference/widecolumn-modeled-data-table-operations-with-tablestore-cli) | Data table operations reference |

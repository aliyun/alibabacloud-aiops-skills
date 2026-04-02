# Tablestore Instance Operations

An instance is the entity you use to access and manage the Tablestore service. Each instance is equivalent to a database.

## Prerequisites

- Tablestore service must be activated. See [Activate Tablestore Service](https://help.aliyun.com/zh/tablestore/developer-reference/activate-tablestore-service).
- Aliyun CLI must be installed and configured.
- Tablestore CLI must be installed and configured.

---

## Create an Instance

Create a **high-performance instance** under the **CU model** (pay-as-you-go) in a specified region.

> **Important:**
> - The instance name must be globally unique within the region. If a name conflict occurs, choose a different name.
> - The Tablestore CLI can only create high-performance instances under the CU model (pay-as-you-go).

### Command Format

```bash
create_instance -d <description> -n <instanceName> -r <regionId>
```

### Parameters

| Parameter | Required | Example | Description |
|-----------|----------|---------|-------------|
| `-n` | Yes | `myinstance` | Instance name. See [Instance Naming Rules](https://help.aliyun.com/zh/tablestore/product-overview/instance). |
| `-r` | Yes | `cn-hangzhou` | Region ID. See [Regions](https://help.aliyun.com/zh/tablestore/product-overview/endpoints). |
| `-d` | No | `"My instance"` | Instance description. |

### Example

Create a high-performance instance named `myinstance` in the China East 1 (Hangzhou) region:

```bash
create_instance -d "First instance created by CLI." -n myinstance -r cn-hangzhou
```

---

## Describe an Instance

View instance information such as instance name, creation time, and account ID.

### Command Format

```bash
describe_instance -r <regionId> -n <instanceName>
```

### Parameters

| Parameter | Required | Example | Description |
|-----------|----------|---------|-------------|
| `-n` | Yes | `myinstance` | Instance name. |
| `-r` | Yes | `cn-hangzhou` | Region ID. |

### Example

```bash
describe_instance -r cn-hangzhou -n myinstance
```

### Sample Response

```json
{
  "ClusterType": "ssd",
  "CreateTime": "2024-07-18 09:15:10",
  "Description": "First instance created by CLI.",
  "InstanceName": "myinstance",
  "Network": "NORMAL",
  "Quota": {
    "EntityQuota": 64
  },
  "ReadCapacity": 5000,
  "Status": 1,
  "TagInfos": {},
  "UserId": "1379************",
  "WriteCapacity": 5000
}
```

---

## List Instances

List all instances in a specified region.

### Command Format

```bash
list_instance -r <regionId>
```

### Parameters

| Parameter | Required | Example | Description |
|-----------|----------|---------|-------------|
| `-r` | Yes | `cn-hangzhou` | Region ID. |

### Example

```bash
list_instance -r cn-hangzhou
```

### Sample Response

```json
[
  "myinstance"
]
```

> **Note:** If no instances exist in the region, the result will be empty.

---

## Configure an Instance

After creating an instance, you must configure it before operating on its resources.

### Command Format

```bash
config --endpoint <endpoint> --instance <instanceName>
```

### Parameters

| Parameter | Required | Example | Description |
|-----------|----------|---------|-------------|
| `--endpoint` | Yes | `http://myinstance.cn-hangzhou.ots.aliyuncs.com` | Instance endpoint. Supports public and VPC endpoints. |
| `--instance` | Yes | `myinstance` | Instance name. |

### Endpoint Format

| Network Type | Format |
|-------------|--------|
| **Public** | `http(s)://<instance_name>.<region_id>.ots.aliyuncs.com` |
| **VPC** | `http(s)://<instance_name>.<region_id>.vpc.tablestore.aliyuncs.com` |

### Example

```bash
config --endpoint http://myinstance.cn-hangzhou.ots.aliyuncs.com --instance myinstance
```

---

## Auto-Create Instance Workflow (for Agent Use)

When the agent needs to ensure an OTS instance exists, follow this workflow:

### Step 1: Extract Region ID from Endpoint

Parse the `region_id` from the user-provided `ots_endpoint`:
- `http://ots-cn-hangzhou.aliyuncs.com` → `cn-hangzhou`

### Step 2: Check If Instance Exists

```bash
tablestore_cli list_instance -r <region_id>
```

If the instance name appears in the returned list, it already exists — skip creation.

### Step 3: Create Instance If Not Found

```bash
tablestore_cli create_instance -n <instance_name> -r <region_id> -d "Auto-created by Agent"
```

> **Note:** This operation is idempotent — if the instance already exists, the command will return an error but will not cause side effects. Always check existence first to provide a better user experience.

### Step 4: Verify Creation

```bash
tablestore_cli describe_instance -r <region_id> -n <instance_name>
```

Confirm `"Status": 1` (active) before proceeding.

# OSS Mounting Guide

This guide covers how to mount and use Alibaba Cloud OSS (Object Storage Service) as distributed storage in MaxFrame jobs using the `with_fs_mount` decorator.

## Overview

The `with_fs_mount` decorator enables file system-level mounting of OSS buckets in MaxCompute. This allows you to access OSS files like a local disk, which is more efficient than traditional SDK-based methods like `pd.read_csv("oss://...")`.

### Use Cases

- Loading raw data from OSS for cleaning or processing
- Writing intermediate results to OSS for downstream consumption
- Sharing trained model files, configuration files, and other static resources

## Prerequisites

### 1. Enable OSS Service and Create Bucket

1. Log in to [OSS Console](https://oss.console.aliyun.com/)
2. Navigate to **Bucket List** in the left navigation
3. Click **Create Bucket**
4. Note your bucket name (e.g., `xxx-oss-test-sh`)

### 2. Create RAM Role for MaxCompute

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Navigate to **Identity Management > Roles**
3. Click **Create Role**
4. Click **Create Service Linked Role** in the top right
5. Select **Cloud Service** as the trusted principal type
6. Select **MaxCompute (Cloud Native Big Data Computing Service)** as the trusted principal
7. In the **Permission Management** tab, click **Add Authorization**
8. Add the following permission policies:

| Policy | Description | Link |
|--------|-------------|------|
| `AliyunOSSFullAccess` | Full access to OSS | [Policy Detail](https://ram.console.aliyun.com/policies/detail?policyType=System&policyName=AliyunOSSFullAccess) |
| `AliyunMaxComputeFullAccess` | Full access to MaxCompute | [Policy Detail](https://ram.console.aliyun.com/policies/detail?policyType=System&policyName=AliyunMaxComputeFullAccess) |

## Basic Usage

### Recommended: Using Role ARN

```python
from maxframe.udf import with_fs_mount

@with_fs_mount(
    "oss://oss-cn-<region>-internal.aliyuncs.com/<bucket-name>/path/",
    "/mnt/oss_data",
    storage_options={
        "role_arn": "acs:ram::<uid>:role/<role-name>"
    },
)
def _process(batch_df):
    import os
    if os.path.exists('/mnt/oss_data'):
        print(f"Mounted files: {os.listdir('/mnt/oss_data')}")
    else:
        print("/mnt/oss_data not mounted!")
    return batch_df * 2
```

### Not Recommended: Using AccessKey (Testing Only)

```python
# For testing purposes only - NOT recommended for production
storage_options={
    "access_key_id": "LTAI5t...",
    "access_key_secret": "Wp9H..."
}
```

**Important:** Avoid hardcoding AccessKey. Using `role_arn` allows the system to automatically request temporary STS tokens, preventing AK/SK leakage.

## Resource Configuration

Use `with_running_options` to control resource allocation:

```python
from maxframe.udf import with_running_options, with_fs_mount

@with_running_options(engine="dpe", cpu=2, memory=16)
@with_fs_mount(
    "oss://oss-cn-<region>-internal.aliyuncs.com/<bucket>/path/",
    "/mnt/oss_data",
    storage_options={"role_arn": "acs:ram::<uid>:role/<role-name>"},
)
def _process(batch_df):
    ...
```

### Resource Recommendations

| Parameter | Recommended Value | Notes |
|-----------|------------------|-------|
| `engine` | `"dpe"` | FS Mount only supports DPE engine |
| `cpu` | 1-4 | Increase for complex I/O or decompression |
| `memory` | 8GB+ | Use ≥16GB for large file loading |

## Complete Example: Batch Processing

```python
import os
from odps import ODPS
from maxframe import new_session
from maxframe.udf import with_fs_mount, with_running_options
import maxframe.dataframe as md

# Initialize ODPS client
o = ODPS(
    access_id=os.getenv('ODPS_ACCESS_ID'),
    secret_access_key=os.getenv('ODPS_ACCESS_KEY'),
    project=os.getenv('ODPS_PROJECT'),
    endpoint=os.getenv('ODPS_ENDPOINT'),
)

# Set image (default DPE runtime includes ossfs2)
from maxframe import config
config.options.sql.settings = {
    "odps.session.image": "maxframe_service_dpe_runtime"
}

# Start session
session = new_session(o)
print("LogView:", session.get_logview_address())
print("Session ID:", session.session_id)

# Define UDF with OSS mount
@with_running_options(engine="dpe", cpu=2, memory=8)
@with_fs_mount(
    "oss://oss-cn-<region>-internal.aliyuncs.com/<bucket>/test/",
    "/mnt/oss_data",
    storage_options={
        "role_arn": "acs:ram::<uid>:role/maxframe-oss"
    },
)
def _process(batch_df):
    import pandas as pd
    import os

    # Step 1: Verify mount
    mount_point = "/mnt/oss_data"
    if not os.path.exists(mount_point):
        raise RuntimeError("OSS mount failed!")

    # Step 2: Load data (e.g., mapping table, dictionary)
    mapping_file = os.path.join(mount_point, "category_map.csv")
    if os.path.isfile(mapping_file):
        mapping_df = pd.read_csv(mapping_file)

    # Step 3: Process current chunk
    result = batch_df.copy()
    result['F'] = result['A'] * 10

    return result

# Create DataFrame and apply UDF
data = [[1.0, 2.0, 3.0, 4.0, 5.0], ...]
df = md.DataFrame(data, columns=['A', 'B', 'C', 'D', 'E'])

result_df = df.mf.apply_chunk(
    _process,
    skip_infer=True,
    output_type="dataframe",
    dtypes=df.dtypes,
    index=df.index
)

# Execute and fetch results
result = result_df.execute().fetch()
```

**Note:** `skip_infer=True` skips type inference for faster execution, but requires correct `dtypes` and `index` parameters.

## Debugging

### Verify Mount Status

Add debug logs in your UDF:

```python
import os

print("Mount path exists:", os.path.exists("/mnt/oss_data"))
print("Files in mount:", os.listdir("/mnt/oss_data") if os.path.exists("/mnt/oss_data") else [])
```

Check LogView output for messages like:

```
FS Mount 成功！/mnt/oss_data: ['data.csv', 'config.json', 'model.pkl']
Processing batch with shape: (1000, 5)
```

## OSSFS Dependency

The default `maxframe_service_dpe_runtime` image includes OSSFS. For custom images, you need to install:

- `ossfs2_2.0.3.1_linux_x86_64.deb`

## Key Points

1. **Security First:** Always use `role_arn` instead of hardcoded AccessKey
2. **Engine Requirement:** FS Mount only works with DPE engine (`engine="dpe"`)
3. **Resource Planning:** Allocate sufficient memory for large file operations
4. **Mount Verification:** Always check mount status before processing
5. **Error Handling:** Add proper error handling for mount failures

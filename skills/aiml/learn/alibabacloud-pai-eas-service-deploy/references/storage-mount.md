# Storage Mount Configuration Guide

> Reference: https://help.aliyun.com/zh/pai/user-guide/mount-storage-to-services

EAS services support multiple storage mount methods to mount model files, code files, or other config files into service instances.

**⚠️ Important: OSS models MUST be mounted via storage config as local paths (e.g. `/model_dir`), then use local paths in startup commands. Never pass `oss://` URL directly to vllm/sglang commands!**

**Table of Contents**
- [Storage Type Selection Guide](#storage-type-selection-guide)
- [Supported Storage Types](#supported-storage-types)
- [OSS Mount](#oss-mount)
- [Dataset Mount](#dataset-mount)
- [NAS Mount](#nas-mount)
- [CPFS Mount](#cpfs-mount)
- [Full Config Example](#full-config-example)
- [Notes](#notes)

---

## Storage Type Selection Guide

| Data Type | Recommended Storage | Description |
|-----------|-------------------|-------------|
| Models, images, videos (primarily read) | **OSS** | Most common |
| Frequent small file I/O, shared read/write across instances | NAS | General-purpose NAS |
| HPC, AI training, ultra-low latency needed | Ultra-fast NAS / CPFS | High throughput |
| PAI registered datasets | **Dataset** | Public AI assets |
| Git repositories | Git mount | Read-only |
| PAI registered code | Code config | Public AI assets |
| PAI registered models | PAI models | Read-only |

---

## Supported Storage Types

| Type | Status | Description |
|------|--------|-------------|
| OSS | ✅ Supported | Most common, mount OSS bucket |
| NAS | ✅ Supported | General-purpose NAS, ultra-fast NAS |
| CPFS | ✅ Supported | CPFS (requires Lingjun quota) |
| Dataset | ✅ Supported | PAI dataset (OSS type only) |
| Git mount | ❌ Not supported | Git repositories |
| Code config | ❌ Not supported | PAI code sets |
| PAI models | ❌ Not supported | PAI registered models |
| Image mount | ❌ Not supported | Docker Image mount |
| EmptyDir | ❌ Not supported | Local temp directory |

---

## OSS Mount

### Config Example

```json
{
  "storage": [{
    "mount_path": "/mnt/data/",
    "oss": {
      "path": "oss://bucket-name/path/",
      "readOnly": true
    }
  }]
}
```

### Parameter Description

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mount_path` | string | ✅ | Target path in service instance, e.g. `/mnt/data/` |
| `oss.path` | string | ✅ | OSS path, format `oss://bucket/path/` (note trailing `/`) |
| `oss.readOnly` | bool | ❌ | Read-only, default false |

### Interaction Flow

```
Step 2.2: Storage Mount

1. Do you need to mount storage?
| # | Option | Description |
|---|--------|-------------|
| 1 | Yes | Mount model files or data |
| 2 | No (skip) | No storage mount |

2. Select storage type:
| # | Storage Type | Description |
|---|-------------|-------------|
| 1 | OSS | Mount OSS bucket (most common) |
| 2 | Dataset | Use PAI dataset |

3. OSS config:
   a. Query bucket list: ossutil ls
   b. Select bucket (paginated, max 10)
   c. List directory: ossutil ls oss://bucket-name/
   d. Select model directory
   e. Mount path [/model_dir]: 1. Use default  2. Custom
   f. Permissions [read-only]: 1. Read-only (recommended)  2. Read-write
```

### Multiple OSS Mounts

```json
{
  "storage": [
    {
      "mount_path": "/models",
      "oss": {
        "path": "oss://my-bucket/models/",
        "readOnly": true
      }
    },
    {
      "mount_path": "/data",
      "oss": {
        "path": "oss://my-bucket/data/",
        "readOnly": false
      }
    }
  ]
}
```

### FAQ

**Q: Mounted OSS but getting file not found error?**

A: Usually a path issue. For example:
- Mount `oss://my-bucket/` to `/mnt/data`
- File in OSS: `oss://my-bucket/subfolder/myfile.txt`
- Container access path: `/mnt/data/subfolder/myfile.txt` (not `/mnt/data/myfile.txt`)

**Q: Can I mount OSS from a different region?**

A: No. EAS cannot cross-region mount OSS. Use OSS cross-region replication to sync data to the same region.

---

## Dataset Mount

Mount PAI datasets as public AI assets.

**⚠️ Only OSS-type custom datasets are supported for mounting.**

### Config Example

```json
{
  "storage": [{
    "mount_path": "/mnt/dataset/",
    "dataset": {
      "id": "d-pcsah1t86bm8xxxx",
      "version": "v1",
      "read_only": true
    }
  }]
}
```

### Parameter Description

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mount_path` | string | ✅ | Target path in service instance |
| `dataset.id` | string | ✅ | Dataset ID |
| `dataset.version` | string | ❌ | Dataset version, e.g. `v1` |
| `dataset.read_only` | bool | ❌ | Read-only, default true |

### Query Datasets

```bash
aliyun aiworkspace list-datasets --region cn-hangzhou
```

### Create Datasets

Reference: [Create and manage datasets](https://help.aliyun.com/zh/pai/user-guide/create-and-manage-datasets)

---

## NAS Mount

NAS mount (general-purpose and ultra-fast NAS) only supports same-region intranet mount. Requires direct network connectivity to the NAS VSwitch.

### Config Example

```json
{
  "storage": [{
    "mount_path": "/mnt/data/",
    "nfs": {
      "path": "/",
      "server": "06ba74****-a****.cn-hangzhou.nas.aliyuncs.com",
      "readOnly": false
    }
  }]
}
```

### Parameter Description

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mount_path` | string | ✅ | Target path in service instance, e.g. `/mnt/data/` |
| `nfs.server` | string | ✅ | NAS mount point address |
| `nfs.path` | string | ✅ | Source path in NAS, e.g. `/` |
| `nfs.readOnly` | bool | ❌ | Read-only, default false |
| `nfs.resourceGroup` | string | ❌ | File system resource group |

### Interaction Flow

```
NAS Mount Config:

1. NAS mount point: 06ba74****-a****.cn-hangzhou.nas.aliyuncs.com
2. File system path [/]: 1. Use default  2. Custom
3. Mount path [/mnt/data/]: 1. Use default  2. Custom
4. Permissions [read-only]: 1. Read-only  2. Read-write
```

### Notes

- **Same-region only**: NAS only supports same-region intranet mount
- **Network config**: Requires direct network connectivity to the NAS VSwitch
- **Console**: View file system ID and mount point at [NAS Console](https://nasnext.console.aliyun.com/)
- **Network setup**: See [Network Configuration](https://help.aliyun.com/zh/pai/user-guide/configure-network-connectivity)

---

## CPFS Mount

CPFS file system mount, suitable for HPC and AI training scenarios.

### Config Example

```json
{
  "storage": [{
    "mount_path": "/mnt/data/",
    "nfs": {
      "path": "/",
      "server": "cpfs-xxx.cn-hangzhou.cpfs.aliyuncs.com",
      "readOnly": false
    }
  }]
}
```

### Notes

- **Quota requirement**: Only supported when deploying EAS services with Lingjun quota
- **Same-region only**: CPFS only supports same-region intranet mount
- **Network config**: Requires direct network connectivity to the CPFS VSwitch

---

## Git Mount (Not Supported)

```json
{
  "storage": [{
    "mount_path": "/mnt/data/",
    "git": {
      "repo": "https://codeup.aliyun.com/xxx/eas/aitest.git",
      "branch": "master",
      "commit": "xxx",
      "username": "username",
      "password": "password or access token"
    }
  }]
}
```

---

## EmptyDir Mount (Not Supported)

Read/write to local disk during instance runtime. Content persists across instance restarts.

```json
{
  "storage": [{
    "mount_path": "/data_image",
    "empty_dir": {}
  }]
}
```

### Shared Memory Config

```json
{
  "storage": [{
    "mount_path": "/dev/shm",
    "empty_dir": {
      "medium": "memory",
      "size_limit": 20
    }
  }]
}
```

---

## Full Config Example

```json
{
  "metadata": {
    "name": "my-service",
    "instance": 1
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000
  }],
  "storage": [
    {
      "mount_path": "/model_dir",
      "oss": {
        "path": "oss://my-bucket/models/qwen/",
        "readOnly": true
      }
    },
    {
      "mount_path": "/mnt/dataset/",
      "dataset": {
        "id": "d-xxx",
        "version": "v1",
        "read_only": true
      }
    }
  ]
}
```

---

## Notes

1. **Mount paths cannot overlap**
2. **Mount paths cannot be system reserved paths**: `/`, `/bin`, `/etc`, `/usr`, etc.
3. **OSS path format must be correct**: `oss://bucket/path/`, note the trailing `/`
4. **Permissions**: Model files should use `readOnly: true` to prevent accidental modification
5. **Without storage mount**: Files downloaded to the instance are stored on system disk and will be cleared on restart or update

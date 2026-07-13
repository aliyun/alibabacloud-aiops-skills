# Service Config Field Reference

> This document lists all JSON config fields for PAI-EAS services.

**Table of Contents**
- [Config Structure Overview](#config-structure-overview)
- [metadata (required)](#metadata-required)
- [containers (required)](#containers-required)
- [cloud (public resource group)](#cloud-public-resource-group)
- [storage (mount)](#storage-mount)
- [networking](#networking)
- [autoscaler](#autoscaler)
- [runtime](#runtime)
- [features](#features)
- [Full Example](#full-example)

## Config Structure Overview

```json
{
  "metadata": { ... },      // Service metadata (required)
  "containers": [ ... ],    // Container config (required)
  "cloud": { ... },         // Public resource group config
  "storage": [ ... ],       // Storage mount
  "networking": { ... },    // Network config
  "autoscaler": { ... },    // Autoscaling
  "runtime": { ... },       // Runtime config
  "features": { ... }       // Feature config
}
```

---

## metadata (required)

Service metadata defining basic service information.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | ✅ | - | Service name, lowercase letters/digits/underscores, 3-63 chars |
| `instance` | int | ❌ | 1 | Number of replicas |
| `workspace_id` | string | ❌ | - | Workspace ID |
| `resource` | string | ❌ | - | Dedicated resource group ID (mutually exclusive with cloud.computing) |
| `disk` | string | ❌ | - | Temp disk size, e.g. "30Gi" |
| `shm_size` | int | ❌ | 64 | Shared memory size (GB) |
| `rdma` | int | ❌ | - | Number of RDMA NICs |
| `enable_grpc` | bool | ❌ | false | Enable GRPC protocol |
| `rolling_strategy` | object | ❌ | - | Rolling update strategy |
| `eas` | object | ❌ | - | EAS advanced config |

### rolling_strategy

| Field | Type | Description |
|-------|------|-------------|
| `max_surge` | int | Max new instances during rolling update |
| `max_unavailable` | int | Max unavailable instances during rolling update |

---

## containers (required)

Container config array, must contain at least one container.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `image` | string | ✅ | - | Image URI |
| `port` | int | ✅ | 8000 | Service port |
| `script` | string | ❌ | - | Startup script |
| `command` | string | ❌ | - | Startup command |
| `args` | []string | ❌ | - | Command arguments |
| `env` | []EnvVar | ❌ | - | Environment variables |
| `prepare` | Prepare | ❌ | - | Pre-install config |
| `startup_check` | Probe | ❌ | - | Startup probe |
| `liveness_check` | Probe | ❌ | - | Liveness probe |
| `health_check` | Probe | ❌ | - | Health check |
| `resources` | ResourceRequirements | ❌ | - | Resource limits |

### EnvVar

```json
{"name": "ENV_NAME", "value": "env_value"}
```

### Prepare

```json
{
  "pythonRequirements": ["numpy==1.6.4", "pandas"],
  "pythonRequirementsPath": "/path/to/requirements.txt"
}
```

### Probe (Health Check)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `http_get` | object | - | HTTP check config |
| `initial_delay_seconds` | int | 15 | Initial delay in seconds |
| `period_seconds` | int | 10 | Check interval in seconds |
| `timeout_seconds` | int | 1 | Timeout in seconds |
| `success_threshold` | int | 1 | Success threshold |
| `failure_threshold` | int | 1 | Failure threshold |

```json
{
  "http_get": {"path": "/health", "port": 8000},
  "initial_delay_seconds": 15,
  "period_seconds": 10,
  "timeout_seconds": 1,
  "success_threshold": 1,
  "failure_threshold": 3
}
```

---

## cloud (public resource group)

Config when using public resource group.

### cloud.computing

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `instance_type` | string | either/or | Instance type, e.g. "ecs.gn6i-c8g1.2xlarge" |
| `instances` | []object | either/or | Multi-spec instance list |

```json
{
  "cloud": {
    "computing": {
      "instance_type": "ecs.gn6i-c8g1.2xlarge"
    }
  }
}
```

Or:

```json
{
  "cloud": {
    "computing": {
      "instances": [
        {"type": "ecs.gn6i-c8g1.2xlarge"},
        {"type": "ecs.gn7-c12g1.12xlarge"}
      ]
    }
  }
}
```

### cloud.networking

VPC network config (required for ALB/NLB).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vpc_id` | string | ✅ | VPC ID |
| `vswitch_id` | string | ✅ | VSwitch ID, comma-separated for multi-zone (e.g. `"vsw-a,vsw-b"`) |
| `security_group_id` | string | ✅ | Security group ID |

---

## storage (mount)

Storage mount config array.

### OSS Mount

```json
{
  "mount_path": "/models",
  "oss": {
    "path": "oss://my-bucket/models/",
    "readOnly": true
  }
}
```

### NAS/NFS Mount

```json
{
  "mount_path": "/data",
  "nfs": {
    "server": "xxx.cn-hangzhou.nas.aliyuncs.com",
    "path": "/share"
  }
}
```

### Dataset Mount

```json
{
  "mount_path": "/dataset",
  "dataset": {
    "id": "d-xxx",
    "version": "v1",
    "read_only": true
  }
}
```

---

## networking

### Shared Gateway

No networking field needed.

### ALB Dedicated Gateway

```json
{
  "networking": {
    "gateway": "gw-xxx"
  }
}
```

### NLB

```json
{
  "networking": {
    "nlb": [
      {
        "id": "default",  // or "nlb-xxx"
        "listener_port": 8000,
        "netType": "intranet"
      }
    ]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | "default" for system-created, or actual NLB ID |
| `listener_port` | int | Listener port (cannot be 8080) |
| `netType` | string | "intranet" or "internet" |

---

## autoscaler

### ⚠️ Important: Field Naming Convention

**EAS API uses camelCase**:

| ✅ Correct Field Name | ❌ Wrong Field Name | Description |
|----------------------|---------------------|-------------|
| `min` | ~~`min_replica`~~ | Min replicas |
| `max` | ~~`max_replica`~~ | Max replicas |
| `scaleStrategies` | ~~`scale_strategies`~~ | Scaling strategy array |
| `metricName` | ~~`metric_name`~~ | Metric name |

```json
{
  "autoscaler": {
    "min": 1,
    "max": 10,
    "scaleStrategies": [
      {"metricName": "qps", "threshold": 100},
      {"metricName": "cpu", "threshold": 80}
    ]
  }
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `min` | int | ❌ | 1 | Min replicas |
| `max` | int | ❌ | 10 | Max replicas |
| `scaleStrategies` | []object | ❌ | - | Scaling strategies |

### scaleStrategies

| Field | Description |
|-------|-------------|
| `metricName` | Metric name: qps, cpu, gpu, memory |
| `threshold` | Trigger threshold |

---

## runtime

```json
{
  "runtime": {
    "termination_grace_period": 30
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `termination_grace_period` | int | 30 | Graceful shutdown wait time (seconds) |

---

## features

```json
{
  "features": {
    "eas.aliyun.com/gpu-driver-version": "550.54.15"
  }
}
```

Common features:
- `eas.aliyun.com/gpu-driver-version`: GPU driver version

---

## Full Example

```json
{
  "metadata": {
    "name": "my-llm-service",
    "instance": 2,
    "workspace_id": "<workspace_id>",
    "disk": "30Gi",
    "shm_size": 64,
    "enable_grpc": true,
    "rolling_strategy": {
      "max_surge": 1,
      "max_unavailable": 0
    }
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000,
    "script": "vllm serve /models/qwen-7b --port 8000 --tensor-parallel-size 2",
    "env": [
      {"name": "NCCL_P2P_DISABLE", "value": "1"}
    ],
    "startup_check": {
      "http_get": {"path": "/health", "port": 8000},
      "initial_delay_seconds": 60,
      "period_seconds": 10,
      "failure_threshold": 30
    }
  }],
  "cloud": {
    "computing": {
      "instance_type": "ecs.gn7-c12g1.12xlarge"
    },
    "networking": {
      "vpc_id": "vpc-xxx",
      "vswitch_id": "vsw-zone-a,vsw-zone-b",
      "security_group_id": "sg-xxx"
    }
  },
  "storage": [{
    "mount_path": "/models",
    "oss": {
      "path": "oss://my-bucket/models/qwen-7b",
      "readOnly": true
    }
  }],
  "networking": {
    "gateway": "gw-xxx"
  },
  "autoscaler": {
    "min": 1,
    "max": 5,
    "scaleStrategies": [
      {"metricName": "qps", "threshold": 50}
    ]
  },
  "runtime": {
    "termination_grace_period": 60
  }
}
```

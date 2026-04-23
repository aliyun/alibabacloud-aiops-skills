# Service Features Configuration Guide

Detailed configuration guide for health check, rolling update, GRPC, and autoscaling.

**Table of Contents**
- [Feature Selection Interaction](#feature-selection-interaction)
- [Health Check](#1-health-check)
- [Rolling Update](#2-rolling-update)
- [GRPC](#3-grpc)
- [Autoscaling](#4-autoscaling)
- [Combined Feature Example](#5-combined-feature-example)

---

## Feature Selection Interaction

```
| # | Feature | Default Status |
|---|---------|---------------|
| 1 | Health Check | ✅ Enabled |
| 2 | Rolling Update | ✅ Enabled |
| 3 | GRPC | ❌ Disabled |
| 4 | Autoscaling | ❌ Disabled |

Select features to enable (multi-select with comma, e.g. 1,2,4), or press Enter for defaults:
```

**User input handling**:
- Enter numbers (e.g. `1,3,4`) → Enable corresponding features
- Press Enter → Use defaults (health check + rolling update)
- Enter `none` → Disable all features

---

## 1. Health Check

Health check monitors whether the service is running normally, including startup and liveness probes.

### Startup Probe (startup_check)

Checks whether the service is ready after startup.

### Parameter Description

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| http_get.path | string | `/` | HTTP check path |
| http_get.port | int | 8000 | Check port |
| initial_delay_seconds | int | 60 | Initial delay (how long after startup to begin checking) |
| period_seconds | int | 10 | Check interval |
| timeout_seconds | int | 1 | Single check timeout |
| success_threshold | int | 1 | Success threshold (consecutive successes to consider healthy) |
| failure_threshold | int | 30 | Failure threshold (consecutive failures to consider unhealthy) |

### JSON Config

```json
{
  "containers": [{
    "startup_check": {
      "http_get": {
        "path": "/health",
        "port": 8000
      },
      "initial_delay_seconds": 60,
      "period_seconds": 10,
      "timeout_seconds": 1,
      "success_threshold": 1,
      "failure_threshold": 30
    }
  }]
}
```

### TCP Check

```json
{
  "containers": [{
    "startup_check": {
      "tcp_socket": {
        "port": 8000
      },
      "initial_delay_seconds": 60,
      "period_seconds": 10
    }
  }]
}
```

### Interaction Flow

```
Configure health check parameters:

Check type:
  1. HTTP (recommended)
  2. TCP

HTTP check path [/health]: 1. Use default  2. Custom
Initial delay seconds [60]: 1. Use default  2. Custom
Check interval seconds [10]: 1. Use default  2. Custom
Failure threshold [30]: 1. Use default  2. Custom
```

---

## 2. Rolling Update

Rolling update ensures zero-downtime service upgrades through graceful shutdown and rolling strategy.

### Parameter Description

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| termination_grace_period | int | 30 | Graceful shutdown wait time (seconds) |
| max_surge | int | 1 | Max new instances during rolling |
| max_unavailable | int | 0 | Max unavailable instances during rolling |
| enable_sigterm | bool | true | Enable SIGTERM signal |

### JSON Config

```json
{
  "metadata": {
    "rolling_strategy": {
      "max_surge": 1,
      "max_unavailable": 0
    }
  },
  "eas": {
    "termination_grace_period": 30
  },
  "rpc": {
    "enable_sigterm": true
  }
}
```

### Parameter Details

**termination_grace_period**:
- How long to wait after receiving stop signal before force termination
- Recommended: 30-120 seconds
- Should be longer than time to process current requests

**max_surge**:
- How many new instances can be started during rolling update
- Higher value = faster update, but more resource consumption
- Recommended: 1-2

**max_unavailable**:
- Max instances that can be unavailable during rolling update
- Set to 0 for zero-downtime update
- Recommended: 0 (production)

### Interaction Flow

```
Configure rolling update parameters:

Graceful shutdown wait (seconds) [30]: 1. Use default  2. Custom
Max new instances [1]: 1. Use default  2. Custom
Max unavailable instances [0]: 1. Use default  2. Custom
```

---

## 3. GRPC

Enable GRPC protocol support. Service will support both HTTP and GRPC calls.

### JSON Config

```json
{
  "metadata": {
    "enable_grpc": true
  }
}
```

### Description

- Once enabled, service listens for both HTTP and GRPC requests
- GRPC port defaults to same as HTTP port
- Suitable for high-performance RPC scenarios

### Interaction Flow

```
GRPC protocol enabled.
Service will support both HTTP and GRPC calls.
```

---

## 4. Autoscaling

Auto-adjust service replicas based on load.

### ⚠️ Important: Field Naming Convention

**EAS API uses camelCase**, ensure correct field names:

| ✅ Correct Field Name | ❌ Wrong Field Name | Description |
|----------------------|---------------------|-------------|
| `min` | ~~`min_replica`~~ | Min replicas |
| `max` | ~~`max_replica`~~ | Max replicas |
| `scaleStrategies` | ~~`scale_strategies`~~ | Scaling strategy array |
| `metricName` | ~~`metric_name`~~ | Metric name |

**Using wrong field names will cause config to be ignored, falling back to defaults (min=0, max=0)!**

### Parameter Description

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| min | int | 1 | Min replicas |
| max | int | 10 | Max replicas |
| metricName | string | qps | Scaling metric: qps, cpu, gpu, memory |
| threshold | int | 100 | Scaling threshold |

### JSON Config

```json
{
  "autoscaler": {
    "min": 1,
    "max": 10,
    "scaleStrategies": [
      {"metricName": "qps", "threshold": 100}
    ]
  }
}
```

### Scaling Metrics

| Metric | Description | Recommended Threshold |
|--------|-------------|----------------------|
| qps | Queries per second | 50-200 |
| cpu | CPU utilization (%) | 70-85 |
| gpu | GPU utilization (%) | 70-85 |
| memory | Memory utilization (%) | 70-85 |

### Interaction Flow

```
Configure autoscaling parameters:

Min replicas (min) [1]: 1. Use default  2. Custom
Max replicas (max) [10]: 1. Use default  2. Custom

Scaling metric (metricName):
  1. qps (recommended)
  2. cpu
  3. gpu
  4. memory

Select metric (enter number):

Scaling threshold [100]: 1. Use default  2. Custom
```

### Config Examples

**Example 1: QPS-based autoscaling**
```json
{
  "autoscaler": {
    "min": 1,
    "max": 5,
    "scaleStrategies": [
      {"metricName": "qps", "threshold": 50}
    ]
  }
}
```

**Example 2: Multi-metric autoscaling**
```json
{
  "autoscaler": {
    "min": 2,
    "max": 10,
    "scaleStrategies": [
      {"metricName": "qps", "threshold": 100},
      {"metricName": "cpu", "threshold": 80}
    ]
  }
}
```

### ⚠️ Common Mistakes

**Mistake 1: Using snake_case naming**
```json
// ❌ Wrong - fields will be ignored
{
  "autoscaler": {
    "min_replica": 1,
    "max_replica": 10,
    "scale_strategies": [
      {"metric_name": "qps", "threshold": 100}
    ]
  }
}

// ✅ Correct - use camelCase
{
  "autoscaler": {
    "min": 1,
    "max": 10,
    "scaleStrategies": [
      {"metricName": "qps", "threshold": 100}
    ]
  }
}
```

**Mistake 2: Setting min and max to same value**
```json
// ❌ Wrong - cannot scale with equal min and max
{
  "autoscaler": {
    "min": 5,
    "max": 5
  }
}

// ✅ Correct - max > min
{
  "autoscaler": {
    "min": 1,
    "max": 5
  }
}
```

---

## 5. Combined Feature Example

Enable health check, rolling update, and GRPC together:

```json
{
  "metadata": {
    "name": "my-service",
    "instance": 2,
    "enable_grpc": true,
    "rolling_strategy": {
      "max_surge": 1,
      "max_unavailable": 0
    }
  },
  "eas": {
    "termination_grace_period": 30
  },
  "rpc": {
    "enable_sigterm": true
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000,
    "startup_check": {
      "http_get": {"path": "/health", "port": 8000},
      "initial_delay_seconds": 60,
      "period_seconds": 10,
      "failure_threshold": 30
    }
  }],
  "autoscaler": {
    "min": 1,
    "max": 5,
    "scaleStrategies": [
      {"metricName": "qps", "threshold": 50}
    ]
  }
}
```

---

*References*:
- [Health Check Docs](https://help.aliyun.com/zh/pai/user-guide/advanced-configuration-health-check)
- [Rolling Update Docs](https://help.aliyun.com/zh/pai/user-guide/scrolling-updates-with-graceful-exit)
- [Autoscaling Docs](https://help.aliyun.com/zh/pai/user-guide/autoscaling)

*Last updated*: 2025-03-21 - Fixed autoscaler field naming

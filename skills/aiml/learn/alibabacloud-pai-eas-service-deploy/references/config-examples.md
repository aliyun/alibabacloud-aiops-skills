# Service Configuration Examples

**Contents**
- [JSON Field Conventions](#json-field-conventions-important)
- [Container Mode Configuration](#container-mode-configuration-important)
- [Basic Configuration](#basic-configuration)
- [Full Configuration](#full-configuration)
- [Public Resource Group Configuration](#public-resource-group-configuration)
- [Dedicated Resource Group Configuration](#dedicated-resource-group-configuration)
- [ALB Gateway Configuration](#alb-gateway-configuration)
- [NLB Configuration](#nlb-configuration)
- [Autoscaling Configuration](#autoscaling-configuration)
- [Storage Mount Configuration](#storage-mount-configuration)

## ⚠️ JSON Field Conventions (Important)

**The service name MUST be placed in the `metadata.name` field**, not at the top level:

```json
{
  "metadata": {
    "name": "my-service",    // ✅ Correct: service name goes here
    "instance": 1
  }
}
```

**Incorrect examples:**

```json
{
  "service_name": "my-service",  // ❌ Wrong: invalid field
  "name": "my-service"           // ❌ Wrong: not inside metadata
}
```

## Container Mode Configuration (Important)

When deploying from an image, you MUST configure the `containers` field:

```json
{
  "metadata": { "name": "my-service", "instance": 1 },
  "containers": [{
    "image": "<image-uri>",
    "port": 8000,
    "command": "<startup command>"
  }],
  "storage": [{ "mount_path": "/model_dir", "oss": { "path": "oss://bucket/models/" } }],
  "cloud": { "computing": { "instance_type": "ecs.gn6i-c8g1.2xlarge" } }
}
```

**Key fields:**
- `metadata.name` - service name (required)
- `containers[].image` - image URI (required)
- `containers[].port` - service port (required)
- `containers[].command` - startup command (optional)

**⚠️ Note:** Use the `containers` field; do NOT use `processor` or `processor_path`.

## Basic Configuration

```json
{
  "metadata": {
    "name": "simple_service",
    "instance": 1
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn6i-c8g1.2xlarge" }
  }
}
```

## Full Configuration

```json
{
  "metadata": {
    "name": "myservice",
    "instance": 2,
    "workspace_id": "368951",
    "disk": "30Gi",
    "shm_size": 100,
    "enable_grpc": true
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000,
    "env": [
      {"name": "NCCL_P2P_DISABLE", "value": "1"}
    ]
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn6e-c12g1.12xlarge" },
    "networking": {
      "vpc_id": "vpc-xxx",
      "vswitch_id": "vsw-xxx",
      "security_group_id": "sg-xxx"
    }
  },
  "storage": [{
    "mount_path": "/models",
    "oss": { "path": "oss://my-bucket/models/llama-7b", "readOnly": true }
  }],
  "networking": { "gateway": "gw-xxx" },
  "autoscaler": {
    "min": 1,
    "max": 10,
    "scaleStrategies": [{ "metricName": "qps", "threshold": 100 }]
  }
}
```

## Public Resource Group Configuration

```json
{
  "metadata": { "name": "public-resource-service", "instance": 1 },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn6i-c8g1.2xlarge" }
  },
  "storage": [{
    "mount_path": "/models",
    "oss": { "path": "oss://my-bucket/models/" }
  }]
}
```

## Dedicated Resource Group Configuration

```json
{
  "metadata": { "name": "dedicated-resource-service", "instance": 1 },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn6i-c8g1.2xlarge" }
  },
  "resource": "eas-r-xxx",
  "storage": [{
    "mount_path": "/models",
    "oss": { "path": "oss://my-bucket/models/" }
  }]
}
```

## ALB Gateway Configuration

```json
{
  "metadata": { "name": "alb-gateway-service", "instance": 1 },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn6i-c8g1.2xlarge" },
    "networking": {
      "vpc_id": "{obtained from the gateway}",
      "vswitch_id": "{obtained from the gateway}",
      "security_group_id": "sg-xxx"
    }
  },
  "networking": { "gateway": "gw-xxx" }
}
```

## NLB Configuration

```json
{
  "metadata": { "name": "nlb-service", "instance": 1 },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn6i-c8g1.2xlarge" },
    "networking": {
      "vpc_id": "vpc-xxx",
      "vswitch_id": "vsw-xxx",
      "security_group_id": "sg-xxx"
    }
  },
  "networking": {
    "nlb": [{ "id": "default", "listener_port": 8080, "netType": "intranet" }]
  }
}
```

## Autoscaling Configuration

```json
{
  "autoscaler": {
    "min": 1,
    "max": 10,
    "scaleStrategies": [
      { "metricName": "qps", "threshold": 100 },
      { "metricName": "cpu", "threshold": 80 }
    ]
  }
}
```

## Storage Mount Configuration

```json
{
  "storage": [
    {
      "mount_path": "/models",
      "oss": { "path": "oss://my-bucket/models/", "readOnly": true }
    },
    {
      "mount_path": "/data",
      "nfs": { "server": "xxx.cn-hangzhou.nas.aliyuncs.com", "path": "/share" }
    },
    {
      "mount_path": "/dataset",
      "dataset": { "id": "d-xxx", "version": "v1" }
    }
  ]
}
```

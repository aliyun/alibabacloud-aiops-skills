# 服务配置示例

**目录**
- [JSON 字段规范](#json-字段规范重要)
- [容器模式配置](#容器模式配置重要)
- [基础配置](#基础配置)
- [完整配置](#完整配置)
- [公共资源组配置](#公共资源组配置)
- [专属资源组配置](#专属资源组配置)
- [ALB 网关配置](#alb-网关配置)
- [NLB 配置](#nlb-配置)
- [自动扩缩容配置](#自动扩缩容配置)
- [存储挂载配置](#存储挂载配置)

## ⚠️ JSON 字段规范（重要）

**服务名称必须放在 `metadata.name` 字段**，不是顶层字段：

```json
{
  "metadata": {
    "name": "my-service",    // ✅ 正确：服务名称在这里
    "instance": 1
  }
}
```

**错误示例**：

```json
{
  "service_name": "my-service",  // ❌ 错误：这是无效字段
  "name": "my-service"           // ❌ 错误：不在 metadata 中
}
```

## 容器模式配置（重要）

使用镜像部署时，必须配置 `containers` 字段：

```json
{
  "metadata": { "name": "my-service", "instance": 1 },
  "containers": [{
    "image": "镜像地址",
    "port": 8000,
    "command": "启动命令"
  }],
  "storage": [{ "mount_path": "/model_dir", "oss": { "path": "oss://bucket/models/" } }],
  "cloud": { "computing": { "instance_type": "ecs.gn6i-c8g1.2xlarge" } }
}
```

**关键字段**：
- `metadata.name` - 服务名称（必填）
- `containers[].image` - 镜像地址（必填）
- `containers[].port` - 服务端口（必填）
- `containers[].command` - 启动命令（可选）

**⚠️ 注意**：使用 `containers` 字段，不要使用 `processor` 或 `processor_path`。

## 基础配置

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

## 完整配置

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

## 公共资源组配置

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

## 专属资源组配置

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

## ALB 网关配置

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
      "vpc_id": "{从网关获取}",
      "vswitch_id": "{从网关获取}",
      "security_group_id": "sg-xxx"
    }
  },
  "networking": { "gateway": "gw-xxx" }
}
```

## NLB 配置

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

## 自动扩缩容配置

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

## 存储挂载配置

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

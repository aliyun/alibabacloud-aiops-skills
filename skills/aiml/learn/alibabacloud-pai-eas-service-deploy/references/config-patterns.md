# Complete Config Pattern Examples

This document contains 8 complete JSON config patterns for different deployment scenarios.

## Config Pattern Decision Table

| User Requirement | Pattern | Key Fields |
|-----------------|---------|------------|
| vLLM + OSS + Public Resource + Shared GW | Pattern 1 | `storage[].oss`, `cloud.computing` |
| vLLM + Autoscaling | Pattern 2 | `autoscaler` (camelCase!) |
| vLLM + NLB | Pattern 3 | `networking.nlb` |
| SGLang + Health Check | Pattern 4 | `containers[].startup_check` |
| ComfyUI + OSS | Pattern 5 | `storage[].oss` |
| Custom Image / CPU→GPU Auto-switch | Pattern 6 | Only `containers[].image` |
| EAS Resource Group | Pattern 7 | `metadata.resource` |
| Dedicated Gateway | Pattern 8 | `networking.gateway`, `cloud.networking` |

## Steps to Build JSON

1. Select the best matching pattern based on user requirements
2. Copy the JSON template for that pattern
3. Replace actual values (service name, image URI, OSS path, instance type, etc.)
4. If extra requirements exist (e.g. autoscaling + NLB), merge corresponding fields
5. Save as `service.json`

---

## Pattern 1: vLLM + OSS Mount + Public Resource Group + Shared Gateway

```json
{
  "metadata": {
    "name": "qwen35_7b_prod",
    "instance": 1,
    "workspace_id": "<workspace_id>"
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.13.0rc2.a8ec486.20260305pai-gpu",
    "port": 8000,
    "command": "vllm serve /model_dir --port 8000 --trust-remote-code",
    "startup_check": {
      "http_get": {"path": "/health", "port": 8000},
      "initial_delay_seconds": 120,
      "period_seconds": 10,
      "failure_threshold": 30
    }
  }],
  "storage": [{
    "mount_path": "/model_dir",
    "oss": { "path": "oss://yqtest-model/qwen2.5-0.5b-instruct/", "readOnly": true }
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn7i-c16g1.4xlarge" }
  }
}
```

---

## Pattern 2: vLLM + Autoscaling

```json
{
  "metadata": {
    "name": "qwen_autoscaling_test",
    "instance": 1,
    "workspace_id": "<workspace_id>"
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.13.0rc2.a8ec486.20260305pai-gpu",
    "port": 8000,
    "command": "vllm serve /model_dir --port 8000 --trust-remote-code"
  }],
  "storage": [{
    "mount_path": "/model_dir",
    "oss": { "path": "oss://yqtest-model/qwen2.5-0.5b-instruct/", "readOnly": true }
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn7i-c16g1.4xlarge" }
  },
  "autoscaler": {
    "min": 1,
    "max": 4,
    "scaleStrategies": [
      {"metricName": "qps", "threshold": 20}
    ]
  }
}
```

---

## Pattern 3: vLLM + NLB

```json
{
  "metadata": {
    "name": "qwen_nlb_test",
    "instance": 1,
    "workspace_id": "<workspace_id>"
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.13.0rc2.a8ec486.20260305pai-gpu",
    "port": 8000,
    "command": "vllm serve /model_dir --port 8000 --trust-remote-code"
  }],
  "storage": [{
    "mount_path": "/model_dir",
    "oss": { "path": "oss://yqtest-model/qwen2.5-0.5b-instruct/", "readOnly": true }
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn7i-c16g1.4xlarge" },
    "networking": {
      "vpc_id": "vpc-xxx",
      "vswitch_id": "vsw-zone-a,vsw-zone-b",
      "security_group_id": "sg-xxx"
    }
  },
  "networking": {
    "nlb": [{ "id": "default", "listener_port": 8000, "netType": "intranet" }]
  }
}
```

---

## Pattern 4: SGLang + Health Check

```json
{
  "metadata": {
    "name": "llama3_8b_api",
    "instance": 1,
    "workspace_id": "<workspace_id>"
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/sglang:0.5.8-acclep1.2.1-gpu",
    "port": 8000,
    "command": "python -m sglang.launch_server --model-path /model_dir --host 0.0.0.0 --port 8000",
    "startup_check": {
      "http_get": {"path": "/health", "port": 8000},
      "initial_delay_seconds": 120,
      "period_seconds": 10,
      "failure_threshold": 30
    }
  }],
  "storage": [{
    "mount_path": "/model_dir",
    "oss": { "path": "oss://yqtest-model/llama3-8b-instruct/", "readOnly": true }
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn7i-c16g1.4xlarge" }
  }
}
```

---

## Pattern 5: ComfyUI + OSS Mount

```json
{
  "metadata": {
    "name": "sdxl_inference",
    "instance": 1,
    "workspace_id": "<workspace_id>"
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/comfyui:2.2-api",
    "port": 8000,
    "command": "python main.py --listen 0.0.0.0 --port 8000",
    "startup_check": {
      "http_get": {"path": "/", "port": 8000},
      "initial_delay_seconds": 60,
      "period_seconds": 10,
      "failure_threshold": 30
    }
  }],
  "storage": [{
    "mount_path": "/models",
    "oss": { "path": "oss://yqtest-model/sdxl-v1.0/", "readOnly": true }
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn7i-c16g1.4xlarge" }
  }
}
```

---

## Pattern 6: vLLM + Small Model + GPU Instance (auto-switch from CPU when user requests CPU)

```json
{
  "metadata": {
    "name": "qwen_cpu_service",
    "instance": 2,
    "workspace_id": "<workspace_id>"
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.13.0rc2.a8ec486.20260305pai-gpu",
    "port": 8000,
    "command": "vllm serve /model_dir --port 8000 --trust-remote-code"
  }],
  "storage": [{
    "mount_path": "/model_dir",
    "oss": { "path": "oss://yqtest-model/qwen2.5-0.5b-instruct/", "readOnly": true }
  }],
  "cloud": {
    "computing": { "instance_type": "ecs.gn6i-c4g1.xlarge" }
  }
}
```

---

## Pattern 7: EAS Resource Group Deployment

```json
{
  "metadata": {
    "name": "my_vllm_service",
    "instance": 1,
    "resource": "eas-r-d29k8ytqxzxmqi7l0s",
    "workspace_id": "<workspace_id>",
    "gpu": 1,
    "cpu": 4,
    "memory": 8000
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.13.0rc2.a8ec486.20260305pai-gpu",
    "port": 8000,
    "command": "vllm serve /model_dir --port 8000 --trust-remote-code"
  }],
  "storage": [{
    "mount_path": "/model_dir",
    "oss": { "path": "oss://yqtest-model/qwen2.5-0.5b-instruct/", "readOnly": true }
  }]
}
```

---

## Pattern 8: Dedicated Gateway Deployment

```json
{
  "metadata": {
    "name": "my_gateway_service",
    "instance": 1,
    "workspace_id": "<workspace_id>"
  },
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.13.0rc2.a8ec486.20260305pai-gpu",
    "port": 8000,
    "command": "vllm serve /model_dir --port 8000 --trust-remote-code"
  }],
  "storage": [{
    "mount_path": "/model_dir",
    "oss": { "path": "oss://yqtest-model/qwen2.5-0.5b-instruct/", "readOnly": true }
  }],
  "networking": {
    "gateway": "gw-48hmbdt00fi6x90gft"
  },
  "cloud": {
    "computing": { "instance_type": "ecs.gn7i-c16g1.4xlarge" },
    "networking": {
      "vpc_id": "vpc-bp13kiflgde6v9dc9smc8",
      "vswitch_id": "vsw-bp1bhmnwqdh1ta9z9klms,vsw-bp1lz95xtmjiwqcpq31ng",
      "security_group_id": "sg-bp1e36bfv61nfy1yudyc"
    }
  }
}
```

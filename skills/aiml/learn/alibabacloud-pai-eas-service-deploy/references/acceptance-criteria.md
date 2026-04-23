# Acceptance Criteria: alibabacloud-pai-eas-service-deploy

**Scenario**: PAI-EAS Service Deployment
**Purpose**: Skill test acceptance criteria

**Table of Contents**
- [CLI Command Patterns](#correct-cli-command-patterns)
- [Service Config Validation](#service-config-validation)
- [Authentication Patterns](#authentication-patterns)
- [Parameter Confirmation Requirements](#parameter-confirmation-requirements)
- [Resource Cleanup](#resource-cleanup)

---

# Correct CLI Command Patterns

## 1. EAS Service Operations

### ✅ Correct: Create Service

```bash
aliyun eas create-service --region cn-hangzhou --body "$(cat service.json)" --user-agent AlibabaCloud-Agent-Skills
```

### ❌ Wrong: Missing --user-agent

```bash
aliyun eas create-service --region cn-hangzhou --body "$(cat service.json)"
```

### ❌ Wrong: Using API format instead of plugin mode

```bash
aliyun eas create-service --region cn-hangzhou --body "$(cat service.json)"
```

## 2. AIWorkSpace Operations

### ✅ Correct: List Images

```bash
aliyun aiworkspace list-images --verbose true --labels 'system.official=true,system.supported.eas=true' --page-size 50 --user-agent AlibabaCloud-Agent-Skills
```

### ❌ Wrong: Labels format error

```bash
aliyun aiworkspace list-images --verbose true --labels 'system.official=true' --user-agent AlibabaCloud-Agent-Skills
```

## 3. OSS Operations

### ✅ Correct: List Buckets

```bash
ossutil ls
```

### ✅ Correct: List Objects

```bash
ossutil ls oss://bucket-name/path/
```

### ❌ Wrong: Missing oss:// prefix

```bash
ossutil ls bucket-name/path/
```

## 4. VPC Operations

### ✅ Correct: Query VPC

```bash
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --vpc-id vpc-xxx --user-agent AlibabaCloud-Agent-Skills
```

### ❌ Wrong: Missing user-agent

```bash
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --vpc-id vpc-xxx
```

---

# Service Config Validation

## 1. metadata Config

### ✅ Correct: Service Name Format

```json
{
  "metadata": {
    "name": "my-vllm-service",
    "instance": 1
  }
}
```

### ❌ Wrong: Service name contains uppercase letters

```json
{
  "metadata": {
    "name": "My-VLLM-Service",
    "instance": 1
  }
}
```

### ❌ Wrong: Service name contains special characters

```json
{
  "metadata": {
    "name": "my.vllm.service",
    "instance": 1
  }
}
```

## 2. containers Config

### ✅ Correct: Container Config

```json
{
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "port": 8000,
    "script": "vllm serve /models --port 8000"
  }]
}
```

### ❌ Wrong: Missing port config

```json
{
  "containers": [{
    "image": "eas-registry-vpc.cn-hangzhou.cr.aliyuncs.com/pai-eas/vllm:0.14.0-gpu",
    "script": "vllm serve /models --port 8000"
  }]
}
```

## 3. storage Config

### ✅ Correct: OSS Mount

```json
{
  "storage": [{
    "mount_path": "/models",
    "oss": {
      "path": "oss://bucket/models/",
      "readOnly": true
    }
  }]
}
```

### ❌ Wrong: OSS path missing trailing slash

```json
{
  "storage": [{
    "mount_path": "/models",
    "oss": {
      "path": "oss://bucket/models",
      "readOnly": true
    }
  }]
}
```

### ❌ Wrong: Missing oss:// prefix

```json
{
  "storage": [{
    "mount_path": "/models",
    "oss": {
      "path": "bucket/models/",
      "readOnly": true
    }
  }]
}
```

## 4. cloud Config

### ✅ Correct: Public Resource Group

```json
{
  "cloud": {
    "computing": {
      "instance_type": "ecs.gn7-c12g1.12xlarge"
    }
  }
}
```

### ✅ Correct: Multi-spec Instances

```json
{
  "cloud": {
    "computing": {
      "instances": [
        {"type": "ecs.gn7-c12g1.12xlarge"},
        {"type": "ecs.gn8is.2xlarge"}
      ]
    }
  }
}
```

### ❌ Wrong: Wrong field name

```json
{
  "cloud": {
    "computing": {
      "instanceType": "ecs.gn7-c12g1.12xlarge"
    }
  }
}
```

## 5. networking Config

### ✅ Correct: Dedicated Gateway

```json
{
  "networking": {
    "gateway": "gw-xxx"
  }
}
```

### ✅ Correct: NLB

```json
{
  "networking": {
    "nlb": [{
      "id": "default",
      "listener_port": 9000,
      "netType": "intranet"
    }]
  }
}
```

### ❌ Wrong: NLB port is 8080 (not allowed)

```json
{
  "networking": {
    "nlb": [{
      "id": "default",
      "listener_port": 8080,
      "netType": "intranet"
    }]
  }
}
```

---

# Authentication Patterns

## ✅ Correct: Using CredentialClient (Python SDK)

```python
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_eas20210701.client import Client as EasClient
from alibabacloud_tea_openapi import models as open_api_models

credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.region_id = "cn-hangzhou"
config.user_agent = "AlibabaCloud-Agent-Skills/alibabacloud-pai-eas-service-deploy"
client = EasClient(config)
```

## ❌ Wrong: Hardcoded AK/SK

```python
config = open_api_models.Config(
    access_key_id="LTAIxxx",
    access_key_secret="xxx"
)
```

---

# Parameter Confirmation Requirements

## ✅ Correct: All user parameters must be confirmed

The following parameters must be confirmed before deployment:
- RegionId (region)
- Service name
- Workspace ID
- Image URI
- Instance type
- OSS path (if mounting)
- Gateway ID (if using dedicated gateway)
- VPC/VSwitch/Security group (if using ALB/NLB)

## ❌ Wrong: Using default values without confirmation

```bash
# Wrong: Using default region without asking user
aliyun eas create-service --region cn-hangzhou ...
```

---

# Resource Cleanup

## ✅ Correct: Cleanup after deployment failure

```bash
aliyun eas delete-service \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

## ❌ Wrong: Not cleaning up failed services

Failure to delete after service creation failure leads to resource waste.

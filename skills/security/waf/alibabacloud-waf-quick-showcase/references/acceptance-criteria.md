# Acceptance Criteria: alibabacloud-waf-quick-showcase

**Scenario**: 使用WAF防护ECS上的Web应用
**Purpose**: Skill测试验收标准

---

# Correct CLI Command Patterns

## 1. Product — 验证产品名称存在

### VPC 产品
```bash
# ✅ CORRECT
aliyun vpc --help
# 应显示vpc命令的帮助信息

# ❌ INCORRECT
aliyun VPC --help  # 产品名应为小写
```

### ECS 产品
```bash
# ✅ CORRECT
aliyun ecs --help
# 应显示ecs命令的帮助信息
```

## 2. Command — 验证操作存在于产品下

### VPC 命令
```bash
# ✅ CORRECT - 使用plugin模式（小写连字符）
aliyun vpc create-vpc --help
aliyun vpc create-vswitch --help
aliyun vpc describe-vpcs --help
aliyun vpc delete-vpc --help

# ❌ INCORRECT - 使用传统API格式
aliyun vpc CreateVpc --help  # 应使用 create-vpc
```

### ECS 命令
```bash
# ✅ CORRECT
aliyun ecs create-security-group --help
aliyun ecs authorize-security-group --help
aliyun ecs run-instances --help
aliyun ecs describe-instances --help

# ❌ INCORRECT
aliyun ecs CreateSecurityGroup --help  # 应使用 create-security-group
```

## 3. Parameters — 验证每个参数存在

### create-vpc 参数
```bash
# 验证参数
aliyun vpc create-vpc --help
# 确认以下参数存在:
# --cidr-block
# --vpc-name
# --biz-region-id
# --description
```

### create-vswitch 参数
```bash
aliyun vpc create-vswitch --help
# 确认以下参数存在:
# --vpc-id
# --zone-id
# --cidr-block
# --vswitch-name
```

### create-security-group 参数
```bash
aliyun ecs create-security-group --help
# 确认以下参数存在:
# --vpc-id
# --security-group-name
# --biz-region-id
# --description
# --security-group-type
```

### authorize-security-group 参数
```bash
aliyun ecs authorize-security-group --help
# 确认以下参数存在:
# --security-group-id
# --permissions
# --biz-region-id
```

### run-instances 参数
```bash
aliyun ecs run-instances --help
# 确认以下参数存在:
# --biz-region-id
# --instance-type
# --image-id
# --security-group-id
# --vswitch-id
# --instance-name
# --internet-charge-type
# --internet-max-bandwidth-out
# --system-disk-size
# --system-disk-category
# --password
# --amount
```

## 4. User-Agent Flag — 必须包含

```bash
# ✅ CORRECT - 每个命令必须包含 --user-agent
aliyun vpc create-vpc \
  --biz-region-id cn-hangzhou \
  --cidr-block 192.168.0.0/16 \
  --vpc-name my-vpc \
  --user-agent AlibabaCloud-Agent-Skills

# ❌ INCORRECT - 缺少 --user-agent
aliyun vpc create-vpc \
  --biz-region-id cn-hangzhou \
  --cidr-block 192.168.0.0/16 \
  --vpc-name my-vpc
```

---

# Common SDK Code Patterns (if applicable)

## 1. Import Patterns

### ✅ CORRECT
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient  # Required for RPC
```

### ❌ INCORRECT
```python
# 错误的导入路径
from alibabacloud_openapi.client import Client  # 不存在此模块
from aliyun.sdk import Client  # 旧版SDK，不推荐
```

## 2. Authentication — 必须使用CredentialClient

### ✅ CORRECT
```python
# 使用CredentialClient自动获取凭证
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'ecs.cn-hangzhou.aliyuncs.com'
client = OpenApiClient(config)
```

### ❌ INCORRECT
```python
# 硬编码AK/SK
config = open_api_models.Config()
config.access_key_id = 'LTAI5tXXXXXXXX'  # 安全风险!
config.access_key_secret = '8dXXXXXXXXXXX'  # 安全风险!
```

## 3. API Style — RPC vs ROA

### ✅ CORRECT - RPC Style (ECS/VPC)
```python
params = open_api_models.Params(
    action='CreateVpc',
    version='2016-04-28',
    protocol='HTTPS',
    method='POST',
    auth_type='AK',
    style='RPC',
    pathname='/',  # RPC style always uses '/'
    req_body_type='json',
    body_type='json'
)

# RPC使用query参数
queries = {
    'RegionId': 'cn-hangzhou',
    'CidrBlock': '192.168.0.0/16',
    'VpcName': 'my-vpc'
}
request = open_api_models.OpenApiRequest(
    query=OpenApiUtilClient.query(queries)
)
```

### ❌ INCORRECT
```python
# RPC不应使用body参数
request = open_api_models.OpenApiRequest(
    body={'RegionId': 'cn-hangzhou'}  # 错误！RPC应使用query
)
```

---

# Validation Checklist

- [ ] 所有CLI命令使用plugin模式格式（小写连字符）
- [ ] 所有CLI命令包含 `--user-agent AlibabaCloud-Agent-Skills`
- [ ] 所有参数名称正确（已通过 --help 验证）
- [ ] SDK代码使用 CredentialClient，未硬编码凭证
- [ ] SDK代码正确区分 RPC/ROA 风格
- [ ] 所有用户可定制参数在执行前需确认

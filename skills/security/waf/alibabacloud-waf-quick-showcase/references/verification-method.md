# Success Verification Method

## 场景目标验证

**预期结果**: 完成VPC网络环境搭建、ECS实例创建、Web应用部署，并通过WAF进行安全防护。

## 分步验证

### Step 1: 验证VPC和网络环境

```bash
# 验证VPC创建成功且状态为Available
aliyun vpc describe-vpcs \
  --biz-region-id cn-hangzhou \
  --vpc-id <VpcId> \
  --user-agent AlibabaCloud-Agent-Skills

# 预期输出应包含:
# "Status": "Available"
```

**成功标志**: VPC状态为 `Available`

```bash
# 验证VSwitch创建成功且状态为Available
aliyun vpc describe-vswitches \
  --biz-region-id cn-hangzhou \
  --vswitch-id <VSwitchId> \
  --user-agent AlibabaCloud-Agent-Skills

# 预期输出应包含:
# "Status": "Available"
```

**成功标志**: VSwitch状态为 `Available`

### Step 2: 验证安全组配置

```bash
# 验证安全组存在
aliyun ecs describe-security-groups \
  --biz-region-id cn-hangzhou \
  --security-group-id <SecurityGroupId> \
  --user-agent AlibabaCloud-Agent-Skills

# 验证安全组规则（80端口已开放）
aliyun ecs describe-security-group-attribute \
  --biz-region-id cn-hangzhou \
  --security-group-id <SecurityGroupId> \
  --user-agent AlibabaCloud-Agent-Skills
```

**成功标志**: 
- 安全组存在
- 入方向规则包含 TCP 80端口

### Step 3: 验证ECS实例

```bash
# 验证ECS实例状态为Running
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["<InstanceId>"]' \
  --user-agent AlibabaCloud-Agent-Skills

# 预期输出应包含:
# "Status": "Running"
# "PublicIpAddress": {"IpAddress": ["x.x.x.x"]}
```

**成功标志**: 
- 实例状态为 `Running`
- 已分配公网IP地址

### Step 4: 验证Web应用部署

```bash
# 获取ECS公网IP
ECS_IP=$(aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --instance-ids '["<InstanceId>"]' \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.Instances.Instance[0].PublicIpAddress.IpAddress[0]')

# 验证Web应用可访问
curl --connect-timeout 5 --max-time 10 -I "http://${ECS_IP}/"
```

**成功标志**: 
- HTTP响应状态码为 200
- 能够正常访问Web页面

### Step 5: 验证WAF接入

```bash
# 查询WAF实例信息
aliyun waf-openapi describe-instance \
  --region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills

# 查询已接入WAF的ECS实例
aliyun waf-openapi describe-cloud-resources \
  --instance-id <WAF-InstanceId> \
  --resource-product ecs \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills

# 预期输出应包含接入的ECS实例信息
```

**成功标志**: 
- WAF实例状态正常
- 已接入的云产品列表中包含目标ECS实例

也可以通过控制台验证:

1. 登录 [WAF控制台](https://yundun.console.aliyun.com/?p=waf)
2. 进入 **接入管理 > 云产品接入 > 云服务器ECS**
3. 检查ECS实例的"防护状态"是否显示为"已接入"

## 完整验证脚本

```bash
#!/bin/bash

# 设置变量（请替换为实际值）
REGION="cn-hangzhou"
VPC_ID="<your-vpc-id>"
VSWITCH_ID="<your-vswitch-id>"
SG_ID="<your-security-group-id>"
INSTANCE_ID="<your-ecs-instance-id>"
WAF_INSTANCE_ID="<your-waf-instance-id>"

echo "=== 验证VPC状态 ==="
aliyun vpc describe-vpcs --biz-region-id $REGION --vpc-id $VPC_ID --user-agent AlibabaCloud-Agent-Skills | jq '.Vpcs.Vpc[0].Status'

echo "=== 验证VSwitch状态 ==="
aliyun vpc describe-vswitches --biz-region-id $REGION --vswitch-id $VSWITCH_ID --user-agent AlibabaCloud-Agent-Skills | jq '.VSwitches.VSwitch[0].Status'

echo "=== 验证ECS状态 ==="
aliyun ecs describe-instances --biz-region-id $REGION --instance-ids "[\"$INSTANCE_ID\"]" --user-agent AlibabaCloud-Agent-Skills | jq '.Instances.Instance[0].Status'

echo "=== 获取ECS公网IP ==="
ECS_IP=$(aliyun ecs describe-instances --biz-region-id $REGION --instance-ids "[\"$INSTANCE_ID\"]" --user-agent AlibabaCloud-Agent-Skills | jq -r '.Instances.Instance[0].PublicIpAddress.IpAddress[0]')
echo "ECS公网IP: $ECS_IP"

echo "=== 验证Web应用 ==="
curl --connect-timeout 5 --max-time 10 -I "http://${ECS_IP}/" 2>/dev/null | head -1

echo "=== 验证WAF实例 ==="
aliyun waf-openapi describe-instance --region-id $REGION --user-agent AlibabaCloud-Agent-Skills | jq '.InstanceId'

echo "=== 验证ECS已接入WAF ==="
aliyun waf-openapi describe-cloud-resources --instance-id $WAF_INSTANCE_ID --resource-product ecs --page-number 1 --page-size 10 --user-agent AlibabaCloud-Agent-Skills | jq '.CloudResources'

echo "=== 验证完成 ==="
```

## 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| VPC创建失败 | 配额不足或网段冲突 | 检查VPC配额，更换CIDR网段 |
| ECS启动失败 | 实例规格不可用 | 更换可用区或实例规格 |
| 无法访问Web应用 | 安全组规则未配置 | 检查80端口是否开放 |
| WAF接入失败 | 授权未完成 | 在WAF控制台完成云产品授权 |

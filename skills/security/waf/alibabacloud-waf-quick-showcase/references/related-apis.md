# Related APIs

本技能涉及的所有CLI命令和API列表。

## VPC 相关

| Product | CLI Command | API Action | API Version | Description |
|---------|-------------|------------|-------------|-------------|
| VPC | `aliyun vpc create-vpc` | CreateVpc | 2016-04-28 | 创建专有网络VPC |
| VPC | `aliyun vpc describe-vpcs` | DescribeVpcs | 2016-04-28 | 查询VPC列表 |
| VPC | `aliyun vpc delete-vpc` | DeleteVpc | 2016-04-28 | 删除VPC |
| VPC | `aliyun vpc create-vswitch` | CreateVSwitch | 2016-04-28 | 创建交换机 |
| VPC | `aliyun vpc describe-vswitches` | DescribeVSwitches | 2016-04-28 | 查询交换机列表 |
| VPC | `aliyun vpc delete-vswitch` | DeleteVSwitch | 2016-04-28 | 删除交换机 |

## ECS 相关

| Product | CLI Command | API Action | API Version | Description |
|---------|-------------|------------|-------------|-------------|
| ECS | `aliyun ecs create-security-group` | CreateSecurityGroup | 2014-05-26 | 创建安全组 |
| ECS | `aliyun ecs delete-security-group` | DeleteSecurityGroup | 2014-05-26 | 删除安全组 |
| ECS | `aliyun ecs authorize-security-group` | AuthorizeSecurityGroup | 2014-05-26 | 添加安全组入方向规则 |
| ECS | `aliyun ecs describe-security-groups` | DescribeSecurityGroups | 2014-05-26 | 查询安全组列表 |
| ECS | `aliyun ecs run-instances` | RunInstances | 2014-05-26 | 创建并启动ECS实例 |
| ECS | `aliyun ecs create-instance` | CreateInstance | 2014-05-26 | 创建ECS实例 |
| ECS | `aliyun ecs start-instance` | StartInstance | 2014-05-26 | 启动ECS实例 |
| ECS | `aliyun ecs stop-instance` | StopInstance | 2014-05-26 | 停止ECS实例 |
| ECS | `aliyun ecs delete-instance` | DeleteInstance | 2014-05-26 | 释放ECS实例 |
| ECS | `aliyun ecs describe-instances` | DescribeInstances | 2014-05-26 | 查询ECS实例列表 |
| ECS | `aliyun ecs describe-images` | DescribeImages | 2014-05-26 | 查询可用镜像列表 |
| ECS | `aliyun ecs describe-instance-types` | DescribeInstanceTypes | 2014-05-26 | 查询实例规格 |

## WAF 3.0 相关

| Product | CLI Command | API Action | API Version | Description |
|---------|-------------|------------|-------------|-------------|
| WAF | `aliyun waf-openapi create-postpaid-instance` | CreatePostpaidInstance | 2021-10-01 | 创建WAF按量付费实例 |
| WAF | `aliyun waf-openapi describe-instance` | DescribeInstance | 2021-10-01 | 查询WAF实例详情 |
| WAF | `aliyun waf-openapi release-instance` | ReleaseInstance | 2021-10-01 | 释放WAF实例 |
| WAF | `aliyun waf-openapi sync-product-instance` | SyncProductInstance | 2021-10-01 | 同步ECS/CLB/NLB资产到WAF |
| WAF | `aliyun waf-openapi describe-product-instances` | DescribeProductInstances | 2021-10-01 | 查询已同步的云产品资产列表 |
| WAF | `aliyun waf-openapi create-cloud-resource` | CreateCloudResource | 2021-10-01 | 云产品(ECS/CLB)接入WAF |
| WAF | `aliyun waf-openapi modify-cloud-resource` | ModifyCloudResource | 2021-10-01 | 修改云产品接入配置 |
| WAF | `aliyun waf-openapi delete-cloud-resource` | DeleteCloudResource | 2021-10-01 | 取消云产品接入 |
| WAF | `aliyun waf-openapi describe-cloud-resources` | DescribeCloudResources | 2021-10-01 | 查询已接入WAF的云产品列表 |
| WAF | `aliyun waf-openapi describe-resource-support-regions` | DescribeResourceSupportRegions | 2021-10-01 | 查询云产品接入支持的地域 |

## 官方文档链接

- [VPC API参考](https://help.aliyun.com/zh/vpc/developer-reference/api-vpc-2016-04-28-createvpc)
- [ECS API参考](https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-overview)
- [WAF 3.0 API参考](https://help.aliyun.com/zh/waf/web-application-firewall-3-0/developer-reference/api-waf-openapi-2021-10-01-overview)

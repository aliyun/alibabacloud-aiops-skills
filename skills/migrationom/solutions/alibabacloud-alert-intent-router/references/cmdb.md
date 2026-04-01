# Enterprise CMDB / 企业资源配置管理数据库

> **可选配置 / Optional Configuration**
> 
> CMDB 为可选配置。如果未配置，技能将使用云平台 API 查询资源信息。
> 配置 CMDB 可以提供以下增强功能：
> - 业务名称到资源 ID 的映射（如 `db-prod-01` → `rm-bp1xxx`）
> - 资源关联关系（如 ECS 关联的 RDS、SLB）
> - 自定义业务标签和分组
>
> CMDB is optional. If not configured, the skill will query resource info via Cloud API.
> Configuring CMDB provides enhanced features like business name mapping and resource relationships.

> **Maintenance / 维护说明**: This file is manually maintained by the enterprise.
> Update this file when resources are added, modified, or decommissioned.
> 此文件由企业手动维护。当资源新增、变更或下线时，请更新此文件。

## Resource Registry / 资源注册表


### Load Balancers / 负载均衡

| CLB Instance ID | Region | Backend ECS | Protocol | Port | Description |
|-----------------|--------|-------------|----------|------|-------------|
| alb-ndov**** | cn-hangzhou | i-bp16ts1hirmyg**** | tcp | 80 | HTTP监听器 |

### Backend Server Details / 后端服务器详情

| ECS Instance ID | Name | Region | VPC |
|-----------------|------|--------|-----|
| i-bp16ts**** | ecs-instance | cn-hangzhou | vpc-bp1o***** | 


### 微服务源与目标IP配置

| Source Instance ID | Target Instance ID | Region | Protocol | Port |
|-----------------|------|--------|-----|--------|
| i-bp1frg**** | i-bp1gsn**** | cn-hangzhou | TCP | 80 | 
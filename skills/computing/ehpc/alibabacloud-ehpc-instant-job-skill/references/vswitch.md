# 阿里云网络vSwitch管理手册（CLI版本）

## 概述
虚拟交换机（vSwitch）是阿里云专有网络VPC中的基础网络组件，用于连接云资源（如ECS实例、容器等）。本手册介绍使用阿里云 CLI 进行 vSwitch 的增删改查操作。

## 前置条件
1. **安装阿里云CLI**：确保已安装并配置阿里云 CLI
2. **权限配置**：AccessKey 需要具备 VPC 相关权限
3. **区域选择**：确认操作的区域（如 cn-shanghai）
4. **VPC准备**：vSwitch 必须关联到现有的 VPC
5. **User-Agent标识**：所有命令均应附加 `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill` 参数，用于服务端识别调用来源。如已通过 `aliyun configure ai-mode set-user-agent` 配置，则会自动附加，无需手动添加。

## 1. 创建vSwitch（Create）

### 基本创建命令
```bash
# 创建基本vSwitch
aliyun vpc CreateVSwitch \
    --VpcId vpc-xxxxxx \
    --ZoneId cn-shanghai-a \
    --CidrBlock 192.168.1.0/24 \
    --VSwitchName "e-hpc-compute-vswitch" \
    --Description "VSwitch for E-HPC Instant compute jobs" \
    --RegionId cn-shanghai
```

### 高级创建选项
```bash
# 创建支持IPv6的vSwitch
aliyun vpc CreateVSwitch \
    --VpcId vpc-xxxxxx \
    --ZoneId cn-shanghai-b \
    --CidrBlock 192.168.2.0/24 \
    --Ipv6CidrBlock 255 \
    --VSwitchName "ipv6-enabled-vswitch" \
    --Description "IPv6 enabled vSwitch for high-performance computing" \
    --RegionId cn-shanghai

# 带标签的vSwitch创建
aliyun vpc CreateVSwitch \
    --VpcId vpc-xxxxxx \
    --ZoneId cn-shanghai-c \
    --CidrBlock 192.168.3.0/24 \
    --VSwitchName "tagged-vswitch" \
    --Tag.1.Key Environment \
    --Tag.1.Value Production \
    --Tag.2.Key Project \
    --Tag.2.Value E-HPC \
    --RegionId cn-shanghai
```

### 参数说明
- **VpcId**: 关联的VPC ID（必需）
- **ZoneId**: 可用区ID（必需），可通过 `aliyun ecs DescribeZones` 查询
- **CidrBlock**: vSwitch网段（必需），必须在VPC网段范围内，子网掩码16-29位
- **VSwitchName**: vSwitch名称（可选），1-128字符
- **Description**: 描述信息（可选），1-256字符
- **Ipv6CidrBlock**: IPv6网段最后8位（0-255），仅当VPC启用IPv6时可用
- **RegionId**: 区域ID（可选），默认使用配置的区域

### CIDR规划建议
- **E-HPC场景**：建议使用 /24 或 /25 网段（256或128个IP）
- **避免冲突**：确保不与VPC路由表中的目标网段冲突
- **预留空间**：为未来扩展预留IP地址空间

## 2. 查询vSwitch（Read/List）

### 查询所有vSwitch
```bash
# 查询指定区域的所有vSwitch
aliyun vpc DescribeVSwitches --RegionId cn-shanghai

# 分页查询（每页20条，第1页）
aliyun vpc DescribeVSwitches \
    --PageSize 20 \
    --PageNumber 1 \
    --RegionId cn-shanghai
```

### 条件查询
```bash
# 查询指定VPC下的vSwitch
aliyun vpc DescribeVSwitches \
    --VpcId vpc-xxxxxx \
    --RegionId cn-shanghai

# 查询指定可用区的vSwitch
aliyun vpc DescribeVSwitches \
    --ZoneId cn-shanghai-a \
    --RegionId cn-shanghai

# 查询特定名称的vSwitch
aliyun vpc DescribeVSwitches \
    --VSwitchName "e-hpc-compute-vswitch" \
    --RegionId cn-shanghai

# 查询特定vSwitch详情
aliyun vpc DescribeVSwitches \
    --VSwitchId vsw-xxxxxx \
    --RegionId cn-shanghai
```

### 查询结果字段说明
- **VSwitchId**: vSwitch ID（如 vsw-uf6wc3sfmxo6rsubsozcd）
- **VpcId**: 关联的VPC ID
- **ZoneId**: 所在可用区
- **CidrBlock**: 网段CIDR
- **Status**: 状态（Available/Deleting等）
- **AvailableIpAddressCount**: 可用IP数量
- **CreationTime**: 创建时间

## 3. 修改vSwitch（Update）

### 修改基本信息
```bash
# 修改vSwitch名称和描述
aliyun vpc ModifyVSwitchAttribute \
    --VSwitchId vsw-xxxxxx \
    --VSwitchName "updated-e-hpc-vswitch" \
    --Description "Updated description for E-HPC jobs" \
    --RegionId cn-shanghai
```

### 启用IPv6功能
```bash
# 为vSwitch启用IPv6（需要VPC已启用IPv6）
aliyun vpc ModifyVSwitchAttribute \
    --VSwitchId vsw-xxxxxx \
    --EnableIPv6 true \
    --Ipv6CidrBlock 200 \
    --RegionId cn-shanghai
```

### 参数说明
- **VSwitchId**: 要修改的vSwitch ID（必需）
- **VSwitchName**: 新名称（可选）
- **Description**: 新描述（可选）
- **EnableIPv6**: 是否启用IPv6（true/false）
- **Ipv6CidrBlock**: IPv6网段最后8位（仅当启用IPv6时需要）

## 4. 删除vSwitch（Delete）

### 删除vSwitch
```bash
# 删除vSwitch（确保没有关联资源）
aliyun vpc DeleteVSwitch \
    --VSwitchId vsw-xxxxxx \
    --RegionId cn-shanghai
```

### 删除前检查（Dry Run）
```bash
# 执行删除前的预检查
aliyun vpc DeleteVSwitch \
    --VSwitchId vsw-xxxxxx \
    --DryRun true \
    --RegionId cn-shanghai
```

### 删除注意事项
- **资源清理**：确保vSwitch上没有运行的ECS实例、ENI等资源
- **E-HPC依赖**：如果vSwitch被E-HPC Instant作业使用，需先删除相关作业
- **不可恢复**：删除后无法恢复，请谨慎操作
- **异步操作**：删除操作可能需要几分钟完成

## 5. VPC管理基础（vSwitch依赖）

### 查询VPC列表
```bash
# 查询区域内的VPC
aliyun vpc DescribeVpcs --RegionId cn-shanghai

# 查询特定VPC
aliyun vpc DescribeVpcs \
    --VpcId vpc-xxxxxx \
    --RegionId cn-shanghai
```

### 创建VPC（如果需要）
```bash
# 创建基本VPC
aliyun vpc CreateVpc \
    --CidrBlock 192.168.0.0/16 \
    --VpcName "e-hpc-vpc" \
    --Description "VPC for E-HPC Instant" \
    --RegionId cn-shanghai
```

## 6. E-HPC Instant 作业中的vSwitch使用

### 在作业中指定vSwitch
```bash
# 容器作业指定vSwitch
aliyun ehpcinstant CreateJob \
    --region cn-shanghai \
    --JobName 'job-with-specific-vswitch' \
    --DeploymentPolicy '{"Network":{"Vswitch":["vsw-xxxxxx"]},"AllocationSpec":"Standard"}' \
    --Tasks '[{
        "TaskSpec": {
            "TaskExecutor": [{
                "Container": {
                    "Image": "registry.cn-shanghai.aliyuncs.com/registry/image:tag",
                    "Command": "[\"/bin/sh\", \"-c\", \"echo hello\"]"
                }
            }],
            "Resource": {
                "Cores": 2,
                "Memory": 4
            }
        },
        "ExecutorPolicy": {"MaxCount": 1}
    }]' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

### 多vSwitch高可用配置
```bash
# 指定多个vSwitch实现高可用
aliyun ehpcinstant CreateJob \
    --region cn-shanghai \
    --DeploymentPolicy '{"Network":{"Vswitch":["vsw-xxxxxx","vsw-yyyyyy"]},"AllocationSpec":"Standard"}' \
    --Tasks '[{...}]' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

## 7. 常用操作示例

### 完整vSwitch创建流程
```bash
#!/bin/bash
# 1. 查询可用区
ZONE_ID=$(aliyun ecs DescribeZones \
    --RegionId cn-shanghai \
    --output cols=ZoneId rows=1)

echo "Selected Zone: $ZONE_ID"

# 2. 查询VPC（假设已有VPC）
VPC_ID=$(aliyun vpc DescribeVpcs \
    --RegionId cn-shanghai \
    --output cols=VpcId rows=1)

echo "Using VPC: $VPC_ID"

# 3. 创建vSwitch
VSWITCH_ID=$(aliyun vpc CreateVSwitch \
    --VpcId $VPC_ID \
    --ZoneId $ZONE_ID \
    --CidrBlock 192.168.10.0/24 \
    --VSwitchName "auto-created-vswitch" \
    --Description "Auto created for E-HPC" \
    --RegionId cn-shanghai \
    --output cols=VSwitchId rows=1)

echo "Created vSwitch: $VSWITCH_ID"

# 4. 验证创建结果
aliyun vpc DescribeVSwitches \
    --VSwitchId $VSWITCH_ID \
    --RegionId cn-shanghai
```

### vSwitch监控脚本
```bash
# 检查vSwitch可用IP数量
aliyun vpc DescribeVSwitches \
    --VSwitchId vsw-xxxxxx \
    --RegionId cn-shanghai \
    --output cols=VSwitchId,AvailableIpAddressCount,CidrBlock

# 列出所有活跃的vSwitch
aliyun vpc DescribeVSwitches \
    --RegionId cn-shanghai \
    --output cols=VSwitchId,VSwitchName,ZoneId,CidrBlock,AvailableIpAddressCount
```

### 批量操作示例
```bash
# 批量查询多个vSwitch
VSWITCH_IDS="vsw-xxxxxx,vsw-yyyyyy,vsw-zzzzzz"
aliyun vpc DescribeVSwitches \
    --VSwitchId $VSWITCH_IDS \
    --RegionId cn-shanghai
```

## 8. 故障排查

### 常见问题及解决方案
| 问题 | 解决方案 |
|------|----------|
| **CIDR冲突** | 确保vSwitch CIDR在VPC范围内且不与路由冲突 |
| **可用区不支持** | 使用 `DescribeZones` 查询支持的可用区 |
| **配额不足** | 联系阿里云增加vSwitch配额 |
| **删除失败** | 检查是否有资源仍在使用该vSwitch |
| **网络不通** | 检查安全组、路由表和ACL配置 |

### 网络连通性检查
```bash
# 检查vSwitch状态
aliyun vpc DescribeVSwitches \
    --VSwitchId vsw-xxxxxx \
    --RegionId cn-shanghai

# 检查关联的路由表
aliyun vpc DescribeRouteTables \
    --VpcId vpc-xxxxxx \
    --RegionId cn-shanghai

# 检查安全组规则
aliyun ecs DescribeSecurityGroupAttribute \
    --SecurityGroupId sg-xxxxxx \
    --RegionId cn-shanghai
```

## 9. 最佳实践

1. **可用区选择**：
   - 选择与计算资源相同的可用区减少延迟
   - 多可用区部署提高可用性

2. **CIDR规划**：
   - 使用连续的网段便于管理
   - 为不同用途的vSwitch分配不同网段
   - 预留足够的IP地址空间

3. **命名规范**：
   - 包含用途、环境、区域信息
   - 示例：`prod-cn-shanghai-a-e-hpc-compute`

4. **标签管理**：
   - 使用标签进行资源分类和成本分摊
   - 标签示例：Environment=Production, Project=E-HPC, Owner=TeamA

5. **安全配置**：
   - 配置适当的网络安全组规则
   - 使用网络ACL进行额外的安全控制
   - 定期审查网络配置

## 10. 参考文档
- [阿里云VPC产品文档](https://help.aliyun.com/product/27706.html)
- [VPC API文档](https://api.aliyun.com/document/Vpc/2016-04-28/overview)
- [可用区查询](https://help.aliyun.com/document_detail/40654.html)
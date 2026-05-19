# 阿里云文件存储NAS管理手册（CLI版本）

## 概述
阿里云文件存储NAS（Network Attached Storage）提供共享文件存储服务，支持 NFS 和 SMB 协议。本手册介绍使用阿里云 CLI 进行 NAS 文件系统的增删改查操作。

## 前置条件
1. **安装阿里云CLI**：确保已安装并配置阿里云 CLI
2. **权限配置**：AccessKey 需要具备 NAS 相关权限
3. **区域选择**：确认操作的区域（如 cn-shanghai）
4. **User-Agent标识**：所有命令均应附加 `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill` 参数，用于服务端识别调用来源。如已通过 `aliyun configure ai-mode set-user-agent` 配置，则会自动附加，无需手动添加。

## 1. 创建文件系统（Create）

### 创建通用型NAS文件系统
```bash
# 创建容量型通用NAS（NFS协议）
aliyun nas CreateFileSystem \
    --ProtocolType NFS \
    --StorageType Capacity \
    --Description "E-HPC Instant NAS for compute jobs" \
    --RegionId cn-shanghai

# 创建性能型通用NAS（NFS协议）
aliyun nas CreateFileSystem \
    --ProtocolType NFS \
    --StorageType Performance \
    --Description "E-HPC Instant NAS for compute jobs" \
    --RegionId cn-shanghai

# 创建容量型通用NAS（SMB协议）
aliyun nas CreateFileSystem \
    --ProtocolType SMB \
    --StorageType Capacity \
    --Description "SMB file system for Windows workloads" \
    --RegionId cn-shanghai
```

### 参数说明
- **ProtocolType**: 协议类型（NFS/SMB/cpfs）
- **StorageType**: 存储类型（Performance/Capacity/Premium/standard/advance）
- **FileSystemType**: 文件系统类型（standard/extreme/cpfs/cpfsse）
- **Capacity**: 容量（GiB），极速型和CPFS必需
- **ZoneId**: 可用区ID，极速型和CPFS必需
- **EncryptType**: 加密类型（0=不加密，1=NAS托管密钥，2=KMS托管密钥）


### 创建注意事项
- **默认创建规格**：因涉及到成本及性价比因素，在用户未指定的情况下默认创建通用容量型NAS文件存储，NFS协议。
- **执行前与用户确认**：配置明确后进一步与用户确认，用户同意后执行创建。

## 2. 查询文件系统（Read/List）

### 查询所有文件系统
```bash
# 查询所有类型的文件系统
aliyun nas DescribeFileSystems --RegionId cn-shanghai

# 分页查询（每页10条，第1页）
aliyun nas DescribeFileSystems \
    --PageSize 10 \
    --PageNumber 1 \
    --RegionId cn-shanghai

# 查询特定类型的文件系统
aliyun nas DescribeFileSystems \
    --FileSystemType standard \
    --RegionId cn-shanghai

# 查询特定文件系统
aliyun nas DescribeFileSystems \
    --FileSystemId 31a8e4xxxx \
    --RegionId cn-shanghai
```

### 查询结果字段说明
- **FileSystemId**: 文件系统ID
- **ProtocolType**: 协议类型
- **StorageType**: 存储类型
- **MeteredSize**: 已使用容量（Byte）
- **CreateTime**: 创建时间
- **Status**: 状态（Active/Creating/Stopping等）

## 3. 创建挂载点（Mount Target）

### 为VPC网络创建挂载点
```bash
# 为通用NAS创建VPC挂载点
aliyun nas CreateMountTarget \
    --FileSystemId 31a8e4xxxx \
    --NetworkType Vpc \
    --VpcId vpc-xxxx \
    --VSwitchId vsw-xxxx \
    --AccessGroupName DEFAULT_VPC_GROUP_NAME \
    --RegionId cn-shanghai

# 为极速NAS创建挂载点（自动使用默认权限组）
aliyun nas CreateMountTarget \
    --FileSystemId extreme-xxxx \
    --NetworkType Vpc \
    --VpcId vpc-xxxx \
    --VSwitchId vsw-xxxx \
    --RegionId cn-shanghai
```

### 查询挂载点
```bash
# 查询文件系统的所有挂载点
aliyun nas DescribeMountTargets \
    --FileSystemId 31a8e4xxxx \
    --RegionId cn-shanghai

# 查询特定挂载点
aliyun nas DescribeMountTargets \
    --FileSystemId 31a8e4xxxx \
    --MountTargetDomain 31a8e4xxxx.cn-shanghai.nas.aliyuncs.com \
    --RegionId cn-shanghai
```

### 挂载点关键信息
- **MountTargetDomain**: 挂载地址（用于实际挂载）
- **VpcId**: 关联的VPC ID
- **VSwitchId**: 关联的交换机ID
- **Status**: 挂载点状态（Active/Inactive）

## 4. 修改文件系统（Update）

### 修改文件系统描述
```bash
aliyun nas ModifyFileSystem \
    --FileSystemId 31a8e4xxxx \
    --Description "Updated description for E-HPC jobs" \
    --RegionId cn-shanghai
```

### 修改挂载点（仅支持修改描述）
```bash
aliyun nas ModifyMountTarget \
    --FileSystemId 31a8e4xxxx \
    --MountTargetDomain 31a8e4xxxx.cn-shanghai.nas.aliyuncs.com \
    --Description "Updated mount target description" \
    --RegionId cn-shanghai
```

### 扩容文件系统（仅极速型和CPFS）
```bash
# 扩容极速型NAS
aliyun nas UpgradeFileSystem \
    --FileSystemId extreme-xxxx \
    --Capacity 1000 \
    --RegionId cn-shanghai
```

## 5. 删除文件系统（Delete）

### 删除挂载点（必需先删除）
```bash
# 注意：NAS CLI没有直接删除挂载点的命令
# 需要通过控制台或等待文件系统删除时自动清理
```

### 删除文件系统
```bash
# 删除通用型NAS文件系统
aliyun nas DeleteFileSystem \
    --FileSystemId 31a8e4xxxx \
    --RegionId cn-shanghai

# 删除极速型NAS文件系统
aliyun nas DeleteFileSystem \
    --FileSystemId extreme-xxxx \
    --RegionId cn-shanghai
```

### 删除注意事项
- **必须先卸载**：确保没有客户端正在使用文件系统
- **数据不可恢复**：删除后数据无法恢复，请谨慎操作
- **挂载点自动清理**：删除文件系统时，关联的挂载点会自动删除

## 6. E-HPC Instant 作业中的NAS使用

### 在容器作业中挂载NAS
```bash
aliyun ehpcinstant CreateJob \
    --region cn-shanghai \
    --JobName 'job-with-nas' \
    --Tasks '[{
        "TaskSpec": {
            "TaskExecutor": [{
                "Container": {
                    "Image": "registry.cn-shanghai.aliyuncs.com/registry/image:tag",
                    "Command": "[\"/bin/sh\", \"-c\", \"echo hello > /mnt/nas/output.txt\"]",
                }
            }],
            "Resource": {
                "Cores": 2,
                "Memory": 4
            },
            "VolumeMount": [
              {
                "MountPath": "/mnt",
                "VolumeDriver": "alicloud/nas",
                "MountOptions": "{\"server\":\"xxx.cn-shanghai.nas.aliyuncs.com\",\"vers\":\"3\",\"path\":\"/\",\"options\":\"nolock,tcp,noresvport\"}"
              }
            ],
        },
        "ExecutorPolicy": {"MaxCount": 1}
    }]' \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

### NAS挂载参数说明
- **Server**: NAS服务器地址（挂载点域名）
- **Path**: NAS文件系统中的路径（通常为"/"）
- **MountPath**: 容器内的挂载路径
- **ReadOnly**: 是否只读挂载（true/false）

## 7. 常用操作示例

### 完整创建流程示例
```bash
#!/bin/bash
# 1. 创建文件系统
FILESYSTEM_ID=$(aliyun nas CreateFileSystem \
    --ProtocolType NFS \
    --StorageType Performance \
    --Description "E-HPC NAS" \
    --RegionId cn-shanghai \
    --output cols=FileSystemId rows=1)

echo "Created FileSystem: $FILESYSTEM_ID"

# 2. 等待文件系统激活（实际使用中需要检查状态）
sleep 60

# 3. 创建挂载点
aliyun nas CreateMountTarget \
    --FileSystemId $FILESYSTEM_ID \
    --NetworkType Vpc \
    --VpcId your-vpc-id \
    --VSwitchId your-vswitch-id \
    --RegionId cn-shanghai

# 4. 获取挂载地址
MOUNT_DOMAIN=$(aliyun nas DescribeMountTargets \
    --FileSystemId $FILESYSTEM_ID \
    --RegionId cn-shanghai \
    --output cols=MountTargetDomain rows=1)

echo "Mount Domain: $MOUNT_DOMAIN"
```

### 查询和监控脚本
```bash
# 查询文件系统使用情况
aliyun nas DescribeFileSystems \
    --FileSystemId 31a8e4xxxx \
    --RegionId cn-shanghai \
    --output cols=FileSystemId,MeteredSize,TotalSize

# 列出所有活跃的文件系统
aliyun nas DescribeFileSystems \
    --RegionId cn-shanghai \
    --output cols=FileSystemId,ProtocolType,StorageType,Status,CreateTime
```

## 8. 故障排查

### 常见问题及解决方案
| 问题 | 解决方案 |
|------|----------|
| **创建失败：配额不足** | 联系阿里云增加NAS配额 |
| **挂载失败：网络不通** | 检查VPC、VSwitch、安全组配置 |
| **权限拒绝** | 检查权限组（Access Group）规则 |
| **性能不佳** | 选择合适的存储类型和规格 |
| **跨区域访问** | 确保ECS实例和NAS在同一区域 |

### 权限组配置
通用型NAS需要配置权限组来控制访问权限：
```bash
# 创建权限组
aliyun nas CreateAccessGroup \
    --AccessGroupName e-hpc-access-group \
    --NetworkType Vpc \
    --RegionId cn-shanghai

# 添加访问规则
aliyun nas CreateAccessRule \
    --AccessGroupName e-hpc-access-group \
    --SourceCidrIp 192.168.0.0/16 \
    --RWAccessMode RW \
    --UserAccessType no_squash \
    --Priority 1 \
    --RegionId cn-shanghai
```

## 9. 最佳实践
1. **区域一致性**：NAS文件系统与E-HPC Instant作业在同一区域
2. **可用区优化**：极速型NAS选择与计算资源相同的可用区
3. **存储类型选择**：
   - 通用计算：通用型NAS（性能型）
   - 高性能计算：极速型NAS
   - 大规模并行：CPFS
4. **安全配置**：启用加密保护敏感数据
5. **监控告警**：设置容量和性能监控

## 10. 参考文档
- [阿里云NAS产品文档](https://help.aliyun.com/product/27517.html)
- [NAS API文档](https://api.aliyun.com/document/NAS/2017-06-26/overview)
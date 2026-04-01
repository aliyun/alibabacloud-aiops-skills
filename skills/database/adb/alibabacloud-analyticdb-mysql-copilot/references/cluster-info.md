# 集群信息查询

> **🚨🚨🚨 MUST | P0 | NON-NEGOTIABLE — 执行检查清单 🚨🚨🚨**
>
> 当用户询问集群信息时，**必须执行以下检查项**：
>
> - [ ] **MUST**：根据用户需求执行对应的 `aliyun adb DescribeDBClusters` 或 `DescribeDBClusterAttribute` 命令
> - [ ] **MUST**：在回复**第一行**输出命令字符串，格式：`执行命令：aliyun adb <APIName> --RegionId <region-id>`
> - [ ] **NON-NEGOTIABLE**：不得跳过API调用直接给出建议
>
> **违反任一检查项 = 任务失败**

当用户想了解"有哪些实例"、"实例配置是什么"、"集群状态"等信息时，按以下步骤操作。

## 一、查询集群列表

**回复格式模板**（必须遵守）：
```
执行命令：`aliyun adb DescribeDBClusters --RegionId <region-id>`

[查询结果、表格等内容]
```

列出指定地域下的所有 ADB MySQL 集群：

```bash
aliyun adb DescribeDBClusters --version 2021-12-01 --RegionId <region-id> --DBClusterVersion All --PageNumber 1 --PageSize 100
```

## 二、查询集群详细属性

获取单个集群的完整配置信息（规格、VPC、存储、版本等）：

```bash
aliyun adb DescribeDBClusterAttribute --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id>
```

**返回值关键字段**：

| 字段 | 含义 |
|------|------|
| `DBClusterId` | 集群 ID |
| `DBClusterDescription` | 集群描述 / 别名 |
| `DBClusterStatus` | 集群状态（Running、Stopped 等） |
| `DBClusterType` | 集群类型 |
| `CommodityCode` | 计费方式 |
| `ComputeResource` | 计算资源规格 |
| `StorageResource` | 存储资源规格 |
| `DBVersion` | 内核版本 |
| `VPCId` / `VSwitchId` | 网络信息 |
| `ConnectionString` | 连接地址 |
| `Port` | 端口 |
| `CreationTime` | 创建时间 |
| `ExpireTime` | 到期时间（包年包月时有效） |

## 三、查询存储空间概览

了解集群的磁盘使用情况：

```bash
aliyun adb DescribeDBClusterSpaceSummary --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id>
```

**返回值关键字段**：

| 字段 | 含义 |
|------|------|
| `TotalSize` | 总数据大小（单位：字节） |
| **HotData** | **热数据信息** |
| `HotData.TotalSize` | 热数据总大小（字节） |
| `HotData.DataSize` | 表记录数据大小（字节） |
| `HotData.IndexSize` | 普通索引数据大小（字节） |
| `HotData.PrimaryKeyIndexSize` | 主键索引数据大小（字节） |
| `HotData.OtherSize` | 其他数据大小（字节） |
| **ColdData** | **冷数据信息** |
| `ColdData.TotalSize` | 冷数据总大小（字节） |
| `ColdData.DataSize` | 表记录数据大小（字节） |
| `ColdData.IndexSize` | 普通索引数据大小（字节） |
| `ColdData.PrimaryKeyIndexSize` | 主键索引数据大小（字节） |
| `ColdData.OtherSize` | 其他数据大小（字节） |
| **DataGrowth** | **数据增长信息** |
| `DataGrowth.DayGrowth` | 最近一天数据增长量（字节） |
| `DataGrowth.WeekGrowth` | 最近七天的日均数据增长量（字节） |

> **计算公式**：
> - 总数据大小 = 热数据大小 + 冷数据大小
> - 热数据大小 = 表记录数据 + 普通索引 + 主键索引 + 其他数据
> - 最近七天日均增长 = (当前数据大小 - 7天前数据大小) / 7

## 四、常见使用场景

- **用户说"帮我看看有哪些 ADB 实例"** → 执行步骤 1
- **用户说"amv-xxx 这个实例是什么配置"** → 执行步骤 2
- **用户说"这个集群快到期了吗"** → 执行步骤 2，查看 `ExpireTime`
- **用户说"磁盘还剩多少空间"** → 执行步骤 3
- **用户不知道 cluster-id** → 先执行步骤 1 获取列表，再选择目标集群执行后续操作

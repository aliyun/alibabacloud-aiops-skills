# RAM 权限策略

本文档列出了阿里云视频锻造工坊（MPS 点播视频处理）所需的全部 RAM 权限。

> **重要说明**：MPS (媒体处理服务) 的 API 不支持资源级别的 RAM 授权，必须使用 `"Resource": "*"`。
> 这是阿里云 MPS 服务的设计限制，详见 [MPS RAM 授权说明](https://help.aliyun.com/zh/mps/developer-reference/api-mts-2014-06-18-overview)。
> 为降低风险，建议通过 **条件限制（Condition）** 约束访问来源 IP 或时间窗口。

## 权限概览

| 服务 | RAM Action | 描述 | 必需性 |
|------|------------|------|--------|
| MPS | mts:SubmitJobs | 提交转码任务 | 必需 |
| MPS | mts:QueryJobList | 查询转码任务列表 | 必需 |
| MPS | mts:SubmitSnapshotJob | 提交截图任务 | 必需 |
| MPS | mts:QuerySnapshotJobList | 查询截图任务列表 | 必需 |
| MPS | mts:SubmitMediaInfoJob | 提交媒体信息探测任务 | 必需 |
| MPS | mts:QueryMediaInfoJobList | 查询媒体信息任务列表 | 必需 |
| MPS | mts:SubmitMediaCensorJob | 提交内容审核任务 | 可选（审核功能） |
| MPS | mts:QueryMediaCensorJobDetail | 查询内容审核任务详情 | 可选（审核功能） |
| MPS | mts:QueryMediaCensorJobList | 查询内容审核任务列表 | 可选（审核功能） |
| MPS | mts:SearchPipeline | 查询管道列表 | 必需 |
| MPS | mts:QueryPipelineList | 查询管道详情 | 必需 |
| MPS | mts:QueryTemplateList | 查询转码模板列表 | 可选（模板管理） |
| OSS | oss:GetObject | 下载 OSS 对象 | 必需 |
| OSS | oss:PutObject | 上传 OSS 对象 | 必需 |
| OSS | oss:DeleteObject | 删除 OSS 对象 | 可选（清理功能） |
| OSS | oss:ListObjects | 列出 OSS 对象 | 必需 |
| OSS | oss:GetBucketInfo | 获取 Bucket 信息 | 可选 |

## 按功能模块权限

### 1. OSS 文件操作

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:PutObject",
        "oss:DeleteObject",
        "oss:ListObjects",
        "oss:GetBucketInfo"
      ],
      "Resource": [
        "acs:oss:*:*:your-bucket-name",
        "acs:oss:*:*:your-bucket-name/*"
      ]
    }
  ]
}
```

### 2. 媒体信息探测

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mts:SubmitMediaInfoJob",
        "mts:QueryMediaInfoJobList"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. 截图功能

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mts:SubmitSnapshotJob",
        "mts:QuerySnapshotJobList"
      ],
      "Resource": "*"
    }
  ]
}
```

### 4. 转码功能

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mts:SubmitJobs",
        "mts:QueryJobList",
        "mts:QueryTemplateList"
      ],
      "Resource": "*"
    }
  ]
}
```

### 5. 内容审核

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mts:SubmitMediaCensorJob",
        "mts:QueryMediaCensorJobDetail",
        "mts:QueryMediaCensorJobList"
      ],
      "Resource": "*"
    }
  ]
}
```

### 6. 管道管理

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mts:SearchPipeline",
        "mts:QueryPipelineList"
      ],
      "Resource": "*"
    }
  ]
}
```

## 完整权限策略

将以下策略附加到您的 RAM 用户或角色，即可使用本 Skill 的全部功能：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mts:SubmitJobs",
        "mts:QueryJobList",
        "mts:SubmitSnapshotJob",
        "mts:QuerySnapshotJobList",
        "mts:SubmitMediaInfoJob",
        "mts:QueryMediaInfoJobList",
        "mts:SubmitMediaCensorJob",
        "mts:QueryMediaCensorJobDetail",
        "mts:QueryMediaCensorJobList",
        "mts:SearchPipeline",
        "mts:QueryPipelineList",
        "mts:QueryTemplateList"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:PutObject",
        "oss:DeleteObject",
        "oss:ListObjects",
        "oss:GetBucketInfo"
      ],
      "Resource": [
        "acs:oss:*:*:your-bucket-name",
        "acs:oss:*:*:your-bucket-name/*"
      ]
    }
  ]
}
```

> **注意**：请将 `your-bucket-name` 替换为您实际使用的 OSS Bucket 名称。

## 安全增强：带条件限制的策略

由于 MPS API 不支持资源级别授权，建议使用 **条件限制（Condition）** 增强安全性：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "mts:SubmitJobs",
        "mts:QueryJobList",
        "mts:SubmitSnapshotJob",
        "mts:QuerySnapshotJobList",
        "mts:SubmitMediaInfoJob",
        "mts:QueryMediaInfoJobList",
        "mts:SubmitMediaCensorJob",
        "mts:QueryMediaCensorJobDetail",
        "mts:QueryMediaCensorJobList",
        "mts:SearchPipeline",
        "mts:QueryPipelineList",
        "mts:QueryTemplateList"
      ],
      "Resource": "*",
      "Condition": {
        "IpAddress": {
          "acs:SourceIp": ["203.0.113.0/24", "198.51.100.0/24"]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:PutObject",
        "oss:DeleteObject",
        "oss:ListObjects",
        "oss:GetBucketInfo"
      ],
      "Resource": [
        "acs:oss:*:*:your-bucket-name",
        "acs:oss:*:*:your-bucket-name/*"
      ]
    }
  ]
}
```

> **条件限制说明**：
> - `acs:SourceIp`：限制只能从指定 IP 地址范围访问（替换为您的实际 IP 段）
> - 更多条件类型请参考 [RAM 条件关键字](https://help.aliyun.com/zh/ram/user-guide/policy-elements-condition)

## 最小权限原则

如果您只需要使用部分功能，可以仅授予对应的权限：

| 使用场景 | 所需权限 |
|----------|----------|
| 仅上传/下载 | `oss:GetObject`, `oss:PutObject` |
| 仅转码 | `mts:SubmitJobs`, `mts:QueryJobList`, `mts:SearchPipeline` + OSS 权限 |
| 仅截图 | `mts:SubmitSnapshotJob`, `mts:QuerySnapshotJobList`, `mts:SearchPipeline` + OSS 权限 |
| 仅审核 | `mts:SubmitMediaCensorJob`, `mts:QueryMediaCensorJobDetail`, `mts:SearchPipeline` + OSS 权限 |
| 仅媒体信息 | `mts:SubmitMediaInfoJob`, `mts:QueryMediaInfoJobList`, `mts:SearchPipeline` + OSS 权限 |
| 清理资源 | `oss:DeleteObject`, `oss:ListObjects` |
| 管道查询 | `mts:SearchPipeline`, `mts:QueryPipelineList` |

## 系统策略推荐

如果不想自定义策略，可以使用阿里云提供的系统策略：

| 系统策略 | 说明 |
|----------|------|
| `AliyunMTSFullAccess` | MPS 服务完整权限 |
| `AliyunOSSFullAccess` | OSS 服务完整权限 |

```bash
# 通过 RAM 控制台附加系统策略
# 或使用 CLI
aliyun ram AttachPolicyToUser --PolicyType System --PolicyName AliyunMTSFullAccess --UserName <your-user>
aliyun ram AttachPolicyToUser --PolicyType System --PolicyName AliyunOSSFullAccess --UserName <your-user>
```

## 参考链接

- [MPS RAM 授权说明](https://help.aliyun.com/zh/mps/developer-reference/api-mts-2014-06-18-overview)
- [OSS RAM 授权说明](https://help.aliyun.com/zh/oss/user-guide/ram-policy)
- [RAM 控制台](https://ram.console.aliyun.com/)

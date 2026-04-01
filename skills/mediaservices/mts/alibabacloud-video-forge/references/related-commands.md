# 相关 CLI 命令

本文档列出阿里云视频锻造工坊涉及的 MPS 和 OSS CLI 命令。

> **注意**：本 Skill 主要使用 Python SDK 脚本实现，以下 CLI 命令可用于手动操作或调试。

## MPS (媒体处理服务) 命令

### 转码相关

| 命令 | 说明 | 示例 |
|------|------|------|
| `aliyun mts submit-jobs` | 提交转码任务 | `aliyun mts submit-jobs --Input '{"Bucket":"xxx","Location":"xxx","Object":"xxx"}' --OutputBucket xxx --OutputLocation cn-shanghai --TemplateId xxx --PipelineId xxx --user-agent AlibabaCloud-Agent-Skills` |
| `aliyun mts query-job-list` | 查询转码任务 | `aliyun mts query-job-list --JobIds xxx --user-agent AlibabaCloud-Agent-Skills` |

### 截图相关

| 命令 | 说明 | 示例 |
|------|------|------|
| `aliyun mts submit-snapshot-job` | 提交截图任务 | `aliyun mts submit-snapshot-job --Input '{"Bucket":"xxx","Object":"xxx"}' --SnapshotConfig '{"Time":"5000","OutputFile":{"Bucket":"xxx","Object":"xxx"}}' --PipelineId xxx --user-agent AlibabaCloud-Agent-Skills` |
| `aliyun mts query-snapshot-job-list` | 查询截图任务 | `aliyun mts query-snapshot-job-list --SnapshotJobIds xxx --user-agent AlibabaCloud-Agent-Skills` |

### 媒体信息相关

| 命令 | 说明 | 示例 |
|------|------|------|
| `aliyun mts submit-media-info-job` | 提交媒体信息任务 | `aliyun mts submit-media-info-job --Input '{"Bucket":"xxx","Object":"xxx"}' --PipelineId xxx --user-agent AlibabaCloud-Agent-Skills` |
| `aliyun mts query-media-info-job-list` | 查询媒体信息任务 | `aliyun mts query-media-info-job-list --MediaInfoJobIds xxx --user-agent AlibabaCloud-Agent-Skills` |

### 内容审核相关

| 命令 | 说明 | 示例 |
|------|------|------|
| `aliyun mts submit-media-censor-job` | 提交内容审核任务 | `aliyun mts submit-media-censor-job --Input '{"Bucket":"xxx","Object":"xxx"}' --PipelineId xxx --user-agent AlibabaCloud-Agent-Skills` |
| `aliyun mts query-media-censor-job-detail` | 查询审核任务详情 | `aliyun mts query-media-censor-job-detail --JobId xxx --user-agent AlibabaCloud-Agent-Skills` |
| `aliyun mts query-media-censor-job-list` | 查询审核任务列表 | `aliyun mts query-media-censor-job-list --JobIds xxx --user-agent AlibabaCloud-Agent-Skills` |

### 管道相关

| 命令 | 说明 | 示例 |
|------|------|------|
| `aliyun mts search-pipeline` | 搜索管道列表 | `aliyun mts search-pipeline --PageNumber 1 --PageSize 10 --user-agent AlibabaCloud-Agent-Skills` |
| `aliyun mts query-pipeline-list` | 查询管道详情 | `aliyun mts query-pipeline-list --PipelineIds xxx --user-agent AlibabaCloud-Agent-Skills` |
| `aliyun mts update-pipeline` | 更新管道状态 | `aliyun mts update-pipeline --PipelineId xxx --Name xxx --State Active --user-agent AlibabaCloud-Agent-Skills` |

### 模板相关

| 命令 | 说明 | 示例 |
|------|------|------|
| `aliyun mts query-template-list` | 查询模板列表 | `aliyun mts query-template-list --TemplateIds xxx --user-agent AlibabaCloud-Agent-Skills` |
| `aliyun mts search-template` | 搜索模板 | `aliyun mts search-template --PageNumber 1 --PageSize 10 --user-agent AlibabaCloud-Agent-Skills` |

## OSS (对象存储服务) 命令

> OSS 操作推荐使用 `ossutil` 工具或本 Skill 提供的 Python 脚本。

### 使用 ossutil

| 命令 | 说明 | 示例 |
|------|------|------|
| `ossutil cp` | 上传/下载文件 | `ossutil cp ./video.mp4 oss://bucket/input/video.mp4` |
| `ossutil ls` | 列出文件 | `ossutil ls oss://bucket/output/ --limit 100` |
| `ossutil sign` | 生成签名 URL | `ossutil sign oss://bucket/output/video.mp4 --timeout 3600` |

### 安装 ossutil

```bash
# macOS
brew install ossutil

# Linux
wget https://gosspublic.alicdn.com/ossutil/1.7.14/ossutil64
chmod +x ossutil64
sudo mv ossutil64 /usr/local/bin/ossutil

# 配置
ossutil config
```

## 凭证验证命令

```bash
# 验证 CLI 凭证配置
aliyun configure list

# 测试 MPS 服务连通性
aliyun mts search-pipeline --PageNumber 1 --PageSize 1 --user-agent AlibabaCloud-Agent-Skills

# 测试 ECS 服务（基本连通性测试）
aliyun ecs describe-regions --user-agent AlibabaCloud-Agent-Skills
```

## 常用组合命令

### 查看管道并选择

```bash
# 列出所有管道
aliyun mts search-pipeline --PageNumber 1 --PageSize 20 --user-agent AlibabaCloud-Agent-Skills

# 查看管道详情
aliyun mts query-pipeline-list --PipelineIds "pipeline-id-1,pipeline-id-2" --user-agent AlibabaCloud-Agent-Skills
```

### 转码工作流

```bash
# 1. 提交转码任务
JOB_RESPONSE=$(aliyun mts submit-jobs \
  --Input '{"Bucket":"your-bucket","Location":"oss-cn-shanghai","Object":"input/video.mp4"}' \
  --OutputBucket your-bucket \
  --OutputLocation oss-cn-shanghai \
  --TemplateId S00000001-100020 \
  --PipelineId your-pipeline-id \
  --Outputs '[{"OutputObject":"output/transcode/video.mp4"}]' \
  --user-agent AlibabaCloud-Agent-Skills)

# 2. 提取 JobId
JOB_ID=$(echo $JOB_RESPONSE | jq -r '.JobResultList.JobResult[0].Job.JobId')

# 3. 查询任务状态
aliyun mts query-job-list --JobIds $JOB_ID --user-agent AlibabaCloud-Agent-Skills
```

### 审核工作流

```bash
# 1. 提交审核任务
CENSOR_RESPONSE=$(aliyun mts submit-media-censor-job \
  --Input '{"Bucket":"your-bucket","Location":"oss-cn-shanghai","Object":"input/video.mp4"}' \
  --PipelineId your-audit-pipeline-id \
  --user-agent AlibabaCloud-Agent-Skills)

# 2. 提取 JobId
CENSOR_JOB_ID=$(echo $CENSOR_RESPONSE | jq -r '.JobId')

# 3. 查询审核结果
aliyun mts query-media-censor-job-detail --JobId $CENSOR_JOB_ID --user-agent AlibabaCloud-Agent-Skills
```

## 注意事项

1. **user-agent 标识**：所有 `aliyun` CLI 命令必须包含 `--user-agent AlibabaCloud-Agent-Skills`
2. **区域设置**：MPS 服务需要指定正确的区域（如 cn-shanghai）
3. **JSON 参数**：Input、Output 等参数需要使用 JSON 格式
4. **管道选择**：不同任务类型需要使用对应类型的管道（转码/审核）

## 参考链接

- [MPS CLI 文档](https://help.aliyun.com/zh/mps/developer-reference/api-mts-2014-06-18-overview)
- [OSS CLI 文档](https://help.aliyun.com/zh/oss/developer-reference/ossutil-overview)
- [Aliyun CLI 文档](https://help.aliyun.com/zh/cli/)

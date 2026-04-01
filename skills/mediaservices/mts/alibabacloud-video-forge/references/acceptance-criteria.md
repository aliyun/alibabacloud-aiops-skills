# Acceptance Criteria: alibabacloud-video-forge

**Scenario**: 阿里云 MPS 点播视频一站式处理
**Purpose**: Skill 测试验收标准

---

## 1. 环境配置验证

### 1.1 Python 环境
#### ✅ CORRECT
```bash
python3 --version
# Python 3.10.x 或更高版本
```

#### ❌ INCORRECT
```bash
python --version
# Python 2.7.x - 版本过低，不支持
```

### 1.2 SDK 安装
#### ✅ CORRECT
```bash
pip install alibabacloud-mts20140618 alibabacloud-credentials oss2
```

#### ❌ INCORRECT
```bash
# 错误：使用旧版 SDK
pip install aliyun-python-sdk-mts
```

### 1.3 凭证配置
#### ✅ CORRECT
```bash
# 使用 aliyun configure list 检查凭证状态
aliyun configure list
```

#### ❌ INCORRECT
```bash
# 错误：直接打印或读取凭证值
echo $<credential_env_var>    # Never echo credentials
cat ~/.alibabacloud/credentials  # Never read credential files directly
```

---

## 2. OSS 操作验证

### 2.1 上传文件
#### ✅ CORRECT
```bash
python scripts/oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4
```

#### ❌ INCORRECT
```bash
# 错误：缺少必填参数
python scripts/oss_upload.py --local-file ./video.mp4
# 错误：oss-key 不应以 / 开头
python scripts/oss_upload.py --local-file ./video.mp4 --oss-key /input/video.mp4
```

### 2.2 下载文件
#### ✅ CORRECT
```bash
python scripts/oss_download.py --oss-key output/transcode/video.mp4 --local-file ./output.mp4
```

#### ❌ INCORRECT
```bash
# 错误：直接访问 OSS URL（会返回 403）
curl https://bucket.oss-cn-shanghai.aliyuncs.com/output/video.mp4
```

---

## 3. MPS 任务验证

### 3.1 媒体信息探测
#### ✅ CORRECT
```bash
# 使用 --oss-object 参数（以 / 开头）
python scripts/mps_mediainfo.py --oss-object /input/video.mp4
```

#### ❌ INCORRECT
```bash
# 错误：--oss-object 缺少开头的 /
python scripts/mps_mediainfo.py --oss-object input/video.mp4
```

### 3.2 截图任务
#### ✅ CORRECT
```bash
# normal 模式必须指定 --time 参数（毫秒）
python scripts/mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000
```

#### ❌ INCORRECT
```bash
# 错误：normal 模式缺少 --time 参数
python scripts/mps_snapshot.py --oss-object /input/video.mp4 --mode normal
```

### 3.3 转码任务
#### ✅ CORRECT
```bash
# 自适应模式（推荐）
python scripts/mps_transcode.py --oss-object /input/video.mp4

# 指定预设
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 720p

# 多路转码
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset multi
```

#### ❌ INCORRECT
```bash
# 错误：无效的 preset 值
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 720

# 错误：同时指定 preset 和自定义参数（可能冲突）
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 720p --width 1920
```

### 3.4 内容审核
#### ✅ CORRECT
```bash
# 默认审核场景
python scripts/mps_audit.py --oss-object /input/video.mp4

# 指定审核场景（空格分隔）
python scripts/mps_audit.py --oss-object /input/video.mp4 --scenes porn terrorism ad
```

#### ❌ INCORRECT
```bash
# 错误：scenes 使用逗号分隔
python scripts/mps_audit.py --oss-object /input/video.mp4 --scenes porn,terrorism,ad
```

### 3.5 任务轮询
#### ✅ CORRECT
```bash
python scripts/poll_task.py --job-id abc123 --job-type transcode --region cn-shanghai
```

#### ❌ INCORRECT
```bash
# 错误：无效的 job-type
python scripts/poll_task.py --job-id abc123 --job-type video --region cn-shanghai
```

---

## 4. CLI 命令验证

### 4.1 user-agent 标识
#### ✅ CORRECT
```bash
aliyun mts search-pipeline --PageNumber 1 --PageSize 10 --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# 错误：缺少 --user-agent 参数
aliyun mts search-pipeline --PageNumber 1 --PageSize 10
```

### 4.2 命令格式
#### ✅ CORRECT
```bash
# 使用 plugin mode（小写连字符）
aliyun mts submit-jobs --Input '...' --user-agent AlibabaCloud-Agent-Skills
aliyun mts query-job-list --JobIds xxx --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# 错误：使用传统 API 格式（PascalCase action）
aliyun mts SubmitJobs --Input '...'
```

---

## 5. 工作流验证

### 5.1 完整工作流顺序
#### ✅ CORRECT
```
1. 上传视频到 OSS
2. 媒体信息探测
3. 截图生成封面
4. 转码处理
5. 内容审核
6. 下载产物
```

#### ❌ INCORRECT
```
# 错误：在上传之前尝试处理
1. 媒体信息探测（失败：文件不存在）
```

### 5.2 异步任务处理
#### ✅ CORRECT
```bash
# 提交任务后使用 poll_task.py 轮询状态
python scripts/mps_transcode.py --oss-object /input/video.mp4
# 记录返回的 job-id
python scripts/poll_task.py --job-id <job-id> --job-type transcode --region cn-shanghai
```

#### ❌ INCORRECT
```bash
# 错误：提交任务后立即尝试下载（任务可能未完成）
python scripts/mps_transcode.py --oss-object /input/video.mp4
python scripts/oss_download.py --oss-key output/transcode/video.mp4 --local-file ./output.mp4
```

---

## 6. 常见错误场景

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| `InvalidAccessKeyId` | AK 无效或未配置 | 检查凭证配置 |
| `SignatureDoesNotMatch` | SK 错误 | 重新配置凭证 |
| `Forbidden.RAM` | 权限不足 | 需要 MPS 和 OSS 相关权限 |
| `InvalidParameter` | 参数格式错误 | 检查参数值格式 |
| `ResourceNotFound` | OSS 文件不存在 | 确认文件路径正确 |
| `PipelineNotFound` | 管道不存在 | 使用 `mps_pipeline.py` 查询可用管道 |

---

## 7. 预期输出验证

### 7.1 转码成功
```json
{
  "JobId": "xxx",
  "State": "TranscodeSuccess",
  "Output": {
    "OutputFile": {
      "Bucket": "your-bucket",
      "Object": "output/transcode/video.mp4"
    }
  }
}
```

### 7.2 审核通过
```json
{
  "JobId": "xxx",
  "State": "Success",
  "Suggestion": "pass",
  "Results": []
}
```

### 7.3 审核发现违规
```json
{
  "JobId": "xxx",
  "State": "Success",
  "Suggestion": "block",
  "Results": [
    {
      "Scene": "porn",
      "Label": "xxx",
      "Rate": 99.9
    }
  ]
}
```

# 成功验证方法

本文档提供各项操作的成功验证步骤和预期结果。

## 1. 环境验证

### 1.1 Python 环境验证

```bash
# 验证 Python 版本
python3 --version
# 预期输出: Python 3.10.x 或更高版本
```

### 1.2 依赖安装验证

```bash
# 验证 SDK 安装
python3 -c "import alibabacloud_mts20140618; print('MTS SDK OK')"
python3 -c "import oss2; print('OSS2 SDK OK')"
python3 -c "import alibabacloud_credentials; print('Credentials SDK OK')"
# 预期输出: 三行 OK 信息
```

### 1.3 Aliyun CLI 验证（可选）

```bash
# 验证 CLI 版本
aliyun version
# 预期输出: 版本号 >= 3.3.1

# 验证 CLI 配置
aliyun configure list
# 预期输出: 显示当前配置的 profile 信息
```

### 1.4 凭证验证

```bash
# 使用 Aliyun CLI 检查凭证配置
aliyun configure list

# 预期输出: 显示当前配置的 profile 和凭证状态

# 使用环境变量加载器检查
python scripts/load_env.py --check-only

# 预期输出:
# ✅ 凭证配置: 已通过默认凭证链获取
# ✅ ALIBABA_CLOUD_OSS_BUCKET: 已配置
# ✅ ALIBABA_CLOUD_OSS_ENDPOINT: 已配置
```

## 2. OSS 操作验证

### 2.1 上传验证

```bash
# 上传文件
python scripts/oss_upload.py --local-file ./test.mp4 --oss-key input/test.mp4

# 预期输出:
# ✅ 上传成功
# 文件: input/test.mp4
# 大小: xxx bytes
# ETag: "xxxx"
```

**验证方式**：
```bash
# 列出文件确认上传成功
python scripts/oss_list.py --prefix input/
# 预期: 应看到 input/test.mp4 在列表中
```

### 2.2 下载验证

```bash
# 下载文件
python scripts/oss_download.py --oss-key input/test.mp4 --local-file ./downloaded.mp4

# 预期输出:
# ✅ 下载成功
# 本地文件: ./downloaded.mp4
# 大小: xxx bytes
```

**验证方式**：
```bash
# 检查本地文件是否存在
ls -la ./downloaded.mp4
# 预期: 显示文件信息，大小应与上传文件一致
```

### 2.3 列表验证

```bash
# 列出文件
python scripts/oss_list.py --prefix output/

# 预期输出:
# 找到 X 个文件
# output/transcode/xxx.mp4
# output/snapshot/xxx.jpg
```

## 3. 媒体处理验证

### 3.1 媒体信息探测验证

```bash
# 提交媒体信息探测任务
python scripts/mps_mediainfo.py --oss-object /input/video.mp4

# 预期输出:
# ✅ 媒体信息探测完成
# 文件格式: mp4
# 时长: xxx 秒
# 视频流: H.264, 1920x1080, 30fps
# 音频流: AAC, 48000Hz, stereo
```

**成功标志**：
- 返回码为 0
- 输出包含视频和音频流信息
- 显示时长、分辨率、编码格式等信息

### 3.2 截图验证

```bash
# 提交截图任务
python scripts/mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000

# 预期输出:
# ✅ 截图任务完成
# 任务 ID: xxx
# 输出文件: snapshot/00001.jpg
```

**验证方式**：
```bash
# 列出截图文件
python scripts/oss_list.py --prefix snapshot/
# 预期: 应看到生成的截图文件

# 下载截图确认
python scripts/oss_download.py --oss-key snapshot/00001.jpg --local-file ./snapshot.jpg
# 预期: 本地可查看截图文件
```

### 3.3 转码验证

```bash
# 提交转码任务（自适应模式）
python scripts/mps_transcode.py --oss-object /input/video.mp4

# 预期输出:
# ✅ 转码任务提交成功
# 任务 ID: xxx
# 输出路径: output/transcode/xxx.mp4
```

**轮询验证**：
```bash
# 查询转码任务状态
python scripts/poll_task.py --job-id <job-id> --job-type transcode --region cn-shanghai

# 预期输出（成功）:
# 任务 ID: xxx
# 状态: TranscodeSuccess / Success
# 输出文件: output/transcode/xxx.mp4
```

**最终验证**：
```bash
# 下载转码后的文件
python scripts/oss_download.py --oss-key output/transcode/xxx.mp4 --local-file ./transcoded.mp4

# 验证文件可播放
# 使用本地播放器打开 transcoded.mp4 确认视频正常
```

### 3.4 内容审核验证

```bash
# 提交审核任务
python scripts/mps_audit.py --oss-object /input/video.mp4

# 预期输出（审核通过）:
# ✅ 审核完成
# 任务 ID: xxx
# 审核结果: pass
# 各场景结果:
#   - porn: pass
#   - terrorism: pass
```

**查询已提交任务**：
```bash
# 查询审核任务结果
python scripts/mps_audit.py --query-job-id <job-id>

# 预期输出:
# 任务 ID: xxx
# 状态: success
# 审核结论: pass / review / block
```

**审核结果说明**：
| 结果 | 说明 |
|------|------|
| pass | 审核通过，内容合规 |
| review | 需要人工复核 |
| block | 内容违规，建议屏蔽 |

## 4. 管道验证

```bash
# 列出所有管道
python scripts/mps_pipeline.py

# 预期输出:
# PipelineId              Name                    State    Type
# ----------------------  ----------------------  -------  --------
# xxx                     mts-service-pipeline    Active   Standard
# xxx                     xxx-audit-pipeline      Active   AIVideoCensor
```

```bash
# 自动选择管道
python scripts/mps_pipeline.py --select

# 预期输出:
# xxx (仅输出 PipelineId)
```

## 5. 完整工作流验证

完整执行一站式视频处理流程后，验证以下内容：

### 5.1 输出文件检查

```bash
# 列出所有输出文件
python scripts/oss_list.py --prefix output/

# 预期输出:
# output/transcode/xxx.mp4    # 转码后的视频
# output/snapshot/00001.jpg   # 截图文件
```

### 5.2 任务状态检查

- 所有提交的任务状态为 `Success` 或 `TranscodeSuccess`
- 审核任务结果为 `pass`（如果内容合规）

### 5.3 产物质量检查

```bash
# 下载并检查转码后的视频
python scripts/oss_download.py --oss-key output/transcode/xxx.mp4 --local-file ./final.mp4

# 使用 ffprobe 检查视频信息（如果已安装 ffmpeg）
ffprobe ./final.mp4

# 预期: 视频可正常播放，分辨率和码率符合预期
```

## 6. 常见错误排查

### 6.1 任务失败

```bash
# 查看详细错误信息
python scripts/poll_task.py --job-id <job-id> --job-type transcode --region cn-shanghai --verbose

# 常见错误:
# - InvalidParameter: 参数错误，检查输入参数
# - ResourceNotFound: 资源不存在，检查 OSS 文件路径
# - InsufficientBalance: 余额不足
# - PermissionDenied: 权限不足，检查 RAM 权限
```

### 6.2 OSS 访问失败

```bash
# 检查 OSS 配置
python scripts/load_env.py --check-only

# 验证 Bucket 访问
python scripts/oss_list.py --prefix ""

# 常见错误:
# - AccessDenied: 权限不足或 Bucket 不存在
# - InvalidAccessKeyId: AK 无效
# - SignatureDoesNotMatch: SK 错误
```

### 6.3 管道不可用

```bash
# 列出所有管道检查状态
python scripts/mps_pipeline.py --verbose

# 常见错误:
# - 所有管道状态为 Paused
# - 没有符合任务类型的管道

# 解决方案:
# - 在 MPS 控制台激活管道
# - 确保有对应类型的管道（转码/审核）
```

# 脚本用法示例集

> 所有脚本均支持 `--help` 查看完整帮助文档。
> 完整参数说明见 [`params.md`](params.md)。

## 目录

- [OSS 文件上传 — oss_upload.py](#oss-文件上传--oss_uploadpy)
- [OSS 文件下载 — oss_download.py](#oss-文件下载--oss_downloadpy)
- [OSS 文件列表 — oss_list.py](#oss-文件列表--oss_listpy)
- [媒体信息探测 — mps_mediainfo.py](#媒体信息探测--mps_mediainfopy)
- [截图与雪碧图 — mps_snapshot.py](#截图与雪碧图--mps_snapshotpy)
- [多清晰度转码 — mps_transcode.py](#多清晰度转码--mps_transcodepy)
- [内容审核 — mps_audit.py](#内容审核--mps_auditpy)
- [管道查询与选择 — mps_pipeline.py](#管道查询与选择--mps_pipelinepy)
- [完整端到端工作流示例](#完整端到端工作流示例)

---

## OSS 文件上传 — oss_upload.py

### 基础用法

```bash
# 最简用法（使用环境变量中的 bucket 和 endpoint）
python scripts/oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4

# 显示详细日志
python scripts/oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4 --verbose
```

### 高级用法

```bash
# 指定 bucket 和 endpoint（覆盖环境变量）
python scripts/oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4 \
    --bucket mybucket --endpoint oss-cn-hangzhou.aliyuncs.com

# 上传图片文件
python scripts/oss_upload.py --local-file ./photo.jpg --oss-key input/photo.jpg
```

### 预览模式

```bash
# 预览模式（不实际上传）
python scripts/oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4 --dry-run

# 预览模式 + 详细日志
python scripts/oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4 --dry-run --verbose
```

---

## OSS 文件下载 — oss_download.py

### 基础用法

```bash
# 最简用法（使用环境变量中的 bucket 和 endpoint）
python scripts/oss_download.py --oss-key output/result.mp4 --local-file ./result.mp4

# 显示详细日志
python scripts/oss_download.py --oss-key output/result.mp4 --local-file ./result.mp4 --verbose
```

### 高级用法

```bash
# 指定 bucket 和 endpoint（覆盖环境变量）
python scripts/oss_download.py --oss-key output/result.mp4 --local-file ./result.mp4 \
    --bucket mybucket --endpoint oss-cn-hangzhou.aliyuncs.com

# 下载到指定目录（自动创建）
python scripts/oss_download.py --oss-key output/result.mp4 --local-file ./downloads/video/result.mp4
```

### 预签名 URL

```bash
# 仅生成预签名 URL，不下载文件
python scripts/oss_download.py --oss-key input/video.mp4 --local-file ./video.mp4 --sign-url
```

### 预览模式

```bash
# 预览模式（不实际下载）
python scripts/oss_download.py --oss-key output/result.mp4 --local-file ./result.mp4 --dry-run
```

---

## OSS 文件列表 — oss_list.py

### 基础用法

```bash
# 列出 Bucket 根目录下的所有文件（使用环境变量中的 bucket）
python scripts/oss_list.py

# 列出指定路径下的文件
python scripts/oss_list.py --prefix output/transcode/

# 限制返回数量
python scripts/oss_list.py --prefix output/ --max-keys 50
```

### 高级用法

```bash
# 指定 bucket 和 endpoint（覆盖环境变量）
python scripts/oss_list.py --prefix input/ --bucket mybucket --endpoint oss-cn-hangzhou.aliyuncs.com

# 显示详细日志
python scripts/oss_list.py --prefix output/transcode/ --verbose
```

### JSON 格式输出

```bash
# JSON 格式输出
python scripts/oss_list.py --prefix output/ --json

# JSON 格式 + 限制数量
python scripts/oss_list.py --prefix output/transcode/ --json --max-keys 20
```

---

## 媒体信息探测 — mps_mediainfo.py

### 基础用法

```bash
# 使用公网 URL 探测媒体信息
python scripts/mps_mediainfo.py --url https://example.com/video.mp4

# 使用 OSS 对象路径探测（自动从环境变量获取 bucket）
python scripts/mps_mediainfo.py --oss-object /input/video.mp4
```

### 高级用法

```bash
# 指定地域
python scripts/mps_mediainfo.py --url https://example.com/video.mp4 --region cn-hangzhou

# 输出完整 JSON 格式
python scripts/mps_mediainfo.py --url https://example.com/video.mp4 --json

# OSS 输入 + JSON 输出
python scripts/mps_mediainfo.py --oss-object /input/video.mp4 --json

# 指定 Pipeline ID
python scripts/mps_mediainfo.py --oss-object /input/video.mp4 --pipeline-id your-pipeline-id
```

### 预览模式

```bash
# Dry Run 模式（仅打印请求参数）
python scripts/mps_mediainfo.py --url https://example.com/video.mp4 --dry-run
```

---

## 截图与雪碧图 — mps_snapshot.py

### 基础用法

```bash
# 普通截图（指定时间点，单位毫秒）
python scripts/mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000

# 雪碧图
python scripts/mps_snapshot.py --url https://example.com/video.mp4 --mode sprite
```

### 高级用法

```bash
# 使用 OSS 对象作为输入
python scripts/mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000

# 自定义输出位置和数量
python scripts/mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 \
    --count 3 --interval 10

# 指定地域
python scripts/mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --region cn-hangzhou

# 自定义输出尺寸
python scripts/mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --width 1280 --height 720
```

### 异步模式

```bash
# 异步模式（不等待结果）
python scripts/mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --async

# 指定 Pipeline ID
python scripts/mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --pipeline-id your-pipeline-id
```

### 预览模式

```bash
# Dry Run 模式
python scripts/mps_snapshot.py --url https://example.com/video.mp4 --mode normal --time 5000 --dry-run

# Dry Run 模式 + 雪碧图
python scripts/mps_snapshot.py --url https://example.com/video.mp4 --mode sprite --dry-run
```

---

## 多清晰度转码 — mps_transcode.py

### 基础用法

**自适应模式（推荐）**：

```bash
# 自适应单路窄带高清转码（默认）
# 自动检测源视频分辨率，选择最合适的清晰度，使用窄带高清模板
python scripts/mps_transcode.py --oss-object /input/video.mp4

# URL 输入 + 自适应模式
python scripts/mps_transcode.py --url https://example.com/video.mp4
```

**手动指定清晰度**：

```bash
# OSS 输入 + 720p 预设
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 720p

# OSS 输入 + 1080p 预设
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 1080p
```

### 多清晰度输出

```bash
# 同时生成 360p/480p/720p/1080p 四个版本
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset multi
```

### 自定义参数

```bash
# 自定义编码 + 分辨率 + 码率
python scripts/mps_transcode.py --oss-object /input/video.mp4 \
    --codec H.265 --width 1920 --height 1080 --bitrate 3000

# HLS 切片输出
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 720p --container hls
```

### 使用模板

```bash
# 直接使用 MPS 模板 ID
python scripts/mps_transcode.py --oss-object /input/video.mp4 --template-id your-template-id
```

### 输出配置

```bash
# 自定义输出 bucket 和目录
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 720p \
    --output-bucket mybucket --output-prefix output/custom/

# 指定地域
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 720p --region cn-hangzhou
```

### 异步模式

```bash
# 提交后不等待任务完成
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 720p --async

# 详细输出 + 不等待
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset multi --async --verbose
```

### 预览模式

```bash
# Dry Run 模式（自适应）
python scripts/mps_transcode.py --oss-object /input/video.mp4 --dry-run

# Dry Run 模式 + 指定清晰度
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset 720p --dry-run

# Dry Run 模式 + 多清晰度
python scripts/mps_transcode.py --oss-object /input/video.mp4 --preset multi --dry-run
```

---

## 内容审核 — mps_audit.py

### 基础用法

```bash
# 对 URL 进行默认审核（porn, terrorism）
python scripts/mps_audit.py --url https://example.com/video.mp4

# 使用 OSS 对象作为输入
python scripts/mps_audit.py --oss-object /input/video.mp4
```

### 指定审核场景

```bash
# 仅审核涉黄和暴恐
python scripts/mps_audit.py --url https://example.com/video.mp4 --scenes porn terrorism

# 仅审核广告和 Logo
python scripts/mps_audit.py --url https://example.com/video.mp4 --scenes ad logo

# 仅审核音频反垃圾
python scripts/mps_audit.py --url https://example.com/video.mp4 --scenes audio
```

### 高级用法

```bash
# 指定地域
python scripts/mps_audit.py --url https://example.com/video.mp4 --region cn-hangzhou

# 输出完整 JSON 格式
python scripts/mps_audit.py --url https://example.com/video.mp4 --json
```

### 异步模式

```bash
# 异步模式（不等待结果）
python scripts/mps_audit.py --url https://example.com/video.mp4 --async
```

### 查询已有任务

```bash
# 查询已有任务结果
python scripts/mps_audit.py --query-job-id your-job-id --region cn-shanghai

# 查询已有任务 + JSON 输出
python scripts/mps_audit.py --query-job-id your-job-id --region cn-shanghai --json
```

### 预览模式

```bash
# Dry Run 模式
python scripts/mps_audit.py --url https://example.com/video.mp4 --dry-run

# Dry Run 模式 + 指定审核场景
python scripts/mps_audit.py --url https://example.com/video.mp4 --scenes porn terrorism --dry-run
```

---

## 管道查询与选择 — mps_pipeline.py

### 基础用法

```bash
# 列出所有管道（表格格式）
python scripts/mps_pipeline.py

# 指定区域
python scripts/mps_pipeline.py --region cn-hangzhou

# JSON 格式输出
python scripts/mps_pipeline.py --json
```

### 按类型选择管道

```bash
# 列出转码管道
python scripts/mps_pipeline.py --type standard

# 列出窄带高清转码管道
python scripts/mps_pipeline.py --type narrowband

# 列出审核管道
python scripts/mps_pipeline.py --type audit

# 按类型自动选择并输出 PipelineId
python scripts/mps_pipeline.py --type audit --select
```

### 自动选择模式

```bash
# 自动选择并输出 PipelineId（适合 shell 脚本捕获）
python scripts/mps_pipeline.py --select

# 捕获到环境变量
export ALIBABA_CLOUD_MPS_PIPELINE_ID=$(python scripts/mps_pipeline.py --select)

# 指定首选管道名称
python scripts/mps_pipeline.py --select --name my-custom-pipeline

# 自动选择 + JSON 输出详细信息
python scripts/mps_pipeline.py --select --json
```

### 高级用法

```bash
# 显示详细日志
python scripts/mps_pipeline.py --verbose

# 自动选择模式 + 详细日志
python scripts/mps_pipeline.py --select --verbose

# 指定区域和首选名称
python scripts/mps_pipeline.py --region cn-beijing --select --name beijing-pipeline
```

### 在其他脚本中使用

配合转码脚本使用（管道 ID 可选，会自动选择）：

```bash
# 方式1：让脚本自动选择管道（推荐）
python scripts/mps_transcode.py --oss-object /input/video.mp4

# 方式2：手动指定管道 ID
PIPELINE_ID=$(python scripts/mps_pipeline.py --select)
python scripts/mps_transcode.py \
    --oss-object /input/video.mp4 \
    --preset 720p \
    --pipeline-id "$PIPELINE_ID"
```

### 在 Shell 脚本中使用

```bash
#!/bin/bash

# 方式1：使用自动管道选择（推荐，无需获取 Pipeline ID）
python scripts/mps_transcode.py \
    --oss-object /input/video.mp4 \
    --preset multi

# 方式2：手动获取并指定 Pipeline ID
PIPELINE_ID=$(python scripts/mps_pipeline.py --select)

if [ -z "$PIPELINE_ID" ]; then
    echo "错误：无法获取 Pipeline ID"
    exit 1
fi

echo "使用 Pipeline ID: $PIPELINE_ID"

python scripts/mps_transcode.py \
    --oss-object /input/video.mp4 \
    --preset multi \
    --pipeline-id "$PIPELINE_ID"
```

---

## 完整端到端工作流示例

以下是一个**一站式视频标准化处理场景**的完整工作流示例，涵盖从上传到下载的全过程。

> **注意**：本工作流已支持管道自动选择，无需手动配置 `PIPELINE_ID`。

```bash
#!/bin/bash
# ============================================
# 一站式视频标准化处理工作流
# ============================================

# 配置变量
LOCAL_VIDEO="./source_video.mp4"
OSS_INPUT_KEY="input/video.mp4"
OSS_OUTPUT_DIR="output"
REGION="cn-shanghai"
# PIPELINE_ID 已可选，脚本会自动选择适合的管道

echo "========================================"
echo "Step 1: 上传本地视频到 OSS"
echo "========================================"
python scripts/oss_upload.py \
    --local-file "$LOCAL_VIDEO" \
    --oss-key "$OSS_INPUT_KEY" \
    --verbose

echo ""
echo "========================================"
echo "Step 2: 媒体信息探测"
echo "========================================"
python scripts/mps_mediainfo.py \
    --oss-object "/$OSS_INPUT_KEY" \
    --region "$REGION"

echo ""
echo "========================================"
echo "Step 3: 视频截图"
echo "========================================"
python scripts/mps_snapshot.py \
    --oss-object "/$OSS_INPUT_KEY" \
    --mode normal --time 5000 \
    --output-prefix "$OSS_OUTPUT_DIR/snapshot/" \
    --region "$REGION"

echo ""
echo "========================================"
echo "Step 4: 自适应转码（自动选择最佳清晰度）"
echo "========================================"
# 自适应模式：自动检测源视频分辨率，选择最合适的清晰度，使用窄带高清模板
python scripts/mps_transcode.py \
    --oss-object "/$OSS_INPUT_KEY" \
    --output-prefix "$OSS_OUTPUT_DIR/transcode/" \
    --region "$REGION"

echo ""
echo "========================================"
echo "Step 5: 内容审核"
echo "========================================"
python scripts/mps_audit.py \
    --oss-object "/$OSS_INPUT_KEY" \
    --scenes porn terrorism ad \
    --region "$REGION"

echo ""
echo "========================================"
echo "Step 6: 列出所有输出文件"
echo "========================================"
python scripts/oss_list.py \
    --prefix "$OSS_OUTPUT_DIR/" \
    --json

echo ""
echo "========================================"
echo "Step 7: 下载转码后的视频到本地"
echo "========================================"
# OSS 文件需要签名才能访问，推荐下载到本地查看
python scripts/oss_download.py \
    --oss-key "$OSS_OUTPUT_DIR/transcode/transcoded.mp4" \
    --local-file "./output_video.mp4" \
    --verbose

echo ""
echo "========================================"
echo "Step 8: 下载封面截图到本地（可选）"
echo "========================================"
python scripts/oss_download.py \
    --oss-key "$OSS_OUTPUT_DIR/snapshot/00001.jpg" \
    --local-file "./output_thumbnail.jpg"

echo ""
echo "========================================"
echo "工作流完成！"
echo "输出文件："
echo "  - 视频: ./output_video.mp4"
echo "  - 封面: ./output_thumbnail.jpg"
echo "========================================"
```

### 工作流说明

| 步骤 | 脚本 | 功能说明 |
|------|------|----------|
| Step 1 | `oss_upload.py` | 将本地视频上传到 OSS，作为后续处理的输入 |
| Step 2 | `mps_mediainfo.py` | 探测视频的媒体信息（分辨率、码率、编码格式等） |
| Step 3 | `mps_snapshot.py` | 生成视频截图/封面 |
| Step 4 | `mps_transcode.py` | 自适应转码，自动选择最佳清晰度，使用窄带高清模板 |
| Step 5 | `mps_audit.py` | 内容审核，检测涉黄、暴恐、广告等违规内容 |
| Step 6 | `oss_list.py` | 列出所有输出文件，查看处理结果 |
| Step 7 | `oss_download.py` | 下载转码后的视频到本地 |
| Step 8 | `oss_download.py` | 下载封面截图到本地 |

**关于产物获取**：
- OSS 文件需要签名才能在线访问，直接访问 URL 会返回 403 错误
- 推荐使用 `oss_download.py` 将结果下载到本地查看
- 如需在线预览，可使用 `--sign-url` 参数生成临时预签名 URL

### 其他常见工作流

#### 视频发布前处理工作流

```bash
# 1. 上传
python scripts/oss_upload.py --local-file ./video.mp4 --oss-key input/video.mp4

# 2. 内容审核（必须先审核，管道自动选择）
python scripts/mps_audit.py --oss-object /input/video.mp4 --scenes porn terrorism ad

# 3. 自适应转码（自动选择最佳清晰度）
python scripts/mps_transcode.py --oss-object /input/video.mp4

# 4. 生成封面截图
python scripts/mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000

# 5. 下载产物到本地
python scripts/oss_download.py --oss-key output/transcode/transcoded.mp4 --local-file ./output.mp4
```

#### 视频编辑工作流

```bash
# 1. 上传原始素材
python scripts/oss_upload.py --local-file ./raw.mp4 --oss-key input/raw.mp4

# 2. 探测媒体信息（管道自动选择）
python scripts/mps_mediainfo.py --oss-object /input/raw.mp4

# 3. 截图获取关键帧（管道自动选择）
python scripts/mps_snapshot.py --oss-object /input/raw.mp4 --mode normal --time 5000 --count 5

# 4. 转码为统一格式（管道自动选择）
python scripts/mps_transcode.py --oss-object /input/raw.mp4 --preset 1080p --codec H.264

# 5. 下载结果
python scripts/oss_download.py --oss-key output/transcode/transcoded.mp4 --local-file ./edited.mp4
```


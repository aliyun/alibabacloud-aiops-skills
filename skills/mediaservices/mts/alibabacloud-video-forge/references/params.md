# 参数文档

> 所有脚本均支持 `--help` 显示完整帮助文档。
> 完整用法示例见 [`scripts-detail.md`](scripts-detail.md)。

## 目录

- [通用参数（所有脚本）](#通用参数所有脚本)
- [OSS 文件上传参数 oss_upload.py](#oss-文件上传参数-oss_uploadpy)
- [OSS 文件下载参数 oss_download.py](#oss-文件下载参数-oss_downloadpy)
- [OSS 文件列表参数 oss_list.py](#oss-文件列表参数-oss_listpy)
- [OSS 文件删除参数 oss_delete.py](#oss-文件删除参数-oss_deletepy)
- [媒体信息探测参数 mps_mediainfo.py](#媒体信息探测参数-mps_mediainfopy)
- [截图与雪碧图参数 mps_snapshot.py](#截图与雪碧图参数-mps_snapshotpy)
- [多清晰度转码参数 mps_transcode.py](#多清晰度转码参数-mps_transcodepy)
- [内容审核参数 mps_audit.py](#内容审核参数-mps_auditpy)
- [管道查询与选择参数 mps_pipeline.py](#管道查询与选择参数-mps_pipelinepy)

---

## 通用参数（所有脚本）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--help` / `-h` | - | 否 | - | 显示完整的帮助文档 |
| `--dry-run` / `-d` | flag | 否 | false | 预览模式，只显示将要执行的操作，不实际调用 API |
| `--verbose` / `-v` | flag | 否 | false | 显示详细日志 |

### 环境变量（所有脚本共用）

| 环境变量 | 说明 |
|----------|------|
| `ALIBABA_CLOUD_OSS_BUCKET` | OSS Bucket 名称 |
| `ALIBABA_CLOUD_OSS_ENDPOINT` | OSS Endpoint（如 oss-cn-hangzhou.aliyuncs.com） |
| `ALIBABA_CLOUD_MPS_PIPELINE_ID` | MPS Pipeline ID（可选，未设置时自动选择） |
| `ALIBABA_CLOUD_REGION` | 服务区域（可选，默认 cn-shanghai） |

> **凭证说明**：脚本使用 Alibaba Cloud 默认凭证链获取凭证，通过 `aliyun configure` 配置。

---

## OSS 文件上传参数 oss_upload.py

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--local-file` / `-f` | string | 是 | - | 本地文件路径 |
| `--oss-key` / `-k` | string | 是 | - | OSS 对象键（Key），如 input/video.mp4 |
| `--bucket` / `-b` | string | 否 | 环境变量 | OSS Bucket 名称（默认使用环境变量 ALIBABA_CLOUD_OSS_BUCKET） |
| `--endpoint` / `-e` | string | 否 | 环境变量 | OSS Endpoint（默认使用环境变量 ALIBABA_CLOUD_OSS_ENDPOINT） |
| `--dry-run` / `-d` | flag | 否 | false | 预览模式，只显示将要执行的操作，不实际上传 |
| `--verbose` / `-v` | flag | 否 | false | 显示详细日志 |

---

## OSS 文件下载参数 oss_download.py

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--oss-key` / `-k` | string | 是 | - | OSS 对象键（Key），如 input/video.mp4 |
| `--local-file` / `-f` | string | 是 | - | 本地保存路径 |
| `--bucket` / `-b` | string | 否 | 环境变量 | OSS Bucket 名称（默认使用环境变量 ALIBABA_CLOUD_OSS_BUCKET） |
| `--endpoint` / `-e` | string | 否 | 环境变量 | OSS Endpoint（默认使用环境变量 ALIBABA_CLOUD_OSS_ENDPOINT） |
| `--sign-url` / `-s` | flag | 否 | false | 仅生成预签名 URL，不下载文件 |
| `--dry-run` / `-d` | flag | 否 | false | 预览模式，只显示将要执行的操作，不实际下载 |
| `--verbose` / `-v` | flag | 否 | false | 显示详细日志 |

---

## OSS 文件列表参数 oss_list.py

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--prefix` / `-p` | string | 否 | "" | 路径前缀，用于过滤指定目录下的文件（如 output/transcode/） |
| `--max-keys` / `-m` | int | 否 | 100 | 最大返回文件数量 |
| `--bucket` / `-b` | string | 否 | 环境变量 | OSS Bucket 名称（默认使用环境变量 ALIBABA_CLOUD_OSS_BUCKET） |
| `--endpoint` / `-e` | string | 否 | 环境变量 | OSS Endpoint（默认使用环境变量 ALIBABA_CLOUD_OSS_ENDPOINT） |
| `--json` / `-j` | flag | 否 | false | 以 JSON 格式输出 |
| `--verbose` / `-v` | flag | 否 | false | 显示详细日志 |

---

## OSS 文件删除参数 oss_delete.py

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--oss-key` / `-k` | string | 条件 | - | OSS 对象键，删除单个文件（与 --prefix 互斥） |
| `--prefix` / `-p` | string | 条件 | - | OSS 路径前缀，配合 --recursive 使用（与 --oss-key 互斥） |
| `--recursive` / `-r` | flag | 条件 | false | 递归删除前缀下的所有文件（仅与 --prefix 配合使用，必填） |
| `--force` / `-f` | flag | 否 | false | 强制删除，跳过确认提示（用于脚本自动化） |
| `--bucket` / `-b` | string | 否 | 环境变量 | OSS Bucket 名称（默认使用环境变量 ALIBABA_CLOUD_OSS_BUCKET） |
| `--endpoint` / `-e` | string | 否 | 环境变量 | OSS Endpoint（默认使用环境变量 ALIBABA_CLOUD_OSS_ENDPOINT） |
| `--dry-run` / `-d` | flag | 否 | false | 预览模式，只显示将要删除的文件，不实际删除 |
| `--verbose` / `-v` | flag | 否 | false | 显示详细日志 |

**说明**：
- `--oss-key` 和 `--prefix` 必须指定其中一个
- 使用 `--prefix` 时必须同时指定 `--recursive` 参数
- 建议先使用 `--dry-run` 预览要删除的文件

---

## 媒体信息探测参数 mps_mediainfo.py

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--url` | string | 条件 | - | 媒体文件公网 URL（与 --oss-object 互斥） |
| `--oss-object` | string | 条件 | - | OSS 对象路径（如 /input/video.mp4，与 --url 互斥） |
| `--region` | string | 否 | cn-shanghai | MPS 服务区域 |
| `--pipeline-id` | string | 否 | 自动选择 | MPS Pipeline ID（可选，默认自动选择） |
| `--json` | flag | 否 | false | 输出完整 JSON 格式 |
| `--dry-run` | flag | 否 | false | 仅打印请求参数，不实际调用 API |
| `--user-data` | string | 否 | - | 用户自定义数据 |

**说明**：
- `--url` 和 `--oss-object` 必须指定其中一个
- 使用 `--oss-object` 时需要配置 `ALIBABA_CLOUD_OSS_BUCKET` 环境变量
- `--pipeline-id` 为可选参数，未指定时自动选择合适的管道

---

## 截图与雪碧图参数 mps_snapshot.py

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--url` | string | 条件 | - | 媒体文件公网 URL（与 --oss-object 互斥） |
| `--oss-object` | string | 条件 | - | OSS 对象路径（如 /input/video.mp4，与 --url 互斥） |
| `--mode` | string | 否 | normal | 截图模式：normal（普通截图）、sprite（雪碧图） |
| `--time` | int | 条件 | - | 截图时间点（毫秒），用于 normal 模式，必填 |
| `--count` | int | 否 | 1 | 截图数量 |
| `--interval` | int | 否 | 10 | 截图间隔（秒） |
| `--width` | int | 否 | - | 输出宽度（像素） |
| `--height` | int | 否 | - | 输出高度（像素） |
| `--output-prefix` | string | 否 | snapshot/{Count} | 输出文件前缀 |
| `--output-bucket` | string | 否 | 环境变量 | 输出 OSS Bucket 名称 |
| `--pipeline-id` | string | 否 | 自动选择 | MPS Pipeline ID（可选，默认自动选择） |
| `--region` | string | 否 | cn-shanghai | MPS 服务区域 |
| `--async` | flag | 否 | false | 仅提交任务，不等待结果 |
| `--dry-run` | flag | 否 | false | 仅打印请求参数，不实际调用 API |

**说明**：
- 输入源 `--url`、`--oss-object` 二者互斥，必须指定其中一个
- `--mode normal` 模式下必须指定 `--time` 参数（单位：毫秒）

---

## 多清晰度转码参数 mps_transcode.py

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--url` | string | 条件 | - | 公网可访问的视频 URL（与 --oss-object 互斥） |
| `--oss-object` | string | 条件 | - | OSS 对象路径（如 /input/video.mp4，与 --url 互斥） |
| `--preset` | string | 否 | - | 清晰度预设：360p、480p、720p、1080p、4k、multi（multi=同时生成4个版本）。不指定时使用自适应模式 |
| `--codec` | string | 否 | H.264 | 视频编码格式：H.264、H.265 |
| `--width` | int | 否 | - | 视频宽度（像素） |
| `--height` | int | 否 | - | 视频高度（像素） |
| `--bitrate` | int | 否 | - | 视频码率（kbps） |
| `--container` | string | 否 | mp4 | 封装格式：mp4、hls |
| `--fps` | int | 否 | - | 帧率 |
| `--template-id` | string | 否 | - | 直接使用 MPS 模板 ID（覆盖自适应模式） |
| `--output-bucket` | string | 否 | 环境变量 | 输出 OSS Bucket（默认从环境变量读取） |
| `--output-prefix` | string | 否 | output/transcode/ | 输出文件前缀 |
| `--pipeline-id` | string | 否 | 自动选择 | MPS Pipeline ID（可选，默认自动选择） |
| `--region` | string | 否 | cn-shanghai | 服务区域 |
| `--async` | flag | 否 | false | 提交后不等待任务完成 |
| `--verbose` / `-v` | flag | 否 | false | 输出详细信息 |
| `--dry-run` | flag | 否 | false | 仅打印请求参数，不实际调用 API |

**说明**：
- `--url` 和 `--oss-object` 必须指定其中一个（推荐使用 `--oss-object`）
- **自适应模式**（默认）：不指定 `--preset` 时，自动检测源视频分辨率，选择最合适的清晰度，优先使用窄带高清模板（低码率高画质）
- `--pipeline-id` 为可选参数，未指定时自动选择 Standard 或 NarrowBandHDV2 管道
- 清晰度预设参数表：

| 预设 | 分辨率 | 视频码率 | 音频码率 |
|------|--------|----------|----------|
| 360p | 640x360 | 800 kbps | 64 kbps |
| 480p | 854x480 | 1200 kbps | 96 kbps |
| 720p | 1280x720 | 2500 kbps | 128 kbps |
| 1080p | 1920x1080 | 4500 kbps | 128 kbps |
| 4k | 3840x2160 | 15000 kbps | 192 kbps |
| multi | 同时生成 360p/480p/720p/1080p 四个版本 | - | - |

---

## 内容审核参数 mps_audit.py

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--url` | string | 条件 | - | 媒体文件公网 URL（与 --oss-object、--query-job-id 互斥） |
| `--oss-object` | string | 条件 | - | OSS 对象路径（如 /input/video.mp4，与 --url 互斥） |
| `--query-job-id` | string | 条件 | - | 查询已有任务结果（与 --url、--oss-object 互斥） |
| `--scenes` | string | 否 | porn,terrorism | 审核场景，空格分隔。可选：porn、terrorism、ad、live、logo、audio |
| `--output-prefix` | string | 否 | audit/{Count} | 异常帧输出文件前缀 |
| `--output-bucket` | string | 否 | 环境变量 | 输出 OSS Bucket 名称 |
| `--pipeline-id` | string | 否 | 自动选择 | MPS Pipeline ID（可选，默认自动选择 AIVideoCensor 管道） |
| `--region` | string | 否 | cn-shanghai | MPS 服务区域 |
| `--async` | flag | 否 | false | 仅提交任务，不等待结果 |
| `--dry-run` | flag | 否 | false | 仅打印请求参数，不实际调用 API |

**说明**：
- 输入源 `--url`、`--oss-object`、`--query-job-id` 三者互斥，必须指定其中一个
- 不指定 `--scenes` 时默认进行 porn、terrorism 审核

**审核场景说明**：

| 场景 | 说明 |
|------|------|
| porn | 涉黄检测 |
| terrorism | 暴恐检测 |
| ad | 广告检测 |
| live | 直播检测 |
| logo | Logo识别 |
| audio | 音频反垃圾 |

---

## 管道查询与选择参数 mps_pipeline.py

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--region` | string | 否 | cn-shanghai | MPS 服务区域 |
| `--select` | flag | 否 | false | 自动选择模式：仅输出选中的 PipelineId（适合 shell 脚本捕获） |
| `--name` | string | 否 | mts-service-pipeline | 首选管道名称，用于自动选择时的匹配 |
| `--type` | string | 否 | - | 按类型过滤/选择管道：standard（转码）、narrowband（窄带高清）、audit（审核） |
| `--json` | flag | 否 | false | 以 JSON 格式输出 |
| `--verbose` / `-v` | flag | 否 | false | 显示详细日志 |

**说明**：
- 默认模式（无 `--select`）：列出所有管道并以表格形式展示
- `--select` 模式：自动选择最佳管道（优先匹配 `--name` 指定的名称，其次选择第一个 Active 状态的管道）
- `--type` 参数：按任务类型过滤管道，配合 `--select` 可按类型自动选择
  - `standard`：转码管道（Standard）
  - `narrowband`：窄带高清转码管道（NarrowBandHDV2）
  - `audit`：审核管道（AIVideoCensor）
- 自动选择优先级：1) 名称匹配且状态为 Active；2) 任意 Active 状态的管道
- `--select` 模式下默认仅输出 PipelineId，配合 `--json` 可输出详细信息

**使用场景**：
- 首次使用时查看可用的管道列表
- 在脚本中自动获取 Pipeline ID 而无需硬编码
- 配合 `--type` 按任务类型自动选择对应管道
- 配合其他脚本动态设置 `ALIBABA_CLOUD_MPS_PIPELINE_ID` 环境变量

---


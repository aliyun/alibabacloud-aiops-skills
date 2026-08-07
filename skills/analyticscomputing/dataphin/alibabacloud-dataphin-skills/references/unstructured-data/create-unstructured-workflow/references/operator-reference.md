# 算子参考：47 算子清单 / 推荐模型 / 支持格式 / 关键约束

> 组装工作流选型算子时查本文。算子的完整 `pluginConfig` 类型/默认值/校验规则以 Dataphin 界面为权威（界面创建同类算子后下载 JSON 对照）。

## 一、算子清单（按分类，key 即 step.key）

> ⚠️ **分类分节名即 `step.type` 取值**（normal/text/document/image/video/audio/vector）——组装时逐算子按本清单查 type，勿类比推断。两条铁则（人工校准）：
> 1. **`file_basic_info` 是唯一双分类算子**：normal 与 text 两个面板都有，`type` 取两值均合法（本套件示例用 normal，界面回环验证过）；
> 2. 其余“基本信息”算子均只有单一分类：`image_basic_info`→**image**、`video_basic_info`→video、`audio_basic_info`→audio，**没有双层，写 normal 就是错**（实测踩坑：image_basic_info 被类比 file_basic_info 误写 normal）。

### 通用（normal，3 个）

| 算子 | key | 支持格式 / 输入约束 |
|---|---|---|
| 文件基本信息 | `file_basic_info` | pdf、jpg、png、arw、bmp、cr2、heic、nef、tiff、webp、html、csv、json、xml、md、txt、doc、及音视频通用格式集 |
| MD5 精准去重 | `md5_dedup` | **仅解析 PG 元数据表字段值**（不消费 URL） |
| Python 脚本 | `python_executor` | 自定义脚本（URL→PG 桥接兜底手段） |

### 文本（text，9 个 + file_basic_info 复挂）

| 算子 | key | 支持格式 / 输入约束 |
|---|---|---|
| 文本 chunk 切分 | `text_chunking` | md、txt、html、csv、json（也是 URL→PG 桥接首选） |
| 特殊字符移除 | `special_character_removal` | txt、md、csv、json、xml、html |
| 违规内容替换 | `violation_content_replacer` | txt、md、csv、json、xml、html |
| 隐私信息打码 | `pii_masking` | txt、md、csv、json、xml、html |
| 简繁体转换 | `chinese_conversion` | txt、md、csv、json、xml、html |
| HTML 正文提取 | `html_extraction` | txt、md、csv、json、xml、html |
| SimHash 文本近似去重 | `simhash_dedup` | **仅解析 PG 元数据表字段值** |
| 文本推理(LLM) | `llm_inference` | **仅解析 PG 元数据表字段值** |
| 多语言文本质量分 | `text_quality_score` | **仅解析 PG 元数据表字段值** |

> `file_basic_info` 在组件库中同时挂 `normal` 和 `text` 两个分类，任取其一。

### 文档（document，5 个）

| 算子 | key | 支持格式 |
|---|---|---|
| PDF 解析 | `pdf_parser` | pdf |
| Word 解析 | `word_parse` | doc、docx |
| PPT 解析 | `ppt_parse` | ppt、pptx |
| Excel 解析 | `excel_parse` | xls、xlsx |
| PPT 文档转换 | `ppt_doc_transform` | ppt、pptx（pagetoppt 按页拆分 / pagetopng 按页转图） |

### 图片（image，8 个）

| 算子 | key | 支持格式 |
|---|---|---|
| 图像基本信息 | `image_basic_info` | jpg、jpeg、png、bmp、tiff、webp、heic、gif、ico、svg 等宽格式集 |
| 图像水印检测 | `image_watermark_detection` | 同 image_basic_info 宽格式集 |
| 图像近似去重（感知 hash） | `image_hash_dedup` | 同 image_basic_info 宽格式集 |
| 图片理解 | `image_understanding` | jpg、png、bmp、webp |
| 图像安全(NSFW)检测 | `nsfw_detection` | jpg、png、bmp、webp（部分模型另支持 tiff） |
| 图像美学评分 | `image_aesthetic_score` | jpg、bmp、nef、jpeg、cr2、tiff、png、arw、heic、webp |
| 图片 OCR | `image_ocr` | **仅 jpg、png**（窄格式，注意） |
| 图像质量评分 | `image_quality_score` | 宽格式集（部分模型支持） |

### 音频（audio，12 个）

音频通用格式集：`aac、amr、avi、flac、flv、m4a、mkv、mov、mp3、mp4、mpeg、ogg、opus、wav、webm、wma、wmv`

| 算子 | key | 支持格式 |
|---|---|---|
| 音频基本信息 | `audio_basic_info` | 音频通用格式集 |
| 音频转码 | `audio_transcoding` | 音频通用格式集 |
| 音频增强 | `audio_enhancement` | 音频通用格式集 |
| 音频转文本(ASR) | `audio_to_text` | 音频通用格式集 |
| 音频时间戳 | `audio_timestamp` | 音频通用格式集 |
| 音频语种检测 | `audio_language_detection` | 音频通用格式集 |
| 音频人声检测(VAD) | `audio_vad` | 音频通用格式集 |
| 音频说话人分离(DIA) | `audio_diarization` | 音频通用格式集 |
| 音频质量分 | `audio_quality_score` | 音频通用格式集 |
| 音频合成检测 | `audio_synthesis_detection` | 音频通用格式集 |
| 音色变换 | `tone_conversion` | 音频通用格式集 |
| 音频切片 | `audio_chunk` | **仅 mp3、mov、avi、mkv、m4a、wav**（比通用集窄，切片链路前置 `audio_transcoding`） |

### 视频（video，7 个）

| 算子 | key | 支持格式 |
|---|---|---|
| 视频基本信息 | `video_basic_info` | **仅 mp4、mov、m4v**（窄格式，链路起点注意） |
| 视频抽取音频 | `video_audio_extractor` | mp4、mov、m4v |
| 视频音频检测 | `audio_presence_detection` | mp4、mkv、avi、mov、flv、wmv、webm、mpeg 等宽格式集 |
| 视频关键帧抽取 | `video_keyframe_extraction` | mp4、avi、mkv、mov、webm、flv、ts、wmv、3gp、mpeg |
| 视频画质质量分 | `video_quality_score` | 同 video_keyframe_extraction |
| 视频切片 | `video_segment` | mp4、mov、mkv、avi、flv、mpeg 等 |
| 视频格式转换 | `video_format_conversion` | 最宽格式集（mp4/avi/mkv/rm/rmvb/mxf 等 27 种） |

### 向量（vector，2 个）

| 算子 | key | 支持格式 |
|---|---|---|
| 文本 Embedding | `text_embedding` | md、txt、html、csv、json（也可消费表字段文本） |
| 图片 Embedding | `image_embedding` | jpg、png |

## 二、使用大模型的算子 → 推荐基准模型

| 模态 | 算子 key | 推荐基准模型 |
|---|---|---|
| 文本 | `llm_inference` / `text_quality_score` | qwen3.6-plus |
| 文档 | `pdf_parser` / `excel_parse` / `ppt_parse` / `word_parse` | qwen3-vl-plus |
| 图像 | `image_watermark_detection` / `image_understanding` / `nsfw_detection` / `image_aesthetic_score` / `image_quality_score` / `image_ocr` | qwen3.6-plus |
| 视频 | `video_keyframe_extraction` / `video_quality_score` | qwen3.6-plus |
| 音频 | `audio_quality_score` / `audio_to_text` / `audio_timestamp` / `audio_language_detection` / `audio_vad` / `audio_diarization` | fun-asr |
| 音频 | `audio_synthesis_detection` | Qwen3.5-Omni-Plus |
| 向量 | `text_embedding` | text-embedding-v4（维度 1024） |
| 向量 | `image_embedding` | qwen3-vl-embedding |

速记规律：文档解析类（含图片理解环节）→ 视觉模型 `qwen3-vl-plus`；文本/图像/视频的理解评分类 → 通用大模型 `qwen3.6-plus`；音频系列（除合成检测）→ `fun-asr`。

**注意**：推荐模型 ≠ 唯一可用（可换同类模型）；`modelId` 必须查询实际环境的模型实例（租户内映射），禁止凭模型名编造。

**多列输出（enableOutputMultiColumn）[人工注入]**：仅 `llm_inference` 与 `image_understanding` 支持——开启后通过 `customOutputColumns[{name,type,comment,example}]` 把模型输出直接拆成多个结构化字段落表（关闭时单列默认 `answer` / `image_content`）。结构与选型建议见 [`workflow-json-spec.md`](workflow-json-spec.md) §多列输出。

## 三、格式兼容预检要点

1. 连接算子时，除字段契约（输出 ⊇ 输入）外必须检查**格式兼容**——如视频链路 `video_basic_info` 只支持 mp4/mov/m4v，源数据含 mkv 会被跳过；`audio_chunk` 支持面显著窄于其他音频算子，切片链路要提前 `audio_transcoding` 转码。
2. 格式过滤（filters）非必需——解析类算子内部自动跳过不匹配文件类型；本表用于**判断链路能不能处理目标数据**，而非要求逐一配 filters。
3. 「仅解析 PG 元数据表字段值」的算子（`md5_dedup` / `simhash_dedup` / `llm_inference` / `text_quality_score`）不消费文件/URL，输入必须是上游解析/切分后落表的文本列。

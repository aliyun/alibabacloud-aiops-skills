---
name: alibabacloud-maxframe-video-frame-pipeline
description: This skill should be used when the user asks to "build a frame extraction job" / "视频抽帧 / 抽关键帧", "label driving images with a VLM" / "图像打标 / image labeling with Qwen-VL", "compute image embeddings" / "图像向量化 / multi-modal embedding", "build a video_table / image_table / clip_dir_table for AI FUNC", "扫 OSS 建 video meta 表", or mentions driving-scene / ADAS / 智驾 / 智能驾驶 / 自动驾驶 / 路测 / 行车记录仪 / 座舱 video or image pipelines on MaxFrame + OSS + ODPS. Not for audio (use driving-audio-maxframe-job).
---

# Driving Video MaxFrame Job

## Overview

Generate customer-neutral MaxFrame job scaffolds for driving-video workflows.
Frame extraction uses an ffmpeg-based `mf.apply_chunk` UDF (with
`with_fs_mount` + `with_running_options`); image labeling and embedding use
AI FUNC multi-modal models loaded via `read_odps_model`. Keep all stages in
one lazy DAG by default and externalize all runtime settings.

## When to Use

- Building a video manifest table by scanning OSS, when the customer has
  videos sitting in OSS but no inventory table yet (Stage 0)
- Frame extraction from in-car / cabin / dashcam / road-test video tables
- Clip-to-keyframe labeling pipelines (`clip_dir_table` → keyframe rows → labels)
- Image labeling jobs, including direct-image requests that ask for labeling
  plus embedding outputs
- Image / multi-modal embedding jobs derived from image workflows

## Minimum Input

- `scenario_name`
- `input_shape`
- `targets`
- `output_table` or `output_tables`

## Decision Flow

1. **Check for an upstream `video_table`** when the request starts from
   videos. If the customer does not already have an ODPS inventory table
   with a `video_path` column, prepend Stage 0 (manifest build): a plain
   PyODPS + `alibabacloud_oss_v2` script that lists the OSS prefix with
   `list_objects_v2_paginator` and writes a
   `video_path / size_bytes / last_modified` table. See
   [references/build_video_meta.md](references/build_video_meta.md).
   Skip Stage 0 only when the customer points at an existing inventory
   table or hands over a small in-Python path list for PoC.
2. Map the request into one of four abstract scenario types: video frame
   extraction, clip-to-keyframe labeling, image labeling, or embedding.
3. Treat `targets` as a separate output dimension inside the chosen scenario type.
4. Default to **single-job, single-output** for downstream stages even when
   the request starts from `video_table` and asks for downstream
   labeling/embedding. Chain `frame_extraction → image_labeling` in one
   lazy DAG. Only emit a split-video pair
   (`video_frame_extraction.py` + `image_labeling.py`) when the customer
   explicitly says they need an intermediate frame table for reuse, audit,
   or independent retry. (Stage 0 manifest build is always a separate
   script — it is not a MaxFrame stage.)
5. Ask for any missing minimum inputs; if ambiguity remains, use a generic,
   customer-neutral scaffold with explicit user-fill fields.
6. Generate code, schema guidance, and a short walkthrough.

## Migration Rule

When modernizing existing online jobs, replace UDF + direct DashScope calls
with AI FUNC. Do not generate MaxFrame UDF wrappers for labeling or
embedding, do not call DashScope HTTP / OpenAI-compatible clients directly,
and do not require `DASHSCOPE_API_KEY`.

## Pipeline Selection

| input_shape | targets | pipeline |
|---|---|---|
| `oss_prefix` (no inventory table yet) | `manifest` | video-manifest (Stage 0; PyODPS + alibabacloud_oss_v2) |
| `video_table` | `frame-extraction` only | video-frame-extraction |
| `video_table` | `frame-extraction` + labeling/embedding | single-job: frames lazy → image-labeling lazy (default); split only on explicit ask |
| `clip_dir_table` | `labeling` | clip-to-keyframe labeling |
| `image_table` | `labeling` and/or `embedding` | image-labeling |
| `labeled_image_table` | `embedding` | image-labeling |

For `image_table` with both `labeling` and `embedding`, route to a single
image-labeling pipeline that emits both outputs in the same DAG.

If `video_table` is requested but the customer doesn't have one yet, run
the `video-manifest` Stage 0 first; the manifest table then satisfies
`video_table` for the downstream stages.

## Input Contract

**Required:**

- `scenario_name`
- `input_shape`: `oss_prefix` | `video_table` | `clip_dir_table` | `image_table` | `labeled_image_table`
- `targets`: one or more of `manifest`, `frame-extraction`, `labeling`, `image-labeling`, `embedding`
- For `oss_prefix`: `oss_bucket` + `oss_region` + `oss_endpoint` + `video_input_table` (the meta output). `oss_endpoint` is required because Stage 0 embeds it into every `video_path` URI (`oss://<endpoint>/<bucket>/<key>`) — downstream frame_extraction's `with_fs_mount(OSS_ROOT, ...)` matches on the full prefix, so a bare `oss://<bucket>/<key>` URI would silently break the path substitution. Stage 0 uses OSS SDK v2 with a RAM user AK/SK (`OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET`); `role_arn` is only used inside the MaxFrame DAG, not Stage 0.
- For all other shapes: `output_table` (single-stage, default) or
  `output_tables` (`{"frames": "...", "final": "..."}`) only when
  split-video is explicitly requested

**Optional:** `source_table`, `partition_col`, `partition_value`,
`oss_root`, `oss_mount_path`, `oss_role_arn` (MaxFrame-side), `oss_prefix`,
`video_extensions`, `meta_lifecycle`, `frame_fps`,
`frame_sample_count`, `ffmpeg_timeout_sec`, `label_prompt_style`,
`vlm_model`, `embedding_model`, `embedding_dim`, `model_project`,
`gpu_quota`, `gpu_count`, `need_intermediate_table`, `need_oss_writeback`.

## Reference Map

| Topic | Reference |
|---|---|
| Stage 0 — build video meta table from OSS prefix (PyODPS + alibabacloud_oss_v2) | [references/build_video_meta.md](references/build_video_meta.md) |
| AI FUNC multi-modal call shapes (generate / embed / messages= / dimensions=) | [references/ai_func_calls.md](references/ai_func_calls.md) |
| Frame extraction via ffmpeg + apply_chunk + with_fs_mount | [references/frame_extraction.md](references/frame_extraction.md) |
| Required runtime config (env vars, OSS role, GPU quota) | [references/runtime_config.md](references/runtime_config.md) |
| Output schemas and failure semantics | [references/output_contracts.md](references/output_contracts.md) |
| Path safety, credential rules, prompt safety | [references/safety.md](references/safety.md) |

Runnable starting points: [scripts/build_video_meta.py](scripts/build_video_meta.py),
[scripts/frame_extraction_minimal.py](scripts/frame_extraction_minimal.py),
[scripts/image_labeling_minimal.py](scripts/image_labeling_minimal.py).

## Code Generation Patterns

**Common skeleton:** imports → env vars / constants → schema helpers →
`apply_chunk` UDFs (frame extraction) → AI FUNC stages → assemble + write.

**Required imports for image labeling / embedding:**

```python
import os
import json
import math
import pandas as pd
from odps import ODPS
import maxframe.dataframe as md
from maxframe import new_session
from maxframe.config import options
from maxframe.learn.contrib.llm import ContentPart, ImageContentType
from maxframe.learn.utils import read_odps_model
```

`ContentPart` and `ImageContentType` live at `maxframe.learn.contrib.llm`
(re-exported from `learn/contrib/llm/core.py`). Verified against
release/v2.7.

**Required imports for frame extraction UDFs:**

```python
from maxframe.udf import with_fs_mount, with_running_options
```

**AI FUNC default patterns** — full call shapes in
[references/ai_func_calls.md](references/ai_func_calls.md). Quick reference:

- Load: `read_odps_model(MODEL_NAME, project=MODEL_PROJECT)` after setting `odps_options.catalog.endpoint = f"http://{o.get_catalog_host()}"` once. `MODEL_PROJECT` for Aliyun public managed models is typically `bigdata_public_modelset`. Full rationale + per-region catalog host table in [references/ai_func_calls.md](references/ai_func_calls.md).
- Multi-modal labeling: `model.generate(df, messages=[...with ContentPart...], simple_output=False, params={"max_tokens": 1024})`
- Image embedding: `model.embed(df, input=[ContentPart.image(data=df["image_url"], type=ImageContentType.IMAGE_URL)], simple_output=False)`
- Text embedding (on labels): `text_embedding_model.embed(label_text_series, dimensions=EMBEDDING_DIM, simple_output=False)`

**Critical kwarg rules:**

- Use `messages=` for multi-modal `generate()` (preferred in 2.7;
  `prompt_template=` still works as a legacy alias).
- For text embedding, `dimensions` is **plural** and a **top-level kwarg**.
  Never put it in `params`, never spell it `dimension`.
- Multi-modal `embed()` does not accept `dimensions=`; pass model-specific
  dimension knobs through `params={...}` if and only if the target model
  documents that key.
- Frame-extraction UDF resources go through
  `@with_running_options(engine="dpe", cpu=..., memory=...)`. AI FUNC
  stages take **behavior knobs only** in `running_options=` (never a
  quota nickname — AI FUNC manages its own service-side quota):
  generate → `{"enable_thinking": False, "enable_real_rpm_stats": True}`;
  embed → `{"enable_real_rpm_stats": True}`. Full table and rationale
  in [references/ai_func_calls.md](references/ai_func_calls.md).
- `cp.image(...)` with an OSS URL **must** pass
  `storage_options={"access_key_id": OSS_ACCESS_KEY_ID, "access_key_secret":
  OSS_ACCESS_KEY_SECRET}` — the AI FUNC inference service can't fetch
  OSS via the caller's `role_arn`.

**Embedding target rule:** plain `embedding` in image / video workflows
means **image embedding** by default (multi-modal). If labels are generated
and the user requests label / text embedding, emit `label_embedding` as a
separate stage on the `label_text` column using a text embedding model.

**Response assembly:** keep AI FUNC outputs lazy, concatenate source
identifiers with each stage's `response` / `success` columns, then call
`combined.mf.apply_chunk(...)` to parse JSON, validate embeddings, and
produce final row-level status. Successful rows emit parsed labels and
JSON-dumped embeddings; failed rows preserve source identifiers and set
`status="failed"`, `error_stage`, and `error_msg`.

## Frame and Clip Contracts

**Video frame extraction job:**

- Input table contains source video identifiers plus an OSS path column
  (`video_path`).
- Use the ffmpeg-based UDF in [references/frame_extraction.md](references/frame_extraction.md).
  The UDF mounts OSS via `with_fs_mount(oss_root, mount_path, storage_options={"role_arn": ...})`,
  uses `ffprobe` for duration, then `ffmpeg` for frame sampling, and emits
  one row per frame with `video_path`, `frame_idx` (lineage), `image_id`,
  `image_url` (consumed by AI FUNC), and `status` / `error_stage` /
  `error_msg`.
- The `image_id` / `image_url` columns intentionally match the
  image-labeling input contract (`IMAGE_ID_COL` / `IMAGE_URL_COL`,
  defaults `image_id` / `image_url`), so the frame table is a drop-in
  input for the image-labeling stage — `image_url` goes straight into
  `ContentPart.image(data=df["image_url"], ...)` with no rename.
- `image_id` is synthesized as `<video_basename>_<frame_idx:04d>`,
  which also matches the JPEG filename written by ffmpeg — useful for
  debugging.

**Clip-to-keyframe labeling job:**

- Required input columns: `clip_id`, a clip directory or root path column,
  optionally source video identifiers, partition columns, time-range metadata.
- Expand each clip into keyframe image rows before labeling. The expanded
  rows must include `clip_id`, `keyframe_id` or `frame_index`, optional
  timestamp, `image_url` (or equivalent path parts), and any source
  lineage columns.
- Expansion failures are row-level: `status="failed"`,
  `error_stage="keyframe_expansion"`, `error_msg`. Labeling failures use
  `error_stage="label"`.
- Path safety: normalize paths, reject `..` traversal, reject absolute /
  local paths unless explicitly allowed, ensure resolved paths stay under
  the declared OSS / input prefix, and ensure any OSS write-back stays
  under the declared output prefix.

## Default Generation Rules

- Use AI FUNC (ODPS-managed models loaded via `read_odps_model`) for
  labeling and embedding by default.
- Keep `MODEL_PROJECT`, `LABEL_MODEL` (or `VLM_MODEL`), `EMBEDDING_MODEL`,
  `EMBEDDING_DIM` configurable. Read from env or dotenv.
- No `DASHSCOPE_API_KEY` required.
- Stop at ODPS / MaxCompute tables by default. Add intermediate tables
  only when they serve a real fan-out or reuse need.

## Output Contract

**Outputs:** main job code + schema guidance + short walkthrough.

**Naming convention** (`<scenario_name>_<pipeline_kind>`):

- `<scenario_name>_video_frame_extraction.py`
- `<scenario_name>_image_labeling.py`
- `<scenario_name>_walkthrough.md`
- `<scenario_name>_schema.sql` when needed
- Filenames use underscores; scenario type names in docs use hyphens.

**Walkthrough must explain:** scenario type, single-job vs split-video
choice, required env vars (including `OSS_ROLE_ARN`,
`MODEL_PROJECT`, `LABEL_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`),
input / output table expectations, run order, the failure semantics for
each stage.

Detailed column contracts in [references/output_contracts.md](references/output_contracts.md).

## Safety Rules

- Do not mention customer names, real OSS buckets, real ODPS projects,
  paths, prompts, schemas, or private rules.
- Do not hardcode credentials. OSS goes through `role_arn`; ODPS through
  env vars. Do not emit `access_key_id` / `access_key_secret` literals
  in `storage_options`.
- Do not generate UDF-based labeling / embedding or direct DashScope
  clients for online-job migration.
- Require path safety and OSS write-back safety for path-based scenarios.
- Keep unresolved fields explicit rather than filling with unsafe assumptions.

Full rules in [references/safety.md](references/safety.md).

## Observability

All Alibaba Cloud API SDK calls must include a User-Agent header for
traceability.

**UA template:**

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxframe-video-frame-pipeline/{session-id}
```

**session-id generation rule:** generate a 32-character hex string once per
session (e.g. `uuid.uuid4().hex`) and store it in the `SKILL_SESSION_ID`
environment variable. All SDK calls within the same session share this
single session-id.

**SDK integration (alibabacloud_oss_v2):**

```python
import os
cfg = oss.config.load_default()
cfg.user_agent = (
    f"AlibabaCloud-Agent-Skills/alibabacloud-maxframe-video-frame-pipeline"
    f"/{os.getenv('SKILL_SESSION_ID', 'unknown')}"
)
client = oss.Client(cfg)
```

## Verification Scenarios

**Scenario 0** — `oss_prefix` + `manifest`: PyODPS +
`alibabacloud_oss_v2` script (no MaxFrame); uses
`StaticCredentialsProvider` + `list_objects_v2_paginator`, writes one
row per video file with `video_path / size_bytes / last_modified`.
Output becomes the `video_table` for downstream stages. `main(o)`
takes the ODPS handle as an explicit argument; the `__main__` block
documents three paths — DataWorks PyODPS 3 node (use injected
global `o`), DataWorks Notebook node (`o = %odps` magic),
or env-based `o = ODPS(...)` elsewhere — and the user picks one.

**Scenario 1** — `video_table` + `frame-extraction`: single job using the
ffmpeg `apply_chunk` UDF; writes one frame table; no AI FUNC.

**Scenario 2** — `video_table` + `frame-extraction,labeling,embedding`
(default single-job): one lazy DAG combining frame extraction + image
labeling + image embedding; one final table; no intermediate write
unless `need_intermediate_table=true`.

**Scenario 2b** — same but customer asks "give me the frames table for
audit": split-video pair (`<scenario>_video_frame_extraction.py` +
`<scenario>_image_labeling.py`); walkthrough explains stage handoff.

**Scenario 3** — `image_table` + `labeling,embedding`: single
image-labeling pipeline; AI FUNC defaults with configurable
`MODEL_PROJECT`, `LABEL_MODEL` / `VLM_MODEL`, `EMBEDDING_MODEL`,
`EMBEDDING_DIM`; emits both `label_text` and `image_embedding`.

**Scenario 4** — ambiguous request: ask for missing minimum inputs; fall
back to a generic scaffold with explicit user-fill fields if still
ambiguous; never invent customer-specific assumptions.

**Cross-scenario checks — every output must:**

- contain no hardcoded model names, endpoints, credentials, OSS buckets,
  or ODPS projects
- use AI FUNC model loading via `read_odps_model`, not UDF wrappers or
  direct DashScope API calls
- preserve `status`, `error_stage`, `error_msg` for stages that emit
  per-row failure (frame extraction UDFs, AI FUNC stages with
  `simple_output=False`)
- contain no invented helper APIs outside the documented MaxFrame contract
- include concrete frame / clip schema handoff guidance when the scenario
  starts from videos or clips
- for AI FUNC stages, emit behavior knobs only —
  `running_options={"enable_thinking": False, "enable_real_rpm_stats": True}`
  for generate, `{"enable_real_rpm_stats": True}` for embed — and
  **never** emit `gu_quota_name` / `inference_quota_name` (the
  inference-quota lookup will fail). CPU resources for frame
  extraction go via `with_running_options(...)` as before.
- for AI FUNC `cp.image(...)` with OSS URLs, **always** pass
  `storage_options={"access_key_id": OSS_ACCESS_KEY_ID,
  "access_key_secret": OSS_ACCESS_KEY_SECRET}` — the inference
  service can't fetch OSS without inline credentials.
- use `dimensions` (plural) as a top-level kwarg for text embedding
- prefer `messages=` over `prompt_template=` for multi-modal generation

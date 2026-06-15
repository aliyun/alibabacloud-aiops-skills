# Video Runtime Config

Driving-video pipelines combine CPU-side ffmpeg UDFs with GPU-side AI FUNC
multi-modal model calls. They do not require a special session image
(unlike the audio ASR path), but they do depend on properly-scoped GPU
quota and OSS role.

## Session creation

```python
import os

import dotenv
from odps import ODPS
from odps import options as odps_options
from maxframe.session import new_session

dotenv.load_dotenv()

o = ODPS(
    access_id=os.environ["ODPS_ACCESS_ID"],
    secret_access_key=os.environ["ODPS_ACCESS_KEY"],
    project=os.environ["ODPS_PROJECT"],
    endpoint=os.environ["ODPS_ENDPOINT"],
)

# Required only when the job calls `read_odps_model` (image-labeling /
# embedding stages). Apply the catalog endpoint to the PyODPS global
# option -- it is consulted by both the explicit `read_odps_model` call
# and the in-operator `ODPS.from_global()` paths, so this single line
# works in DataWorks, local, ECS, and production runners.
odps_options.catalog.endpoint = f"http://{o.get_catalog_host()}"

session = new_session(o)
print(f"Logview: {session.get_logview_address()}")
```

No `major_version` should be set unless the customer explicitly requires
a non-default channel.

## Required env vars

| Env var            | Purpose                                                   |
|--------------------|-----------------------------------------------------------|
| `ODPS_ACCESS_ID`   | ODPS auth                                                                |
| `ODPS_ACCESS_KEY`  | ODPS auth                                                                |
| `ODPS_PROJECT`     | Default project for `read_odps_table` / `to_odps_table`                  |
| `ODPS_ENDPOINT`    | Region-specific MaxCompute endpoint                                      |
| `OSS_ROLE_ARN`     | STS role used by frame-extraction `with_fs_mount`                        |
| `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` | Required by `cp.image(..., storage_options=...)` so the AI FUNC inference service can fetch OSS URLs (`role_arn` is not honored on the AI FUNC path) |
| `MODEL_PROJECT`    | Usually `bigdata_public_modelset` for Aliyun-hosted managed models       |

The catalog endpoint is derived at runtime from `o.get_catalog_host()`
and applied to `odps_options.catalog.endpoint` -- not an env var. See
[ai_func_calls.md](ai_func_calls.md) for the per-region catalog
endpoint table when `get_catalog_host()` is unavailable.
| `OSS_ROOT`         | OSS prefix being mounted (no trailing slash)              |
| `OSS_MOUNT_PATH`   | Local mount target inside rund container, e.g. `/mnt/...` |
| `MODEL_PROJECT`    | ODPS project hosting the AI FUNC model resources          |
| `VLM_MODEL`        | Multi-modal model name in the catalog (labeling)          |
| `EMBEDDING_MODEL`  | Text or multi-modal embedding model name                  |
| `EMBEDDING_DIM`    | Output dimension when text embedding is requested         |

`MODEL_PROJECT` must come from the customer; do not default it (though
`bigdata_public_modelset` is the conventional public managed-model
project for Aliyun-hosted Qwen-VL family). AI FUNC is MaxFrame's
built-in Bailian inference; no GPU quota is needed on this path —
`GPU_QUOTA` is NOT a required env for this skill.

## Dataframe-side options

When the pipeline reads ODPS tables that need partition pushdown or
specific session settings, externalize them too:

```python
from maxframe.config import options

options.sql.enable_mcqa = False   # default for non-ASR jobs
options.dag.settings = {"engine_order": ["MCSQL", "DPE", "SPE"]}
# Drop both blocks unless the customer asks for engine ordering or MCQA toggling.
```

For driving-video pipelines the defaults are usually fine — only emit
the block when the customer asks for tuning.

## Quota wiring

- Frame-extraction UDF: CPU/memory via `@with_running_options(engine="dpe", cpu=..., memory=...)`.
- **AI FUNC stages (`model.generate` / `model.embed`)**: do NOT pass
  `gu_quota_name` / `inference_quota_name`. AI FUNC calls Aliyun's
  built-in Bailian inference; the operator manages its own
  service-side quota. Passing one of those keys triggers a
  `resolve_inference_quota` lookup that errors out. Use behavior
  knobs instead:
  `running_options={"enable_thinking": False, "enable_real_rpm_stats": True}`
  for generate; `{"enable_real_rpm_stats": True}` for embed
  (`enable_thinking` is generate-only). See ai_func_calls.md
  "Resource controls" for the full table.

Do not pass `gu` / `gu_quota` to AI FUNC operators directly either —
those kwargs belong on the audio accessor (`df["x"].audio.transcribe`),
which is a different API surface from AI FUNC.

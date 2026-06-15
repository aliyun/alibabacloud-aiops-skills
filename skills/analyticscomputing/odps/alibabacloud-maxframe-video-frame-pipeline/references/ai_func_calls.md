# AI FUNC Multi-Modal Call Shapes (release/2.7)

Multi-modal LLMs are loaded through ODPS-managed model resources and
exposed via the `ContentPart` / `ImageContentType` API at
`maxframe.learn.contrib.llm`.

## Imports

```python
from maxframe.learn.contrib.llm import ContentPart, ImageContentType
from maxframe.learn.utils import read_odps_model
```

`ContentPart` and `ImageContentType` are re-exported from
`maxframe.learn.contrib.llm.__init__`. Do not import from
`maxframe.learn.contrib.llm.multi_modal` — that module only re-exports them
internally.

## Loading models

Production-portable pattern — apply the catalog endpoint to the PyODPS
global option before calling `read_odps_model`:

```python
from odps import options as odps_options

odps_options.catalog.endpoint = f"http://{o.get_catalog_host()}"

vlm_model = read_odps_model(VLM_MODEL, project=MODEL_PROJECT)
embedding_model = read_odps_model(EMBEDDING_MODEL, project=MODEL_PROJECT)
```

For `LLM` models with the `text-generation` task, `read_odps_model` returns
`ManagedTextGenLLM`. For `MLLM` models with the `image-text-to-text` task,
it returns `ManagedMultiModalGenLLM`. For `text-embedding`, it returns
`ManagedTextEmbeddingModel`. For `multi-modal-embedding`, it returns
`ManagedMultiModalEmbeddingModel`. The factory branches in
`learn/contrib/llm/models/odps.py:_determine_model_class`.

**Why the global option, not `odps_entry=`?** Passing `odps_entry=o`
also works in test / DataWorks environments, but does not match how
`read_odps_model` is invoked in production code paths (where it's
called from within MaxFrame operators that build their own ODPS handle
via `ODPS.from_global()`). Setting `odps_options.catalog.endpoint`
once on the PyODPS global option works in both contexts, so emit this
pattern uniformly.

`o.get_catalog_host()` returns just the host (e.g. `oxs` in OXS daily,
`catalogapi.cn-shanghai-vpc.maxcompute.aliyun-inc.com` in cn-shanghai
VPC). The `f"http://"` prefix is required — without scheme, PyODPS
errors with `MissingSchema: Invalid URL 'oxs/api/catalog/...'`.

### Catalog endpoint per region

When `o.get_catalog_host()` is not available (very old PyODPS), the
explicit per-region endpoints below can be set instead. All use
`http://` (NOT https) as a prefix.

| Region        | Public                                              | VPC                                                   | OXS / intranet                                            |
|---------------|-----------------------------------------------------|-------------------------------------------------------|-----------------------------------------------------------|
| cn-shanghai   | `catalogapi.cn-shanghai.maxcompute.aliyun.com`     | `catalogapi.cn-shanghai-vpc.maxcompute.aliyun-inc.com`   | `catalogapi.cn-shanghai-intranet.maxcompute.aliyun-inc.com`   |
| cn-hangzhou   | `catalogapi.cn-hangzhou.maxcompute.aliyun.com`     | `catalogapi.cn-hangzhou-vpc.maxcompute.aliyun-inc.com`   | `catalogapi.cn-hangzhou-intranet.maxcompute.aliyun-inc.com`   |
| cn-beijing    | `catalogapi.cn-beijing.maxcompute.aliyun.com`      | `catalogapi.cn-beijing-vpc.maxcompute.aliyun-inc.com`    | `catalogapi.cn-beijing-intranet.maxcompute.aliyun-inc.com`    |
| cn-shenzhen   | `catalogapi.cn-shenzhen.maxcompute.aliyun.com`     | `catalogapi.cn-shenzhen-vpc.maxcompute.aliyun-inc.com`   | `catalogapi.cn-shenzhen-intranet.maxcompute.aliyun-inc.com`   |
| cn-chengdu    | `catalogapi.cn-chengdu.maxcompute.aliyun.com`      | `catalogapi.cn-chengdu-vpc.maxcompute.aliyun-inc.com`    | `catalogapi.cn-chengdu-intranet.maxcompute.aliyun-inc.com`    |
| cn-hongkong   | `catalogapi.cn-hongkong.maxcompute.aliyun.com`     | `catalogapi.cn-hongkong-vpc.maxcompute.aliyun-inc.com`   | `catalogapi.cn-hongkong-intranet.maxcompute.aliyun-inc.com`   |
| eu-central-1  | `catalogapi.eu-central-1.maxcompute.aliyun.com`    | `catalogapi.eu-central-1-vpc.maxcompute.aliyun-inc.com`  | `catalogapi.eu-central-1-intranet.maxcompute.aliyun-inc.com`  |
| daily / OXS internal | — | — | `catalogapi.odps.aliyun-inc.com` |

Prefer the network class that matches the ODPS endpoint (public OSS
endpoint → public catalogapi; VPC OSS / private MaxCompute → VPC; OXS
intranet → intranet).

The `MODEL_PROJECT` for Aliyun-hosted public managed models is
`bigdata_public_modelset`. Available task families today (as of 2026/05):
`image-text-to-text` (Qwen-VL family), `multi-modal-embedding`,
`text-generation`, `sentence-embedding`, `automatic-speech-recognition`.
Use `o.list_models()` in `bigdata_public_modelset` to see the current
catalog.

## Multi-modal labeling (image + text → text)

```python
cp = vlm_model.content_part   # property returning ContentPart class

STORAGE_OPTIONS = {
    "access_key_id": OSS_ACCESS_KEY_ID,
    "access_key_secret": OSS_ACCESS_KEY_SECRET,
}

label_df = vlm_model.generate(
    df,
    messages=[
        {
            "role": "user",
            "content": [
                cp.text(LABEL_PROMPT),
                cp.image(
                    data=df["image_url"],
                    type=ImageContentType.IMAGE_URL,
                    storage_options=STORAGE_OPTIONS,
                ),
            ],
        }
    ],
    simple_output=False,
    params={"max_tokens": 1024},
)
# label_df: response (str), success (bool)
```

Notes:

- `messages=` is the preferred kwarg in 2.7; `prompt_template=` still works
  as a legacy alias but new code should use `messages=`.
- `cp.image` accepts `data=Series_or_str`, `type=ImageContentType.IMAGE_URL`
  (or `BINARY` / `BASE64` — the latter two require `mime_type`).
- **For OSS-backed images, `storage_options={"access_key_id": ...,
  "access_key_secret": ...}` is REQUIRED.** The AI FUNC inference
  service runs in its own context and needs the OSS credentials inline
  to fetch the URL; `role_arn` is not honored on this code path.
  Source the AK/SK from env vars (`OSS_ACCESS_KEY_ID` /
  `OSS_ACCESS_KEY_SECRET`); never hardcode.
- `simple_output=False` keeps the raw provider response with token usage.

## Image embedding (multi-modal)

```python
emb_df = embedding_model.embed(
    df,
    input=[
        cp.image(
            data=df["image_url"],
            type=ImageContentType.IMAGE_URL,
            storage_options=STORAGE_OPTIONS,
        ),
    ],
    simple_output=False,
    params={"timeout": 120, "dimension": EMBEDDING_DIM},
)
```

`MultiModalEmbeddingModel.embed` signature is
`embed(data, input, simple_output=False, params=None, **kw)` —
`input` is **positional** (or named) and is a list of `ContentPart`s.
There is **no `dimensions` kwarg** for multi-modal embedding. If the
model supports a custom output dimension, pass the model-specific key
through `params={...}` only after confirming the key with the platform.

## Text embedding (on labels)

```python
text_emb_df = text_embedding_model.embed(
    label_text_series,         # Series, not DataFrame
    dimensions=EMBEDDING_DIM,  # plural, top-level kwarg
    simple_output=False,
    params={"timeout": 120},
)
```

For text embedding, `dimensions` is a real top-level kwarg
(`ManagedTextEmbeddingModel.embed`, signature in
`learn/contrib/llm/models/managed.py`). **Never** put it in `params`,
**never** spell it `dimension`.

## Resource controls

AI FUNC = MaxFrame's built-in Bailian model inference. The operator
calls Aliyun's hosted models (qwen-vl-* / qwen3-vl-embedding /
qwen3.6-* etc.) on the user's behalf -- there is **no GPU container,
no GU quota, no inference quota to wire up** on this code path.

`running_options=` carries **behavior knobs** only:

| Key                       | Meaning                                                                 | When to set                                    |
|---------------------------|-------------------------------------------------------------------------|------------------------------------------------|
| `enable_thinking`         | Controls CoT/reasoning mode for Qwen3 reasoning models                  | `False` for concise output (skip CoT prefix); `generate` only |
| `enable_real_rpm_stats`   | Server-side rate-limit telemetry                                        | `True` to surface RPM stats in logs            |
| `verbose`                 | Server-side verbose logging                                             | `True` for debugging                           |

Production-tested pattern:

```python
GENERATE_RUN_OPTS = {"enable_thinking": False, "enable_real_rpm_stats": True}
EMBED_RUN_OPTS = {"enable_real_rpm_stats": True}   # embed has no `enable_thinking`

label_df = vlm_model.generate(df, messages=[...], simple_output=False,
                              params={"max_tokens": 1024},
                              running_options=GENERATE_RUN_OPTS)

emb_df = embedding_model.embed(df, input=[cp.image(...)],
                               simple_output=False,
                               params={"timeout": 120, "dimension": EMBEDDING_DIM},
                               running_options=EMBED_RUN_OPTS)
```

**Never** emit `gu_quota_name` / `inference_quota_name` on AI FUNC
calls — they trigger `resolve_inference_quota` lookups that fail
unless the project has an explicitly registered inference quota
nickname. AI FUNC manages its own service-side quotas.

**For multi-modal embedding output dimension**, pass
`params={"dimension": EMBEDDING_DIM}` (singular, inside `params`) --
verified against production qwen3-vl-embedding. This differs from
text embedding (`dimensions=` plural, top-level kwarg).

(Audio ASR / Whisper goes through a different API surface entirely --
`df["x"].audio.transcribe(gu=..., gu_quota=...)` on the audio accessor
-- not AI FUNC. That path DOES take `gu` / `gu_quota` directly. See
the audio skill for details.)

## Response parsing

- Multi-modal label response: `choices[0].message.content` (string,
  often JSON when the prompt requests structured output).
- Token counts: `usage.prompt_tokens`, `usage.completion_tokens` for
  generation; `usage.total_tokens` for embedding.
- Multi-modal embedding vector: `output.embeddings[0].embedding` (list of
  floats).
- Missing token values become `0`, not row failures.
- Malformed labels / embeddings should fail the row at the specific
  stage (`error_stage="label"` or `error_stage="image_embedding"`).

# Output Contracts

## Frame extraction output

| Column        | Type     | Notes                                                       |
|---------------|----------|-------------------------------------------------------------|
| `video_path`  | string   | Source OSS URI; preserved on every emitted row              |
| `frame_idx`   | int64    | 0-based frame index within the video; `-1` on failure       |
| `image_id`    | string   | `<video_basename>_<frame_idx:04d>`; empty on failure        |
| `image_url`   | string   | OSS URI of the derived JPEG; empty on failure               |
| `status`      | string   | `"ok"` or `"failed"`                                        |
| `error_stage` | string   | `""` or `"frame_extraction"`                                |
| `error_msg`   | string   | Empty on success; ffprobe / ffmpeg stderr on failure        |

`image_id` and `image_url` intentionally match the image-labeling input
contract (`IMAGE_ID_COL` / `IMAGE_URL_COL`), so the frame table is a
drop-in input for `image_labeling_minimal.py` — no column rename, no
env override needed.

Add additional source-lineage columns (e.g. `clip_id`, `partition_value`)
only if they exist on the input table.

## Image labeling output

Source identifiers (preserved from input — `image_id`, `image_url`
plus the lineage columns `video_path`, `frame_idx` when flowing from
the frame-extraction stage; or `image_id`, `image_url` alone for
direct `image_table` flows) plus:

| Column              | Type    | Notes                                                                |
|---------------------|---------|----------------------------------------------------------------------|
| `label_text`        | string  | Parsed label text (JSON-as-string when the prompt requests structured output) |
| `label_input_token` | int64   | From `response.usage.prompt_tokens`; `0` if missing                  |
| `label_output_token`| int64   | From `response.usage.completion_tokens`; `0` if missing              |
| `label_response`    | string  | Raw response (only when `simple_output=False`)                       |
| `label_success`     | bool    | From the AI FUNC operator                                            |
| `image_embedding`   | string  | JSON-dumped vector (when image embedding is in scope)                |
| `image_embedding_total_token` | int64 | From `response.usage.total_tokens`; `0` if missing             |
| `label_embedding`   | string  | JSON-dumped vector (when label/text embedding is in scope)          |
| `label_embedding_total_token` | int64 | From `response.usage.total_tokens`; `0` if missing             |
| `status`            | string  | `"ok"` or `"failed"`                                                 |
| `error_stage`       | string  | `""`, `"label"`, `"image_embedding"`, or `"label_embedding"`         |
| `error_msg`         | string  | Empty on success; provider error text on failure                     |

Drop columns that are not requested by `targets`. The walkthrough must
list which columns appear and which do not, based on the chosen target set.

## Split-video final output

Identical to the image-labeling output above, plus the lineage columns
(`video_path`, `frame_idx`) that the frame extraction stage emitted.
The `image_id` / `image_url` columns are already part of the image-
labeling output. The `frames` table is written separately and can be
reused.

## Failure semantics by stage

| Stage              | Failure source                  | `error_stage` value      |
|--------------------|---------------------------------|--------------------------|
| frame extraction   | ffprobe / ffmpeg / no frames    | `frame_extraction`       |
| keyframe expansion | path traversal / IO             | `keyframe_expansion`     |
| labeling           | `label_success=False`           | `label`                  |
| label JSON parse   | malformed JSON in response      | `label`                  |
| image embedding    | `image_embedding_success=False` | `image_embedding`        |
| label embedding    | `label_embedding_success=False` | `label_embedding`        |

A row failed at stage N must preserve all source identifiers and leave
later-stage columns as `None` / empty rather than dropping the row.

## Token bookkeeping

When `simple_output=False`, the AI FUNC response contains a `usage` block.
After the row-level assembly `apply_chunk`, the final table should expose
token counts as integer columns rather than embedded JSON. Missing values
default to `0`.

## Why `simple_output=False`

It returns the raw provider response with `success` and full `usage`
metadata. The walkthrough must mention that `simple_output=True` would
flatten the response but lose token metadata; for billing-aware customers,
keep `False`.

# Build Video Meta Table (Stage 0)

The downstream frame-extraction job reads an ODPS table whose `video_path`
column points at OSS-hosted videos. If the customer does not already have
such an inventory table, run this stage first to produce one.

This stage is **not** a MaxFrame job — it is a plain Python script that
uses the OSS Python SDK v2 (`alibabacloud_oss_v2`) to list and `pyodps`
to write. It runs on the customer's machine, a small ECS / Jenkins
runner, or a DataWorks PyODPS node — not inside DPE.

Use [scripts/build_video_meta.py](../scripts/build_video_meta.py).

## Output schema

| Column          | Type    | Notes                                                              |
|-----------------|---------|--------------------------------------------------------------------|
| `video_path`    | string  | OSS URI: `oss://<endpoint>/<bucket>/<key>` — endpoint embedded so the URI starts with `OSS_ROOT` exactly, which `with_fs_mount` relies on in frame_extraction. |
| `size_bytes`    | bigint  | Object size; zero-byte objects are filtered out                    |
| `last_modified` | string  | UTC `YYYY-MM-DD HH:MM:SS` from OSS object metadata                 |

This is intentionally minimal and customer-neutral. To carry vehicle ID /
trip ID / date partition columns, run a follow-up `INSERT OVERWRITE ...
SELECT ..., regexp_extract(video_path, ...)` SQL job, or extend the
manifest script with project-specific parsing. Do **not** bake regex
parsing into this skill — path conventions vary too much across
customers.

## Required env vars

| Env var                 | Purpose                                                        |
|-------------------------|----------------------------------------------------------------|
| `OSS_ACCESS_KEY_ID`     | OSS auth — RAM user AK with `oss:ListObjects` on the prefix    |
| `OSS_ACCESS_KEY_SECRET` | OSS auth — paired secret                                       |
| `OSS_REGION`            | Bucket region, e.g. `cn-shanghai` (required by SDK v2 V4 sig)  |
| `OSS_ENDPOINT`          | e.g. `oss-cn-shanghai-internal.aliyuncs.com` — embedded into every `video_path` URI so downstream `with_fs_mount(OSS_ROOT, ...)` matches |
| `OSS_BUCKET`            | Target bucket name                                             |
| `VIDEO_INPUT_TABLE`     | Output ODPS table; created if missing, then truncated          |

ODPS auth env vars are required **only** in non-DataWorks environments
(see "ODPS handle on DataWorks vs elsewhere" below for the explicit
two-path setup):

| Env var          | Purpose                              |
|------------------|--------------------------------------|
| `ODPS_ACCESS_ID` | ODPS auth (long-term)                |
| `ODPS_ACCESS_KEY`| ODPS auth (long-term)                |
| `ODPS_PROJECT`   | Project that will hold the meta table|
| `ODPS_ENDPOINT`  | Region-specific MaxCompute endpoint  |

Optional:

| Env var              | Default                       | Notes                                                    |
|----------------------|-------------------------------|----------------------------------------------------------|
| `OSS_PREFIX`         | `""` (whole bucket)           | Scope the scan; recommended for prod                     |
| `OSS_LIST_MAX_KEYS`  | `1000`                        | Page size for `list_objects_v2_paginator`                |
| `VIDEO_EXTENSIONS`   | `.mp4,.mov,.mkv,.avi`         | Filter; lowercase compare                                |
| `MANIFEST_LIFECYCLE` | `30`                          | ODPS table lifecycle (days)                              |

## OSS SDK v2 usage

The script uses the patterns documented in the
[OSS Python SDK v2 dev guide](https://github.com/aliyun/alibabacloud-oss-python-sdk-v2/blob/master/DEVGUIDE-CN.md):

```python
import alibabacloud_oss_v2 as oss

credentials_provider = oss.credentials.StaticCredentialsProvider(
    access_key_id=OSS_ACCESS_KEY_ID,
    access_key_secret=OSS_ACCESS_KEY_SECRET,
)
cfg = oss.config.load_default()
cfg.credentials_provider = credentials_provider
cfg.region = OSS_REGION
cfg.endpoint = OSS_ENDPOINT
client = oss.Client(cfg)

list_request = oss.ListObjectsV2Request(
    bucket=OSS_BUCKET,
    prefix=OSS_PREFIX,
    max_keys=1000,
)
paginator = client.list_objects_v2_paginator()
for page in paginator.iter_page(list_request):
    for obj in page.contents or []:
        ...
```

Notes:

- SDK v2 defaults to V4 signature; `region` is mandatory. `endpoint`
  is required by this script too — not because the SDK can't derive it
  (it can, from region), but because the endpoint is **embedded into
  every `video_path` URI written to the meta table**. Downstream
  `with_fs_mount(OSS_ROOT, ...)` matches on the full
  `oss://<endpoint>/<bucket>/<prefix>` prefix; if the meta table writes
  bare `oss://<bucket>/<key>` URIs, frame extraction's
  `video_path.replace(f"{OSS_ROOT}/", f"{OSS_MOUNT_PATH}/")` silently
  no-ops and ffmpeg tries to open a literal `oss://...` string.
- For prod, prefer the intranet endpoint (e.g.
  `oss-cn-shanghai-internal.aliyuncs.com`) — both the SDK call and the
  embedded URI then go through VPC and avoid public-network egress.
- `obj.last_modified` is a `datetime` (timezone-aware), not a Unix
  timestamp — call `.strftime(...)` directly.
- `page.contents` is `None` when a page is empty; the script guards with
  `or []`.

## ODPS handle on DataWorks vs elsewhere

The script does **not** auto-detect the runtime — it asks the user to
pick one of three explicit paths in the `if __name__ == "__main__":`
block. The three paths cannot share the same line of Python because
`%odps` is IPython magic (Notebook only), `o` as a pre-injected
global only exists in PyODPS 3 nodes, and env-based `ODPS(...)` is
the only one that runs in plain CPython.

```python
if __name__ == "__main__":
    # (A) DataWorks PyODPS 3 node -- `o` is pre-injected as a module
    #     global. Do nothing; just call `main(o)`. Do NOT write
    #     `o = %odps` here -- it's a SyntaxError on this kernel.
    #
    # (B) DataWorks Notebook node (IPython kernel) -- comment out (C)
    #     and uncomment:
    #
    # o = %odps
    #
    # (C) Local / ECS / Jenkins / any non-DataWorks runner -- build
    #     from explicit env vars (default):
    o = ODPS(
        access_id=os.environ["ODPS_ACCESS_ID"],
        secret_access_key=os.environ["ODPS_ACCESS_KEY"],
        project=os.environ["ODPS_PROJECT"],
        endpoint=os.environ["ODPS_ENDPOINT"],
    )
    main(o)
```

`main(o)` takes the ODPS handle as an explicit argument so the three
runtime paths stay isolated and `main()` itself is runtime-agnostic.

**Why the PyODPS 3 vs Notebook split matters:** PyODPS 3 nodes run
plain CPython with `o` pre-bound at module level, so `o = %odps`
there is a literal `SyntaxError`. Notebook nodes run an IPython
kernel where `%odps` is a registered line magic that returns the
ODPS handle. Mixing the two will fail one runtime or the other.

## When to run

- **One-shot**: at customer onboarding, once they've uploaded their video
  corpus to OSS.
- **Refresh**: whenever new videos land. A cron / DataWorks scheduled
  task that reruns this script daily / hourly is fine — the script
  truncates and re-writes the whole manifest. For incremental upserts,
  switch to a partitioned manifest table and write only the new
  partition.
- **Idempotent**: rerunning produces the same table contents (modulo any
  new files). The script truncates before writing, so partial old state
  is never mixed with new.

## Behavior notes

- `list_objects_v2_paginator().iter_page(...)` paginates internally at
  `OSS_LIST_MAX_KEYS` per page (default 1000). For a prefix with a few
  million keys, expect steady network traffic for several minutes —
  the script prints elapsed time at the end so the customer can plan
  reruns.
- Zero-byte objects are filtered (they're usually placeholder
  "directory" markers from console uploads).
- Trailing-slash keys (also pseudo-directories) are skipped.
- `last_modified` is OSS-side; useful for incremental SQL on the
  manifest (`WHERE last_modified > '<watermark>'`) without re-listing
  OSS.
- The script truncates the destination table before writing. For
  append semantics, change to a partitioned table and write into a
  new partition per run.

## How downstream stages consume this manifest

`examples/frame_extraction_minimal.py` reads `VIDEO_INPUT_TABLE` with
`md.read_odps_table(...)` and assumes the `video_path` column exists.
The other manifest columns (`size_bytes`, `last_modified`) are not
required by frame extraction itself — they're there for the customer's
own incremental / cost-tracking logic. Frame extraction will pass them
through if the customer keeps them in the select-list, or drop them by
projecting only `video_path` before `apply_chunk`.

## When to NOT use this stage

- The customer already maintains a data catalog / inventory table with a
  `video_path` (or equivalent) column. Just point `VIDEO_INPUT_TABLE` at
  that existing table — no Stage 0 needed.
- The customer is in pure PoC and just has a handful of OSS URIs. Hand
  them the `md.DataFrame({"video_path": [...]})` pattern from the
  original product demo instead of building a manifest table.

## When to NOT use a pure-Python script

If the OSS prefix holds tens of millions of files, a single-threaded
paginator loop will take hours. The alternative is to seed a small
DataFrame of sub-prefixes (e.g., one row per date or per vehicle ID)
and fan out the listing inside a MaxFrame `apply_chunk` UDF. That
pattern is not currently in this skill — flag it to the customer and
work out the sub-prefix sharding with them before scaffolding.

## Safety

- The RAM user behind `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET`
  only needs `oss:ListObjects` (and `oss:GetObject` for reachability
  checks). Do not reuse a key with write permissions for
  this read-only job. Prefer a minimum-privilege RAM user dedicated to
  manifest builds.
- Read all credentials from env. Never hardcode them in the script.
  The user's `.env` is gitignored; generated scaffolds should never
  check in real values.
- `VIDEO_INPUT_TABLE` should be customer-namespaced (e.g.,
  `<scenario>_video_manifest`) to avoid collisions across pipelines.
- This script's static AK/SK is for the **Stage 0 setup runner only**.
  Inside the MaxFrame DAG, OSS access still goes through `role_arn` via
  `with_fs_mount` / `url.download`.

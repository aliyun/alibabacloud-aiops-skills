"""
Stage 0: Build the driving-video meta table.

Lists an OSS prefix with the alibabacloud_oss_v2 SDK, filters by video file
extensions, and writes one row per video to an ODPS table that downstream
stages (frame_extraction_minimal.py, image_labeling_minimal.py) consume as
VIDEO_INPUT_TABLE.

This is a one-shot setup / periodic refresh job. It runs as a plain Python
script and does NOT use MaxFrame, DPE, or GPU. Suitable for tens of
thousands up to a few million files. For larger scales, switch to a
MaxFrame-parallel listing pattern (seed sub-prefixes and fan out via
apply_chunk) -- see references/build_video_meta.md.

Required env vars:
- OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET   OSS auth (RAM user AK/SK)
- OSS_REGION                                  e.g. "cn-shanghai"
- OSS_ENDPOINT                                e.g. "oss-cn-shanghai-internal.aliyuncs.com"
                                              -- embedded in every `video_path` URI so
                                              that downstream frame_extraction's
                                              `with_fs_mount(OSS_ROOT, ...)` can match
                                              and substitute the mount path.
- OSS_BUCKET                                  target bucket
- VIDEO_INPUT_TABLE                           output ODPS table name

ODPS handle (pick one based on the runtime):
- DataWorks **PyODPS 3** node -- the platform auto-injects `o` as a
  module global. Just call `main(o)`; do NOT write `o = %odps`
  (that magic only exists in the Notebook kernel and would be a
  SyntaxError here).
- DataWorks **Notebook** node (IPython-based) -- write `o = %odps`
  to bind the magic-provided handle, then call `main(o)`.
- Anywhere else (local laptop, ECS, Jenkins, ...) -- build the
  handle from explicit env vars: ODPS_ACCESS_ID, ODPS_ACCESS_KEY,
  ODPS_PROJECT, ODPS_ENDPOINT.

Optional env vars:
- OSS_PREFIX            scan only this prefix; default "" = whole bucket
- OSS_LIST_MAX_KEYS     page size for list_objects_v2, default 1000
- VIDEO_EXTENSIONS      comma-separated, default ".mp4,.mov,.mkv,.avi"
- META_LIFECYCLE        table lifecycle in days, default 30
"""

import os
import time

import alibabacloud_oss_v2 as oss
import dotenv
from odps import ODPS

dotenv.load_dotenv()

OSS_ACCESS_KEY_ID = os.environ["OSS_ACCESS_KEY_ID"]
OSS_ACCESS_KEY_SECRET = os.environ["OSS_ACCESS_KEY_SECRET"]
OSS_REGION = os.environ["OSS_REGION"]
OSS_ENDPOINT = os.environ["OSS_ENDPOINT"]
OSS_BUCKET = os.environ["OSS_BUCKET"]
OSS_PREFIX = os.environ.get("OSS_PREFIX", "")

VIDEO_INPUT_TABLE = os.environ["VIDEO_INPUT_TABLE"]
VIDEO_EXTENSIONS = tuple(
    ext.strip().lower()
    for ext in os.getenv("VIDEO_EXTENSIONS", ".mp4,.mov,.mkv,.avi").split(",")
    if ext.strip()
)
META_LIFECYCLE = int(os.getenv("META_LIFECYCLE", "30"))
LIST_MAX_KEYS = int(os.getenv("OSS_LIST_MAX_KEYS", "1000"))


def build_oss_client():
    """OSS SDK v2 client with static RAM user AK/SK."""
    credentials_provider = oss.credentials.StaticCredentialsProvider(
        access_key_id=OSS_ACCESS_KEY_ID,
        access_key_secret=OSS_ACCESS_KEY_SECRET,
    )
    cfg = oss.config.load_default()
    cfg.credentials_provider = credentials_provider
    cfg.region = OSS_REGION
    cfg.endpoint = OSS_ENDPOINT
    cfg.user_agent = (
        f"AlibabaCloud-Agent-Skills/alibabacloud-maxframe-video-frame-pipeline"
        f"/{os.getenv('SKILL_SESSION_ID', 'unknown')}"
    )
    return oss.Client(cfg)


def iter_oss_videos(client):
    """Yield (oss_uri, size_bytes, last_modified_iso) for video files."""
    list_request = oss.ListObjectsV2Request(
        bucket=OSS_BUCKET,
        prefix=OSS_PREFIX,
        max_keys=LIST_MAX_KEYS,
    )
    paginator = client.list_objects_v2_paginator()
    for page in paginator.iter_page(list_request):
        for obj in page.contents or []:
            key = obj.key
            if key.endswith("/"):
                continue
            if not key.lower().endswith(VIDEO_EXTENSIONS):
                continue
            size = int(obj.size or 0)
            if size == 0:
                continue
            # Endpoint embedded so video_path starts with OSS_ROOT exactly,
            # which frame_extraction's `with_fs_mount` relies on for path
            # substitution. See references/frame_extraction.md.
            uri = f"oss://{OSS_ENDPOINT}/{OSS_BUCKET}/{key}"
            lm = obj.last_modified
            last_modified = lm.strftime("%Y-%m-%d %H:%M:%S") if lm else ""
            yield (uri, size, last_modified)


def write_meta(o, rows):
    """Create-if-missing + truncate + write rows on the given ODPS handle."""
    schema = "video_path string, size_bytes bigint, last_modified string"
    table = o.create_table(
        VIDEO_INPUT_TABLE,
        schema,
        if_not_exists=True,
        lifecycle=META_LIFECYCLE,
    )
    table.truncate()
    with table.open_writer() as writer:
        writer.write(rows)
    return table


def main(o):
    """Run the full pipeline against the given ODPS handle `o`."""
    target = f"oss://{OSS_BUCKET}/{OSS_PREFIX}" if OSS_PREFIX else f"oss://{OSS_BUCKET}/"
    print(f"Scanning {target} for extensions {VIDEO_EXTENSIONS}")

    oss_client = build_oss_client()
    start = time.perf_counter()
    rows = list(iter_oss_videos(oss_client))
    elapsed = time.perf_counter() - start
    print(f"Found {len(rows)} video files in {elapsed:.1f}s")

    if not rows:
        print("Nothing to write; aborting")
        return

    table = write_meta(o, rows)
    total_bytes = sum(r[1] for r in rows)
    print(f"Wrote {len(rows)} rows to {table.name}")
    print(f"Total video size: {total_bytes / (1024 ** 3):.2f} GiB")


if __name__ == "__main__":
    # ---- Choose ONE of the three ODPS handle paths ----
    #
    # (A) DataWorks PyODPS 3 node -- `o` is pre-injected as a module
    #     global by the platform; do nothing here. Just call `main(o)`
    #     at the end. Do NOT write `o = %odps` -- the `%odps` magic
    #     is Notebook-only and is a SyntaxError on PyODPS 3 nodes.
    #
    # (B) DataWorks Notebook node (IPython kernel) -- comment out (C)
    #     below and uncomment:
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

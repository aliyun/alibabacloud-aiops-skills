# Frame Extraction

There is no first-class `video` accessor in MaxFrame 2.7. Frame extraction
runs as a customer-side `mf.apply_chunk` UDF that mounts OSS via
`with_fs_mount`, sets resources via `with_running_options`, and shells
out to `ffprobe` / `ffmpeg`. The pattern below is verified on real
driving-video inputs.

## Imports

```python
import glob
import math
import os
import subprocess

import pandas as pd

from maxframe.udf import with_fs_mount, with_running_options
```

## UDF skeleton

```python
@with_running_options(engine="dpe", cpu=2, memory=8)
@with_fs_mount(
    OSS_ROOT,                              # e.g. "oss://oss-cn-shanghai-internal.aliyuncs.com/<bucket>/<prefix>"
    OSS_MOUNT_PATH,                        # e.g. "/mnt/driving_oss"
    storage_options={"role_arn": OSS_ROLE_ARN},
)
def frame_extraction_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in chunk.iterrows():
        video_path = row["video_path"]
        try:
            local_video_path = video_path.replace(f"{OSS_ROOT}/", f"{OSS_MOUNT_PATH}/")
            local_output_dir = os.path.join(OSS_MOUNT_PATH, "frames")
            os.makedirs(local_output_dir, exist_ok=True)

            base_name = os.path.splitext(os.path.basename(local_video_path))[0]
            local_output_pattern = os.path.join(local_output_dir, f"{base_name}_%04d.jpg")
            video_dir, video_name = video_path.rsplit("/", 1)
            video_basename = video_name.rsplit(".", 1)[0]

            probe = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    local_video_path,
                ],
                capture_output=True, text=True, check=False,
            )
            if probe.returncode != 0:
                raise RuntimeError(f"ffprobe_failed: {probe.stderr.strip()}")
            try:
                duration = float(probe.stdout.strip())
            except ValueError as exc:
                raise ValueError("invalid_duration") from exc
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError("invalid_duration")

            ff = subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-i", local_video_path,
                    "-vf", f"fps={FRAME_FPS}",
                    "-q:v", "2",
                    "-start_number", "0",
                    local_output_pattern,
                ],
                capture_output=True, text=True,
                timeout=FFMPEG_TIMEOUT_SEC, check=False,
            )
            if ff.returncode != 0:
                raise RuntimeError(f"ffmpeg_failed: {ff.stderr.strip()}")

            frame_files = sorted(glob.glob(local_output_pattern.replace("%04d", "*")))
            if not frame_files:
                raise ValueError("no_frames_found")

            for frame_idx, _ in enumerate(frame_files):
                rows.append(
                    {
                        "video_path": video_path,
                        "frame_idx": frame_idx,
                        "image_id": f"{video_basename}_{frame_idx:04d}",
                        "image_url": (
                            f"{video_dir}/frames/"
                            f"{video_basename}_{frame_idx:04d}.jpg"
                        ),
                        "status": "ok",
                        "error_stage": "",
                        "error_msg": "",
                    }
                )
        except Exception as exc:
            rows.append(
                {
                    "video_path": video_path,
                    "frame_idx": -1,
                    "image_id": "",
                    "image_url": "",
                    "status": "failed",
                    "error_stage": "frame_extraction",
                    "error_msg": str(exc),
                }
            )
    return pd.DataFrame(rows)
```

The output column names (`image_id`, `image_url`) intentionally match
the image-labeling input contract so the frame table can be consumed
directly by `image_labeling_minimal.py` (or chained lazily in a
single-job DAG) without any column rename. `image_id` is synthesized as
`<video_basename>_<frame_idx:04d>`, which also matches the JPEG
filename on disk -- useful for debugging.

## Wiring it into a MaxFrame DAG

```python
df = md.read_odps_table(VIDEO_INPUT_TABLE)  # has column: video_path

frames = df.mf.apply_chunk(
    frame_extraction_chunk,
    output_type="dataframe",
    dtypes=pd.Series(
        {
            "video_path":  "object",
            "frame_idx":   "int64",
            "image_id":    "object",
            "image_url":   "object",
            "status":      "object",
            "error_stage": "object",
            "error_msg":   "object",
        }
    ),
)

md.to_odps_table(frames, FRAME_OUTPUT_TABLE, overwrite=True).execute()
```

For single-job pipelines (default), the `frames` DataFrame is fed
directly into the AI FUNC labeling stage without an intermediate write —
see [ai_func_calls.md](ai_func_calls.md).

## Configurable knobs

| Env var                  | Meaning                                                |
|--------------------------|--------------------------------------------------------|
| `OSS_ROOT`               | OSS prefix being mounted (no trailing slash)           |
| `OSS_MOUNT_PATH`         | Local mount target inside the rund container          |
| `OSS_ROLE_ARN`           | STS role used by `with_fs_mount`                      |
| `FRAME_FPS`              | ffmpeg `-vf fps=<value>`. Default `1/1` (1 frame/sec) |
| `FFMPEG_TIMEOUT_SEC`     | Hard timeout on ffmpeg per video. Default 300         |

## Why `with_fs_mount` instead of `url.download`

- ffmpeg works on local files, not byte streams. Mounting OSS lets ffmpeg
  read once and write derived frames back without staging through Python
  buffers.
- The same mount lets us write derived frame JPEGs directly under
  `<OSS_ROOT>/frames/...`, which is what downstream `image_url` columns
  point at.
- `url.download(storage_options={"role_arn": ...})` is the right tool for
  pulling small audio bytes into a Series, but it materializes data per
  row — bad fit for hundreds-of-MB driving videos.

## Failure semantics

- Per-row try/except inside the UDF means a corrupt video produces a
  single failed row (`status="failed", error_stage="frame_extraction"`)
  rather than killing the whole instance.
- Successful rows fan out: one input video row produces N frame rows.
  Downstream stages should preserve `video_path` for lineage.
- `error_msg` should carry just the relevant ffprobe / ffmpeg stderr; do
  not include full local paths that might leak environment details.

## Path safety

- The UDF only translates `OSS_ROOT/...` paths into mount paths. Do not
  accept arbitrary `local_video_path` values from the input table.
- If the input table contains paths outside `OSS_ROOT`, fail the row
  with `error_stage="frame_extraction"`, `error_msg="path_outside_root"`
  rather than silently mounting a different bucket.

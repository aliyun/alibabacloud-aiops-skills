"""
Minimal driving-video frame extraction job.

Reads an ODPS table whose `video_path` column points at OSS-hosted videos,
extracts frames via ffmpeg under an OSS mount, and writes one row per
frame to an output table.

Output schema matches the image-labeling input contract so the frame
table can be fed straight into image_labeling_minimal.py without column
remapping:
  video_path, frame_idx (lineage)
  image_id, image_url   (consumed by AI FUNC: cp.image(data=image_url, ...))
  status, error_stage, error_msg

Required env vars:
- ODPS_ACCESS_ID, ODPS_ACCESS_KEY, ODPS_PROJECT, ODPS_ENDPOINT
- OSS_ROLE_ARN, OSS_ROOT, OSS_MOUNT_PATH
- VIDEO_INPUT_TABLE, FRAME_OUTPUT_TABLE
"""

import glob
import math
import os
import subprocess

import dotenv
import pandas as pd
from odps import ODPS

import maxframe.dataframe as md
from maxframe.session import new_session
from maxframe.udf import with_fs_mount, with_running_options

dotenv.load_dotenv()

OSS_ROLE_ARN = os.environ["OSS_ROLE_ARN"]
OSS_ROOT = os.environ["OSS_ROOT"]
OSS_MOUNT_PATH = os.environ["OSS_MOUNT_PATH"]

VIDEO_INPUT_TABLE = os.environ["VIDEO_INPUT_TABLE"]
FRAME_OUTPUT_TABLE = os.environ["FRAME_OUTPUT_TABLE"]

FRAME_FPS = os.getenv("FRAME_FPS", "1/1")
FFMPEG_TIMEOUT_SEC = int(os.getenv("FFMPEG_TIMEOUT_SEC", "300"))


@with_running_options(engine="dpe", cpu=2, memory=8)
@with_fs_mount(
    OSS_ROOT,
    OSS_MOUNT_PATH,
    storage_options={"role_arn": OSS_ROLE_ARN},
)
def frame_extraction_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in chunk.iterrows():
        video_path = row["video_path"]
        try:
            if not video_path.startswith(f"{OSS_ROOT}/"):
                raise ValueError("path_outside_root")

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
                capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SEC, check=False,
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


def main():
    o = ODPS(
        access_id=os.environ["ODPS_ACCESS_ID"],
        secret_access_key=os.environ["ODPS_ACCESS_KEY"],
        project=os.environ["ODPS_PROJECT"],
        endpoint=os.environ["ODPS_ENDPOINT"],
    )

    session = new_session(o)
    print(f"Logview: {session.get_logview_address()}")

    try:
        df = md.read_odps_table(VIDEO_INPUT_TABLE)
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
    finally:
        session.destroy()


if __name__ == "__main__":
    main()

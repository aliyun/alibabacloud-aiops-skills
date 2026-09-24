# New Job Example: Built-in Multimodal Video Pipeline

Use this pattern for video-frame extraction, a built-in image expression, and JSON output. Check the selected package's source/docstrings for the frame schema and supported options before adapting it.

## Complete `job.py`

```python
import pyflink.dataframe as pf


SOURCE_VIDEO_GLOB = "oss://<source-bucket>/videos/**/*.mp4"
SINK_JSON_PATH = "oss://<sink-bucket>/video-frame-metrics/"
SAMPLE_INTERVAL_MS = 5000
MAX_FRAMES_PER_VIDEO = 120


def main() -> None:
    frames = pf.read_video_frames(
        SOURCE_VIDEO_GLOB,
        frame_selector="sample",
        sample_interval_ms=SAMPLE_INTERVAL_MS,
        max_frames=MAX_FRAMES_PER_VIDEO,
        image_height=360,
        image_width=640,
        on_error="skip",
        concurrency=4,
    )

    frame_metrics = frames.with_column(
        "aspect_ratio",
        pf.col("frame").image.aspect_ratio(),
    ).select(
        video_uri=pf.col("metadata").get("uri"),
        frame_index=pf.col("metadata").get("frame_index"),
        time_ms=pf.col("metadata").get("time_ms"),
        aspect_ratio=pf.col("aspect_ratio"),
    )

    frame_metrics.write_json(
        SINK_JSON_PATH,
        mode="overwrite",
        write_null_properties=False,
    )


if __name__ == "__main__":
    main()
```

## Deployment contract

- Replace both OSS paths after the source and sink methods are confirmed.
- Keep frame extraction in `read_video_frames` and image inspection in the built-in `.image.aspect_ratio()` expression.
- Do not replace the source, extraction, image operation, and sink shaping with one Python callback.
- Tune interval, frame limit, dimensions, concurrency, and error policy from confirmed latency, quality, and resource requirements.

This pipeline selects no third-party Python package, local model, or independent runtime file. Syntax and artifact checks are local; OSS discovery, frame decoding, multimodal execution, resource use, and sink output are VVR-only.

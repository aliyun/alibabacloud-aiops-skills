# Capability Overview

## Feature Tree

```
Alibaba Cloud MPS Video Processing
│
├── 📤 Upload
│   └── Upload video to OSS storage
│
├── 🔍 Probe
│   └── Get media info (duration, bitrate, resolution, etc.)
│
├── 🖼️ Snapshot
│   └── Normal snapshots and sprite sheet generation
│
├── 🎬 Transcode
│   ├── Adaptive single-stream Narrowband HD transcoding (auto-select best resolution based on source)
│   ├── Multi-resolution transcoding (LD/SD/HD/FHD/2K/4K)
│   ├── Super-resolution enhancement
│   └── Narrowband HD compression
│
├── 🛡️ Moderation
│   └── Content moderation (pornography, violence, advertising, etc.)
│
└── 📥 Download
    └── Get download links for processed videos
```

## Automatic Pipeline Management

This skill supports automatic pipeline selection without manual Pipeline ID configuration:

- Scripts automatically select or create appropriate pipelines based on task type when `--pipeline-id` is not specified
- Different task types use different pipelines:
  - Transcoding tasks: Use Standard or NarrowBandHDV2 pipelines
  - Moderation tasks: Use AIVideoCensor pipeline
- `ALIBABA_CLOUD_MPS_PIPELINE_ID` environment variable is optional:
  - If set, this value takes priority
  - If not set, automatically select pipeline suitable for current task type

To manually view or select pipelines:

```bash
# List all pipelines
python scripts/mps_pipeline.py

# List pipelines by type
python scripts/mps_pipeline.py --type standard     # Transcoding pipelines
python scripts/mps_pipeline.py --type audit        # Moderation pipelines

# Auto-select and get Pipeline ID
export ALIBABA_CLOUD_MPS_PIPELINE_ID=$(python scripts/mps_pipeline.py --select)
echo "Pipeline ID: $ALIBABA_CLOUD_MPS_PIPELINE_ID"
```

---
name: alibabacloud-video-forge
description: Alibaba Cloud Media Processing Service (MPS) one-stop video processing skill. Use when users need video processing, transcoding, snapshot generation, content moderation, or video upload. For video distribution scenarios, complete video upload, snapshot, multi-resolution transcoding, and content moderation in a single workflow for efficient standardized video asset production.
---

# Alibaba Cloud Video Forge

One-stop video processing through Alibaba Cloud Media Processing Service (MPS), including cover generation, multi-resolution transcoding, content moderation, and more.

## 🚀 Quick Start

**Easiest Way** - One-click video processing:

```bash
# Method 1: Use end-to-end workflow script (Recommended)
python scripts/video_workflow.py --input /path/to/video.mp4

# Method 2: Check environment first
python scripts/health_check.py

# Method 3: Execute steps manually
python scripts/oss_upload.py --local-file video.mp4 --oss-key input/video.mp4
python scripts/mps_transcode.py --oss-object input/video.mp4 --preset multi
python scripts/mps_audit.py --oss-object input/video.mp4
```

### Common Scenarios

#### Scenario 1: Bilibili Video Publishing
```bash
python scripts/video_workflow.py \
  --input my_video.mov \
  --preset 720p \
  --generate-cover \
  --scenes porn terrorism ad
```

#### Scenario 2: UGC Content Moderation
```bash
python scripts/mps_audit.py --oss-object /input/user_uploaded.mp4
```

#### Scenario 3: Multi-Resolution Transcoding
```bash
python scripts/mps_transcode.py \
  --oss-object /input/course_video.mp4 \
  --preset multi \
  --output-prefix output/course_2024/
```

---

## Scenario Description

This skill supports video distribution scenarios:

1. **Transcoding** — Multi-resolution transcoding with Narrowband HD compression
2. **Content Moderation** — Auto-detect sensitive content (pornography, terrorism, advertising)
3. **Snapshot** — Generate cover images and sprite sheets
4. **Anti-piracy** — Configure encryption for content protection

### Architecture

```
OSS Bucket + MPS Pipeline + Transcoding Templates + Moderation Service
```

**Components**:
- **OSS**: Store videos and outputs
- **MPS Pipeline**: Task queue management
- **Transcoding Templates**: Narrowband HD, Standard presets
- **Moderation**: Auto content safety checks

**Target Users**: Video platforms, content creators, corporate training, education platforms

## Capability Overview

See [references/capability-overview.md](references/capability-overview.md) for detailed feature tree and automatic pipeline management.

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed, see `references/cli-installation-guide.md`.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

> **Pre-check: Python >= 3.10 required**
> Run `python3 --version` to verify.

> **Pre-check: Alibaba Cloud Credentials Required**
>
> Run `aliyun configure list` to check credential status. If no valid profile, configure via `aliyun configure`.
> See [references/security-guidelines.md](references/security-guidelines.md) for credential security rules.

## Environment Variables

**Required environment variables:**
- `ALIBABA_CLOUD_REGION` - Service region (default: cn-shanghai)
- `ALIBABA_CLOUD_OSS_BUCKET` - OSS Bucket name
- `ALIBABA_CLOUD_OSS_ENDPOINT` - OSS endpoint
- `ALIBABA_CLOUD_MPS_PIPELINE_ID` - MPS Pipeline ID (optional, auto-selected if not set)

> **Security Note:** Credentials are managed via the Alibaba Cloud default credential chain. Configure credentials using `aliyun configure` command. NEVER handle AK/SK directly in scripts or commands.

## 🔒 Security Guidelines

See [references/security-guidelines.md](references/security-guidelines.md) for complete security guidelines and credential management best practices.

## SDK Installation

See [references/sdk-installation.md](references/sdk-installation.md) for detailed installation guide and troubleshooting.

> Run `python3 --version` to verify. Some scripts may fail with older Python versions.

## RAM Permissions

> **[MUST] RAM Permission Pre-check:** Verify that the current user has the following RAM permissions before execution.
> See `references/ram-policies.md` for complete permission list and details.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., input video path, output bucket, template ID, etc.)
> MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|------------------|-------------|---------|
| input-url | Required | Input video URL or local path | - |
| output-bucket | Optional | Output OSS Bucket | Environment variable value |
| output-path | Optional | Output path prefix | output/ |
| template-id | Optional | Transcoding template ID | System preset template |
| resolutions | Optional | Transcoding resolution list | 720p,1080p |
| audit | Optional | Whether to perform content moderation | true |
| pipeline-id | Optional | MPS Pipeline ID | Auto-select |

## Core Workflow

### Scenario 1: One-stop Video Standardization

Complete workflow: User provides video → Upload to OSS → Media info probe → Cover generation (snapshot) → Multi-resolution transcoding → Content moderation → Summary results (with download links)

#### Step 0: Automatic Pipeline Selection (Optional)

This skill supports automatic pipeline management, typically no manual Pipeline ID configuration needed. Scripts automatically select appropriate pipelines based on task type.

To manually specify:

```bash
# Method 1: Set environment variable (highest priority)
export ALIBABA_CLOUD_MPS_PIPELINE_ID="your-pipeline-id"

# Method 2: Command line parameter
python scripts/mps_transcode.py --oss-object /input/video.mp4 --pipeline-id your-pipeline-id

# Method 3: Use script auto-selection
export ALIBABA_CLOUD_MPS_PIPELINE_ID=$(python scripts/mps_pipeline.py --select)
```

#### Step 1: Upload Video to OSS

```bash
source .venv/bin/activate
python scripts/oss_upload.py --local-file /path/to/video.mp4 --oss-key input/video.mp4
```

#### Step 2: Media Info Probe

```bash
python scripts/mps_mediainfo.py --oss-object /input/video.mp4
```

#### Step 3: Cover Generation (Snapshot)

Use snapshot function to generate video cover at specified time:

```bash
python scripts/mps_snapshot.py --oss-object /input/video.mp4 --mode normal --time 5000
```

#### Step 4: Adaptive Transcoding (Auto-select best resolution and Narrowband HD template)

```bash
# Adaptive mode: Auto-detect source video resolution, select best quality, use Narrowband HD template
python scripts/mps_transcode.py --oss-object /input/video.mp4

# Or manually specify multi-stream transcoding
python scripts/mps_transcode.py \
  --oss-object /input/video.mp4 \
  --preset multi
```

#### Step 5: Content Moderation

```bash
python scripts/mps_audit.py --oss-object /input/video.mp4
```

#### Step 6: Poll Task Status

```bash
python scripts/poll_task.py --job-id <job-id-from-step-4> --job-type transcode --region cn-shanghai
```

#### Complete Example

```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Upload video
python scripts/oss_upload.py --local-file ./my_video.mp4 --oss-key input/my_video.mp4

# 3. Get media info
python scripts/mps_mediainfo.py --oss-object /input/my_video.mp4

# 4. Cover generation (snapshot at 5 seconds)
python scripts/mps_snapshot.py --oss-object /input/my_video.mp4 --mode normal --time 5000

# 5. Submit transcoding job (adaptive mode: auto-select best resolution)
python scripts/mps_transcode.py \
  --oss-object /input/my_video.mp4
# Save the returned job-id

# 6. Poll transcoding job status
python scripts/poll_task.py --job-id <job-id> --job-type transcode --region cn-shanghai --interval 10

# 7. Content moderation
python scripts/mps_audit.py --oss-object /input/my_video.mp4

# 8. Download processed video to local
python scripts/oss_download.py --oss-key output/transcode/transcoded.mp4 --local-file ./output_video.mp4
```

## Other Scenarios

### Scenario 2: Transcoding Only

Execute transcoding only, without snapshot and moderation:

```bash
source .venv/bin/activate
python scripts/mps_transcode.py \
  --oss-object /input/video.mp4 \
  --preset 1080p \
  --template-id "your-template-id"
```

### Scenario 3: Content Moderation

Execute content moderation only:

```bash
source .venv/bin/activate
python scripts/mps_audit.py \
  --oss-object /input/video.mp4 \
  --scenes porn terrorism ad
```

## Success Verification

After video processing, check results:

1. Script exit code is 0
2. Output contains processed media info (OSS path)
3. Transcoding job status is "Success"
4. Content moderation shows no violations
5. Artifacts downloaded locally (using `oss_download.py`)

**Notes on Artifact Retrieval**:
- OSS files require signing for online access, direct URL access returns 403 error
- Recommend using `oss_download.py` to download results locally
- For online preview, use `--sign-url` parameter to generate temporary pre-signed URL

```bash
# Verify transcoding success
python scripts/poll_task.py --job-id <job-id> --job-type transcode --region cn-shanghai
# Expected output: Status: Success

# Verify moderation result
python scripts/mps_audit.py --query-job-id <audit-job-id>
# Expected output: Moderation passed, no violations
```

## Troubleshooting

See [references/troubleshooting.md](references/troubleshooting.md) for comprehensive troubleshooting guide.

---

## Cleanup

Intermediate files and output files from this skill are stored in OSS. To clean up:

```bash
# Delete single file
python scripts/oss_delete.py --oss-key output/transcode/video.mp4

# Delete all files under directory (recursive delete)
python scripts/oss_delete.py --prefix output/ --recursive

# Force delete (skip confirmation, for script automation)
python scripts/oss_delete.py --oss-key output/video.mp4 --force

# Preview mode (view files to be deleted without actually deleting)
python scripts/oss_delete.py --prefix output/ --recursive --dry-run
```

> **Note**: Delete operations are irreversible. Confirm before executing. Use `--dry-run` to preview first.

## Available Scripts

| Script | Description |
|--------|-------------|
| `scripts/load_env.py` | Environment variable loader, auto-scan and load Alibaba Cloud credentials |
| `scripts/poll_task.py` | MPS async task poller, query task status |
| `scripts/oss_upload.py` | Upload local file to OSS |
| `scripts/oss_download.py` | Download file from OSS to local |
| `scripts/oss_list.py` | List files in OSS Bucket |
| `scripts/oss_delete.py` | Delete OSS files or directories (supports recursive delete) |
| `scripts/mps_mediainfo.py` | Get media file info (resolution, bitrate, duration, etc.) |
| `scripts/mps_snapshot.py` | Snapshot and sprite sheet generation (supports normal/sprite mode) |
| `scripts/mps_transcode.py` | Video transcoding (supports adaptive Narrowband HD, multi-resolution presets, custom parameters) |
| `scripts/mps_audit.py` | Content safety moderation (supports multiple moderation scenarios) |
| `scripts/mps_pipeline.py` | Pipeline list query and auto-selection (get Pipeline ID) |

## Best Practices

1. **Always check environment variables first** — Run `python scripts/load_env.py --check-only` at the start of each session
2. **Use polling instead of waiting** — Use `poll_task.py` to auto-poll status after submitting jobs
3. **Choose resolutions wisely** — Select appropriate transcoding resolutions based on target user devices
4. **Enable content moderation** — For UGC content, always enable automatic moderation
5. **Use virtual environment** — Ensure dependency isolation to avoid version conflicts
6. **Automatic pipeline management** — No need to manually configure Pipeline ID, scripts auto-select appropriate pipelines based on task type

## Reference Documentation

| Document | Description |
|----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | Complete RAM permission policy list |
| [references/params.md](references/params.md) | Script parameter documentation |
| [references/scripts-detail.md](references/scripts-detail.md) | Detailed script usage examples |
| [references/verification-method.md](references/verification-method.md) | Success verification methods |
| [references/related-commands.md](references/related-commands.md) | Related CLI commands |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Testing acceptance criteria |

## CLI Command Standards

> **Important**: If using `aliyun` CLI commands, all commands **MUST** include the `--user-agent AlibabaCloud-Agent-Skills` parameter.
> Example: `aliyun mts search-pipeline --PageNumber 1 --PageSize 10 --user-agent AlibabaCloud-Agent-Skills`

# Related Commands - Yike Storyboard Skill

This document lists all CLI commands used in the Yike Storyboard skill.

## Core Commands

| Product | CLI Command | Description |
|---------|-------------|-------------|
| ICE | `aliyun ice create-yike-asset-upload` | Get Yike asset upload credentials |
| ICE | `aliyun ice submit-yike-storyboard-job` | Submit Yike storyboard job |
| ICE | `aliyun ice get-yike-storyboard-job` | Query Yike storyboard job status |
| OSS | `aliyun ossutil cp` | Upload file to OSS |

## Command Details

### 1. Get Upload Credentials

```bash
aliyun ice create-yike-asset-upload \
  --file-ext txt \
  --file-type StoryboardInput \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard
```

**Parameters:**
- `--file-ext`: (Required) File extension, e.g., `txt`, `docx`
- `--file-type`: File type, use `StoryboardInput` for storyboard input
- `--region`: Region, default `cn-shanghai`

**Response Fields:**
- `UploadAddress`: Base64 encoded OSS upload address info
- `UploadAuth`: Base64 encoded STS temporary credentials
- `FileURL`: File URL after upload

### 2. Upload File to OSS

```bash
# Upload using STS temporary credentials
aliyun ossutil cp /path/to/novel.txt oss://bucket-name/object-key \
  --mode StsToken \
  --access-key-id <AccessKeyId> \
  --access-key-secret <AccessKeySecret> \
  --sts-token <SecurityToken> \
  --endpoint <Endpoint>
```

**Parameters:**
- `--mode StsToken`: Use STS temporary credential authentication
- `--access-key-id`: STS temporary AccessKeyId
- `--access-key-secret`: STS temporary AccessKeySecret
- `--sts-token`: STS SecurityToken
- `--endpoint`: OSS Endpoint

### 3. Submit Storyboard Job

```bash
aliyun ice submit-yike-storyboard-job \
  --file-url "<FileURL>" \
  --source-type Script \
  --style-id CinematicRealism \
  --narration-voice-id sys_GentleYoungMan \
  --aspect-ratio "9:16" \
  --resolution 720P \
  --shot-split-mode dialogue \
  --shot-prompt-mode multi \
  --video-model "wan2.6-r2v-flash" \
  --exec-mode StoryboardOnly \
  --title "My Story" \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard
```

**Parameters:**
| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--file-url` | ✅ | Uploaded file URL | From upload step |
| `--source-type` | ✅ | Source type | `Novel` or `Script` |
| `--style-id` | ✅ | Storyboard style ID | `Ghibli`, `CinematicRealism` |
| `--narration-voice-id` | ✅ | Narration voice ID | `sys_GentleYoungMan` |
| `--aspect-ratio` | | Video aspect ratio | `9:16`, `16:9` |
| `--resolution` | | Resolution | `720P`, `1K`, `2K`, `4K` |
| `--shot-split-mode` | ✅ | Shot split mode | `dialogue`, `thirdPersonNarration` |
| `--shot-prompt-mode` | | Shot generation mode | `multi` |
| `--video-model` | | Video model | `wan2.6-r2v-flash` |
| `--exec-mode` | | Execution mode | `StoryboardOnly` |
| `--title` | | Storyboard title | Any string |

**Response Fields:**
- `JobId`: Job ID for status tracking

### 4. Query Job Status

```bash
aliyun ice get-yike-storyboard-job \
  --job-id <JobId> \
  --region cn-shanghai \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard
```

**Parameters:**
- `--job-id`: (Required) Job ID

**Response Fields:**
- `JobStatus`: Job status (`Running`/`Succeeded`/`Failed`/`Suspended`)
- `JobResult`: Job result JSON containing `StoryboardInfoList`

## Auxiliary Commands

| Product | CLI Command | Description |
|---------|-------------|-------------|
| STS | `aliyun sts get-caller-identity` | Verify current identity |
| ICE | `aliyun ice list-yike-productions` | List Yike productions |
| ICE | `aliyun ice batch-get-yike-ai-app-job` | Batch get jobs |

## Important Notes

1. All `aliyun` CLI commands MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-yike-storyboard`
2. ICE service is currently only available in `cn-shanghai` region
3. OSS upload uses STS temporary credentials with limited validity period
4. The `--title` parameter is optional but recommended for identification

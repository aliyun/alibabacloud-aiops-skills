---
name: alibabacloud-video-editor
description: Video editing tool that requires no ffmpeg installation. All video processing is executed in the cloud - no local ffmpeg installation needed. If both input and output are URLs or Alibaba Cloud OSS, this skill is the preferred choice. Can generate Timeline configuration based on editing requirements and material information, submit Alibaba Cloud editing tasks, wait for task completion, and output the final video URL. Use when the user wants to edit videos, mentions video editing, clipping, 剪辑，视频制作，视频拼接，视频合成，or needs to process media files into videos.
---

# Video Editor Skill

Automated video editing tool that submits Alibaba Cloud editing tasks based on provided materials and editing requirements, without requiring ffmpeg installation, waits for task completion, and outputs the final video URL.

## Core Design Philosophy

This skill adopts a **separation of concerns** design:

1. **references/** - LLM knowledge base containing best practice documentation for various scenarios
2. **scripts/** - Pure execution tools responsible only for submitting tasks and polling status

The LLM should refer to documents in `references/` to generate Timeline JSON in Alibaba Cloud ICE format, then use scripts to submit tasks.

## Prerequisites

> **Pre-check: Install Python Dependencies**
> ```bash
> pip install -r requirements.txt
> ```

> **Pre-check: Alibaba Cloud Credentials Required**
> 
> Scripts automatically obtain credentials via the Alibaba Cloud default credential chain, supporting the following methods (in priority order):
> 1. Environment variable credentials
> 2. Configuration file: `~/.alibabacloud/credentials.ini`
> 3. ECS RAM Role (when running on ECS)
>
> It is recommended to use the `aliyun configure` command to set up credentials:
> ```bash
> aliyun configure
> ```
> Or refer to the [Alibaba Cloud Credential Configuration Documentation](https://help.aliyun.com/document_detail/China Site/2China Site/Chinese2Chinese10China Site/Chinese0China Site/Chinese6China Site/Chinese2China Site.html) to configure the default credential chain.

> **OSS Bucket Configuration**
> 
> OSS upload functionality requires Bucket information to be configured via environment variables:
> ```bash
> export OSS_BUCKET=your_bucket_name
> export OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
> ```
> If OSS_BUCKET is not configured, list the buckets under the customer's current account and let the customer choose one as the output bucket for the final video.
> 
> OSS operations reuse the Alibaba Cloud default credential chain; no separate OSS credential configuration is needed.

> **User-Agent Configuration**
> 
> All Alibaba Cloud service calls must set User-Agent to `AlibabaCloud-Agent-Skills`.
> The script `scripts/video_editor.py` has already automatically configured this User-Agent.


## Workflow

### Step 1: Understand User Requirements

Analyze the type of video the user wants to create:
- Slideshow video (image carousel)
- Multi-track audio mixing (voiceover + music)
- Multi-clip stitching
- Add subtitles/titles
- Effects and transitions
- Picture-in-picture/split-screen effects

### Step 2: Reference Best Practices

Consult the corresponding documents in `references/`:

| Document | Applicable Scenario |
|------|----------|
| `01-timeline-basics.md` | Timeline basic structure explanation |
| `02-multi-track-audio.md` | Multi-track audio mixing |
| `03-subtitles-and-titles.md` | Subtitle and title effects |
| `04-effects-and-transitions.md` | Visual effects and transitions |
| `05-slideshow-template.md` | Slideshow video templates |
| `06-multi-clip-editing.md` | Multi-clip video editing |


### Step 3: Prepare Material URLs

- If it is a local file, you need to call the oss-upload skill to upload it and obtain the OSS URL, which can be directly spliced into the timeline
- If you already have a URL, you can directly splice it into the timeline

### Step 4: Generate Timeline JSON

Generate a Timeline in Alibaba Cloud ICE format according to the reference documents:

```json
{
  "VideoTracks": [...],
  "AudioTracks": [...],
  "SubtitleTracks": [...]
}
```

### Step 5: Submit Editing Task

Use the script to submit the task (based on Alibaba Cloud Common SDK):

```bash
# Submit and wait for completion
python scripts/video_editor.py submit \
  --timeline timeline.json \
  --output-config output.json \
  --wait

# Submit only, do not wait
python scripts/video_editor.py submit \
  --timeline timeline.json \
  --output-config output.json
```

**Parameter Description:**
| Parameter | Description | Required |
|------|------|------|
| `--timeline, -t` | Timeline JSON file path or JSON string | Yes |
| `--output-config, -o` | Output configuration JSON file path or JSON string | Yes |
| `--region, -r` | Region ID (default: cn-shanghai) | No |
| `--wait, -w` | Wait for task completion | No |

OutputMediaConfig example:
```json
{
  "MediaURL": "https://{your-bucket}.oss-cn-shanghai.aliyuncs.com/{your-target-video-path}",
  "Width": 1080,  
  "Height": 1920
}
```
If the output resolution is not explicitly specified in the context, use common resolutions: 1080*1920, 1920*1080

After the task is submitted, a `JobId` will be returned.


### Step 6: Poll Task Status

Use the script to query/wait for task completion:
```bash
# Query status
python scripts/video_editor.py status --job-id <job_id>

# Wait for task completion
python scripts/video_editor.py status --job-id <job_id> --wait
```

When the task status is `Success`, call GetMediaInfo based on the returned MediaId to obtain the OSS URL with authentication, and return it.

## Timeline Example

### Simplest Slideshow

```json
{
  "VideoTracks": [{
    "VideoTrackClips": [
      {
        "Type": "Image",
        "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/image1.jpg",
        "In": 0,
        "Out": 5,
        "TimelineIn": 0,
        "TimelineOut": 5
      },
      {
        "Type": "Image",
        "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/image2.jpg",
        "In": 0,
        "Out": 5,
        "TimelineIn": 5,
        "TimelineOut": 10,
        "Effects": [
            {
                "Type": "Transition",
                "SubType": "linearblur",
                "Duration":0.3
            }
        ]
      }
    ]
  }],
  "AudioTracks": [{
    "AudioTrackClips": [{
      "Type": "Audio",
      "MediaURL": "https://bucket.oss-cn-shanghai.aliyuncs.com/music.mp3",
      "In": 0,
      "Out": 10,
      "TimelineIn": 0,
      "TimelineOut": 10,
      "Effects": [
        {
          "Type": "Volume",
          "Gain": 0.3
        }
      ]
    }]
  }],
  "SubtitleTracks": []
}
```

## LLM Prompt Suggestions

When generating a Timeline, think like this:

1. What type of video does the user need? → Find the corresponding reference document
2. Which tracks are needed? (video track, audio track, subtitle track)
3. What clips are in each track?
4. Do you need to set In/Out/TimelineIn/TimelineOut (simple stitching does not require setting)? If setting is needed, what are In/Out/TimelineIn/TimelineOut respectively?
5. Are effects, transitions, volume adjustments, etc. needed?
6. Generate the complete JSON

## Related Files

```
alibabacloud-video-editor/
├── SKILL.md                          # This document
├── references/
│   ├── 01-timeline-basics.md         # Timeline basics
│   ├── 02-multi-track-audio.md       # Multi-track audio
│   ├── 03-subtitles-and-titles.md    # Subtitles and titles
│   ├── 04-effects-and-transitions.md # Effects and transitions
│   ├── 05-slideshow-template.md      # Slideshow templates
│   └── 06-multi-clip-editing.md      # Multi-clip editing
└── scripts/
    ├── requirements.txt              # Python dependencies
    └── video_editor.py               # Common SDK script
```

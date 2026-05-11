# Common Recipes

Quick-reference templates for frequent use cases. Copy and adjust parameters as needed.

| Use Case | Operations | Flags | Notes |
|----------|-----------|-------|-------|
| Thumbnail (width 400, webp) | `"resize:w=400" "format:target=webp"` | `--output-mode download --output-path $WORKSPACE_OUTPUT/thumb.webp` | Output path is sufficient |
| Compress JPEG to 80% quality | `"quality:q=80"` | `--output-mode download --output-path $WORKSPACE_OUTPUT/compressed.jpg` | Output path is sufficient |
| Resize + compress + convert | `"resize:w=800" "quality:q=80" "format:target=webp"` | `--output-mode download --output-path $WORKSPACE_OUTPUT/optimized.webp` | Output path is sufficient |
| Text watermark bottom-right | `"watermark:text=YourText,g=se,size=40,color=FFFFFF,t=50"` | `--output-mode download --output-path $WORKSPACE_OUTPUT/watermarked.jpg` | Output path is sufficient |
| Resize + format + blind watermark | `"resize:w=1200" "format:target=png" "blindwatermark-embed:content=YourMark,s=high"` | `--output-mode save --target-key output/marked.png` | Download to `$WORKSPACE_OUTPUT` |
| Video first N sec to GIF | `"video/animation:f=gif,t=5000"` | `--output-mode save --target-key output/anim.gif` | Only add w/h/fps when user specifies |
| Video transcode to MP4 | `"video/convert:f=mp4,vcodec=h264"` | `--output-mode save --target-key output/video.mp4` | Must specify `vcodec` when user says "transcode" (default h264). Without vcodec, only remux is performed. Use user-specified codec if provided |
| Video slim (lqhd) | `"video/convert:f=mp4,vcodec=h264,videoslim=1"` | `--output-mode save --target-key output/video_slim.mp4` | `videoslim` requires `vcodec` (default h264) or it is silently ignored |
| Video compress / reduce bitrate | `"video/convert:f=mp4,vcodec=h264,vb=2000000"` | `--output-mode save --target-key output/video_vbr.mp4` | `vb` requires `vcodec` (default h264) or it is silently ignored |
| Audio WAV to AAC | `"audio/convert:f=aac"` | `--output-mode save --target-key output/audio.aac` | Only add ar/ac/ab when user specifies |
| Local file upload + resize | `"resize:w=600,h=600" "format:target=jpg"` | `--uri /path/to/file --output-mode download --output-path $WORKSPACE_OUTPUT/resized.jpg` | Output path is sufficient |
| Multi-frame snapshot (every 1s) | `"video/snapshots:f=jpg,inter=1000"` | `--output-mode save --target-key output/frames/frame --output-path $WORKSPACE_OUTPUT/` | Single command auto-submits + polls + downloads all frames. Never use snapshot loop instead. target-key must NOT have file extension |
| Face detection | `"faces"` | | Returns JSON; use alone, no chaining |
| Video sprite (5x5 sheet) | `"video/sprite:f=jpg,sw=160,sh=120,tw=5,th=5,num=25"` | `--output-mode save --target-key output/sprite.jpg` | `num=tw*th` ensures enough frames to fill grid. Missing num/inter causes black cells |
| Video single frame at 5s | `"video/snapshot:t=5000,f=jpg"` | `--output-mode download --output-path $WORKSPACE_OUTPUT/frame.jpg` | Keep original size (omit w/h). Output path is sufficient |
| Video concat | `"video/concat:f=mp4,vcodec=h264,acodec=aac/sur,o_<base64_key>,ss_0,t_<ms>"` | `--output-mode save --target-key output/concatenated.mp4` | Main video via `--source`, append via `/sur,o_<base64>`. Must validate input params (resolution, framerate, codec) match. Output duration should ≈ sum of inputs |
| HLS playlist | `"hls/m3u8:ss=0,t=10000"` | `--output-mode url` | Must use url mode. Never download/save. Returns signed URL for browser/player |

> ⚠️ **Parameters in recipes are examples, NOT defaults.** Only pass parameters the user explicitly requests. OSS uses official defaults for unspecified parameters.

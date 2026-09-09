# Stream Quality Troubleshooting Guide

Interpretation guide for the JSON output of `scripts/live_quality.py` and
`scripts/live_node.py`. All recommendations below are publisher-side or
console-side manual guidance — this skill never applies them automatically.

## 1. Live streaming protocols

### 1.1 RTMP (Real-Time Messaging Protocol)

- TCP-based, default port 1935
- Latency: 1-3 seconds
- Ingest hard requirements: video codec H.264, audio codec AAC
- HEVC/H.265 ingest is NOT supported over RTMP
- Prefer CBR bitrate control; VBR peak spikes cause buffering

### 1.2 SRT (Secure Reliable Transport)

- UDT-based, default port 8080
- Latency: 0.5-2 seconds
- Encrypted transport with ARQ packet-loss recovery, tolerant of weak networks
- Best for long-distance ingest over the public internet

### 1.3 WebRTC

- UDP-based, latency below 1 second
- First choice for interactive live streaming; NAT traversal is complex
- Requires STUN/TURN servers

### 1.4 HLS (HTTP Live Streaming)

- HTTP segment-based; latency 5-30 seconds (standard HLS), 2-4 seconds with LL-HLS
- Most CDN-friendly; best playback compatibility

### 1.5 HTTP-FLV

- HTTP long-connection based; latency 1-3 seconds
- Browsers need flv.js for playback; the most common playback protocol for live platforms

## 2. Quality issues and how to read them

### 2.1 Ingest (push stream) failures

| Symptom | Likely cause | What to check |
|---------|--------------|---------------|
| Connection refused | Wrong ingest URL / auth failure | URL format; whether the `auth_key` has expired |
| Connected but no picture | Video codec is not H.264 | `video_codec` field in the encoding check |
| Stream drops | Unstable network / bitrate too high | Lower the bitrate; check network jitter |
| Missing audio | Audio codec is not AAC | RTMP requires AAC; transcode with `ffmpeg -c:a aac` |
| Green screen | Lost keyframes / corrupted reference frames | Check the GOP setting; keep a sane keyframe interval |

### 2.2 High latency

| Factor | Impact | Fix (publisher side) |
|--------|--------|----------------------|
| B-frames | Adds encoding + decoding latency | `-bf 0 -tune zerolatency` (flagged `critical` by the script) |
| GOP too large | Long wait for the first frame | `-g 50 -keyint_min 50` |
| Slow encoder preset | High encoding latency | Use `veryfast` or `ultrafast` |
| Player buffer | Oversized buffer | Reduce player buffer below 1s |
| Protocol choice | RTMP ~2s, HLS ~10s+ | Consider WebRTC/SRT/LL-HLS |
| VBR peaks | Buffering at peaks | Use CBR or VBV limits for live |

### 2.3 Picture problems

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Pixelation / mosaic | Bitrate too low / packet loss | Raise the bitrate, or use SRT |
| Stuttering | Unstable framerate / network jitter | Constant framerate (CFR) + CBR |
| Tearing | VFR encoding | `-vsync cfr` (flagged as unstable framerate by the script) |
| Green screen | Lost keyframes | Check GOP settings |
| Blurry | Bitrate too low | Raise the video bitrate |
| Black screen | Codec incompatibility / stream not ready | Check codec format; confirm ingest is established |

### 2.4 Audio problems

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| No audio | RTMP requires AAC | `ffmpeg -c:a aac -ar 44100 -b:a 128k` |
| Audio-video out of sync | PTS/DTS offset | `ffmpeg -fflags +genpts -avoid_negative_ts make_zero` (the script flags PTS offsets > 200ms) |
| Noise / clipping | Abnormal sample rate / level too high | Normalize sample rate to 44100/48000; apply audio filters |
| AAC-HE incompatibility | Some low-end devices fail to decode | Downgrade to AAC-LC: `-profile:a aac_low` (flagged `warning` by the script) |

### 2.5 Script severity semantics

- `critical` — the stream violates a live-streaming hard requirement (e.g. B-frames, HEVC over RTMP, non-AAC audio, no video track); fix before anything else.
- `warning` — works but degrades experience (unstable framerate, low fps, long keyframe interval, PTS drift, duration mismatch).
- `info` — suggestion-level (keyframe interval between 2s and 4s).
- `overall_status`: `healthy` / `warning` / `critical` / `unreachable`.

## 3. CDN node analysis

### 3.1 Live CDN architecture

```
publisher -> origin (center) -> center nodes -> edge nodes -> viewers
```

### 3.2 Common node problems

| Problem | Symptom | Investigation direction |
|---------|---------|--------------------------|
| Pull fails in one region | Viewers in a specific area see a black screen | Check edge-node coverage for that region |
| Origin fetch failure | Widespread pull failures | Check origin reachability and center-node status |
| High node latency | Pull latency far above expectation | Probe each node's RTT and locate the slow node |
| Node cache anomaly | Stale content / pixelated playback | Purge CDN cache; check the origin fetch path |

### 3.3 How `live_node.py` probes

1. DNS resolution discovers edge-node IPs for the domain.
2. Each IP is probed with ICMP ping (latency + loss) and a TCP connect on the stream port (1935 for RTMP).
3. Node status: `error` when TCP is unreachable, `warning` when packet loss exceeds 50%, otherwise `healthy`.
4. With `--trace-origin`, traceroute maps the path and the inferred push domain is probed.
5. The `summary` block gives total/healthy/warning counts and average latency — quote it verbatim when reporting.

## 4. Recommended encoding parameters

### Standard live ingest (H.264 + AAC over RTMP)

```bash
ffmpeg -i input \
  -c:v libx264 -preset veryfast -tune zerolatency -bf 0 \
  -g 50 -keyint_min 50 \
  -b:v 2500k -maxrate 3000k -bufsize 5000k \
  -c:a aac -ar 44100 -b:a 128k \
  -f flv rtmp://push.example.com/app/stream
```

### Ultra-low-latency ingest (SRT)

```bash
ffmpeg -i input \
  -c:v libx264 -preset ultrafast -tune zerolatency -bf 0 -g 30 \
  -c:a aac -f mpegts "srt://srt.example.com:8080?streamid=app/stream"
```

### Common fix commands (mirror of the script recommendations)

| Problem | Fix command |
|---------|-------------|
| B-frames in a live stream | `ffmpeg -i input -c:v libx264 -preset veryfast -tune zerolatency -bf 0 -g 50 -f flv rtmp://...` |
| Non-AAC audio | `ffmpeg -i input -c:v copy -c:a aac -ar 44100 -b:a 128k -f flv rtmp://...` |
| GOP too large | `ffmpeg -i input -c:v libx264 -g 50 -keyint_min 50 -f flv rtmp://...` |
| Audio-video out of sync | `ffmpeg -i input -c copy -fflags +genpts -avoid_negative_ts make_zero output.mp4` |

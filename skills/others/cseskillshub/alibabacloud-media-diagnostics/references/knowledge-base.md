# Media Diagnostics Knowledge Base

Common root causes, investigation steps, and repair commands for media playback and streaming problems. Entries are grouped by module; refer to them when a triage symptom needs root-cause explanation or repair guidance.

---

## 1. Container Structure Problems

### 1.1 moov atom at the end of the file (not faststart)

**Symptom**: Online playback waits for the whole file to download before starting; the progress bar cannot be dragged.

**Root cause**: The MP4 `moov` box holds all frame index tables (stts/stss/stsc/stsz/stco). The player must parse `moov` before playback. If `moov` sits after `mdat` (at the end of the file), the player must request the whole file or issue a Range request to the tail to fetch it.

**Severity**: High - severely degrades online playback experience.

**Investigation**:
- Script check: parse the ISO BMFF box structure and compare `moov` / `mdat` offsets (done automatically by `media_analyze.py` for local MP4/MOV files).
- ffprobe heuristic: if `format.tags.compatible_brands` lacks `isml` and the file is large, `moov` is likely at the end.
- Tools: `mp4dump`, `AtomicParsley --textdata`.

**Fix**:
```bash
ffmpeg -i input.mp4 -c copy -movflags +faststart output.mp4
```

**Note**: faststart moves the entire `moov` to the beginning. For very long videos (>4h) the `moov` may become oversized (>50MB); consider fMP4/CMAF instead.

---

### 1.2 FLV missing keyframe index

**Symptom**: An FLV file cannot be seeked; it only plays from the beginning.

**Root cause**: FLV seeking relies on the `keyframes` array inside `onMetaData` (timestamp-to-offset mapping). Some recorders never write this data.

**Severity**: High.

**Investigation**:
```bash
ffprobe -show_format input.flv | grep -i keyframe
```
Alternatively parse the FLV header Script Tag directly.

**Fix**:
```bash
ffmpeg -i input.flv -c copy -flvflags add_keyframe_index output.flv
# or use yamdi
yamdi -i input.flv -o output.flv
```

---

### 1.3 MP4 ftyp box anomalies

**Symptom**: Some players/platforms refuse to recognize or process the MP4 file.

**Root cause**: The `ftyp` box declares the file brand and compatible brand list. If `major_brand` or `compatible_brands` lacks the brand the target platform requires, the file may be rejected.

**Severity**: Low.

**Common major_brand values**:
- `isom` - ISO Base Media File Format
- `mp41`/`mp42` - MP4 v1/v2
- `M4V ` - iTunes Video
- `dash` - DASH

---

## 2. Codec Compatibility Problems

### 2.1 H.265/HEVC web compatibility

**Symptom**: Chrome/Firefox cannot play the video and report an unsupported format; Safari/iOS plays it fine.

**Root cause**:
- Chrome/Firefox do not support HEVC by default (patent costs).
- Windows Chrome (108+) can hardware-decode HEVC only with the HEVC video extension installed.
- Android WebView support depends on device hardware.

**Severity**: High - affects a large share of web users.

**Investigation**:
```bash
ffprobe -v quiet -show_streams -select_streams v input | grep codec_name
# Output "hevc" confirms the problem
```

**Fix**:
```bash
# Transcode to H.264 (best compatibility)
ffmpeg -i input.mp4 -c:v libx264 -preset medium -crf 23 -c:a copy output.mp4

# 2-pass if quality must be preserved
ffmpeg -i input.mp4 -c:v libx264 -b:v 5M -pass 1 -f null /dev/null
ffmpeg -i input.mp4 -c:v libx264 -b:v 5M -pass 2 -c:a copy output.mp4
```

---

### 2.2 AAC-HE / HEv2 profile compatibility

**Symptom**: Low-end Android phones or older iOS devices fail to play audio or play silence.

**Root cause**: HE-AAC (SBR) and HE-AAC v2 (SBR+PS) use spectral band replication and parametric stereo; decoding is more complex than AAC-LC and some older chips do not support it.

**Severity**: Medium.

**Investigation**:
```bash
ffprobe -v quiet -show_streams -select_streams a input | grep profile
# Output "HE-AAC" or "HE-AACv2" confirms the problem
```

**Fix**:
```bash
ffmpeg -i input.mp4 -c:v copy -c:a aac -profile:a aac_low -b:a 128k output.mp4
```

---

### 2.3 High 10 Profile (10-bit)

**Symptom**: Mobile playback stutters, the device overheats, or the screen stays black.

**Root cause**: 10-bit color depth (yuv420p10le/yuv422p10le) cannot be hardware-decoded on most mobile devices; software decoding overloads the CPU.

**Severity**: Medium.

**Investigation**:
```bash
ffprobe -v quiet -show_streams -select_streams v input | grep -E "profile|pix_fmt"
# profile = High 10 and pix_fmt contains 10le/10be
```

**Fix**:
```bash
ffmpeg -i input.mp4 -c:v libx264 -pix_fmt yuv420p -c:a copy output.mp4
```

---

## 3. HLS / TS Problems

### 3.1 TS continuity counter discontinuity

**Symptom**: Glitching, mosaic, or green color blocks during playback.

**Root cause**: Each PID in a TS stream must carry a continuously incrementing 4-bit counter (0-15 wrap). A discontinuity means packet loss; the decoder lacks reference data and glitches.

**Common causes**:
- CDN origin-fetch or cache anomalies truncating segments
- Network jitter causing packet loss during live ingest
- Segmenter bugs
- Frames dropped during original recording

**Severity**: High.

**Investigation**: Run `media_analyze.py` on the local TS file; the TS continuity check reports per-PID counter errors.

**Fix**: Re-segment from the source file.

---

### 3.2 Incomplete TS segment (PES truncation)

**Symptom**: Playback stutters, skips frames, or aborts at a specific segment.

**Root cause**: A TS segment whose size is not a multiple of 188 bytes has an incomplete final TS packet. Typical causes:
- File truncated during upload/transfer
- CDN cache anomaly
- Segmenter process killed unexpectedly

**Severity**: High.

**Investigation**:
```bash
# Check whether the file size is a multiple of 188
SIZE=$(stat -f%z segment.ts)  # macOS
echo "$SIZE % 188" | bc
# Non-zero means truncation risk
```

---

### 3.3 Missing PAT/PMT tables

**Symptom**: The player cannot recognize the audio/video programs inside the TS stream and reports "cannot play".

**Root cause**: PAT (PID 0x0000) and PMT are the program mapping tables of a TS stream; the player finds the audio/video PIDs via PAT->PMT. The first segment must contain PAT/PMT.

**Severity**: High.

**Fix**: Ensure every TS segment header contains PAT/PMT:
```bash
ffmpeg -i input -c copy -f hls -hls_time 10 -hls_flags split_by_time output.m3u8
```

---

### 3.4 HLS segment unreachable

**Symptom**: HLS playback interrupts repeatedly; the player reports segment download errors (HTTP 403/404 or connection failures) while the m3u8 playlist itself loads fine.

**Root cause**: Individual segment requests fail at the CDN layer. Typical causes:
- Origin fetch failure: the segment file is missing on the origin or the origin is unreachable from the CDN edge
- Expired URL authentication: the signed segment URL (or the auth query parameters) has passed its validity window, so the CDN rejects it with 403
- Stale playlist: the playlist still references segments that have been deleted or re-segmented on the origin

**Severity**: High - interrupts playback whenever a bad segment is reached.

**Investigation**:
- Run `hls_check.py` against the m3u8 URL: it sample-checks segment reachability with HTTP HEAD and reports the per-segment status code and error.
- Compare the HEAD status codes: 403 suggests expired authentication (check the signature/expiration parameters in the segment URL); 404 suggests a missing origin object; connection errors suggest an origin/edge reachability problem.
- Check the URL signature validity window against the time the playback started.

**Fix**: Regenerate fresh signed URLs (or extend the authentication validity window), and verify on the origin/CDN console that the referenced segment objects actually exist.

---

### 3.5 Duplicated segments / frames after a live-recording reconnect (CDN reconnect replay)

**Symptom**: Recorded live playback shows repeated frames or visibly duplicated segments at specific points; the recorded timeline is longer than the real event.

**Root cause**: When the ingest connection drops and the recorder (or CDN edge) reconnects, both ends may replay a short GOP/segment window to keep the stream continuous. The overlapping window is written twice into the recording, producing duplicated frames and duplicated TS segments. This is a content-level problem: the container and each individual segment are structurally valid, so triage cannot auto-detect it.

**Severity**: Medium.

**Investigation**:
- Manual, content-level comparison is required: compute the hash of consecutive segments and compare timestamps — identical hashes or overlapping timestamp ranges mark the duplicated window:
```bash
for f in seg*.ts; do echo "$f $(md5 -q "$f")"; done
ffprobe -v quiet -show_entries format=start_time,duration -of csv "$f"
```
- Cross-check the recording logs for reconnect events around the duplicated timestamps.

**Fix**: De-duplicate the recording by cutting out the replayed window, then re-segment:
```bash
ffmpeg -i recording.ts -ss <dup_start> -to <dup_end> -c copy -f segment -segment_time 10 clean_%03d.ts
```
Preventively, align the reconnect replay window between ingest and recorder, or enable de-duplication in the recording pipeline.

---

## 4. Bitrate / Frame Rate Problems

### 4.1 Bitrate spikes

**Symptom**: Buffering and stuttering during playback, especially at scene changes with complex content.

**Root cause**: With VBR encoding, peak bitrate can far exceed the average. When a peak interval exceeds what the player buffer has preloaded, playback stalls.

**Threshold**: peak/average > 3x is considered abnormal.

**Severity**: Medium.

**Fix**:
```bash
# Use VBV (Video Buffering Verifier) to bound bitrate variation
ffmpeg -i input -c:v libx264 -b:v 2M -maxrate 4M -bufsize 4M output.mp4
```

---

### 4.2 Variable frame rate (VFR)

**Symptom**: Audio and video drift out of sync over time, or mismatch only in specific intervals.

**Root cause**: Screen recorders and phone cameras often produce VFR video. Players render at fixed frame intervals; the accumulated error causes desync.

**Severity**: Medium.

**Investigation**:
```bash
ffprobe -v quiet -show_streams -select_streams v input | grep -E "r_frame_rate|avg_frame_rate"
# A difference >10% indicates VFR
```

**Fix**:
```bash
ffmpeg -i input -c:v libx264 -r 30 -vsync cfr -c:a copy output.mp4
```

---

### 4.3 Non-monotonic DTS

**Symptom**: Frame skipping, flickering, or picture corruption after seeking.

**Root cause**: DTS (Decode Time Stamp) must be strictly monotonically increasing. Regressions usually come from:
- Timestamps not reset when concatenating multiple clips
- Timestamp jumps after live recording interruption and reconnect
- Encoder bugs

**Severity**: High.

**Fix**:
```bash
# Regenerate timestamps
ffmpeg -i input -c copy -fflags +genpts -avoid_negative_ts make_zero output.mp4
```

---

### 4.4 Audio/video duration mismatch

**Symptom**: Audio keeps playing after the video ends, or the picture freezes while audio has already ended.

**Root cause**: The encoded durations of the audio and video tracks differ, e.g.:
- Audio/video devices started or stopped at different times during recording
- Editor exported tracks without alignment
- Container-level duration fields inconsistent

**Threshold**: a difference > 0.5s is considered abnormal.

**Severity**: High.

**Fix**:
```bash
# Trim to the shorter track
ffmpeg -i input -c copy -shortest output.mp4
```

---

## 5. Live Stream Latency Factors

### 5.1 B-frames in a live stream

**Symptom**: High end-to-end latency and slow first frame.

**Root cause**: B-frames require future reference frames, adding encoding and decoding delay proportional to the B-frame count. Live streaming has zero tolerance for B-frames.

**Severity**: High.

**Fix**:
```bash
ffmpeg -i input -c:v libx264 -preset veryfast -tune zerolatency -bf 0 -g 50 -f flv rtmp://...
```

### 5.2 Non-AAC audio over RTMP/FLV

**Symptom**: Push failure or audio errors at ingest.

**Root cause**: The RTMP/FLV protocol only carries AAC audio. Other codecs (e.g. MP3-only setups, Opus) are rejected or misparsed by many ingest endpoints.

**Severity**: High.

**Fix**:
```bash
ffmpeg -i input -c:v copy -c:a aac -ar 44100 -b:a 128k -f flv rtmp://...
```

### 5.3 Oversized GOP / keyframe interval

**Symptom**: Long first-frame wait and slow stream/ABR switching.

**Root cause**: A keyframe interval above 4 seconds forces players to wait for the next keyframe before rendering. 1-2 seconds (GOP = fps x 1~2) is recommended for live streaming.

**Severity**: Medium.

**Fix**:
```bash
# Assuming 25fps, a 2-second GOP
ffmpeg -i input -c:v libx264 -g 50 -keyint_min 50 -f flv rtmp://...
```

---

## Repair Command Quick Reference

| Problem | Repair command |
|---------|----------------|
| moov at the end | `ffmpeg -i input.mp4 -c copy -movflags +faststart output.mp4` |
| H.265 compatibility | `ffmpeg -i input -c:v libx264 -preset medium -crf 23 output.mp4` |
| Corrupted TS segments | `ffmpeg -i input -c copy -f hls -hls_time 10 -hls_list_size 0 output.m3u8` |
| FLV without keyframe index | `ffmpeg -i input.flv -c copy -flvflags add_keyframe_index output.flv` |
| Unstable VFR | `ffmpeg -i input -c:v libx264 -r 30 -vsync cfr output.mp4` |
| Audio/video duration mismatch | `ffmpeg -i input -c copy -shortest output.mp4` |
| Live B-frames | `ffmpeg -i input -c:v libx264 -preset veryfast -tune zerolatency -bf 0 -g 50 -f flv rtmp://...` |
| Live non-AAC audio | `ffmpeg -i input -c:v copy -c:a aac -ar 44100 -b:a 128k -f flv rtmp://...` |
| Oversized live GOP | `ffmpeg -i input -c:v libx264 -g 50 -keyint_min 50 -f flv rtmp://...` |
| Non-monotonic DTS | `ffmpeg -i input -c copy -fflags +genpts -avoid_negative_ts make_zero output.mp4` |

---

## References

- ApsaraVideo VOD documentation: https://help.aliyun.com/zh/vod/
- ApsaraVideo Live documentation: https://help.aliyun.com/zh/live/

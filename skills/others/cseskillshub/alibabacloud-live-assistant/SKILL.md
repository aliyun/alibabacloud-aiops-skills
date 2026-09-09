---
name: alibabacloud-live-assistant
description: |
  Read-only diagnostics for Alibaba Cloud Live: stream quality checks
  (codecs, bitrate, GOP, B-frames, A/V sync), CDN edge-node probing, local
  recording/snapshot, traffic-theft analysis on abused live domains, and
  signed push/pull test URL generation; never changes any configuration.
  Use when the user reports live stream stuttering, pixelation or latency,
  push/pull stream failures, audio-video out of sync, wants to probe live
  CDN nodes or record a stream, suspects live traffic theft or anomalous
  billing, needs a URL authentication check, or asks for push/pull test URLs.
  Triggers: "live stream stuttering", "live stream pixelation",
  "live stream latency", "push stream failed", "pull stream failed",
  "audio video out of sync", "live CDN node check", "live traffic theft",
  "anomalous live billing", "live URL authentication check",
  "live stream recording", "generate push stream URL",
  "generate pull stream URL".
---

# Alibaba Cloud Live Assistant

Diagnose and troubleshoot Alibaba Cloud Live (ApsaraVideo Live) problems: "my live stream is stuttering / pixelated", "push stream failed", "audio and video are out of sync", "is someone abusing my live domain and driving up the bill", "generate push/pull test URLs for my live domain", "record a few seconds of the live stream to check".

Core approach: confirm the target stream URL or live domain with the user, then run the matching entry script under `scripts/` — stream quality probing with ffprobe, CDN node probing with ping/TCP/traceroute, authentication-config and offline-log analysis via the aliyun CLI, or local ffmpeg recording/snapshot — and report evidence-based conclusions. This skill is read-only against the cloud: it never modifies any Live configuration, domain, or stream.

## Absolute Rules

1. **ABSOLUTE PROHIBITION (read-only cloud enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating Live API — e.g. `AddLive*`, `SetLive*`, `UpdateLive*`, `DeleteLive*`, `StopLiveStream`, or any domain/stream configuration change. This includes scripts "for the user to run manually". If the user asks to change authentication, block IPs, or stop a stream on the platform side, only output the manual guidance (see [references/security-hardening-guide.md](references/security-hardening-guide.md)) and declare this skill is read-only.
2. **ABSOLUTE PROHIBITION (credential handling):** Never read, print, or pass AK/SK/STS tokens explicitly. Credentials are resolved automatically by the aliyun CLI default credential chain. Never accept AK/SK from the user or from another script. Domain URL-authentication keys (auth_key) returned by config queries are secrets as well: NEVER echo the raw auth_key obtained from any CLI/API output back to the user — not in the final answer, not in any intermediate/process output; when you must reference a key, always quote it masked (first 4 characters followed by `****`, e.g. `vqEf****`). Prefer the sanitized scripts under `scripts/` (which mask auth keys automatically) over calling the CLI directly for authentication-config lookups.
3. **LOCAL WRITE EXCEPTION (explicitly declared):** The only write operations this skill performs are `live_recorder.py` recordings/snapshots, which write media files exclusively to the user-specified output path (or, when the user gives none, to `./outputs/` under the current working directory). No other file, directory, or system state is ever modified.
4. **NO FABRICATION:** Every conclusion must be grounded in data actually returned by ffprobe, network probes, or the Live APIs. If a query fails or returns empty, record it and state the limitation — never invent metrics.
5. **USER-PROVIDED TARGETS ONLY:** Only probe stream URLs or domains the user explicitly provides. Never scan, sweep, or guess domains.
6. **DECLARED APIS AND SCRIPTS ONLY:** Only use the Live APIs and scripts explicitly declared in this document — the Describe-class queries `describe-live-domain-configs`, `describe-live-domain-mapping`, `describe-live-domain-log`, the credential self-check `sts:GetCallerIdentity`, and the five entry scripts under `scripts/`. Never probe, enumerate, or call any other Live API (e.g. `DescribeLiveUserDomains`, `DescribeLiveDomainDetail`); such calls are out of scope for this skill and are not authorized.

## User Confirmation

- Before running any diagnosis, confirm the target with the user: a stream URL for quality/node/recording tasks, or a live domain (ingest or playback) for authentication/traffic-theft/URL-generation tasks.
- If the user has not provided the target, ask for it first. Never guess, derive, or scan for domains or stream URLs on your own.
- Before starting a recording or snapshot, confirm the output path and duration with the user; prefer `--dry-run` to preview the ffmpeg command when the user is unsure.

## Execution Principle

MANDATORY:

- **Single entry points**: all diagnosis MUST be executed through the scripts under `scripts/` listed in Commands. Do not hand-assemble alternative command chains, and do not freestyle ffprobe/aliyun CLI variants that bypass these scripts.
- **Read-only cloud access**: the scripts only call Describe-class Live APIs; the only other call is the agent-level credential self-check `sts:GetCallerIdentity`.
- **Interpret, then advise**: after each script run, interpret the JSON output using [references/stream-quality-troubleshooting.md](references/stream-quality-troubleshooting.md) (quality/node results) or [references/security-hardening-guide.md](references/security-hardening-guide.md) (security results), and give evidence-based suggestions as manual guidance only.

## Credentials

Credentials are resolved automatically by the aliyun CLI default credential chain (configured via `aliyun configure`, environment variables, or `~/.aliyun/config.json`). This skill never asks for, reads, prints, or passes AK/SK/STS tokens.

```bash
# Optional self-check: verify that the CLI credential chain works
aliyun sts get-caller-identity
```

**Identity verification failure**: if `aliyun sts get-caller-identity` fails, the default credential chain is not configured. Guide the user to run `aliyun configure` — never ask for AK/SK. Note that only `live_stream_url_generator.py` and `live_theft_handler.py` call the cloud APIs; the other three scripts are purely local (ffprobe/ping/ffmpeg) and need no credentials.

## Observability

All OpenAPI calls (invoked through the aliyun CLI) include:

- **User-Agent**: `--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`
- **SKILL_NAME**: `alibabacloud-live-assistant`
- **session-id**: a 32-character hex string generated once per session (one `uuid.uuid4().hex` per script run) and attached to every CLI command in the same run.

The cloud-calling scripts implement this automatically: `_SESSION_ID = uuid.uuid4().hex` and `_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-live-assistant/{_SESSION_ID}"` are appended as the `--user-agent` argument of every `aliyun` invocation.

## Prerequisites

1. **aliyun CLI 3.x with the `aliyun-cli-live` plugin** — required for the two cloud-calling scripts; all Live queries use plugin mode (e.g. `aliyun live describe-live-domain-configs`, `aliyun live describe-live-domain-mapping`, `aliyun live describe-live-domain-log`). No direct HTTP signing, no external Python SDK.
2. **Python 3.9+** — standard library only, no third-party dependencies.
3. **ffmpeg / ffprobe** — required by `live_quality.py` (stream probing) and `live_recorder.py` (recording/snapshot).
4. **curl / dig** — HTTP probing and DNS inspection; `live_node.py` additionally uses `ping` and `traceroute`.
5. **Alibaba Cloud credentials** — resolved automatically by the CLI default credential chain; never handle AK/SK explicitly (see Credentials).

## Commands

Set the skill directory once, then run the matching entry script:

```bash
SKILL_DIR=~/.qoderwork/skills/alibabacloud-live-assistant
```

### C1 — Stream quality diagnosis

```bash
cd $SKILL_DIR && python3 scripts/live_quality.py <STREAM_URL> [--quick]
```

Checks connectivity, codecs (H.264/AAC, B-frames, HEVC-over-RTMP), bitrate/framerate, GOP/keyframe interval, and audio-video sync; outputs JSON with issues and fix recommendations. `--quick` runs connectivity + codec only.

### C2 — CDN node analysis

```bash
cd $SKILL_DIR && python3 scripts/live_node.py <STREAM_URL_OR_DOMAIN> [--trace-origin] [--verbose]
```

DNS-resolves the live domain, probes each edge node with ICMP ping and TCP connect (port 1935 for RTMP), and summarizes node health and average latency. `--trace-origin` adds traceroute plus an inferred push-domain probe; `--verbose` adds per-node region info.

### C3 — Recording & snapshot

```bash
cd $SKILL_DIR && python3 scripts/live_recorder.py record --url <STREAM_URL> [--output <PATH>] [--duration <SECONDS>] [--format mp4|flv|hls|ts] [--dry-run]
cd $SKILL_DIR && python3 scripts/live_recorder.py snapshot --url <STREAM_URL> [--output <PATH>] [--dry-run]
cd $SKILL_DIR && python3 scripts/live_recorder.py stop --recording-id <PID_OR_PIDFILE>
cd $SKILL_DIR && python3 scripts/live_recorder.py stop --all
```

Records the stream locally (MP4/FLV/HLS/TS, duration-limited or until Ctrl+C) or captures a single frame. `--dry-run` previews the ffmpeg command without executing. Output is written only to the specified path (default: `./outputs/` under the working directory). For `stop`, a numeric `--recording-id` must match a PID recorded by this tool (arbitrary PIDs are never signaled); `--all` stops every active recording.

### C4 — Domain security analysis (traffic theft)

```bash
cd $SKILL_DIR && python3 scripts/live_theft_handler.py analyze --domain <LIVE_DOMAIN> --start-time 2026-06-24T08:00:00Z --end-time 2026-06-24T20:00:00Z
cd $SKILL_DIR && python3 scripts/live_theft_handler.py guide
cd $SKILL_DIR && python3 scripts/live_theft_handler.py step <1-4>
cd $SKILL_DIR && python3 scripts/live_theft_handler.py checklist
```

`analyze` queries the URL-authentication config (`describe-live-domain-configs`, function `aliauth`), downloads offline access logs for the window (`describe-live-domain-log`), computes Top IP/URL/Referer/UA statistics and anomaly features, and emits a standardized abuse report.

`guide`, `step`, and `checklist` print the full 4-step handling SOP, per-step guidance, and the handling checklist respectively — use them when the user wants to follow the process manually.

### C5 — Push/pull test URL generation

```bash
cd $SKILL_DIR && python3 scripts/live_stream_url_generator.py generate --domain <LIVE_DOMAIN> [--app-name live] [--stream-name <NAME>] [--expire-seconds 3600]
```

Resolves the ingest/playback domain pair (`describe-live-domain-mapping`), reads each domain's `aliauth` config (`describe-live-domain-configs`), and generates signed RTMP/RTS ingest URLs plus RTMP/FLV/M3U8/RTS playback URLs (Type-A `auth_key` when authentication is enabled). Default stream name is `MMDD_test`.

## Capabilities

| # | Capability | Description |
|---|-----------|-------------|
| C1 | Stream quality diagnosis | Connectivity, codec/B-frame/HEVC checks, bitrate/framerate, GOP, audio-video sync, with fix recommendations (`live_quality.py`) |
| C2 | CDN node analysis | DNS discovery of edge nodes, ICMP/TCP latency probing, health summary, optional origin tracing (`live_node.py`) |
| C3 | Recording & snapshot | Local MP4/FLV/HLS/TS recording and single-frame snapshot of a user-specified stream, written only to the user-specified path (`live_recorder.py`) |
| C4 | Domain security analysis (traffic theft) | URL-authentication status check + offline-log Top-N forensics + standardized abuse report and 4-step SOP (`live_theft_handler.py`) |
| C5 | Push/pull test URL generation | Domain-mapping resolution + aliauth-aware signed ingest/playback test URLs (`live_stream_url_generator.py`) |

## Orchestration

This skill touches two Alibaba Cloud products plus local tooling: **ApsaraVideo Live** (Describe-class queries via the `aliyun-cli-live` plugin: `describe-live-domain-configs`, `describe-live-domain-mapping`, `describe-live-domain-log`), **STS** (the single credential self-check `sts:GetCallerIdentity`), and local `ffmpeg`/`ffprobe`/`ping`/`traceroute`/`curl`/`dig`.

Decision criteria — pick the entry by symptom, one entry per symptom, in this order of precedence:

1. Stream looks/feels broken (stuttering, pixelation, latency, A/V sync) with a playable stream URL → **C1** `live_quality.py` first; if quality metrics look normal or connectivity fails, escalate to **C2** `live_node.py` to isolate CDN edge/origin issues.
2. Push/pull failure or connectivity suspected at the network layer (DNS, TCP 1935, node health) → **C2** `live_node.py` (add `--trace-origin` for origin-path problems).
3. Need local evidence of the stream (record a few seconds / grab a frame) → **C3** `live_recorder.py`.
4. Traffic theft, anomalous billing, or URL-authentication concerns on a live domain → **C4** `live_theft_handler.py` (`analyze` runs the auth-config query and offline-log forensics in one pass; use `guide`/`step`/`checklist` for manual SOP guidance).
5. Signed push/pull test URLs needed → **C5** `live_stream_url_generator.py` (it resolves the domain mapping and aliauth config internally).

Call order inside a combined investigation: confirm the target with the user, run the symptom entry above, then interpret results against the matching reference doc; never chain entries speculatively.

**Error recovery order for API failures (MANDATORY):**

1. **Permission error (NoPermission / Forbidden):** MUST first run credential self-check (`aliyun sts get-caller-identity`), then immediately **switch to the equivalent skill script** (e.g. `scripts/live_theft_handler.py` for domain-config queries, `scripts/live_stream_url_generator.py` for domain-mapping queries) to perform the same query through the script's internal API path. This is classified as **auto_fix** — you MUST change the execution approach, not merely retry the same CLI command. Only if the script also fails, record the error and continue to the next query.
2. **Parameter error (InvalidParameter):** Fix the parameter (e.g. adjust time-window format, correct domain name) and retry. This is **auto_fix**.
3. **Throttling error (Throttling):** Wait ~3 seconds, then retry the same command. This is **retry**.
4. **Internal/System error (InternalError):** Wait ~3 seconds cooldown, then retry the same command. This is **retry**.
5. **Never stop the whole diagnosis on a single failed query** — record the error, recover, and continue.

**Domain-type ambiguity (IC scenarios):** When the user provides a root domain (e.g. `example.com`) without specifying whether it is a push (ingest) or pull (playback) domain, you MUST **explicitly state your assumption before running any analysis** — e.g. "I will assume this is a playback (pull) domain and proceed with analysis." Never defer the assumption to a post-hoc remark at the end of the report. Alternatively, ask the user to clarify the domain type before proceeding.

## Examples

**Example 1** — User: "My HLS playback keeps stuttering and looks pixelated, can you check the stream?"

```bash
cd $SKILL_DIR && python3 scripts/live_quality.py "https://pull.example.com/live/demo.m3u8"
cd $SKILL_DIR && python3 scripts/live_node.py pull.example.com --verbose
```

Interpret the issues list (bitrate, framerate stability, GOP, B-frames) per [references/stream-quality-troubleshooting.md](references/stream-quality-troubleshooting.md), then advise publisher-side encoder fixes as manual guidance.

**Example 2** — User: "My live bill jumped last week although we had no events; I suspect someone is abusing pull.example.com."

```bash
cd $SKILL_DIR && python3 scripts/live_theft_handler.py analyze \
  --domain pull.example.com \
  --start-time 2026-08-16T00:00:00Z --end-time 2026-08-17T00:00:00Z
```

Present the authentication status, Top IP/URL evidence, and hardening recommendations per [references/security-hardening-guide.md](references/security-hardening-guide.md). Never apply the hardening configuration from this skill.

**Example 3** — User: "Generate push and pull test URLs for push.example.com so I can verify my ingest setup."

```bash
cd $SKILL_DIR && python3 scripts/live_stream_url_generator.py generate \
  --domain push.example.com --app-name live --stream-name my_test --expire-seconds 7200
```

Show the generated ingest/playback URLs and their expiry; do not display the raw authentication key from the config output.

## Notes

- **Read-only operations**: only Describe-class Live queries and `sts:GetCallerIdentity`; the single local-write exception is recording/snapshot output declared in Absolute Rule 3.
- **RAM permissions**: grant only the exact actions in [references/ram-policies.md](references/ram-policies.md); no wildcards, no write actions.
- **Offline logs are delayed**: `describe-live-domain-log` provides logs only several hours after the fact; align the analysis window to fully past hours.
- **All script output is JSON** — parse it programmatically and summarize the `issues` / `features` / `summary` fields for the user.
- **Error handling**: cloud-calling scripts emit `{"status": "error", "error": ...}` JSON on failure (missing CLI/plugin, bad domain, no permission). On a permission error (NoPermission), MUST first run the credential self-check `aliyun sts get-caller-identity`, then **immediately switch to the equivalent skill script** (e.g. `scripts/live_theft_handler.py` for config queries) to perform the same query — this is **auto_fix** (change approach), NOT merely retrying the same CLI command. Only if the script also fails, report the error honestly and guide the user to install the `aliyun-cli-live` plugin or fix RAM permissions.
- **Quality interpretation**: codec/B-frame/GOP/latency thresholds and encoder fix commands are centralized in [references/stream-quality-troubleshooting.md](references/stream-quality-troubleshooting.md); keep advice consistent with it.
- **Recording is a foreground long-running process**: `live_recorder.py record` blocks until `--duration` elapses or the user presses Ctrl+C; prefer a bounded `--duration` for unattended checks.
- **Probing output is ticket-ready**: node and quality JSON contain raw latency/loss metrics that can be quoted verbatim when reporting to the user.

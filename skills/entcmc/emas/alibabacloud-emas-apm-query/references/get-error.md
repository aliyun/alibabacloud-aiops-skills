# `GetError` - sample detail

Aliyun CLI command: `aliyun emas-appmonitor get-error`
API version: `2019-06-11` · Action: `GetError` · Method: `POST` RPC

Fetches the **complete detail** of a sample via the "sample pointer" triple (`ClientTime` + `Uuid` + `Did`): base dimensions, exception description, backtrace, threads, business log, memory snapshot and more. This is the last link in the "error cluster -> APP source" pipeline.

## Parameters

| CLI flag | Required | Type | Description |
| --- | --- | --- | --- |
| `--app-key` | Yes | int64 | AppKey |
| `--client-time` | Yes | int64 | Sample client time (ms) - from `get-errors.Model.Items[*].ClientTime` |
| `--biz-module` | Recommended | string | One of the 6 enum values; *effectively required*, otherwise the backend has to scan multiple sub-tables |
| `--os` | Recommended | string | `android` / `iphoneos` / `harmony` / `h5`; *effectively required* |
| `--uuid` | No | string | Event unique id - from `get-errors.Model.Items[*].Uuid`. **Strongly recommended**, locks onto one specific crash |
| `--did` | No | string | Device id - from `get-errors.Model.Items[*].Did`. Helps with precise localization |
| `--digest-hash` | No | string | Owning Issue, used as an auxiliary filter |
| `--biz-force` | No | bool | `true` bypasses CDN / cache and forces origin fetch; **do not add** during normal troubleshooting |

**`--time-range` does not exist here**: `get-error` uses `ClientTime` to locate the specific sample, no time window needed.

## `--cli-dry-run` example

```bash
aliyun emas-appmonitor get-error \
  --app-key 12345678 \
  --os iphoneos \
  --biz-module crash \
  --client-time 1776415936000 \
  --uuid 330429fe-3fae-475e-91b0-a2b014845456 \
  --did 6963034097141070746 \
  --digest-hash 3JE6F43KCQ1SV \
  --cli-dry-run
```

## Response structure

`Model` is a single sample object with roughly **65 fields**, grouped by use case below.

### A. Base dimensions

| Field | Type | Description |
| --- | --- | --- |
| `AppKey` | int64 | Echo |
| `ClientTime` | int64 | Client time (ms) |
| `ServerTime` | int64 | Server ingestion time (ms) |
| `TriggeredTime` | int64 | Crash trigger time (present in some modules) |
| `SessionId` | string | Session id |
| `Uuid` | string | Event unique id |
| `Utdid` | string | UTDID (desensitized) |
| `AppVersion` | string | APP version |
| `Build` | string | Build number |
| `Os` | string | `iphoneos` / `android` / `harmony` |
| `OsVersion` | string | System version |
| `Brand` | string | Brand |
| `DeviceModel` | string | Device model |
| `Resolution` | string | Screen resolution |
| `Channel` | string | Distribution channel |
| `Language` | string | Language |
| `Country` / `Province` / `City` | string | Geography |
| `Carrier` / `Isp` / `Access` / `AccessSubType` | string | Carrier / network |
| `CpuModel` | string | CPU model |
| `ClientIp` | string | Client IP |
| `UserId` / `UserNick` | string | Business-side user |
| `Pid` | int | Process id |
| `ProcessName` / `ParentProcessName` | string | Process name |
| `InMainProcess` | int | Whether main process (`1`/`0`) |
| `ForeGround` / `ForceGround` | int | Whether foreground |
| `IsJailbroken` / `IsSimulator` / `IsSpeedVersion` | int | Device state flags |
| `SdkType` / `SdkVersion` | string | APM SDK type and version |

### B. Exception description

| Field | Type | Description |
| --- | --- | --- |
| `ExceptionType` | string | Exception type (iOS `EXC_BAD_ACCESS`; Android `java.lang.NullPointerException`) |
| `ExceptionSubtype` | string | Sub-type |
| `ExceptionCodes` | string | Signal / KERN code (iOS) |
| `ExceptionMsg` | string | Exception reason description |
| `ExceptionDetail` | string | Detailed message (may contain addresses) |
| `Summary` | string | Machine-generated summary |
| `Digest` | string | Stack digest (plaintext) |
| `DigestHash` | string | Owning Issue |
| `ReportType` | string | Internal report type (`MOTU_IOS_CRASH` / `MOTU_ANDROID_CRASH`, etc.) |
| `ReportContent` | string | Raw crash report (iOS raw before and after symbolication) |
| `LaunchedCrashStage` / `LaunchedTime` | int / int64 | Launch stage / launch duration (used to detect launch crash) |
| `LagCost` | int64 | lag duration (ms, lag only) |

### C. Stack & threads

| Field | Type | Description |
| --- | --- | --- |
| `Backtrace` | string | **Crash thread stack** (the main one to look at). Frames separated by newlines; iOS (post-symbolicated) looks like `0   apm_ios_demo   EAPMDemoTriggerStackOverflow(unsigned long)`, Android looks like `at com.example.Foo.bar(Foo.java:45)` |
| `ThreadName` | string | Crashing thread name |
| `Threads` | array<object> | All threads (crash / anr); each item has `ThreadId` / `ThreadName` / `Stack` / `IsMain` |
| `BinaryUuids` | string | UUID mapping for executable segments (used by iOS symbolication) |
| `SymbolicFileType` | string | Symbol file type |

### D. Business log & extensions

| Field | Type | Description |
| --- | --- | --- |
| `EventLog` | string | Event log (page navigation / lifecycle / breadcrumbs, in time order) |
| `MainLog` | string | Main thread log (e.g. tail of logcat) |
| `BusinessLogType` | string | Business log tag |
| `CustomInfo` | string | Developer-injected key-values |
| `AdditionalCustomInfo` | string | Extra custom info |
| `Controllers` | string | Page path (iOS VC stack / Android Activity stack) |
| `View` | string | Current view path |
| `RuntimeExtData` | string | Runtime extension data |
| `MoreInfo1` / `MoreInfo2` | string | Reserved business fields |

### E. Memory & IO (memory_* / crash OOM)

| Field | Type | Description |
| --- | --- | --- |
| `MemInfo` | string | Memory usage summary (available / peak / GC count) |
| `MemoryMap` | string | memory map (iOS / Android Native) |
| `FileDescriptor` | string | FD usage (commonly used for iOS OOM) |

## Usage flow (core of this Skill)

1. **Extract the stack**: `Model.Backtrace` is the key field. Print it first for a coarse judgment.
2. **Compare threads** (anr / deadlock): iterate `Model.Threads[]`, find the thread with `IsMain=true` plus other "lock-holding" threads.
3. **Triage by exception type**: the combination of `ExceptionType` + `ExceptionSubtype` + `ExceptionCodes` points to the root-cause family:
   - iOS `EXC_BAD_ACCESS / KERN_INVALID_ADDRESS` -> wild pointer / use-after-free
   - iOS `EXC_CRASH / SIGABRT` -> explicit `abort()`; read the message in `ExceptionDetail`
   - Android `java.lang.NullPointerException` + `ReportType=MOTU_ANDROID_CRASH` -> null dereference
4. **Timeline**: combine `EventLog` (event order) + `Controllers` (page path) + `TriggeredTime` to reconstruct what happened in the last N seconds before the crash.
5. **Code localization**: keep frames in `Backtrace` whose prefix is the APP bundle id / package name; grep by class + method + file name across the Cursor workspace.
6. **Emit the fix**: combine `ExceptionMsg` with the code context; propose a root-cause hypothesis + fix plan (both an immediate hotfix and a longer-term refactor).

## Key JMESPath expressions

```bash
# Stack + exception reason only (most common)
--cli-query "Model.{type:ExceptionType,subType:ExceptionSubtype,codes:ExceptionCodes,msg:ExceptionMsg,stack:Backtrace}"

# Event log + page path only
--cli-query "Model.{eventLog:EventLog,mainLog:MainLog,controllers:Controllers,custom:CustomInfo}"

# Multi-thread state (find blocking threads)
--cli-query "Model.Threads[*].{name:ThreadName,isMain:IsMain,stack:Stack}"

# Grab all base dimensions
--cli-query "Model.{appVer:AppVersion,osVer:OsVersion,brand:Brand,device:DeviceModel,net:Access,utdid:Utdid}"
```

## Common errors

| Symptom | Meaning | Action |
| --- | --- | --- |
| `Error: required flag ... not set` | Missing `--client-time` or `--app-key` | Fill in the required parameter |
| `Model=null`, `Success=true` | Sample cannot be found for this `ClientTime+Uuid` | Check whether `--biz-module` / `--os` match; sample may have passed cold retention |
| `Code: 200, Message: "unknown error"` | Backend error | Report with `RequestId`; in rare cases `--biz-force true` bypasses the cache |
| `Forbidden.NoRAMPermission` | Missing `emasha:ViewError` | See `ram-policies.md` |

## Response size & performance

- The `get-error` JSON response can be **hundreds of KB to several MB** (all threads + business logs); **do not truncate with `head` / `tail`**, it will corrupt the JSON.
- The right approach is to dump to disk and then process with `jq`:

```bash
aliyun emas-appmonitor get-error ... > /tmp/emas-error-$(date +%s).json
jq '.Model | {type:.ExceptionType,msg:.ExceptionMsg,stack:.Backtrace}' /tmp/emas-error-*.json
```

- **3~5 samples per Issue is enough** - the main question is whether the stack is stable and whether the exception path is concentrated.

## Tips

- **Always include `--uuid`**: it is the only field that uniquely pinpoints a specific crash; with only `ClientTime`, you can hit multiple samples sharing the same millisecond.
- **Do not batch / parallelize `get-error`**: the server has per-account QPS limits; `dig_issue.sh` already runs serially with sleep.
- **Android obfuscated stacks**: when you see class names like `a.a.a.b.c`, prompt the user for `mapping.txt`; otherwise `Backtrace` cannot be mapped to source.
- **iOS not symbolicated**: `Backtrace` full of hex addresses or image UUIDs (`C768F963-A0CC-3F5C-A1D3-...`) means the user must upload the dSYM for that version to the EMAS console and then pull the latest samples.

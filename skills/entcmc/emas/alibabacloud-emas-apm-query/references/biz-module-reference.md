# `biz-module` reference

`biz-module` is the top-level taxonomy of emas-appmonitor; it determines which sub-service the API calls, which tables are queried, and which fields are returned. This Skill supports the 6 values below:

| biz-module | Meaning | Scenario | Typical root causes |
| --- | --- | --- | --- |
| `crash` | Crash | Process terminates abnormally (iOS `EXC_*` / Android `java.lang.*Exception` / NDK signal) | null pointer, out-of-bounds, race condition, native memory corruption |
| `anr` | ANR | Android main thread blocked beyond timeout (system "Not Responding" dialog) | main-thread IO, lock contention, slow broadcast receivers |
| `lag` | Lag | Low FPS / main-thread execution over threshold without ANR | big-image decoding, over-layout, synchronous network calls, JSON parsing |
| `custom` | Custom business exception | Business errors reported via `reportError(errorCode, errorMsg, stack)` | business validation failure, unexpected API response, front-/back-end contract drift |
| `memory_leak` | Memory leak | Reference chains that SDK detected as non-releasable | static holding of Activity, singleton holding Context, unregistered listeners |
| `memory_alloc` | Memory allocation | Large one-off allocations / rapid bulk growth | Bitmap decode without inSampleSize, unbounded cache, loading big JSON at once |

## `biz-module` x platform x `filterCode` matrix

The table below is auto-summarized from `assets/system-filters/<biz-module>-<platform>.json`:

| biz_module | platform | Static-enum filterCodes | Dynamic filterCodes (consumer must supply values) |
| --- | --- | --- | --- |
| `anr` | `android` | `utdid`, `clientIp`, `userNick`, `userId`, `isForeground`, `isJailbroken`, `inMainProcess`, `digestHash`, `isSimulator`, `issueStatus` | `appVersion`, `build`, `firstVersion`, `osVersion`, `brand`, `deviceModel`, `channel`, `language`, `view`, `access`, `country`, `province`, `city`, `resolution`, `processName`, `carrier`, `cpuModel`, `tag`, `additionalCustomInfo` |
| `crash` | `android` | `crashType`, `isOom`, `shadow_launchedCrashDuration`, `utdid`, `clientIp`, `userNick`, `userId`, `isForeground`, `isJailbroken`, `inMainProcess`, `digestHash`, `isSimulator`, `issueStatus` | same as anr |
| `crash` | `iphoneos` | `componentType`, `crashType`, `shadow_launchedCrashDuration`, `utdid`, `clientIp`, `userNick`, `userId`, `isForeground`, `isJailbroken`, `inMainProcess`, `digestHash`, `issueStatus` | same as anr |
| `crash` | `harmony` | `crashType`, `utdid`, `clientIp`, `userNick`, `userId`, `isForeground`, `inMainProcess`, `digestHash`, `issueStatus` | `appVersion`, `build`, `firstVersion`, `osVersion`, `brand`, `deviceModel`, `channel`, `language`, `view`, `access`, `country`, `province`, `city`, `resolution`, `processName`, `carrier`, `cpuModel`, `tag` |
| `custom` | `android` | `customErrorLanguage`, `isCustomErrorFlag`, `utdid`, `clientIp`, `userNick`, `userId`, `isForeground`, `isJailbroken`, `inMainProcess`, `digestHash`, `isSimulator`, `issueStatus` | same as anr |
| `custom` | `iphoneos` | same as custom/android (minus `isSimulator`) | same as anr |
| `custom` | `harmony` | `utdid`, `clientIp`, `userNick`, `userId`, `isForeground`, `inMainProcess`, `digestHash`, `issueStatus` | same as crash/harmony |
| `lag` | `android` | `utdid`, `clientIp`, `userNick`, `userId`, `isForeground`, `isJailbroken`, `inMainProcess`, `digestHash`, `isSimulator`, `issueStatus` | same as anr |
| `lag` | `iphoneos` | same as lag/android (minus `isSimulator`) | same as anr |
| `lag` | `harmony` | `utdid`, `clientIp`, `userNick`, `userId`, `isForeground`, `inMainProcess`, `digestHash`, `issueStatus` | same as crash/harmony |
| `memory_alloc` | `android` | `deviceId`, `clientIp`, `userNick`, `userId`, `isForeground`, `isJailbroken`, `digestHash`, `isSimulator`, `issueStatus` | `appVersion`, `build`, `firstVersion`, `osVersion`, `brand`, `deviceModel`, `channel`, `language`, `access`, `country`, `province`, `city`, `resolution`, `carrier`, `cpuModel`, `tag`, `additionalCustomInfo` |
| `memory_alloc` | `iphoneos` | same as memory_alloc/android (minus `isSimulator`) | same as memory_alloc/android |
| `memory_leak` | `android` | same as memory_alloc/android | same as memory_alloc/android |
| `memory_leak` | `iphoneos` | same as memory_alloc/android (minus `isSimulator`) | same as memory_alloc/android |

> `harmony` does not have the `anr` / `memory_leak` / `memory_alloc` taxonomy, so those rows are omitted above.
> For the complete field set (including the Chinese `filterName`, `filterValues` candidate lists, and `filterType` widget kinds), read the corresponding JSON directly.

## Canonical pattern for reading static filter enums

```bash
# $SKILL_DIR is expected to be exported ahead of time by SKILL.md section 7.0; no hardcoding here.
# If invoked in script-mode without an exported SKILL_DIR, auto-detect from the Skill root:
: "${SKILL_DIR:=$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)}"

BIZ=crash          # crash / anr / lag / custom / memory_leak / memory_alloc
OS=iphoneos        # android / iphoneos / harmony

FILTER_DIR="$SKILL_DIR/assets/system-filters"
INDEX="$FILTER_DIR/index.json"

# 1) Prefer index.json to resolve the file name (most reliable)
FILE="$FILTER_DIR/$(jq -r --arg bm "$BIZ" --arg os "$OS" \
  '.files[] | select(.bizModule == $bm and .platform == $os) | .file' \
  "$INDEX")"

# 2) Fallback: if index.json is missing or the entry is not found, derive from the naming convention
[[ -f "$FILE" ]] || FILE="$FILTER_DIR/${BIZ}-${OS}.json"

[[ -f "$FILE" ]] || { echo "[ERROR] Filter definition not found for $BIZ x $OS: $FILE" >&2; return 1 2>/dev/null || exit 1; }

# All static filterCodes
jq -r '.filters[] | select(.dynamic == false) | .filterCode' "$FILE"

# Candidate enum values for a specific filterCode (name + value pairs)
jq -r '.filters[] | select(.filterCode == "crashType") | .filterValues[] | "\(.value)\t\(.name)"' "$FILE"

# Group by widget kind (checkbox / radio / select / text)
jq -r '.filters | group_by(.filterType) | .[] | {type:.[0].filterType, codes:[.[].filterCode]}' "$FILE"
```

> To switch the `biz_module x platform` combination, change only `BIZ=` / `OS=` on the top two lines; the file path and existence check are handled by the `FILE=` / fallback / `-f` triplet below, so the JSON filename no longer needs to be maintained by hand.

## Key-field cheat sheet by biz_module

### crash
- **Main discriminator**: `crashType` (Android: `MOTU_ANDROID_CRASH` Java / `MOTU_ANDROID_NATIVE_CRASH` Native; iOS: `MOTU_IOS_CRASH` / `MOTU_IOS_MACH_EXCEPTION` / `MOTU_IOS_NATIVE_CRASH`, etc.)
- **Launch crash window**: `shadow_launchedCrashDuration` static enum (typically `0-5s / 5-10s / 10s+`; read the JSON for exact values)
- **Is OOM** (Android only): `isOom` (0/1)
- **iOS component** (iOS only): `componentType` (APP / Extension / Watch)
- **Issue status**: `issueStatus` = `NEW / OPEN / CLOSE / FIXED`

### anr (Android only)
- Few ANR-specific filterCodes; rely mostly on generic dimensions (device / version / foreground)
- `isForeground=1` is usually a "user-visible ANR"; prioritize it
- `inMainProcess=1` keeps the main process only

### lag
- No dedicated `lagCost` filter (the SDK applies a threshold when reporting; the CLI only supports dimension filtering)
- Common combo: `isForeground=1` + `inMainProcess=1` + `appVersion in [...]`

### custom
- **Main discriminator**: `customErrorLanguage` (`Java / OC / Swift / JavaScript / ArkTS / Dart ...`)
- `isCustomErrorFlag` distinguishes whether this is a "custom error code" report (legacy API vs new API)

### memory_leak
- Common: `osVersion` (some OS versions have specific leaks) + `deviceModel` + `digestHash` (locate the same leak site)
- `isJailbroken=1` can be used to exclude jailbroken-device noise

### memory_alloc
- Filters are the same as memory_leak
- In the API response, `AllocSizePct90 / Pct70 / Pct50 / Max` are in-cluster percentiles; usually sort by `AllocSizePct90 desc` and pick top issues

## Pitfalls

1. **`--biz-module` CLI `--help` is not exhaustive**: `aliyun emas-appmonitor get-issues --help` only lists `crash/lag/custom` and a few options, but dry-run verifies that `anr / memory_leak / memory_alloc` **are all forwarded** to the backend. The Skill guarantees all 6 values are directly usable.
2. **Missing biz_modules for `harmony`**: `anr`, `memory_leak`, `memory_alloc` have no data on the `harmony` platform; if you pass these combinations, the API returns `Model.Items=[]` and `Total=0`, **without error**. When this happens, check the OS combination first.
3. **The same filterCode across biz_modules may have different meanings**: see the "Differences across biz_modules" section in `filter-reference.md`.
4. **`digestHash` as a filterCode**: **invalid** inside `get-issues` (the list is itself aggregated by `digestHash`; filtering by `digestHash` is not supported); to target one `digestHash`, use `get-issue` rather than `get-issues + filter`.

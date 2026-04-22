# CLI cheat sheet for this Skill

All commands assume `aliyun-cli 3.3.3+` with the `aliyun-cli-emas-appmonitor` plugin (`aliyun plugin install --names emas-appmonitor`).

## 1. General environment setup

```bash
# Version
aliyun version

# View / switch profile (do NOT echo AK/SK)
aliyun configure list
aliyun configure set --current <profile>

# Enable auto plugin install
aliyun configure set --auto-plugin-install true

# Plugins
aliyun plugin update
aliyun plugin install --names emas-appmonitor
aliyun plugin list | grep emas-appmonitor
```

## 2. AI-mode lifecycle

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-emas-apm-query"
# ... business commands ...
aliyun configure ai-mode disable
```

## 3. The 4 core APIs

### 3.1 `get-issues` - fetch aggregated error list

```bash
NOW_MS=$(($(date +%s) * 1000)); START_MS=$(($NOW_MS - 7*86400000))
aliyun emas-appmonitor get-issues \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ_MODULE" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  [--filter '<json>'] \
  [--name '<keyword>'] \
  [--order-by ErrorCount|ErrorRate|ErrorDeviceCount|ErrorDeviceRate] \
  [--order-type asc|desc] \
  [--status 1|2|3|4] \
  [--page-index <int>] \
  [--page-size <int>]
```

### 3.2 `get-issue` - fetch aggregated error details

```bash
aliyun emas-appmonitor get-issue \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ_MODULE" \
  --digest-hash "$HASH" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  [--filter '<json>']
```

### 3.3 `get-errors` - sample list

```bash
aliyun emas-appmonitor get-errors \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ_MODULE" \
  --digest-hash "$HASH" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS \
  --page-index 1 --page-size 20 \
  [--filter '<json>'] \
  [--utdid '<utdid>']
```

`--time-range` here accepts only `StartTime` + `EndTime`, not `Granularity`.

### 3.4 `get-error` - sample details

```bash
aliyun emas-appmonitor get-error \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ_MODULE" \
  --digest-hash "$HASH" \
  --client-time "$CLIENT_TIME" --uuid "$UUID" --did "$DID" \
  [--biz-force false]
```

The triple `(client-time, uuid, did)` comes from `get-errors.Items[*]`; all three are required.

## 4. Parallel scan over 6 bizModules (entry point when no DigestHash is given)

```bash
NOW_MS=$(($(date +%s) * 1000)); START_MS=$(($NOW_MS - 7*86400000))

for MOD in crash anr lag custom memory_leak memory_alloc; do
  aliyun emas-appmonitor get-issues \
    --app-key "$APP_KEY" --os "$OS" --biz-module "$MOD" \
    --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
    --filter '{"Operator":"and","SubFilters":["{\"operator\":\"in\",\"key\":\"issueStatus\",\"values\":[1,2,3,4]}"]}' \
    --order-by ErrorCount --order-type desc --page-index 1 --page-size 5 \
    --cli-query 'Model.Items[*].{Module:`'"$MOD"'`,DigestHash:DigestHash,Type:Type,ErrorCount:ErrorCount,ErrorDeviceCount:ErrorDeviceCount,FirstVersion:FirstVersion}' > /tmp/top_${MOD}.json
done

# Merge, sort, take Top 5
jq -s 'flatten | sort_by(-(.ErrorCount // 0)) | .[0:5]' /tmp/top_*.json
```

Skip irrelevant combinations to reduce RPC: ANR only applies to `android`; `memory_leak` / `memory_alloc` do not apply to `harmony`.

## 5. Chained calls

```bash
# Step 1: Top 1 DigestHash (--cli-query's scalar output is a JSON string; use jq -r to strip quotes)
DH=$(aliyun emas-appmonitor get-issues \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$MOD" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  --order-by ErrorCount --order-type desc --page-index 1 --page-size 1 \
  --cli-query 'Model.Items[0].DigestHash' | jq -r .)

# Step 2: Aggregated details of this Issue
aliyun emas-appmonitor get-issue \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$MOD" \
  --digest-hash "$DH" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day

# Step 3: Latest sample triple (three CLI calls; you can also do one call and parse with jq)
SAMPLE=$(aliyun emas-appmonitor get-errors \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$MOD" \
  --digest-hash "$DH" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS \
  --page-index 1 --page-size 1 \
  --cli-query 'Model.Items[0].{CT:ClientTime,UUID:Uuid,DID:Did}')
CT=$(echo "$SAMPLE" | jq -r .CT)
UUID=$(echo "$SAMPLE" | jq -r .UUID)
DID=$(echo "$SAMPLE" | jq -r .DID)

# Step 4: Full sample details
aliyun emas-appmonitor get-error \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$MOD" \
  --digest-hash "$DH" \
  --client-time "$CT" --uuid "$UUID" --did "$DID" > /tmp/sample.json
```

## 6. Debug helpers

```bash
# Do not send the request; inspect the CLI-serialized request parameters
aliyun emas-appmonitor get-issues ... --cli-dry-run

# DEBUG log (includes HTTP body)
aliyun emas-appmonitor get-issues ... --log-level DEBUG

# Specify a custom endpoint (private network / Apsara Stack)
aliyun emas-appmonitor get-issues ... --endpoint emas-appmonitor.cn-shanghai.aliyuncs.com

# Select specific fields only
aliyun emas-appmonitor get-issue ... --cli-query 'Model.{Hash:DigestHash,Type:Type,Stack:Stack}'
```

## 7. CLI query templates

| Scenario | JMESPath |
| --- | --- |
| Top Hash only | `Model.Items[0].DigestHash` |
| Flatten Top N | `Model.Items[*].{Hash:DigestHash,Count:ErrorCount}` |
| Issue overview | `Model.{Hash:DigestHash,Type:Type,AffectedVersions:AffectedVersions,Stack:Stack}` |
| Sample triple | `Model.Items[*].{CT:ClientTime,UUID:Uuid,DID:Did}` |
| Sample dimensions | `Model.{App:AppVersion,Os:OsVersion,Brand:Brand,Model:DeviceModel,Country:Country}` |

## 8. Arguments to avoid / use with caution

| Argument | Reason |
| --- | --- |
| `--biz-force true` (on `get-error`) | Bypasses the cache and forces a refresh, adding load on the backend; use only when the cache is stale. |
| Blind `--pager` | Sample lists are usually large; pulling them fully can take minutes, not suitable inside an Agent loop. |
| `eq` / `neq` / `not_in` inside `--filter` | Observed not to work; use `in` or `or` instead. See [filter-reference.md](filter-reference.md). |
| `--region` | EMAS AppMonitor is only in `cn-shanghai` today; explicit override is usually unnecessary. |

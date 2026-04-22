# Success verification method

这份文档给出 6 步**可直接复制执行**的 CLI 校验步骤，用于验证本 Skill 端到端可用。
所有命令只调用 `aliyun emas-appmonitor` 的 4 个只读 API，不会产生任何写入操作。

执行前请确认：

- `aliyun version` 输出 `>= 3.3.3`
- `aliyun plugin list | grep emas-appmonitor` 命中一行
- `aliyun configure list` 有一个当前 profile（Mode 非空、RegionId 非空）
- 已准备好一个真实的 `AppKey` 与对应的 `--os`（例如 `335581386 / android`）

以下示例统一使用变量：

```bash
APP_KEY=335581386
OS=android
BIZ=crash
NOW_MS=$(( $(date +%s) * 1000 ))
START_MS=$(( NOW_MS - 24*3600*1000 ))   # 最近 24 小时
```

> 若任一步骤失败：先查 [`cli-installation-guide.md`](cli-installation-guide.md)（CLI / 插件 / 凭证）与 [`ram-policies.md`](ram-policies.md)（RAM 权限）。

---

## Step 1 — Reachable（`get-issues` dry-run）

**目的**：确认 CLI 能正确序列化请求，并且网络可达。

```bash
aliyun emas-appmonitor get-issues \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  --order-by ErrorCount --order-type desc \
  --page-index 1 --page-size 5 \
  --cli-dry-run
```

**判据**：

- ✅ 通过：stdout 打印序列化后的 HTTP 请求体，能看到 `AppKey` / `Os` / `BizModule` / `TimeRange` 字段
- ❌ 失败：`required flags missing` → 按报错补参；`product not exists` → `aliyun plugin install --names emas-appmonitor`

---

## Step 2 — Non-empty（至少一个 bizModule 有数据）

**目的**：确认账号下的 AppKey 在所选时间窗内至少有一条聚合 Issue。

```bash
for MOD in crash anr lag custom memory_leak memory_alloc; do
  TOTAL=$(aliyun emas-appmonitor get-issues \
    --app-key "$APP_KEY" --os "$OS" --biz-module "$MOD" \
    --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
    --page-index 1 --page-size 1 \
    --cli-query 'Model.Total' 2>/dev/null)
  echo "$MOD -> Total=$TOTAL"
done
```

**判据**：

- ✅ 通过：至少一行 `Total` 为正整数
- ❌ 失败：全部 `Total=0`
  - Harmony 下 `anr/memory_leak/memory_alloc` 为 0 属正常（平台不支持）
  - 其它组合全 0 → 时间窗口太窄或 AppKey/OS 不匹配，扩大到 7 天或用 [`appkey-detection.md`](appkey-detection.md) 重新确认 AppKey

---

## Step 3 — Stable（两次同参调用返回一致的 Top 5）

**目的**：确认后端返回是确定性的（无随机排序、无超时切流量）。

```bash
QUERY='Model.Items[*].DigestHash'

A=$(aliyun emas-appmonitor get-issues \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  --order-by ErrorCount --order-type desc \
  --page-index 1 --page-size 5 --cli-query "$QUERY")

sleep 2

B=$(aliyun emas-appmonitor get-issues \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  --order-by ErrorCount --order-type desc \
  --page-index 1 --page-size 5 --cli-query "$QUERY")

diff <(echo "$A") <(echo "$B") && echo "STABLE" || echo "UNSTABLE"
```

**判据**：

- ✅ 通过：输出 `STABLE`，两次 5 个 `DigestHash` 完全一致
- ❌ 失败：输出 `UNSTABLE`
  - 检查时间窗口是否跨越了数据落库边界（改用纯历史窗口，例如 `[now-72h, now-24h]` 再试）
  - 若仍不稳定，`--log-level debug` 抓 `RequestId` 反馈工单

---

## Step 4 — Filter works（添加过滤后 Total 严格 ≤ 全量）

**目的**：确认 `--filter` 语法正确、并真的能缩小结果集。

```bash
TOTAL_ALL=$(aliyun emas-appmonitor get-issues \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  --page-index 1 --page-size 1 \
  --cli-query 'Model.Total')

TOTAL_FILTERED=$(aliyun emas-appmonitor get-issues \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  --filter '{"Operator":"and","SubFilters":["{\"operator\":\"in\",\"key\":\"issueStatus\",\"values\":[1]}"]}' \
  --page-index 1 --page-size 1 \
  --cli-query 'Model.Total')

echo "all=$TOTAL_ALL filtered=$TOTAL_FILTERED"
[[ "$TOTAL_FILTERED" -le "$TOTAL_ALL" ]] && echo "FILTER_OK" || echo "FILTER_BAD"
```

**判据**：

- ✅ 通过：`filtered <= all` 且输出 `FILTER_OK`
- ❌ 失败：`filtered > all` 或 CLI 报错
  - 常见错法见 [`acceptance-criteria.md`](acceptance-criteria.md) §2/§6（SubFilters 元素必须是 JSON 字符串；Root Operator/SubFilters 大写）
  - 过滤键可用值见 [`filter-reference.md`](filter-reference.md) 和 `assets/system-filters/${biz}-${os}.json`

---

## Step 5 — 三级链路（`get-issues → get-issue → get-errors → get-error`）

**目的**：端到端跑通从 Top 聚合到单样本 Stack 的全链路。

```bash
# 5.1 拿 Top 1 的 DigestHash
DH=$(aliyun emas-appmonitor get-issues \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  --order-by ErrorCount --order-type desc \
  --page-index 1 --page-size 1 \
  --cli-query 'Model.Items[0].DigestHash' | jq -r .)
echo "DigestHash=$DH"

# 5.2 聚合详情
aliyun emas-appmonitor get-issue \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ" \
  --digest-hash "$DH" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  --cli-query 'Model.{Hash:DigestHash,Type:Type,Versions:AffectedVersions}'

# 5.3 取最新样本三元组
read CT UUID DID < <(aliyun emas-appmonitor get-errors \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ" \
  --digest-hash "$DH" \
  --time-range StartTime=$START_MS EndTime=$NOW_MS \
  --page-index 1 --page-size 1 \
  --cli-query 'Model.Items[0].[ClientTime,Uuid,Did]' | jq -r '.[] | tostring' | paste -sd ' ' -)
echo "sample: CT=$CT UUID=$UUID DID=$DID"

# 5.4 单样本详情
aliyun emas-appmonitor get-error \
  --app-key "$APP_KEY" --os "$OS" --biz-module "$BIZ" \
  --digest-hash "$DH" \
  --client-time "$CT" --uuid "$UUID" --did "$DID" \
  --cli-query 'Model.{Hash:DigestHash,Stack:Stack,HasBacktrace:(Backtrace!=null)}' \
  > /tmp/emas-step5-error.json

jq -r '.Hash, .HasBacktrace' /tmp/emas-step5-error.json
```

**判据**：

- ✅ 通过：`DH` 非空；`get-issue` 返回 `Hash` 与 5.1 一致；`CT/UUID/DID` 非空；`get-error` 输出的 `Hash` 也与 `DH` 一致
- ❌ 失败：
  - 5.1 `DH=null` → Step 2 已确认有数据时，检查 `--order-by` 是否大小写写错
  - 5.3 缺 `DID` → `get-error` 会直接报 `Code: 100011 Parameter Not Enough`，遵循 SKILL.md 规则始终传 `--did`
  - 5.4 返回空 `Model` → 大概率 `--biz-module` 与 `DigestHash` 不匹配，参考 SKILL.md §6 "Reuse `biz-module`"

---

## Step 6 — Diagnosable（人为引错，确认输出含 `RequestId` + 错误码）

**目的**：确认失败路径本身是可观测、可排障的。

```bash
aliyun emas-appmonitor get-issue \
  --app-key 0 --os "$OS" --biz-module "$BIZ" \
  --digest-hash BADHASH \
  --time-range StartTime=$START_MS EndTime=$NOW_MS Granularity=1 GranularityUnit=day \
  --log-level debug 2>&1 | tee /tmp/emas-step6.log | tail -40
```

**判据**：

- ✅ 通过：日志中能同时看到 `RequestId: ...` 与 `Code: ...`（例如 `Code: 400`、`Code: InvalidParameter`、`Code: NoPermission` 之一）
- ❌ 失败：连不上（DNS/HTTPS）或没有 `RequestId`
  - 检查 `aliyun configure list` 的 Region / Mode
  - 必要时显式指定 `--endpoint emas-appmonitor.cn-shanghai.aliyuncs.com`
  - 权限类报错按 [`ram-policies.md`](ram-policies.md) 的 **Permission Failure Handling** 流程处理

---

## 汇总校验脚本

所有 6 步跑完后，按以下口径给出一句话结论：

| 维度 | 期望 |
| --- | --- |
| Step 1 Reachable | dry-run 成功，HTTP body 可见 |
| Step 2 Non-empty | 至少 1 个 bizModule 有 `Total >= 1` |
| Step 3 Stable | 两次 Top 5 `DigestHash` 完全一致 |
| Step 4 Filter | `filtered <= all` |
| Step 5 Chain | 4 个 API 全部返回，`DigestHash` 贯通 |
| Step 6 Diagnosable | 错误响应含 `RequestId` + `Code` |

6 项都打勾即视为本 Skill 在当前 AppKey/账号下验证通过。

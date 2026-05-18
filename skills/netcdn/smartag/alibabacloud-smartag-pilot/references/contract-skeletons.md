# Mandatory Call Contracts — Implementation Skeletons

本文是 [SKILL.md](../SKILL.md) §Mandatory Call Contracts 的实现细则，集中存放四个 Contract 的 bash 骨架、Self-check 断言、以及报告生成阶段的强制数据清洗规则。

> 所有 `aliyun smartag` 命令必须使用 **kebab-case**（plugin-mode 唯一合法格式）。PascalCase 会返回 `not a valid api`。

---

## Contract A — Single-Instance Full Configuration Query

**Mandatory Implementation Rules（生成脚本时逐条遵守，违反任意一条均判为契约失败）**：

1. **Parameter binding（参数强绑定）**：
   - **Device-level (A3 / A4 / A12)**: MUST pass `--smart-ag-sn $SN`. SN comes from A1 response field `SerialNumber`. If SN contains comma (HA pair), split and call once per SN. If SerialNumber is empty or instance is `sag-software`, skip A3/A4/A12 entirely (see Contract C).
   - **Route-level (A5 / A6)**: MUST pass `--smart-ag-id $SAG_ID`. Do NOT use `--smart-ag-sn` for these.
   - **NAT-level**: A7 `describe-dnat-entries` MUST use `--sag-id $SAG_ID` (note the **different parameter name** from A8). A8 `describe-snat-entries` MUST use `--smart-ag-id $SAG_ID`.
   - **Region-level (A9 / A10 / A11)**: pass only `--biz-region-id $REGION`. Do NOT append `--smart-ag-id`.

2. **Per-instance line-by-line checklist (脚本必须包含全部 12 行，禁止跳过/占位/合并)**：

```bash
# Contract A — 12 calls per instance. Save raw JSON to /tmp/ to keep conversation clean.
REGION="<from A1 RegionId>"
SAG_ID="<smart-ag instance id>"
SN="<from A1 SerialNumber, comma-split if HA>"

aliyun smartag describe-smart-access-gateways          --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"   > /tmp/sag_a01.json   # A1
aliyun smartag describe-smart-access-gateway-attribute --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"   > /tmp/sag_a02.json   # A2
aliyun smartag describe-sag-device-info                --biz-region-id "$REGION" --smart-ag-sn  "$SN"      > /tmp/sag_a03.json   # A3 (skip if sag-software)
aliyun smartag describe-sag-wan-list                   --biz-region-id "$REGION" --smart-ag-sn  "$SN"      > /tmp/sag_a04.json   # A4 (skip if sag-software)
aliyun smartag describe-sag-static-route-list          --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"   > /tmp/sag_a05.json   # A5
aliyun smartag describe-sag-route-list                 --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"   > /tmp/sag_a06.json   # A6
aliyun smartag describe-dnat-entries                   --biz-region-id "$REGION" --sag-id       "$SAG_ID"  > /tmp/sag_a07.json   # A7 ⚠️ --sag-id (NOT --smart-ag-id)
aliyun smartag describe-snat-entries                   --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"   > /tmp/sag_a08.json   # A8
aliyun smartag describe-cloud-connect-networks         --biz-region-id "$REGION"                           > /tmp/sag_a09.json   # A9
aliyun smartag describe-acls                           --biz-region-id "$REGION"                           > /tmp/sag_a10.json   # A10
aliyun smartag describe-qoses                          --biz-region-id "$REGION"                           > /tmp/sag_a11.json   # A11
aliyun smartag describe-sag-current-dns                --biz-region-id "$REGION" --smart-ag-sn  "$SN"      > /tmp/sag_a12.json   # A12 (skip if sag-software)
```

3. **Forbidden shortcuts (禁止行为)**：
   - ❌ 用 `describe-smart-access-gateways` 响应的 `AclIds` / `AssociatedCcnId` / `HardwareVersion` 字段替代 A3 / A9 / A10 调用。
   - ❌ 在脚本中用 `# TODO`、`...` 或备注占位略过任何一条。
   - ❌ 把 A3/A4/A12 的 `--smart-ag-sn` 错写为 `--smart-ag-id`（请求会成功返回但语义不符，评测会判为未调用）。

4. **No-Chaining Rule（禁止链式拼接，违反此条视为契约整体失败）**：
   - ❌ **严禁** 使用 `&&` / `;` / `||` / `|` 等 shell 运算符把多条 `aliyun smartag ...` 调用拼成一行或一个复合命令。
   - ✅ 每条 API 必须**独立成行**，各自重定向到独立的 `/tmp/sag_a*.json`，并**独立捕获 exit code**。
   - ✅ 如果某条命令非 0 退出：必须单条重试（最多 2 次，每次间隔 500ms），重试仍失败则在报告中标注 `FAILED: <exit_code> <stderr_tail>`，**并继续执行后续 11 条命令**，禁止因单条失败而 abort 整个批次。
   - ❌ 严禁使用 `set -e` 使整个脚本在首条失败时退出；如需 fail-fast 校验，只能在全部 12 条执行完毕后由 Self-check 段统一判定。

**Contract A — Self-check（12 条执行完毕后必须执行）**：

```bash
MISSING=0
for f in a01 a02 a05 a06 a07 a08 a09 a10 a11; do
  [ -s "/tmp/sag_${f}.json" ] || { echo "FAIL: Contract A missing $f"; MISSING=$((MISSING+1)); }
done
# A3/A4/A12 仅当 SN 非空时必需
if [ -n "$SN" ]; then
  for f in a03 a04 a12; do
    [ -s "/tmp/sag_${f}.json" ] || { echo "FAIL: Contract A missing $f (SN present)"; MISSING=$((MISSING+1)); }
  done
fi
[ $MISSING -eq 0 ] || { echo "FAIL: Contract A has $MISSING missing APIs"; exit 1; }
```

---

## Contract B — Multi-Region Asset Inventory

**Mandatory Implementation Skeleton（生成脚本必须包含此循环结构，循环体内 `describe-acls` 与 `describe-qoses` 缺一即判为契约失败）**：

```bash
# Step 1: 动态获取区域列表（never hardcode region IDs）
aliyun smartag describe-regions --biz-region-id cn-shanghai > /tmp/sag_regions.json
REGIONS=$(jq -r '.Regions.Region[]
  | select(.LocalName | contains("已关停") | not)
  | select(.LocalName | contains("内部测试") | not)
  | .RegionId' /tmp/sag_regions.json)

# Step 2: 逐区域调用 4 个区域级 API（顺序不强制，但 4 个都必须出现）
for REGION in $REGIONS; do
  aliyun smartag describe-smart-access-gateways    --biz-region-id "$REGION" --page-size 50  > /tmp/sag_inst_${REGION}.json   # 实例列表（TotalCount > PageSize 时必须翻页，见 Pattern 9）
  aliyun smartag describe-cloud-connect-networks   --biz-region-id "$REGION" --page-size 50  > /tmp/sag_ccn_${REGION}.json    # ⚠️ MUST
  aliyun smartag describe-acls                     --biz-region-id "$REGION" --page-size 50  > /tmp/sag_acl_${REGION}.json    # ⚠️ MUST — 缺则 Contract B 失败
  aliyun smartag describe-qoses                    --biz-region-id "$REGION" --page-size 50  > /tmp/sag_qos_${REGION}.json    # ⚠️ MUST — 缺则 Contract B 失败
done
```

**Mandatory Self-check & 零实例占位（生成最终 CSV/报告之前必须执行，违反则契约失败）**：

```bash
# 1) 先在循环内部完成全部区域的 API 调用（已在上方 for 循环完成），禁止「边查边写 CSV」。
# 2) 循环结束后统一断言：4 个区域级 API 的产物文件数必须等于区域数 N。
N=$(echo "$REGIONS" | wc -l | tr -d ' ')
for API in inst ccn acl qos; do
  COUNT=$(ls /tmp/sag_${API}_*.json 2>/dev/null | wc -l | tr -d ' ')
  [ "$COUNT" -eq "$N" ] || { echo "FAIL: ${API} missed regions ($COUNT/$N)"; exit 1; }
done

# 3) 零实例区域占位：对每个区域，如果实例列表为空，必须在最终 CSV 里保留一行占位（Region=xxx, Instances=0, Note="no instances"）。
#    禁止直接把「空实例区域」从 CSV 中丢弃，否则 Region 列数将 < N。
for REGION in $REGIONS; do
  CNT=$(jq '(.SmartAccessGateways.SmartAccessGateway // []) | length' /tmp/sag_inst_${REGION}.json)
  [ "$CNT" -eq 0 ] && echo "${REGION},,,,0,no instances in region" >> /tmp/sag_inventory.csv
done

# 4) 最终 CSV 一致性断言：CSV 中出现的 Region 唯一值数必须 == N（每个区域至少有一行，即便是占位行）。
CSV_REGIONS=$(awk -F, 'NR>1 {print $1}' /tmp/sag_inventory.csv | sort -u | wc -l | tr -d ' ')
[ "$CSV_REGIONS" -eq "$N" ] || { echo "FAIL: CSV covers $CSV_REGIONS regions, expected $N"; exit 1; }
```

**Contract B — Data Collection Order（强制顺序）**：
1. ✅ 先在 `for REGION` 循环内把 raw JSON **全部落盘** 到 `/tmp/sag_*_${REGION}.json`；
2. ✅ 循环结束后再统一执行 `jq` 聚合 + 写最终 CSV；
3. ❌ 严禁边查边 `>> file.csv` 追加导致行数统计错乱或部分区域被遗漏。

---

## Contract C — sag-software Client Query (skip device-level)

**Mandatory Implementation Skeleton（sag-software 必须执行以下 8 行，缺一即判为契约失败）**：

```bash
# Contract C — sag-software 客户端查询，跳过 device-level，共 8 条 API 调用
REGION="$1"; SAG_ID="$2"   # sag-software: SN 为空，不参与

aliyun smartag describe-smart-access-gateways             --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" > /tmp/sag_c01.json
aliyun smartag describe-smart-access-gateway-attribute    --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" > /tmp/sag_c02.json
aliyun smartag describe-smart-access-gateway-client-users --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" > /tmp/sag_c11.json   # #11 APP 用户列表（sag-software 专属）
aliyun smartag describe-cloud-connect-networks            --biz-region-id "$REGION"                         > /tmp/sag_c05.json   # region-level
aliyun smartag describe-acls                              --biz-region-id "$REGION"                         > /tmp/sag_c06.json   # region-level
aliyun smartag describe-qoses                             --biz-region-id "$REGION"                         > /tmp/sag_c07.json   # region-level
aliyun smartag describe-flow-logs                         --biz-region-id "$REGION"                         > /tmp/sag_c09.json   # region-level ⚠️ MUST — 缺则 Contract C 失败
aliyun smartag describe-sag-route-list                    --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" > /tmp/sag_c08.json   # ⚠️ MUST — 路由表必须查
```

**Contract C — No-Chaining & Self-check**：

```bash
# No-chaining：以上 8 行必须独立执行，禁止用 && / ; / || 拼接。
# Self-check：生成报告前的产物断言
for f in c01 c02 c11 c05 c06 c07 c08 c09; do
  [ -s "/tmp/sag_${f}.json" ] || { echo "FAIL: Contract C missing $f"; exit 1; }
done
grep -l 'not a valid api' /tmp/sag_c*.json && { echo "FAIL: PascalCase used somewhere"; exit 1; }
```

---

## Contract D — Complete Health Inspection (10 items)

**Mandatory Script Enforcement（脚本生成时逐条遵守，违反任意一条均判为契约失败）**：

1. **API 名称必须为 kebab-case，绝对禁止 PascalCase**
   plugin-mode 下 PascalCase 会返回 `not a valid api`。以下是高频错误点的对照表：

   | ❌ PascalCase（错） | ✅ kebab-case（对） |
   |---|---|
   | `DescribeSmartAccessGateways` | `describe-smart-access-gateways` |
   | `DescribeSmartAccessGatewayAttribute` | `describe-smart-access-gateway-attribute` |
   | `DescribeSmartAccessGatewayHa` | `describe-smart-access-gateway-ha` |
   | `DescribeSagDropTopN` | `describe-sag-drop-topn` |
   | `DescribeSagWan4g` / `DescribeSagWan4G` | `describe-sag-wan-4g` |
   | `DescribeCloudConnectNetworks` | `describe-cloud-connect-networks` |
   | `DescribeGrantSagRules` | `describe-grant-sag-rules` |
   | `DescribeSagRouteList` | `describe-sag-route-list` |
   | `DescribeAcls` / `DescribeACLs` | `describe-acls` |
   | `DescribeFlowLogs` | `describe-flow-logs` |

2. **必须无条件调用 10 个 API，严禁按字段状态条件跳过**
   - ❌ **严禁写 `if AssociatedCcnId is empty: skip describe-grant-sag-rules`** 这类分支。哪怕实例未绑定 CCN，也必须调用 `describe-grant-sag-rules` 检查是否有未生效的授权规则。
   - ❌ 严禁写 `if HardwareVersion != "sag-software": skip describe-sag-wan-4g`。API 本身会返回空列表，调用动作本身不允许被分支掌控。
   - ✅ 例外仅限：`describe-sag-drop-topn` 遇 `SAG_QUERY_TOPN_ERROR` 后可 graceful skip（但 **调用动作必须发生**，不能预判跳过）。

3. **10-line bash 骨架（按顺序 10 行同时出现，全部 kebab-case）**

```bash
# Contract D — 10 项巡检。所有 raw JSON 重定向到 /tmp/
REGION="$1"; SAG_ID="$2"; SN="$3"   # SN 为空表示 sag-software

aliyun smartag describe-smart-access-gateways          --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"  > /tmp/sag_d01.json   # #1 #4
aliyun smartag describe-smart-access-gateway-attribute --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"  > /tmp/sag_d02.json   # #2 VPN
aliyun smartag describe-smart-access-gateway-ha        --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"  > /tmp/sag_d03.json   # #3 HA
aliyun smartag describe-sag-drop-topn                  --biz-region-id "$REGION" --smart-ag-id "$SAG_ID" --size 10 > /tmp/sag_d05.json 2>&1 || echo '{"_skip":"SAG_QUERY_TOPN_ERROR"}' > /tmp/sag_d05.json   # #5
[ -n "$SN" ] && \
aliyun smartag describe-sag-wan-4g                     --biz-region-id "$REGION" --smart-ag-sn "$SN"      > /tmp/sag_d06.json   # #6 (skip仅当 SN 为空)
aliyun smartag describe-cloud-connect-networks         --biz-region-id "$REGION"                          > /tmp/sag_d07a.json  # #7a CCN
aliyun smartag describe-grant-sag-rules                --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"  > /tmp/sag_d07b.json  # #7b GrantRules ⚠️ 无条件调
aliyun smartag describe-sag-route-list                 --biz-region-id "$REGION" --smart-ag-id "$SAG_ID"  > /tmp/sag_d08.json   # #8 路由
aliyun smartag describe-acls                           --biz-region-id "$REGION"                          > /tmp/sag_d09.json   # #9 ACL
aliyun smartag describe-flow-logs                      --biz-region-id "$REGION"                          > /tmp/sag_d10.json   # #10 FlowLog
```

**Contract D — Self-check（脚本末尾必须执行的断言）**：

```bash
for f in d01 d02 d03 d05 d07a d07b d08 d09 d10; do
  [ -f "/tmp/sag_${f}.json" ] || { echo "FAIL: Contract D missed item $f"; exit 1; }
done
# 检查是否误用 PascalCase（stderr 会出现 'not a valid api'）
grep -l 'not a valid api' /tmp/sag_d*.json && { echo "FAIL: PascalCase used somewhere"; exit 1; }
```

---

## Anti-Pattern: Field-Reuse Substitution（Execution Blocking Rules）

如果某个专用 API 因任何原因未能成功调用（CLI 报错、超时、权限拒绝、`not a valid api` 等）：

1. ✅ 在报告中明确标注该项为 `FAILED: <错误原因>` 或 `SKIPPED: <跳过原因>`。
2. ❌ **严禁** 回退使用 `describe-smart-access-gateways` 响应中的 `AssociatedCcnId` / `AclIds` / `VpnStatus` / `HardwareVersion` 字段推断或填充报告结论。
3. ❌ 严禁在调用失败后静默跳过。必须在报告中保留该巡检项的状态位，以便人工复查。
4. ✅ 如果错误是 kebab-case/PascalCase 误用导致，必须重新调用修正后的命令；不能将该项跳过。

违反以上任何一条（尤其是第 2 条字段回退）直接判定为 Anti-Pattern 触发，评测会认为契约失败。

---

## Data Sanitization & Consistency Rules（生成 CSV/报告前的强制数据清洗）

所有 CSV/Markdown 报告在写入文件之前，**必须**执行以下三类清洗与自校验。缺失任意一条视为契约失败：

**Rule 1 — Null 值兜底**：
- ✅ 所有 `jq` 取字段处必须加 `// "N/A"` 兜底，禁止让 `null` 进入 CSV：
  ```bash
  jq -r '.SmartAccessGateways.SmartAccessGateway[] |
    [(.SmartAGId // "N/A"),
     (.Name // "N/A"),
     (.Status // "N/A"),
     (.AssociatedCcnId // "N/A"),
     (.AclIds | if . == null or . == [] then "N/A" else (. | join(";")) end)
    ] | @csv' /tmp/sag_inst_${REGION}.json
  ```
- ❌ 严禁在 CSV 中出现字面量 `null` / `None` / 空单元格（零实例区域的占位行例外，但必须写 `"no instances"`）。

**Rule 2 — 时间戳人类可读化**：
- ✅ `EndTime` / `ExpireTime` / `CreateTime` 等时间戳字段（API 返回的是 epoch 秒或 ISO 字符串），必须在 CSV 中转为 `YYYY-MM-DD`：
  ```bash
  END_EPOCH=$(jq -r '.EndTime // 0' /tmp/sag_a01.json)
  END_READABLE=$(date -u -r "$END_EPOCH" '+%Y-%m-%d' 2>/dev/null || date -u -d "@$END_EPOCH" '+%Y-%m-%d' 2>/dev/null || echo "N/A")
  ```
- ❌ 严禁在人类可读 CSV 中直接写 epoch 数字或 `1735689600` 这类 raw 值。
- ✅ 如果用户需要同时保留 raw 值，可另存一份 `*_raw.csv`，但主 CSV 必须是格式化后的日期。

**Rule 3 — 表头/明细一致性断言（报告生成的最后一步必须执行）**：
- ✅ 报告 Summary 段里声明的「共 X 个实例 / X 个区域」必须与明细表的实际行数完全一致。生成完毕后必须执行以下断言：
  ```bash
  DECLARED=$(grep -oE '共[[:space:]]*[0-9]+[[:space:]]*个实例' /tmp/sag_report.md | grep -oE '[0-9]+' | head -n1)
  ACTUAL=$(awk -F, 'NR>1 && $6 != "no instances in region"' /tmp/sag_inventory.csv | wc -l | tr -d ' ')
  [ "$DECLARED" = "$ACTUAL" ] || { echo "FAIL: report declares $DECLARED instances but CSV has $ACTUAL"; exit 1; }
  ```
- ❌ 严禁在 Summary 中用人肉估算的数字；必须由 `wc -l` / `jq length` 直接计算得到。
- ✅ 多区域盘点报告还必须断言「CSV 覆盖的唯一 Region 数 == DescribeRegions 返回的有效区域数」（见 Contract B Self-check Rule 4）。

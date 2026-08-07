# 验收标准：pause-task-instance

**Scenario**: 按任务名 + 业务日期 + 运行时点暂停/恢复 Dataphin 调度实例
**Purpose**: Skill 测试验收与命令模式校验

---

## 正确模式

### 1. 产品名正确

- 使用 `dataphin-public` 插件，不使用旧 `dataphin` 二进制。

### 2. 命令格式正确

- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`。
- 不使用传统 API 格式 `aliyun dataphin-public RunInstances`。

### 3. 参数格式正确

#### ✅ CORRECT — 暂停实例

```bash
aliyun dataphin-public operate-instance \
  --env PROD \
  --project-id "7295715579274176" \
  --operation PAUSE \
  --instance-id-list '{"Id":"t_8126482847401836544_20260629_8127037173060861955"}'
```

说明：`--instance-id-list` 的每个元素是 JSON 对象字符串，必须包含 `Id` 字段。

#### ✅ CORRECT — 恢复实例（RESUME）

```bash
aliyun dataphin-public operate-instance \
  --env PROD \
  --project-id "7295715579274176" \
  --operation RESUME \
  --instance-id-list '{"Id":"t_8126482847401836544_20260629_8127037173060861955"}'
```

说明：
- RESUME 只把 `SchedulePaused` 从 `true` 切回 `false`，不改变 `StatusList`（仍为 `WAIT_SCHEDULE` 属正常）。
- 恢复后实例到点（DueTime）会被调度自动拉起。
- 若需**立即手动触发**执行，应改用 `--operation RERUN`，而非 RESUME。

#### ✅ CORRECT — 小时任务按时点筛选

```bash
# DueTime 为毫秒时间戳，需转 HH:MM 后筛选
TARGET_HHMM="20:45"
aliyun dataphin-public list-instances ... | jq -r '.PageResult.Data[]? | "\(.Id)\t\(.DueTime)"' \
  | while IFS=$'\t' read -r ID DUE; do
      HM=$(date -r $((DUE/1000)) "+%H:%M")
      [[ "$HM" == "$TARGET_HHMM" ]] && echo "$ID $HM"
    done
```

#### ✅ CORRECT — 验证看 SchedulePaused

```bash
aliyun dataphin-public get-physical-instance ... \
  | jq '.Instance | {Id, StatusList, SchedulePaused:.NodeInfo.SchedulePaused}'
```

### 4. 业务日期取值正确

- 用户说「当日运行的实例」时，bizdate 默认取 T-1（昨天），而非今天。

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project ID 到 Skill 示例中。
- ❌ 使用 `dataphin` 旧 CLI 二进制命令。
- ❌ `operate-instance` 直接传裸实例 ID：
  ```bash
  --instance-id-list t_xxx
  ```
- ❌ 未带 `--user-agent` 调用 `aliyun` API 命令。
- ❌ 用 `StatusList` 判断暂停是否生效（应看 `NodeInfo.SchedulePaused`）。
- ❌ 用今日 bizdate 查不到实例时未回退到 T-1。
- ❌ 恢复调度时用 `RERUN` 而非 `RESUME`。
- ❌ 需要立即手动触发执行时却用 `RESUME`（RESUME 只恢复调度等待，不立即执行；应改用 `RERUN`）。
- ❌ 用 `StatusList` 判断 RESUME 是否生效（应看 `NodeInfo.SchedulePaused=false`）。

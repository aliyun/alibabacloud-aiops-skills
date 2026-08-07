# 验收标准：rerun-task-instance

**Scenario**: 按任务名 + 业务日期重跑 Dataphin 调度实例
**Purpose**: Skill 测试验收与命令模式校验

---

## 正确模式

### 1. 产品名正确

- 使用 `dataphin-public` 插件，不使用旧 `dataphin` 二进制。

### 2. 命令格式正确

- 插件模式：`aliyun dataphin-public <verb-resource> [flags]`。
- 不使用传统 API 格式 `aliyun dataphin-public RunInstances`。

### 3. 参数格式正确

#### ✅ CORRECT — 实例 ID 列表

```bash
aliyun dataphin-public operate-instance \
  --env PROD \
  --project-id "7283355458594816" \
  --operation RERUN \
  --instance-id-list '{"Id":"t_8064978572122849280_20260629_8125159035401928708"}'
```

说明：`--instance-id-list` 的每个元素是 JSON 对象字符串，必须包含 `Id` 字段。

#### ✅ CORRECT — 业务日期查询实例

```bash
aliyun dataphin-public list-instances \
  --env PROD \
  --project-id "7283355458594816" \
  --schedule-type NORMAL \
  --search-text oracle \
  --min-biz-date 20260629 \
  --max-biz-date 20260629 \
  --page 1 --page-size 10
```

说明：`biz-date` 使用 `yyyymmdd` 字符串。

### 4. 用户确认

- 执行 `operate-instance` 前展示目标实例信息并征得用户同意。
- 跨项目搜索到多条实例时，让用户选择唯一目标。

### 5. fix-data 参数格式正确（模式②）

#### ✅ CORRECT — root-instance-id 传 JSON 对象

```bash
aliyun dataphin-public fix-data \
  --env PROD \
  --project-id "7295715579274176" \
  --root-instance-id '{"Id":"t_8127255632277340160_20260629_8127264978126241798"}' \
  --contain-root-instance true \
  --downstream-range ALL_INSTANCE
```

说明：`--root-instance-id` 必须传 JSON 对象 `{"Id":"t_xxx"}`，不能传裸字符串或 JSON 字符串。

### 6. fix-data 验证方法正确（模式②）

#### ✅ CORRECT — 用 get-physical-instance-log 验证 taskrun

```bash
aliyun dataphin-public get-physical-instance-log \
  --env PROD \
  --project-id "7295715579274176" \
  --instance-id t_8127255632277340160_20260629_8127264978126241798 \
  | jq '[.TaskrunLogList[] | {TaskrunId, Status, StartTime, EndTime}]'
```

说明：fix-data 不创建新实例，而是在同一实例下创建新 taskrun。验证必须查 taskrun 日志，不能用 `list-instances`（实例状态不变）。

## 错误模式

- ❌ 硬编码 AK/SK 或真实 tenant/project ID 到 Skill 示例中。
- ❌ 使用 `dataphin` 旧 CLI 二进制命令。
- ❌ `operate-instance` 直接传裸实例 ID：
  ```bash
  --instance-id-list t_xxx
  ```
- ❌ 未带 `--user-agent` 调用 `aliyun` API 命令。
- ❌ 未确认就批量重跑多个项目的同名实例。
- ❌ fix-data 的 `--root-instance-id` 传裸字符串：
  ```bash
  --root-instance-id t_xxx
  ```
  会报 `invalid JSON: invalid character '_' in literal true`。
- ❌ fix-data 的 `--root-instance-id` 传 JSON 字符串（带引号）：
  ```bash
  --root-instance-id '"t_xxx"'
  ```
  会报 `Expected BEGIN_OBJECT but was STRING at path $.rootInstanceId`。
- ❌ fix-data 后用 `list-instances` 验证重跑结果（实例状态不变，无法反映新 taskrun）。

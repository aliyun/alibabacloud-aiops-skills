---
name: get-batch-task-info-by-name
description: |-
  仅知道离线任务名称时，获取任务完整详情（含代码、调度、上游、FileId、NodeId、DagId）。 触发场景：知道任务名但不知道 FileId / 想查看任务代码和调度配置 / 想获取任务的 NodeId 或 DagId / 想查任务上下游关系。 方法：list-files 按 Name 反查 FileId → get-batch-task-info 拿详情。 注意：不要用 ops list-nodes --search-text（入参严格且常报 InternalError）。 触发词：按任务名查询、查看任务代码、查看任务调度、获取 FileId、获取 NodeId、list-files、get-batch-task-info、任务详情。
---
# 按任务名获取离线（batch）任务详情 skill

## 适用场景

- 用户只给了离线任务的**名称**（如 `zh_down`），未给 `file-id`，需要拿到任务代码 / 调度 / 上游 / DagId 等详情
- 编辑、提交、补数据前先读当前配置作为模板（参考 [update-batch-task.md](./update-batch-task.md) §"读取当前配置"）
- 排查 `NodeWithoutUpstream` 等问题时需要看 `TaskInfo.UpStreamList`

> Dataphin 没有"按名称直接 get 任务"的单步 API，必须先在目录树里反查 FileId，再拿 FileId 取详情。

## 核心命令

| 步骤 | 命令 | 关键产物 |
|---|---|---|
| 1. 列目录树按 Name 反查 | `aliyun dataphin-public list-files --category codeManage --recursive true --directory / --env DEV` | 任务的 `Id`（即 FileId） |
| 2. 用 FileId 取详情 | `aliyun dataphin-public get-batch-task-info --file-id <Id>` | `TaskInfo.Code` / `TaskType` / `SchedulePeriod` / `CronExpression` / `UpStreamList` / `DagId` 等 |

## 标准两步操作

```bash
TENANT_ID=<tenant-id>
PROJECT_ID=<project-id>
TASK_NAME=zh_down

# 1) 在 codeManage 目录树里递归找同名非目录文件，取 Id
FILE_ID=$(aliyun dataphin-public list-files \
  --tenant-id $TENANT_ID --project-id $PROJECT_ID \
  --category codeManage --directory "/" --recursive true --env DEV \
  --output json \
  | jq -r --arg n "$TASK_NAME" \
      '.FileList[] | select(.Name == $n and .FileType != "directory") | .Id' \
  | head -n1)

echo "FileId = $FILE_ID"
# => <file-id>

# 2) 用 FileId 拉任务详情
aliyun dataphin-public get-batch-task-info \
  --tenant-id $TENANT_ID --project-id $PROJECT_ID \
  --file-id $FILE_ID --output json
```

返回结构关键字段（节选）：

```json
{
  "TaskInfo": {
    "FileId": 7274117084921600,
    "Name": "zh_down",
    "NodeId": "n_7943347812720771072",
    "TaskType": 10,                    // 10=Shell, 1=Python, 5=Hive_SQL, 21=MaxCompute_SQL ...
    "SchedulePeriod": "DAILY",
    "CronExpression": "0 0 0 * * ?",
    "Priority": 5,
    "Code": "echo 1",                  // ★ 任务代码
    "DagId": "d_7859751600056107008",  // 项目级常量，可推根节点
    "UpStreamList": [],                // 显式上游（不含自动挂载的虚拟根节点）
    "ParamList": [],
    "OwnerName": "SuperAdmin",
    "Published": true
  },
  "Code": "OK", "Success": true
}
```

## 常用过滤套路

- 只拿代码：`... | jq -r '.TaskInfo.Code'`
- 拿 NodeId（运维/补数据用）：`... | jq -r '.TaskInfo.NodeId'`
- 拿 DagId（推根节点用）：`... | jq -r '.TaskInfo.DagId'`
- 同名匹配多个 → 加 Directory 二次精确：`select(.Name == $n and .Directory == "/舟衡/")`
- 模糊匹配查近名：`.FileList[] | select(.Name | test("zh_down"; "i"))`

## ✗ 不要用的方式（历史踩坑）

| 方式 | 为什么不行 |
|---|---|
| `aliyun dataphin-public list-nodes --search-text <name>` | 该接口入参严格（必传 `--node-biz-type` / `--node-sub-biz-type-list`），且对部分 FileType 不返回；实测频繁返回 `DPN.Commons.InternalError` |
| 把任务 Name 当 `--file-id` 传 | `--file-id` 只接受数字 Id，不接受字符串名 |
| 不带 `--recursive true` 列目录 | 默认只返回当前目录第一层，藏在子目录（如 `/舟衡/`）的任务找不到 |
| `--env PROD` 找开发态任务 | DEV/PROD 是两套环境标识，开发中的任务通常只在 DEV 可见 |

## 常见坑

1. **`--directory` 要写根 `/`** + `--recursive true`，否则只看到一层目录
2. **`--category` 必传 `codeManage`**：离线 SQL/Shell/Python 任务、即席查询、管道分别对应不同 category；离线 batch 任务只在 `codeManage` 下
3. **`Content` 字段在 list-files 永远是 null**：代码必须从 `get-batch-task-info` 的 `TaskInfo.Code` 取，不要指望 list-files 直接拿到
4. **同名任务**：项目内允许不同目录下同名，jq 出多条时用 `Directory` 字段消歧
5. **目录类型干扰**：必须 `select(.FileType != "directory")`，否则可能拿到目录节点的 Id 导致 `get-batch-task-info` 报错

## 相关 skill / 命令

- [find-tenant-root-node.md](./find-tenant-root-node.md) — 拿到 `DagId` 后推算虚拟根节点 Name
- [update-batch-task.md](./update-batch-task.md) — 读出 TaskInfo 作为 Update payload 模板
- [submit-batch-task.md](./submit-batch-task.md) — 提交前确认任务状态
- `aliyun dataphin-public get-batch-task-versions --file-id <Id>` — 查历史版本列表
- `aliyun dataphin-public get-batch-task-info-by-version --file-id <Id> --version <v>` — 取指定历史版本详情

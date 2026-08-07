---
name: find-tenant-root-node
description: |-
  查找租户的虚拟根节点（virtual_root_node_xxx）。 触发场景：创建任务时需要指定上游依赖为"根节点" / 遇到 NodeWithoutUpstream 报错 / 新任务 UpStreamList 为空需要挂默认上游 / 需要获取项目 DagId。 方法：读任意已有任务的 TaskInfo.DagId → 去掉 d_ 前缀 → 拼出 virtual_root_node_数字。 注意：后缀不是 project_id 也不是 tenant_id，是项目 DagId 的数字部分。 触发词：根节点、虚拟根节点、virtual_root_node、上游依赖、NodeWithoutUpstream、UpStreamList 为空、DagId、默认上游。
---
# 查找租户根节点 skill

## 背景知识（必读）

Dataphin 的"项目根节点"是**每个项目自动生成的虚拟节点**，用于承接未声明上游的任务。其 Name / OutputName 形如：

```
virtual_root_node_<DagId_num>
```

### 命名规律（实测验证）

**后缀 `<DagId_num>` = 项目 DagId 去掉 `d_` 前缀后的数字部分**，与 project-id、tenant-id 均无关。

- 同项目所有任务共享同一个 `DagId`（项目级常量）
- 读任一任务 `dev get-batch-task-info` 返回的 `TaskInfo.DagId` 即可推出根节点 Name
- 服务端在根节点 `Description` 字段亲自写明："`virtual root node of Dag[d_xxx]`"，可与推导结果互相印证

### 重要事实

- 填 `--input-list` / `UpStreamList.SourceNodeId` **惯用 Name 形式**（`virtual_root_node_xxx`），不填物理 `n_xxx`
- 根节点 Name 不随 env 变（DEV/PROD 同名）

## 适用场景

- 创建 / 提交离线批任务前需要填 `--input-list`，但用户未指定上游 → 挂根节点
- 遇到 `DPN.DataProcess.NodeWithoutUpstream` 错误 → 补齐根节点

## 查询步骤

### 方式 A：项目内已有任务文件

```bash
TENANT_ID=<tenant-id>
PROJECT_ID=<project-id>

# 1) 任取项目内一个非目录文件的 FileId
ANY_FILE_ID=$(aliyun dataphin-public list-files \
  --tenant-id $TENANT_ID --project-id $PROJECT_ID \
  --category codeManage --directory "/" --recursive true --env DEV \
  | jq -r '.FileList[] | select(.FileType != "directory") | .Id' \
  | head -n1)

# 2) 读 DagId，去掉 d_ 前缀，拼根节点 Name
DAG_NUM=$(aliyun dataphin-public get-batch-task-info \
  --tenant-id $TENANT_ID --project-id $PROJECT_ID --file-id $ANY_FILE_ID \
  | jq -r '.TaskInfo.DagId' | sed 's/^d_//')

ROOT_NODE="virtual_root_node_${DAG_NUM}"
echo "$ROOT_NODE"
# => virtual_root_node_<DagId_num>
```

### 方式 B：空项目（无任何任务文件）

```bash
# 先建一个任务文件（无需提交）
FILE_ID=$(aliyun dataphin-public create-batch-task \
  --tenant-id $TENANT_ID --project-id $PROJECT_ID \
  --directory / --batch-task-name _tmp_for_dagid \
  --description "temp" --schedule-type 3 --task-type 999 \
  --output json | jq -r '.CreateResult.FileId')

# 读 DagId
DAG_NUM=$(aliyun dataphin-public get-batch-task-info \
  --tenant-id $TENANT_ID --project-id $PROJECT_ID --file-id $FILE_ID \
  --output json | jq -r '.TaskInfo.DagId | sub("^d_";"")')

ROOT_NODE="virtual_root_node_${DAG_NUM}"
echo "$ROOT_NODE"
```

> ℹ `create-batch-task` 后即可读取 DagId，无需先提交。

拿到 `$ROOT_NODE` 后直接用：

```bash
aliyun dataphin-public update-batch-task \
  --tenant-id $TENANT_ID --project-id $PROJECT_ID --file-id <new-fid> \
  --batch-task-name my_shell --code "echo hello" --task-type 10 \
  --input-list "[\"${ROOT_NODE}\"]"
```

## ✗ 不要用的方式（历史踩坑）

| 方式 | 为什么不行 |
|---|---|
| 按命名规则拼 `virtual_root_node_<project-id>` / `<tenant-id>` | 后缀是 DagId 数字，与 project-id、tenant-id 均无关；拼错触发 `DPN.OP.NodeNotExist` |
| `ops list-nodes --search-text virtual_root_node` | list-nodes 只返回 SCRIPT/LOGICAL_TABLE 真实任务节点，虚拟根节点不在返回范围 |
| 读 `dev get-batch-task-info` 的 `TaskInfo.UpStreamList` 找根节点 | 该字段只含用户显式声明的上游，自动挂的根节点**不**在其中 |
| `ops get-physical-node-by-output-name` 作为发现手段 | 需先知完整 Name；仅可用作事后验证 / 取元数据 |

## 常见坑

1. **空项目也有 DagId**：只要 `create-batch-task` 创建了文件（即使未提交），`get-batch-task-info` 就能返回 `TaskInfo.DagId`。无需先提交 MANUAL 任务触发生成。
2. **同租户项目可能共享同一个 DagId**：实测发现同租户下不同项目（包括 BASIC 和 DEV_PROD 模式）共享相同 DagId，因此根节点的名称相同。但为安全起见，仍建议每次从目标项目内读取确认。
3. **`--input-list` 必须 JSON 数组字符串**：`'["virtual_root_node_xxx"]'`，不能裸传字符串
4. **`UpStreamList` 中的 `SourceNodeId` 和 `SourceNodeOutputName` 都填 Name 形式**：`virtual_root_node_xxx`，不填物理 `n_xxx`。填错触发 `DPN.DataProcess.NodeUpstreamNotExist`
5. **基础模式（BASIC）项目提交时还需指定 `--node-output-name-list`**：否则报 `NodeWithoutDownstream`，详见 [submit-batch-task.md](./submit-batch-task.md)

## 相关命令

- [submit-batch-task.md](./submit-batch-task.md) — 提交任务时用 `UpStreamList` 显式挂根节点
- [update-batch-task.md](./update-batch-task.md) — 任务已存在时改上游
- `aliyun dataphin-public list-files` — 枚举项目内文件拿任意 FileId
- `aliyun dataphin-public get-batch-task-info` — 读任务 DagId（唯一发现路径）
- `aliyun dataphin-public list-projects` — 先拿 ProjectId

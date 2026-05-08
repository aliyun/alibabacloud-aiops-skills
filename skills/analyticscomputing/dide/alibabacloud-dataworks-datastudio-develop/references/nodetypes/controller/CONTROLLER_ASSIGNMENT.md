# Assignment Node（CONTROLLER_ASSIGNMENT）

## Overview

The assignment node is a controller node that passes script execution results to downstream nodes. After execution, it automatically assigns the **last output** to `${outputs}` variable（节点上下文输出变量）; downstream nodes reference it via `inputs.variables` + `inputName`.

```
Assignment Node A                          Downstream Node B
  outputs.variables:                         inputs.variables:
    name: "outputs"              ──►           name: "outputs"
    value: "${outputs}"                        value: "${outputs}"
                                               inputName: "input_var"

                                             代码中使用 ${input_var} 访问赋值结果
```

**Key restriction**: Parameters can only be passed to **direct downstream (one level)** child nodes; cross-level passing is not supported.

## Supported Languages and Output Rules

| Language | script.language | Code File language Field | Output Rule | Transfer Format |
|----------|----------------|--------------------------|-------------|-----------------|
| MaxCompute SQL | `odps` | `"odps"` | The result of the last `SELECT` statement | 2D array `[["v1","v2"],["v3","v4"]]` |
| Python 2 | `python2` | `"python2"` | The output of the last `print` statement | 1D array `["v1","v2","v3"]` |
| Shell | `shell` | `"shell"` | The output of the last `echo` statement | 1D array `["v1","v2","v3"]` |

> **Note**: When fetched from the API, `script.language` may appear as `odps-sql`, `python2`, `shell-script`. When creating nodes, use the short forms above (`odps`, `python`, `shell`).

Code examples for each language:

```sql
-- MaxCompute SQL: The result of the last SELECT statement is assigned to outputs
select col1, col2 from my_table where dt = '${bizdate}';
```

```python
# Python 2: The output of the last print statement is assigned to outputs
print("value1,value2,value3")
```

```bash
# Shell: The output of the last echo statement is assigned to outputs
echo "value1,value2,value3"
```

When output content contains commas, use `\,` to escape: `echo "Electronics,Clothing\, Shoes"` → `["Electronics", "Clothing, Shoes"]`

## Code Storage Format

赋值节点的代码文件使用语言原生文件，后缀与语言保持一致：

| Language | Code File Extension | Example |
|----------|-------------------|---------|
| Shell | `.sh` | `assignment_shell.sh` |
| Python 2 | `.py` | `assignment_python.py` |
| MaxCompute SQL | `.sql` | `assignment_odps.sql` |

build.py 会自动读取代码文件内容并嵌入 `script.content`。

### Three-Language Code File Examples

**Shell** (`assignment_shell.sh`):
```bash
echo "this is assign shell output value"
```

**Python 2** (`assignment_python.py`):
```python
print("this is assign python2 output value")
```

**MaxCompute SQL** (`assignment_odps.sql`):
```sql
select "this is assign odps output value"
```

## Template: 3-File Structure

See [assets/templates/08-assignment-node/](../../../assets/templates/08-assignment-node/) for ready-to-use templates, one per language:

```
08-assignment-node/
├── assignment_shell/                  # Shell 赋值节点
│   ├── assignment_shell.spec.json
│   ├── assignment_shell.sh
│   └── dataworks.properties
├── assignment_odps/                   # MaxCompute SQL 赋值节点
│   ├── assignment_odps.spec.json
│   ├── assignment_odps.sql
│   └── dataworks.properties
├── assignment_python/                 # Python 2 赋值节点
│   ├── assignment_python.spec.json
│   ├── assignment_python.py
│   └── dataworks.properties
└── README.md
```

### Minimal spec.json (Shell)

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "assignment_shell",
        "script": {
          "path": "assignment_shell",
          "language": "shell",
          "runtime": { "command": "CONTROLLER_ASSIGNMENT" },
          "content": ""
        },
        "runtimeResource": {
          "resourceGroup": "${spec.runtimeResource.resourceGroup}"
        },
        "datasource": {
          "name": "${spec.datasource.name}",
          "type": "odps"
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 00 00 * * ?",
          "startTime": "1970-01-01 00:00:00",
          "endTime": "9999-01-01 00:00:00",
          "timezone": "Asia/Shanghai"
        },
        "outputs": {
          "nodeOutputs": [
            {
              "data": "${projectIdentifier}.assignment_shell"
            }
          ],
          "variables": [
            {
              "name": "outputs",
              "scope": "NodeContext",
              "type": "NodeOutput",
              "value": "${outputs}"
            }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "assignment_shell",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root" }
        ]
      }
    ]
  }
}
```

### Minimal spec.json (MaxCompute SQL)

Only the `script` block differs; other fields (trigger, runtimeResource, outputs, inputs, dependencies) are identical to the Shell example above.

```json
"script": {
  "path": "assignment_odps",
  "language": "odps",
  "runtime": { "command": "CONTROLLER_ASSIGNMENT" },
  "content": ""
}
```

Code file `assignment_odps.sql`: `select "this is assign odps output value"`

### Minimal spec.json (Python 2)

```json
"script": {
  "path": "assignment_python",
  "language": "python",
  "runtime": { "command": "CONTROLLER_ASSIGNMENT" },
  "content": ""
}
```

Code file `assignment_python.py`: `print("this is assign python2 output value")`

### datasource Requirement

The assignment node **requires a datasource** even for Shell and Python 2 languages. Typically use an ODPS type datasource:

```json
"datasource": {
  "name": "your_odps_datasource",
  "type": "odps"
}
```

## Parameter Passing Configuration

赋值节点通过 `outputs.variables` 声明输出变量，下游节点通过 `inputs.variables` + `inputName` 接收。

> **`type: "NodeOutput"` 含义**: 该变量类型特指具备赋值能力的节点的代码执行输出内容。目前支持 `type: "NodeOutput"` 的节点类型有：**赋值节点 (CONTROLLER_ASSIGNMENT)**、**HologresSQL**。

```
赋值节点 A                              下游节点 B
outputs.variables:                      inputs.variables:
  name: "outputs"                         name: "outputs"
  scope: "NodeContext"         ──►        scope: "NodeContext"
  type: "NodeOutput"                      type: "NodeOutput"
  value: "${outputs}"                     value: "${outputs}"
                                          inputName: "input_var"  ← 下游访问名
                                        
                                        代码中使用 ${input_var} 获取赋值结果
```

### 1. 赋值节点 outputs.variables

赋值节点**必须**配置一个节点上下文输出变量，表示代码输出的内容将存入该变量：

```json
"outputs": {
  "nodeOutputs": [
    {
      "data": "${projectIdentifier}.assignment_shell"
    }
  ],
  "variables": [
    {
      "name": "outputs",
      "scope": "NodeContext",
      "type": "NodeOutput",
      "value": "${outputs}"
    }
  ]
}
```

- `name` 固定为 `"outputs"`
- `value` 固定为 `"${outputs}"`，代表脚本执行的最后一条输出
- `scope: "NodeContext"` 表示变量作用域为节点上下文
- `type: "NodeOutput"` 特指**具备赋值能力的节点的代码执行输出内容**的上下文变量类型。目前支持该类型的节点有：**赋值节点 (CONTROLLER_ASSIGNMENT)**、**HologresSQL**

### 2. 下游节点 inputs.variables

直接下游节点在 `inputs.variables` 中声明同名变量，并通过 `inputName` 指定在代码中的访问名。

#### 在工作流（CycleWorkflow）中创建时

工作流内的节点可以通过节点名引用，不需要 `referenceVariable` 字段：

```json
"inputs": {
  "variables": [
    {
      "name": "outputs",
      "scope": "NodeContext",
      "type": "NodeOutput",
      "value": "${outputs}",
      "inputName": "input_var"
    }
  ]
}
```

#### 通过 create-node/update-node 单独创建或修改时

通过 API 单独创建或更新节点时，**必须**包含 `referenceVariable` 字段指定赋值来源节点：

```json
"inputs": {
  "variables": [
    {
      "name": "outputs",
      "scope": "NodeContext",
      "type": "NodeOutput",
      "value": "${outputs}",
      "inputName": "input_var",
      "referenceVariable": {
        "name": "outputs",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "value": "${outputs}",
        "node": {
          "nodeId": "<upstream_node_id>"
        }
      }
    }
  ]
}
```

- `referenceVariable`: 指向上游赋值节点的输出变量定义，仅在通过 create-node/update-node API 单独操作时需要
  - `name`/`scope`/`type`/`value` 与赋值节点的 `outputs.variables` 保持一致
  - `node.nodeId`: 上游赋值节点的系统数字 ID（通过 `get-node` / `list-nodes` 获取）

> **⚠️ 不要在 `spec.dependencies` 中重复声明同一条上游依赖。** 当 `inputs.variables[].referenceVariable` 已经指向某个上游赋值节点时，服务端会从该 `referenceVariable` 隐式生成一条依赖边（以上游**系统数字 ID** 为 `output`）。如果同时再在 `spec.dependencies` 中显式声明一条以**命名 output**（`{projectIdentifier}.{nodeName}`）指向同一上游的依赖，赋值节点的 `outputs.nodeOutputs` 同时包含数字 ID 和命名 output 两条记录，两套声明各自匹配到不同 output、互不去重，最终 `list-node-dependencies` 会出现 **2 条** 指向同一上游的 Manual 依赖边。规则：**有 `referenceVariable` 就不要在 `dependencies` 里再写这一条上游**，让 `referenceVariable` 作为这条依赖边的唯一来源。

字段说明：
- `name`/`scope`/`type`/`value`（外层）与赋值节点的 `outputs.variables` 保持一致
- `inputName`: 下游节点代码中通过 `${input_var}` 访问赋值节点的输出内容

> **⚠️ 常见错误：不要使用 `script.parameters` 接收赋值输出。** `script.parameters` 用于调度参数（如 `$yyyymmdd`），上下文参数及赋值节点的输出**必须**通过 `inputs.variables` + `inputName` 接收。将 `type: "NodeOutput"` 的变量放入 `script.parameters` 不会生效。

> **⚠️ 节点间依赖关系统一通过 `spec.dependencies` 配置**，不要在节点对象上声明其他依赖字段。

### 3. 下游节点代码中使用

在下游节点的代码中，通过 `${inputName}` 引用赋值节点传递的值：

```sql
-- 下游 ODPS SQL 节点，使用赋值节点的输出
select * from my_table where user_id in (${input_var});
```

```bash
# 下游 Shell 节点
echo "赋值节点输出: ${input_var}"
```

## Full Examples

### Example 1: Shell Assignment Node

Assign a shell command output and pass to downstream.

**assignment_shell.sh:**
```bash
echo "this is assign shell output value"
```

The output `"this is assign shell output value"` is passed as `["this is assign shell output value"]`.

### Example 2: Python 2 Assignment Node

**assignment_python.py:**
```python
print("this is assign python2 output value")
```

The output `"this is assign python2 output value"` is passed as `["this is assign python2 output value"]`.

### Example 3: MaxCompute SQL Assignment Node

**assignment_odps.sql:**
```sql
select "this is assign odps output value"
```

The output is passed as a 2D array: `[["this is assign odps output value"]]`.

### Example 4: Full Workflow — Assignment + Downstream Consumer

赋值节点 (MaxCompute SQL) 将查询结果传递给下游 ODPS SQL 节点：

```json
{
  "version": "2.0.0",
  "kind": "CycleWorkflow",
  "spec": {
    "nodes": [
      {
        "name": "sql_assign_1",
        "script": {
          "path": "sql_assign_1",
          "language": "odps",
          "content": "",
          "runtime": { "command": "CONTROLLER_ASSIGNMENT" }
        },
        "runtimeResource": { "resourceGroup": "S_res_group_default" },
        "datasource": { "name": "odps_first", "type": "odps" },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 00 00 * * ?",
          "startTime": "1970-01-01 00:00:00",
          "endTime": "9999-01-01 00:00:00",
          "timezone": "Asia/Shanghai"
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.sql_assign_1" }
          ],
          "variables": [
            {
              "name": "outputs",
              "scope": "NodeContext",
              "type": "NodeOutput",
              "value": "${outputs}"
            }
          ]
        }
      },
      {
        "name": "downstream_node",
        "script": {
          "path": "downstream_node",
          "language": "odps-sql",
          "runtime": { "command": "ODPS_SQL" },
          "content": "select * from my_table where user_id in (${assign_result});"
        },
        "runtimeResource": { "resourceGroup": "S_res_group_default" },
        "datasource": { "name": "odps_first", "type": "odps" },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 00 00 * * ?",
          "startTime": "1970-01-01 00:00:00",
          "endTime": "9999-01-01 00:00:00",
          "timezone": "Asia/Shanghai"
        },
        "inputs": {
          "variables": [
            {
              "name": "outputs",
              "scope": "NodeContext",
              "type": "NodeOutput",
              "value": "${outputs}",
              "inputName": "assign_result"
            }
          ]
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.downstream_node" }
          ]
        }
      }
    ],
    "flow": [
      {
        "nodeId": "sql_assign_1",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root" }
        ]
      },
      {
        "nodeId": "downstream_node",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}.sql_assign_1" }
        ]
      }
    ]
  }
}
```

### Example 5: 通过 create-node API 单独创建下游节点（需要 `referenceVariable` 字段）

当赋值节点已存在（如名为 `sql_assign_1`），通过 create-node 单独创建下游节点时，`inputs.variables` 必须包含 `referenceVariable`。**注意：此场景下不要再写 `spec.dependencies` 指向同一个上游赋值节点**——`referenceVariable` 已经会让服务端隐式生成依赖边，重复声明会得到两条指向同一上游的 Manual 依赖（详见上文 `referenceVariable` 字段说明中的 ⚠️）。

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "downstream_consumer",
        "id": "downstream_consumer",
        "script": {
          "path": "downstream_consumer",
          "language": "odps-sql",
          "runtime": { "command": "ODPS_SQL" },
          "content": "select * from my_table where id in (${assign_result});"
        },
        "inputs": {
          "variables": [
            {
              "name": "outputs",
              "scope": "NodeContext",
              "type": "NodeOutput",
              "value": "${outputs}",
              "inputName": "assign_result",
              "referenceVariable": {
                "name": "outputs",
                "scope": "NodeContext",
                "type": "NodeOutput",
                "value": "${outputs}",
                "node": {
                  "nodeId": "700000123456"
                }
              }
            }
          ]
        }
      }
    ]
    // ⚠️ 不要再写 "dependencies": [...] 指向 sql_assign_1：
    //    referenceVariable 已经会让服务端隐式生成这条依赖边，
    //    重复声明会形成 2 条 Manual 依赖（一条以数字 ID、一条以命名 output 为 output）。
  }
}
```

> **注意**：`referenceVariable.node.nodeId` 为上游赋值节点的系统数字 ID（通过 `get-node` / `list-nodes` 获取）。如果下游节点还有**其他**非赋值节点的上游依赖（例如普通节点输出），那些依赖仍然通过 `spec.dependencies` 显式声明；只有"已经被 `referenceVariable` 覆盖到的赋值节点上游"才需要从 `dependencies` 中省略。

## API Exported Format vs Template Format

When fetching assignment nodes from the API (e.g., get-node), the format differs from the template format:

| Field | API Exported | Template (3-file) |
|-------|-------------|-------------------|
| `script.language` | `shell-script`, `odps-sql`, `python2` | `shell`, `odps`, `python` |
| `script.content` | Inline code string | Empty (filled by build.py) |
| Code file | N/A (embedded in spec) | `.sh` / `.py` / `.sql` (原生语言文件) |
| `kind` | `CycleWorkflow` | `Node` or `CycleWorkflow` |
| `outputs.variables` | Includes `id`, `referenceVariable` | Simplified (no `id` needed for creation) |

## Restrictions

| Restriction | Details |
|-------------|---------|
| Pass level | Can only pass to direct downstream (one level) child nodes |
| Pass size | Maximum 2MB; exceeding this will cause execution failure |
| Code comments | Comments are not supported |
| SQL syntax | MaxCompute SQL does not support WITH syntax |
| Python version | Only Python 2 is supported |
| Comma escaping | Use `\,` to escape commas in output |
| datasource | Required for all languages (typically ODPS type) |

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `find no select sql in sql assignment!` | SQL mode missing SELECT | Ensure code contains a SELECT query |
| `OutPut Result is null, cannot handle!` | Python/Shell missing output statement | Add `print()` or `echo` |
| Output array split unexpectedly | Comma not escaped | Use `\,` to escape |
| Downstream node cannot obtain parameters | Cross-level reference or inputs.variables configuration error | Only reference direct upstream; check inputName |
| Node execution failed without specific error | Output exceeds 2MB | Simplify query results |
| Missing datasource error | datasource not configured | Add datasource (ODPS type) even for Shell/Python nodes |
| 下游节点 `${input_var}` 未替换 | 误用 `script.parameters` 而非 `inputs.variables` | 赋值输出**必须**通过 `inputs.variables` + `inputName` 接收 |
| create-node/update-node 添加 inputs.variables 报错 | 缺少 `referenceVariable` 字段 | 单独创建/更新节点时 `inputs.variables` 需要包含 `referenceVariable: {type, scope, nodeId, nodeOutput}` |
| `runtimeResource.resourceGroup` 报错 | 使用了人类可读名称（如 `cx_res_4`）而非资源组 ID | 使用 `list-resource-groups` 获取实际资源组 ID（如 `Serverless_res_group_...`） |
| `list-node-dependencies` 返回 2 条指向同一个上游赋值节点的 Manual 依赖 | create-node/update-node 时同时写了 `inputs.variables[].referenceVariable` **和** `spec.dependencies` 指向同一个上游 | 删掉 `spec.dependencies` 中那条重复的上游依赖，让 `referenceVariable` 作为唯一来源；其他非赋值节点的上游仍正常写在 `dependencies` 中 |

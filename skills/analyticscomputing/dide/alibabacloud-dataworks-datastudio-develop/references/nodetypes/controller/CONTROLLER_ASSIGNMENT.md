# Assignment Node（CONTROLLER_ASSIGNMENT）

## Overview

The assignment node is a controller node that passes script execution results to downstream nodes.After execution, it automatically assigns the **last output** to `${outputs}` variable; downstream nodes reference it via `inputs.variables` .

```
Assignment Node A (executes script -> produces ${outputs})
    │
    ▼
Downstream Node B (references upstream outputs via ${param})
```

**Key restriction**: Parameters can only be passed to **direct downstream (one level)** child nodes; cross-level passing is not supported.

## Supported Languages and Output Rules

| Language | script.language | Output Rule | Transfer Format |
|------|----------------|-------------|---------|
| MaxCompute SQL | `odps` | The result of the last `SELECT` statement | 2D array `[["v1","v2"],["v3","v4"]]` |
| Python 2 | `python` | The output of the last `print` statement | 1D array `["v1","v2","v3"]` |
| Shell | `shell` | The output of the last `echo` statement | 1D array `["v1","v2","v3"]` |

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

The assignment node's code is stored in JSON format (extension `.assign.json`), containing two fields:

```json
{"language": "odps", "content": "select 1"}
```

In `script.content`, it can be plain text (e.g., `"select 1"`) or a complete JSON string (e.g., `"{\"language\":\"odps\",\"content\":\"select 1\"}"`); the system handles both formats automatically.

## Parameter Passing Configuration

### Assignment Node outputs.variables

Declare the output variables of this node for downstream reference:

```json
"outputs": {
  "variables": [
    {
      "artifactType": "Variable",
      "name": "my_assign_node",
      "scope": "NodeContext",
      "type": "NodeOutput",
      "value": "${outputs}",
      "node": {"output": "<this_node_ID>"}
    }
  ],
  "outputs": [
    {
      "artifactType": "NodeOutput",
      "data": "<this_node_ID>",
      "refTableName": "my_assign_node"
    }
  ]
}
```

### Downstream Node inputs.variables

Reference the output of the upstream assignment node:

```json
"inputs": {
  "variables": [
    {
      "artifactType": "Variable",
      "name": "my_assign_node",
      "scope": "NodeContext",
      "type": "NodeOutput",
      "value": "${outputs}",
      "node": {"output": "<upstream_assignment_node_ID>"}
    }
  ]
}
```

In the downstream node code, use `${my_assign_node}` to reference the passed value.

### Downstream Node script.parameters

References must also be declared in parameters:

```json
"parameters": [
  {
    "artifactType": "Variable",
    "name": "my_assign_node",
    "scope": "NodeContext",
    "type": "NodeOutput",
    "value": "${outputs}",
    "node": {"output": "<upstream_assignment_node_ID>"}
  }
]
```

## Full Example

Assignment node (MaxCompute SQL, passing query results to downstream):

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "sql_assign_1",
        "script": {
          "path": "sql_assign_1",
          "language": "odps",
          "content": "select user_id, user_name from dim_user where status = 1;",
          "runtime": {
            "command": "CONTROLLER_ASSIGNMENT"
          }
        },
        "outputs": {
          "variables": [
            {
              "artifactType": "Variable",
              "name": "sql_assign_1",
              "scope": "NodeContext",
              "type": "NodeOutput",
              "value": "${outputs}",
              "node": {"output": "${projectIdentifier}.sql_assign_1"}
            }
          ],
          "nodeOutputs": [
            {
              "data": "${projectIdentifier}.sql_assign_1",
              "artifactType": "NodeOutput"
            }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "sql_assign_1",
        "depends": [
          {"type": "Normal", "output": "${projectIdentifier}_root"}
        ]
      }
    ]
  }
}
```

Downstream node referencing assignment results:

```json
{
  "name": "downstream_node",
  "script": {
    "path": "downstream_node",
    "runtime": {"command": "ODPS_SQL"},
    "content": "select * from my_table where user_id in (${sql_assign_1});",
    "parameters": [
      {
        "artifactType": "Variable",
        "name": "sql_assign_1",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "value": "${outputs}",
        "node": {"output": "${projectIdentifier}.sql_assign_1"}
      }
    ]
  },
  "inputs": {
    "variables": [
      {
        "artifactType": "Variable",
        "name": "sql_assign_1",
        "scope": "NodeContext",
        "type": "NodeOutput",
        "value": "${outputs}",
        "node": {"output": "${projectIdentifier}.sql_assign_1"}
      }
    ],
    "nodeOutputs": [
      {
        "data": "${projectIdentifier}.sql_assign_1",
        "artifactType": "NodeOutput"
      }
    ]
  }
}
```

## Restrictions

| Restriction | Details |
|--------|------|
| Pass level | Can only pass to direct downstream (one level) child nodes |
| Pass size | Maximum 2MB; exceeding this will cause execution failure |
| Code comments | Comments are not supported |
| SQL syntax | MaxCompute SQL does not support WITH syntax |
| Python version | Only Python 2 is supported |
| Comma escaping | Use `\,` to escape commas in output |

## Common Errors

| Error | Cause | Solution |
|------|------|------|
| `find no select sql in sql assignment!` | SQL mode missing SELECT | Ensure code contains a SELECT query |
| `OutPut Result is null, cannot handle!` | Python/Shell missing output statement | Add `print()` or `echo` |
| Output array split unexpectedly | Comma not escaped | Use `\,` to escape |
| Downstream node cannot obtain parameters | Cross-level reference or inputs.variables configuration error | Only reference direct upstream; check node.output |
| Node execution failed without specific error | Output exceeds 2MB | Simplify query results |

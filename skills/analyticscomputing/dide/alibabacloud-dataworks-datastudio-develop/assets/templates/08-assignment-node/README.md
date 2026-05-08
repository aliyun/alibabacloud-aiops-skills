# Example 08: Assignment Node

Assignment node (CONTROLLER_ASSIGNMENT) executes a script and passes the result to downstream nodes via `${outputs}`. Three language variants are provided, one template per language.

## File Structure

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

## Language Comparison

| Template | script.language | Code File | Output Rule | Output Format |
|----------|----------------|-----------|-------------|---------------|
| assignment_shell | `shell` | `.sh` | Last `echo` output | 1D array `["v1","v2","v3"]` |
| assignment_python | `python` | `.py` | Last `print` output | 1D array `["v1","v2","v3"]` |
| assignment_odps | `odps` | `.sql` | Last `SELECT` result | 2D array `[["v1","v2"],["v3","v4"]]` |

## Key Points

- Code file使用语言原生文件（`.sh`/`.py`/`.sql`），build.py 自动嵌入 `script.content`
- `datasource` (ODPS type) is **required** for all three languages
- `runtime.command` is always `CONTROLLER_ASSIGNMENT`
- Output is automatically assigned to `${outputs}` variable for downstream consumption

## Creation Steps

1. Copy the desired language template directory
2. Rename node name/path in spec.json
3. Edit the code file (`.sh`/`.py`/`.sql`) with your actual code
4. Edit dataworks.properties with project-specific values
5. Build: `python scripts/build.py ./assignment_shell`

## Downstream Parameter Passing

See [CONTROLLER_ASSIGNMENT.md](../../../references/nodetypes/controller/CONTROLLER_ASSIGNMENT.md) for full parameter passing configuration.

# PyODPS 3（PYODPS3）

## Overview

- Compute engine: `ODPS`
- Content format: python
- Extension: `.py`
- Code: 1221
- Data source type: `odps`
- Description: PyODPS 3 script (Python 3, operates on MaxCompute)

The PyODPS 3 node is based on the MaxCompute Python SDK (PyODPS) and allows writing code in Python 3 to operate on MaxCompute. It supports executing SQL, DataFrame processing, and resource management. It is recommended that new projects use this node type instead of [PYODPS](./PYODPS.md).

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Core Features

### Built-in Global Variables

The following global variables are preset in the node and do not need to be defined manually:

- **`odps` or `o`**: ODPS entry object for directly calling MaxCompute APIs
- **`args`**: Dictionary-format scheduling parameter container

```python
# PyODPS 3 example
print(o.exist_table('my_table'))

# Get scheduling parameters
bizdate = args['bizdate']
print(f'bizdate: {bizdate}')

# Execute SQL
with o.execute_sql('SELECT COUNT(*) FROM my_table').open_reader() as reader:
    print(reader[0][0])
```

## Restrictions

| Restriction | Description |
|-------|------|
| Python version | MaxCompute uses Python 3.7; using 3.7 locally is recommended to avoid bytecode incompatibility |
| Local data volume | Dedicated resource groups: up to 50MB; Serverless resource groups: 16 CU or less recommended |
| Log size | Maximum output log size is 4MB |
| Concurrent execution | Concurrent execution of multiple Python tasks is not supported |
| Log output | Only `print` is supported; `logger.info` is not supported |
| Third-party packages | Third-party packages with binary code are not supported (except Numpy and Pandas) |

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_pyodps3",
        "script": {
          "path": "example_pyodps3",
          "runtime": {
            "command": "PYODPS3"
          },
          "content": "from odps import ODPS\nimport sys\nprint('PyODPS 3 node')\nprint(sys.version)"
        }
      }
    ]
  }
}
```

## Reference

- [PyODPS 3 Node](https://help.aliyun.com/zh/dataworks/user-guide/pyodps-3-node)

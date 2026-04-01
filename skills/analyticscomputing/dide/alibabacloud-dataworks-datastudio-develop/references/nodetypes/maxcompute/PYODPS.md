# PyODPS 2（PYODPS）

## Overview

- Compute engine: `ODPS`
- Content format: python
- Extension: `.py`
- Code: 221
- Data source type: `odps`
- Description: PyODPS 2 script (Python 2, operates on MaxCompute)

The PyODPS 2 node is based on the MaxCompute Python SDK (PyODPS) and allows writing code in Python 2 to operate on MaxCompute. It supports executing SQL, DataFrame processing, and resource management.

> **Recommendation**: It is recommended that new projects use [PYODPS3](./PYODPS3.md) (Python 3 version).

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Core Features

### Built-in Global Variables

The following global variables are preset in the node and do not need to be defined manually:

- **`odps` or `o`**: ODPS entry object for directly calling MaxCompute APIs
- **`args`**: Dictionary-format scheduling parameter container, used to retrieve parameter values such as `${yyyymmdd}`

```python
# PyODPS 2 example
print(o.exist_table('my_table'))

# Get scheduling parameters
bizdate = args['bizdate']
print('bizdate: ' + bizdate)

# Execute SQL
with o.execute_sql('SELECT COUNT(*) FROM my_table').open_reader() as reader:
    print(reader[0][0])
```

## Restrictions

| Restriction | Description |
|-------|------|
| Python version | Underlying Python 2.7 |
| Local data volume | Dedicated resource groups: up to 50MB; Serverless resource groups: 16 CU or less recommended |
| Log size | Maximum output log size is 4MB |
| Instance Tunnel | Disabled by default; manually set `options.tunnel.use_instance_tunnel = True` |
| Concurrent execution | Concurrent execution of multiple Python tasks is not supported |
| Log output | Only `print` is supported; `logger.info` is not supported |

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_pyodps",
        "script": {
          "path": "example_pyodps",
          "runtime": {
            "command": "PY_ODPS"
          },
          "content": "from odps import ODPS\nimport sys\nprint('PyODPS 2 node')\nprint(sys.version)"
        }
      }
    ]
  }
}
```

## Reference

- [PyODPS 2 Node](https://help.aliyun.com/zh/dataworks/user-guide/pyodps-2-node)

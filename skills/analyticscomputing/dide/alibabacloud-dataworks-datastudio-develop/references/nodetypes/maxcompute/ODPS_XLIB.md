# MaxCompute XLib（ODPS_XLIB）

## Overview

- Compute engine: `ODPS`
- Content format: python
- Extension: `.mc.xlib.py`
- Code: 8
- Data source type: `odps`
- Description: MaxCompute XLib Python script

The MaxCompute XLib node is used to run Python scripts that depend on extension libraries (XLib) on MaxCompute. Unlike PyODPS nodes, XLib nodes can use pre-installed scientific computing libraries such as NumPy.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_xlib",
        "script": {
          "path": "example_odps_xlib",
          "runtime": {
            "command": "ODPS_XLIB"
          },
          "content": "# MaxCompute XLib\nimport numpy as np\nprint(np.__version__)"
        }
      }
    ]
  }
}
```

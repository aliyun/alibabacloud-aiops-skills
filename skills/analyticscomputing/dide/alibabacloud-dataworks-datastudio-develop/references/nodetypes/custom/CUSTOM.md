# Custom Node（CUSTOM）

## Overview

- Code: `9999`
- Compute engine: `CUSTOM`
- Content format: json
- Extension: `.json`
- LabelType: `DATA_PROCESS`
- Description: Custom node type for extending node types not natively supported by DataWorks

Custom nodes allow users to define task types not natively supported by the DataWorks platform through JSON configuration. They are suitable for scenarios that require integration with third-party systems, custom processing logic, or special scheduling needs. The node content is a free-format JSON object; the specific structure is defined by the user based on business requirements.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_custom",
        "script": {
          "path": "example_custom",
          "runtime": {
            "command": "CUSTOM"
          },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Usage Notes

- `script.content` is a custom JSON string; the structure is not strictly constrained and depends on the specific business scenario.
- `script.runtime.command` is fixed as `CUSTOM`.
- Suitable for scenarios involving integration with external systems or extending platform capabilities; requires use with a custom resource group and runtime environment.

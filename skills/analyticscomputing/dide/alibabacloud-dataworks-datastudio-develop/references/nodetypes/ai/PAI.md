# PAI (PAI)

## Overview

- Compute engine: `ALGORITHM`
- Content format: json
- Extension: `.json`
- Data source type: `pai`
- Description: PAI command-line algorithm task node, scheduling PAI Command via JSON configuration

PAI (Platform for AI) is Alibaba Cloud's artificial intelligence platform, providing algorithm capabilities covering the full lifecycle of machine learning and deep learning. In DataWorks, the PAI node is used to schedule PAI command-line tasks (PAI Command), specifying the algorithm name, project, and input/output table parameters via JSON-formatted content configuration, enabling periodic scheduling and automated orchestration of machine learning tasks.

The typical format for PAI Command is: `PAI -name <algorithm_name> -project <project> -DinputTableName=xxx -DoutputTableName=xxx`. The node's `content` field carries these command configuration details in JSON format, which are parsed and executed by the PAI platform.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_pai",
        "script": {
          "path": "example_pai",
          "runtime": { "command": "pai" },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Restrictions

- PAI (Machine Learning Platform) must be activated and bound to the DataWorks workspace.
- A `pai` type data source connection must be configured in the workspace to ensure DataWorks can access PAI platform resources.
- The `content` field is a JSON-formatted string that must contain valid PAI Command configuration; an empty object `{}` is only for placeholder purposes and must be filled with complete algorithm parameters for actual execution.
- Input and output tables referenced in PAI Command must already exist in the corresponding MaxCompute project, and the executing account must have the appropriate read/write permissions.

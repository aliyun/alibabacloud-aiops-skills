# PAI DLC (PAI_DLC)

## Overview

- Code: `1119`
- Compute engine: `ALGORITHM`
- Content format: empty (no code)
- Extension: `.pai.dlc.sh`
- Data source type: `pai`
- Description: Integrates Alibaba Cloud PAI platform's DLC (Deep Learning Containers) distributed training service

The PAI DLC node is used to schedule and run containerized deep learning training tasks from the PAI platform in DataWorks. DLC provides a containerized distributed training environment supporting mainstream deep learning frameworks such as TensorFlow and PyTorch. Users can load existing DLC tasks into DataWorks or directly write task code to enable periodic scheduling of training tasks.

Documentation: <https://help.aliyun.com/zh/dataworks/user-guide/pai-dlc-node>

## Configuration

### Development Methods

The PAI DLC node supports two development methods:

1. **Load Existing Task** -- Search by name and load a DLC task already created on the PAI platform; the system automatically generates the corresponding node code.
2. **Write Code Directly** -- Write DLC task code directly in the editor, supporting dynamic scheduling parameters using `${variable_name}`.

### Common Parameters

The following key parameters can be configured in the code:

| Parameter | Description |
|-----------|-------------|
| `--name` | Task name |
| `--command` | Execution command |
| `--workspace_id` | PAI workspace ID |
| `--priority` | Task priority (1-9) |
| `--workers` | Number of compute nodes |
| `--worker_spec` | Compute node specification |

### Workflow

1. Write or load DLC task code
2. Configure the scheduling resource group and run tests
3. Configure the scheduling period and dependency relationships
4. Publish the node to the production environment
5. Monitor run status in the Operations Center

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_pai_dlc",
        "script": {
          "path": "example_pai_dlc",
          "runtime": { "command": "pai_dlc" },
          "content": ""
        }
      }
    ]
  }
}
```

## Restrictions

- DataWorks must be authorized to access the PAI service before use (one-click authorization supported).
- The node content format is empty; task code is managed on the PAI platform side, and DataWorks does not directly edit script content.
- The PAI workspace and DataWorks workspace must be in the same region.

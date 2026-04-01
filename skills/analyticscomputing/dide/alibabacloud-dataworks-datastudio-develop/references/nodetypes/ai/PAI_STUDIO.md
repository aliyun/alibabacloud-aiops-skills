# PAI Studio (PAI_STUDIO)

## Overview

- Code: `1117`
- Compute engine: `ALGORITHM`
- Content format: json
- Extension: `.json`
- Data source type: `pai`
- Description: PAI visual modeling experiment node for building machine learning workflows via drag-and-drop and scheduling them in DataWorks

PAI Studio (now known as PAI Designer) is the visual modeling tool provided by Alibaba Cloud's PAI platform. In DataWorks, the PAI Studio node is used to load and schedule machine learning experiment workflows created on PAI Designer, enabling periodic automated execution of end-to-end machine learning development processes. Users can arrange components for data preprocessing, feature engineering, model training, and model evaluation by dragging and dropping on PAI Designer, then configure scheduling parameters and dependencies in DataWorks to incorporate the experiment workflow into the production scheduling system.

Documentation: <https://help.aliyun.com/zh/dataworks/user-guide/pai-designer-node>

## Configuration

### Development Methods

The PAI Studio node supports the following methods for creating workflows:

1. **Create Blank Workflow** -- Start from scratch on the PAI Designer canvas, dragging algorithm components and connecting them to build experiments.
2. **Create from Preset Template** -- Use platform-provided templates for quick start, suitable for common machine learning scenarios.
3. **Use Custom Template** -- Create workflows based on team-customized templates for team collaboration and reuse.

### Scheduling Parameters

Supports defining dynamic parameters using `${variable_name}` syntax in workflows, assigning values in the DataWorks scheduling configuration for dynamic input across different scheduling cycles.

### Workflow

1. Create a PAI Designer node in DataWorks
2. Enter PAI Designer to create or edit a machine learning workflow
3. Configure scheduling parameters (if dynamic input is needed)
4. Save and publish the node to the production environment
5. Execute tasks in the Operations Center via "Test" or "Backfill"

> Note: PAI Studio nodes do not have a direct run entry; they must be triggered via the Operations Center.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_pai_studio",
        "script": {
          "path": "example_pai_studio",
          "runtime": { "command": "pai_studio" },
          "content": "{}"
        }
      }
    ]
  }
}
```

## Restrictions

- DataWorks must be authorized to access PAI services before use; only the primary account or RAM users with `AliyunDataWorksFullAccess` permission can perform the authorization.
- A `pai` type data source connection must be configured in the workspace to ensure DataWorks can access PAI platform resources.
- The `content` field is a JSON-formatted string carrying workflow configuration information; an empty object `{}` is for placeholder only and must contain a valid experiment workflow configuration for actual execution.
- The node does not support direct execution in the DataWorks editor; it must be published and then triggered via test or backfill in the Operations Center.

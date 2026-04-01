# XLab (XLAB)

## Overview

- Code: `87`
- Compute engine: `ALGORITHM`
- Content format: empty (no code)
- Extension: `.xlab.json`
- Data source type: `pai`
- Description: Early visual data exploration and analysis node on the PAI platform, for conducting data analysis experiments via a graphical interface

XLab is an early visual data exploration and analysis tool provided by Alibaba Cloud's PAI platform. In DataWorks, the XLab node is used to schedule data analysis experiments created on the XLab platform, supporting graphical exploratory analysis, statistical descriptions, and visual presentations of data, and incorporating analysis workflows into the DataWorks scheduling system for periodic execution.

This node type belongs to an earlier generation of algorithm nodes and has been gradually replaced by PAI Designer (PAI_STUDIO) and other next-generation visual modeling tools. For new scenarios, PAI Designer nodes are recommended.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_xlab",
        "script": {
          "path": "example_xlab",
          "runtime": { "command": "xlab" },
          "content": ""
        }
      }
    ]
  }
}
```

## Restrictions

- This node type is an early algorithm node that has been gradually replaced by PAI Designer (PAI_STUDIO); PAI Designer nodes are recommended for new projects.
- PAI (Machine Learning Platform) must be activated and bound to the DataWorks workspace.
- A `pai` type data source connection must be configured in the workspace to ensure DataWorks can access PAI platform resources.
- The `content` field is an empty string (empty format); experiment configuration is completed through the XLab platform's visual interface rather than written directly in the node script.

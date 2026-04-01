# Alink (ALINK)

## Overview

- Compute engine: `ALGORITHM`
- Content format: empty (no code)
- Extension: `.alink.py`
- Data source type: `pai`
- Description: Flink-based machine learning algorithm node, runs on the PAI platform

Alink is Alibaba's open-source machine learning algorithm platform, built on Apache Flink, supporting both batch and streaming computation modes. In DataWorks, the Alink node is used to schedule Alink algorithm tasks on the PAI platform, enabling automated scheduling and orchestration of common machine learning scenarios such as classification, regression, clustering, recommendation, and feature engineering.

The content format of this node is empty, meaning the node itself does not directly contain algorithm code. Instead, it executes by associating with a pre-configured Alink algorithm task on the PAI platform. Users must first build and debug the algorithm workflow on the PAI platform, then use the DataWorks Alink node for periodic scheduling.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_alink",
        "script": {
          "path": "example_alink",
          "runtime": { "command": "alink" },
          "content": ""
        }
      }
    ]
  }
}
```

## Restrictions

- PAI (Machine Learning Platform) must be activated and bound to the DataWorks workspace.
- Algorithm tasks must be created and configured on the PAI platform first; the Alink node itself does not support directly writing algorithm code (content format is empty).
- Requires a `pai` type data source; the corresponding PAI data source connection must be configured in the workspace.

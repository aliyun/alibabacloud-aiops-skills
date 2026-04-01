# Jupyter Notebook (NOTEBOOK)

## Overview

- Compute engine: `GENERAL`
- Content format: python
- Extension: `.ipynb`
- Description: Interactive, modular data analysis and development environment

The Notebook node provides an interactive data analysis and development environment, supporting Python, SQL, and Markdown cells. It can connect to multiple compute engines such as MaxCompute, EMR, and AnalyticDB, enabling end-to-end tasks from data processing to model development.

## Prerequisites

- The workspace has enabled the new Data Studio (Data Development).
- A Serverless resource group has been created.
- To use Python cells, a personal development environment instance must be created.

## Restrictions

- Serverless resource groups recommend no more than 16 CU; maximum 64 CU per task.
- Only nodes under the project directory can be published and periodically scheduled.
- Lineage analysis only supports specific scenarios (between MaxCompute tables, and table-external data interactions).
- Data Studio auto-save is not enabled by default; code must be saved manually.
- Network policies differ between development and production environments; production dependencies must be ensured through custom images.
- It is recommended to bind the personal development environment and resource group to the same VPC.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_notebook",
        "script": {
          "path": "example_notebook",
          "runtime": {
            "command": "NOTEBOOK"
          },
          "content": ""
        }
      }
    ]
  }
}
```

## Reference

- [Notebook Node](https://help.aliyun.com/zh/dataworks/user-guide/notebook-node)

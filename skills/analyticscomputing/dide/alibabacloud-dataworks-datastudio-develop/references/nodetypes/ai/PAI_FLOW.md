# PAI Flow (PAI_FLOW)

## Overview

- Compute engine: `ALGORITHM`
- Content format: yaml
- Extension: `.yaml`
- Data source type: `pai`
- Description: PAI visual modeling workflow node for end-to-end machine learning pipeline development

PAI Flow provides end-to-end machine learning pipeline development capabilities, sharing the same workflow functionality as the visual modeling designer on Alibaba Cloud's PAI platform. Users can drag and drop nodes such as data reading and RAG data processing onto the canvas and manually connect them to form workflows. PAI Flow nodes support periodic scheduling, enabling automated execution of AI tasks in DataWorks.

Documentation: https://help.aliyun.com/zh/dataworks/user-guide/pai-flow-node

## Configuration

### Supported Sub-node Types

**Source/Target Nodes:**
- Read Data Table -- Read MaxCompute table data
- Read OSS Data -- Read files or folders from object storage paths
- Read CSV File -- Supports reading CSV format data from OSS, HTTP, HDFS
- Write Data Table -- Write data to MaxCompute

**RAG Data Processing Nodes:**
- RAG Text Parse and Chunk -- Parse text files and generate text chunks of specified sizes
- RAG Vector Generation -- Generate text vectors using Embedding models
- RAG Knowledge Base Index Sync -- Sync data to target knowledge base indexes

### Variable Support

File paths support configuring variables (e.g., `${variable}/example.csv`), which can be combined with scheduling parameters for dynamic paths during periodic scheduling.

### Prerequisites

- When creating a DataWorks workspace, check "Create AI workspace with same name"; for existing workspaces, enable "Schedule PAI algorithm tasks" in the Management Center
- Only Serverless resource groups are supported

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_pai_flow",
        "script": {
          "path": "example_pai_flow",
          "runtime": { "command": "PAI_FLOW" },
          "content": ""
        }
      }
    ]
  }
}
```

## Restrictions

- Only supported in new DataWorks workspaces
- Currently only supports source/target nodes and RAG data processing nodes
- Only Serverless resource groups are supported for execution
- Region restrictions: China East 1 (Hangzhou), China East 2 (Shanghai), China North 2 (Beijing), China North 6 (Ulanqab), China South 1 (Shenzhen), Hong Kong, Singapore, Jakarta, Tokyo, Frankfurt, Silicon Valley, Virginia

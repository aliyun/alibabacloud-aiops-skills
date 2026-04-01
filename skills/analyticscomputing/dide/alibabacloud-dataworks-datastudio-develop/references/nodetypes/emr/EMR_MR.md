# EMR MapReduce（EMR_MR）

## Overview

- Compute engine: `EMR`
- Content format: shell
- Extension: `.sh`
- Data source type: `emr`
- Code: 230
- Description: Submit MapReduce jobs on EMR clusters

Submit and run Hadoop MapReduce jobs on EMR clusters via shell scripts, suitable for big data batch processing scenarios using the traditional MapReduce programming model.

## Prerequisites

- An EMR cluster has been created and added as a DataWorks compute resource
- The DataWorks resource group has network connectivity with the EMR cluster
- EMR cluster has Hadoop/YARN service installed

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_emr_mr",
        "script": {
          "path": "example_emr_mr",
          "runtime": {
            "command": "EMR_MR"
          },
          "content": "#!/bin/bash\necho 'hello'"
        }
      }
    ]
  }
}
```

## Reference

- [EMR MR Node](https://help.aliyun.com/zh/dataworks/user-guide/emr-mr-node)

# MaxCompute MapReduce（ODPS_MR）

## Overview

- Compute engine: `ODPS`
- Content format: sql
- Extension: `.mr.sql`
- Code: 11
- Data source type: `odps`
- Description: MaxCompute MapReduce command

The MaxCompute MR node is used to process large-scale datasets in MaxCompute through programs written with the MapReduce Java API. The node content is a jar command that specifies the JAR resource and main class to execute.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource
- The required JAR packages and resource files have been uploaded and published in advance

## Core Features

### Command Format

```sql
jar -resources <JAR_filename> -classpath ./<JAR_filename> <main class fully qualified name> <input table> <output table>;
```

Multiple JAR resources are separated by commas:

```sql
jar -resources example1.jar,example2.jar -classpath ./example1.jar,./example2.jar com.example.WordCount input_table output_table;
```

### Version Support

- **MaxCompute MapReduce**：Native interface, fast execution speed
- **MR2**：Extended version, supports more complex job scheduling logic

## Restrictions

- JAR resources must be uploaded and published in advance before they can be referenced
- For specific restrictions, see the MaxCompute official documentation

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_mr",
        "script": {
          "path": "example_odps_mr",
          "runtime": {
            "command": "ODPS_MR"
          },
          "content": "--MaxCompute MR\njar -resources mr_example.jar -classpath ./mr_example.jar com.example.WordCount;"
        }
      }
    ]
  }
}
```

## Reference

- [MaxCompute MR Node](https://help.aliyun.com/zh/dataworks/user-guide/maxcompute-mr-node)

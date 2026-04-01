# MaxCompute Function（ODPS_FUNCTION）

## Overview

- Compute engine: `ODPS`
- Content format: json
- Extension: `.json`
- Code: 17
- Data source type: `odps`
- Label type: FUNCTION
- Description: MaxCompute UDF function definition

The MaxCompute function node is used to define UDF (User Defined Function) functions in JSON format, specifying the function name, Java class name, and dependent resource files. This node enables version management and automated deployment of custom functions.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource
- The JAR resources that the function depends on have been uploaded and published (via the ODPS_JAR node)

## Content Structure

```json
{
  "name": "function name",
  "className": "Java fully qualified class name",
  "resources": ["dependent resource file names"]
}
```

### UDF Types

MaxCompute supports three types of custom functions:

- **UDF**: Takes one row as input and outputs one row (e.g., format conversion, string processing)
- **UDAF**: Takes multiple rows as input and outputs one row (e.g., custom aggregate functions)
- **UDTF**: Takes one row as input and outputs multiple rows (e.g., data splitting, expanding)

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_function",
        "script": {
          "path": "example_odps_function",
          "runtime": {
            "command": "ODPS_FUNCTION"
          },
          "content": "{\"name\":\"example_func\",\"className\":\"com.example.UDF\",\"resources\":[\"example.jar\"]}"
        }
      }
    ]
  }
}
```

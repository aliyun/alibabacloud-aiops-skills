# Serverless PySpark (SERVERLESS_PYSPARK)

## Overview

- Compute engine: `EMR`
- Content format: python
- Extension: `.py`
- Data source type: `emr`
- Code: 2105
- Description: Serverless PySpark node, Python-based distributed computing on EMR Serverless Spark

DataWorks provides the Serverless PySpark node, allowing users to directly develop and run distributed PySpark tasks based on EMR Serverless Spark without the need to manage cluster infrastructure. This node uses a dual-panel collaborative editing mode: The upper panel is for writing Python business logic, and the lower panel is for writing the `spark-submit` submission command.

## Prerequisites

- An EMR Serverless Spark compute resource has been bound, Ensure the resource group has network connectivity with the compute resource
- Only Serverless resource groups are supported for running this task type
- RAM users must have **Developer** or **Workspace Admin** role permissions

## Core Features

### Dual-panel Editing Mode

**Upper Panel -- Python Business Code**:

Declare referenced external Python files via `##@resource_reference{"resource_name"}`.

```python
##@resource_reference{"utils.py"}
from pyspark.sql import SparkSession
from utils import estimate_pi_in_task
import sys

def main():
    spark = SparkSession.builder.appName("EstimatePi").getOrCreate()
    sc = spark.sparkContext

    total_samples = int(sys.argv[1])
    num_partitions = ${test1}

    # Parallel computation
    counts = sc.parallelize(range(num_partitions), num_partitions) \
        .map(lambda i: estimate_pi_in_task(total_samples // num_partitions)) \
        .reduce(lambda a, b: a + b)

    pi = 4.0 * counts / total_samples
    print(f"Pi is approximately {pi}")

    spark.stop()

if __name__ == "__main__":
    main()
```

**Lower Panel -- spark-submit Command**:

```bash
spark-submit \
  --py-files utils.py \
  serverless_pyspark_test1.py 10000
```

### Scheduling Parameters

- Define dynamic parameters using `${variable_name}` format (e.g., `${test1}` in the example)
- Receive spark-submit command-line parameters via `sys.argv`
- Assign values to variables in the scheduling configuration

### Resource Reference

External Python files must first be uploaded via the resource management module, then:

1. Declare references in code using `##@resource_reference{"resource_name"}`
2. Explicitly declare dependency files in the spark-submit command via `--py-files`

## Restrictions

- The main Python script filename must match the node name, with `.py` suffix
- External `.py` files must be explicitly declared via `--py-files`
- Only submitting the entire Python file is supported; running partial code is not supported
- Only Serverless resource groups are supported for execution

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_serverless_pyspark",
        "script": {
          "path": "example_serverless_pyspark",
          "runtime": {
            "command": "SERVERLESS_PYSPARK"
          },
          "content": "print('hello')"
        }
      }
    ]
  }
}
```

## Related Documentation

- [Serverless PySpark Node](https://help.aliyun.com/zh/dataworks/user-guide/serverless-pyspark-node)

# MaxCompute Perl（ODPS_PERL）

## Overview

- Compute engine: `ODPS`
- Content format: shell
- Extension: `.mc.pl`
- Code: 9
- Data source type: `odps`
- Description: MaxCompute Perl script

The MaxCompute Perl node is used to run Perl scripts in the MaxCompute scheduling environment, suitable for scenarios that require Perl for text processing or data transformation.

## Prerequisites

- The workspace has been bound to a MaxCompute compute resource

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_odps_perl",
        "script": {
          "path": "example_odps_perl",
          "runtime": {
            "command": "odps_pl"
          },
          "content": "#!/usr/bin/perl\nuse strict;\nprint \"MaxCompute Perl\\n\";"
        }
      }
    ]
  }
}
```

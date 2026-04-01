# Perl Script (PERL)

## Overview

- Compute engine: `GENERAL`
- Content format: shell
- Extension: `.pl`
- Description: Run Perl scripts on DataWorks scheduling resource groups

The Perl node is used for writing and scheduling Perl scripts, suitable for traditional Perl scripting scenarios such as text processing, log analysis, and system administration.

## Prerequisites

- The RAM account must be added to the workspace with Developer or Workspace Admin role permissions.

## Restrictions

- The runtime environment depends on the Perl interpreter version pre-installed on the scheduling resource group.
- Interactive syntax is not supported.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_perl",
        "script": {
          "path": "example_perl",
          "runtime": {
            "command": "PERL"
          },
          "content": "#!/usr/bin/perl\nuse strict;\nuse warnings;\nprint \"Hello DataWorks\\n\";"
        }
      }
    ]
  }
}
```

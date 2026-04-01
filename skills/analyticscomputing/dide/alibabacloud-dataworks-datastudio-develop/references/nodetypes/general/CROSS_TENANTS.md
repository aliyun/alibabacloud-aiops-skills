# Cross-Tenant Node (CROSS_TENANTS)

## Overview

- Compute engine: `GENERAL`
- Content format: json
- Extension: `.json`
- Description: Cross-tenant node for task triggering and coordination across DataWorks tenants

The Cross-Tenant node is used to establish task triggering relationships between different DataWorks tenants. By configuring the receive node identifier, it enables cross-tenant workflow coordination, suitable for data collaboration scenarios across multiple teams and organizations.

## Content Structure

`script.content` is the JSON configuration for cross-tenant settings. The key fields are as follows:

| Field | Type | Description |
|------|------|------|
| `receiveNodeIdentify` | string | Receive node identifier, specifying the receive node in the target tenant |

```json
{
  "receiveNodeIdentify": "Node identifier in the target tenant"
}
```

## Restrictions

- The target tenant must have authorized cross-tenant access for the current tenant.
- The receive node identifier must exactly match the node in the target tenant.

## Minimum Spec

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "example_cross_tenants",
        "script": {
          "path": "example_cross_tenants",
          "runtime": {
            "command": "CROSS_TENANTS"
          },
          "content": "{\"receiveNodeIdentify\": \"example_cross_tenants\"}"
        }
      }
    ]
  }
}
```

# DataWorks Data Development RAM Permission List

This document lists all RAM permissions required to use the DataWorks data development SKILL.

## Required Permissions

### Project Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:get-project` | Get project information | get-project |

### Node Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:list-nodes` | List nodes | list-nodes |
| `dataworks:get-node` | Get node details | get-node |
| `dataworks:create-node` | Create node | create-node |
| `dataworks:update-node` | Update node | update-node |
| `dataworks:move-node` | Move a node to a specified path | move-node |
| `dataworks:rename-node` | Rename a node | rename-node |
| `dataworks:list-node-dependencies` | List a node's dependency nodes | list-node-dependencies |

### Workflow Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:list-workflow-definitions` | List workflows | list-workflow-definitions |
| `dataworks:get-workflow-definition` | Get workflow details | get-workflow-definition |
| `dataworks:create-workflow-definition` | Create workflow | create-workflow-definition |
| `dataworks:update-workflow-definition` | Update workflow | update-workflow-definition |
| `dataworks:import-workflow-definition` | Import a workflow definition | import-workflow-definition |
| `dataworks:move-workflow-definition` | Move a workflow to a target path | move-workflow-definition |
| `dataworks:rename-workflow-definition` | Rename a workflow | rename-workflow-definition |

### Deployment Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:create-pipeline-run` | Create deployment process | create-pipeline-run |
| `dataworks:get-pipeline-run` | Get deployment status | get-pipeline-run |
| `dataworks:exec-pipeline-run-stage` | Advance deployment stage | exec-pipeline-run-stage |
| `dataworks:list-pipeline-runs` | Query deployment history | list-pipeline-runs |
| `dataworks:list-pipeline-run-items` | Query deployment items | list-pipeline-run-items |
| `dataworks:abolish-pipeline-run` | Cancel deployment | abolish-pipeline-run |

### Data Source Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:list-data-sources` | List data sources | list-data-sources |

### Resource Group Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:list-resource-groups` | List resource groups | list-resource-groups |

### Resource Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:create-resource` | Create a file resource | create-resource |
| `dataworks:update-resource` | Update file resource information | update-resource |
| `dataworks:move-resource` | Move a file resource to a specified directory | move-resource |
| `dataworks:rename-resource` | Rename a file resource | rename-resource |
| `dataworks:get-resource` | Get file resource details | get-resource |
| `dataworks:list-resources` | List file resources | list-resources |

### Function Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:create-function` | Create a UDF function | create-function |
| `dataworks:update-function` | Update UDF function information | update-function |
| `dataworks:move-function` | Move a function to a target path | move-function |
| `dataworks:rename-function` | Rename a function | rename-function |
| `dataworks:get-function` | Get function details | get-function |
| `dataworks:list-functions` | List functions | list-functions |

### Component Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:create-component` | Create a component | create-component |
| `dataworks:get-component` | Get component details | get-component |
| `dataworks:update-component` | Update a component | update-component |
| `dataworks:list-components` | List components | list-components |

## Recommended Policies

### Minimum Permission Policy (Read-Only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:get-project",
        "dataworks:list-nodes",
        "dataworks:get-node",
        "dataworks:list-node-dependencies",
        "dataworks:list-workflow-definitions",
        "dataworks:get-workflow-definition",
        "dataworks:get-pipeline-run",
        "dataworks:list-pipeline-runs",
        "dataworks:list-pipeline-run-items",
        "dataworks:list-data-sources",
        "dataworks:list-resource-groups",
        "dataworks:get-resource",
        "dataworks:list-resources",
        "dataworks:get-function",
        "dataworks:list-functions",
        "dataworks:get-component",
        "dataworks:list-components"
      ],
      "Resource": "*"
    }
  ]
}
```

### Full Development Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:get-project",
        "dataworks:list-nodes",
        "dataworks:get-node",
        "dataworks:create-node",
        "dataworks:update-node",
        "dataworks:move-node",
        "dataworks:rename-node",
        "dataworks:list-node-dependencies",
        "dataworks:list-workflow-definitions",
        "dataworks:get-workflow-definition",
        "dataworks:create-workflow-definition",
        "dataworks:update-workflow-definition",
        "dataworks:import-workflow-definition",
        "dataworks:move-workflow-definition",
        "dataworks:rename-workflow-definition",
        "dataworks:create-pipeline-run",
        "dataworks:get-pipeline-run",
        "dataworks:exec-pipeline-run-stage",
        "dataworks:list-pipeline-runs",
        "dataworks:list-pipeline-run-items",
        "dataworks:abolish-pipeline-run",
        "dataworks:list-data-sources",
        "dataworks:list-resource-groups",
        "dataworks:create-resource",
        "dataworks:update-resource",
        "dataworks:move-resource",
        "dataworks:rename-resource",
        "dataworks:get-resource",
        "dataworks:list-resources",
        "dataworks:create-function",
        "dataworks:update-function",
        "dataworks:move-function",
        "dataworks:rename-function",
        "dataworks:get-function",
        "dataworks:list-functions",
        "dataworks:create-component",
        "dataworks:get-component",
        "dataworks:update-component",
        "dataworks:list-components"
      ],
      "Resource": "*"
    }
  ]
}
```

## Restrict Permissions by Project

To restrict permissions to a specific project, change `Resource` to the project ARN:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:create-node"
      ],
      "Resource": [
        "acs:dataworks:cn-hangzhou:123456789012:project/my_project_name"
      ]
    }
  ]
}
```

## Common Permission Errors

| Error Code | Description | Solution |
|-------|------|---------|
| `Forbidden.RAM` | Insufficient permissions | Add the corresponding API permission |
| `NoPermission` | No operation permission | Check if the RAM policy is in effect |
| `InvalidAccessKeyId.NotFound` | Invalid AccessKey | Check AccessKey configuration |
| `SignatureDoesNotMatch` | Signature mismatch | Check AccessKeySecret |

## References

- [DataWorks RAM Permission Guide](https://help.aliyun.com/zh/dataworks/user-guide/dataworks-ram-permissions)
- [RAM Policy Management](https://ram.console.aliyun.com/policies)

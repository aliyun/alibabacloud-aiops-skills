# DataWorks Data Development RAM Permission List

This document lists all RAM permissions required to use the DataWorks data development SKILL.

## Required Permissions

### Project Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:GetProject` | Get project information | GetProject |

### Node Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:ListNodes` | List nodes | ListNodes |
| `dataworks:GetNode` | Get node details | GetNode |
| `dataworks:CreateNode` | Create node | CreateNode |
| `dataworks:UpdateNode` | Update node | UpdateNode |
| `dataworks:DeleteNode` | Delete node | DeleteNode |
| `dataworks:MoveNode` | Move a node to a specified path | MoveNode |
| `dataworks:RenameNode` | Rename a node | RenameNode |
| `dataworks:ListNodeDependencies` | List a node's dependency nodes | ListNodeDependencies |

### Workflow Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:ListWorkflowDefinitions` | List workflows | ListWorkflowDefinitions |
| `dataworks:GetWorkflowDefinition` | Get workflow details | GetWorkflowDefinition |
| `dataworks:CreateWorkflowDefinition` | Create workflow | CreateWorkflowDefinition |
| `dataworks:UpdateWorkflowDefinition` | Update workflow | UpdateWorkflowDefinition |
| `dataworks:DeleteWorkflowDefinition` | Delete workflow | DeleteWorkflowDefinition |
| `dataworks:ImportWorkflowDefinition` | Import a workflow definition | ImportWorkflowDefinition |
| `dataworks:MoveWorkflowDefinition` | Move a workflow to a target path | MoveWorkflowDefinition |
| `dataworks:RenameWorkflowDefinition` | Rename a workflow | RenameWorkflowDefinition |

### Deployment Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:CreatePipelineRun` | Create deployment process | CreatePipelineRun |
| `dataworks:GetPipelineRun` | Get deployment status | GetPipelineRun |
| `dataworks:ExecPipelineRunStage` | Advance deployment stage | ExecPipelineRunStage |
| `dataworks:ListPipelineRuns` | Query deployment history | ListPipelineRuns |
| `dataworks:ListPipelineRunItems` | Query deployment items | ListPipelineRunItems |
| `dataworks:AbolishPipelineRun` | Cancel deployment | AbolishPipelineRun |

### Data Source Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:ListDataSources` | List data sources | ListDataSources |

### Resource Group Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:ListResourceGroups` | List resource groups | ListResourceGroups |

### Resource Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:CreateResource` | Create a file resource | CreateResource |
| `dataworks:DeleteResource` | Delete a file resource | DeleteResource |
| `dataworks:UpdateResource` | Update file resource information | UpdateResource |
| `dataworks:MoveResource` | Move a file resource to a specified directory | MoveResource |
| `dataworks:RenameResource` | Rename a file resource | RenameResource |
| `dataworks:GetResource` | Get file resource details | GetResource |
| `dataworks:ListResources` | List file resources | ListResources |

### Function Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:CreateFunction` | Create a UDF function | CreateFunction |
| `dataworks:DeleteFunction` | Delete a UDF function | DeleteFunction |
| `dataworks:UpdateFunction` | Update UDF function information | UpdateFunction |
| `dataworks:MoveFunction` | Move a function to a target path | MoveFunction |
| `dataworks:RenameFunction` | Rename a function | RenameFunction |
| `dataworks:GetFunction` | Get function details | GetFunction |
| `dataworks:ListFunctions` | List functions | ListFunctions |

### Component Management Permissions

| Permission | Description | API |
|-----|------|-----|
| `dataworks:CreateComponent` | Create a component | CreateComponent |
| `dataworks:DeleteComponent` | Delete a component | DeleteComponent |
| `dataworks:GetComponent` | Get component details | GetComponent |
| `dataworks:UpdateComponent` | Update a component | UpdateComponent |
| `dataworks:ListComponents` | List components | ListComponents |

## Recommended Policies

### Minimum Permission Policy (Read-Only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:GetProject",
        "dataworks:ListNodes",
        "dataworks:GetNode",
        "dataworks:ListNodeDependencies",
        "dataworks:ListWorkflowDefinitions",
        "dataworks:GetWorkflowDefinition",
        "dataworks:GetPipelineRun",
        "dataworks:ListPipelineRuns",
        "dataworks:ListPipelineRunItems",
        "dataworks:ListDataSources",
        "dataworks:ListResourceGroups",
        "dataworks:GetResource",
        "dataworks:ListResources",
        "dataworks:GetFunction",
        "dataworks:ListFunctions",
        "dataworks:GetComponent",
        "dataworks:ListComponents"
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
        "dataworks:GetProject",
        "dataworks:ListNodes",
        "dataworks:GetNode",
        "dataworks:CreateNode",
        "dataworks:UpdateNode",
        "dataworks:DeleteNode",
        "dataworks:MoveNode",
        "dataworks:RenameNode",
        "dataworks:ListNodeDependencies",
        "dataworks:ListWorkflowDefinitions",
        "dataworks:GetWorkflowDefinition",
        "dataworks:CreateWorkflowDefinition",
        "dataworks:UpdateWorkflowDefinition",
        "dataworks:DeleteWorkflowDefinition",
        "dataworks:ImportWorkflowDefinition",
        "dataworks:MoveWorkflowDefinition",
        "dataworks:RenameWorkflowDefinition",
        "dataworks:CreatePipelineRun",
        "dataworks:GetPipelineRun",
        "dataworks:ExecPipelineRunStage",
        "dataworks:ListPipelineRuns",
        "dataworks:ListPipelineRunItems",
        "dataworks:AbolishPipelineRun",
        "dataworks:ListDataSources",
        "dataworks:ListResourceGroups",
        "dataworks:CreateResource",
        "dataworks:DeleteResource",
        "dataworks:UpdateResource",
        "dataworks:MoveResource",
        "dataworks:RenameResource",
        "dataworks:GetResource",
        "dataworks:ListResources",
        "dataworks:CreateFunction",
        "dataworks:DeleteFunction",
        "dataworks:UpdateFunction",
        "dataworks:MoveFunction",
        "dataworks:RenameFunction",
        "dataworks:GetFunction",
        "dataworks:ListFunctions",
        "dataworks:CreateComponent",
        "dataworks:DeleteComponent",
        "dataworks:GetComponent",
        "dataworks:UpdateComponent",
        "dataworks:ListComponents"
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
        "dataworks:CreateNode"
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

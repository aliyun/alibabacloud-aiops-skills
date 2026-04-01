# RAM Policies for ESA Functions & Pages

This document describes the RAM (Resource Access Management) permissions required to use this skill.

## Required Permissions

To use the ESA Functions & Pages deployment capabilities, grant the following permissions to your RAM user or role:

### Edge Routine Service

| Action | Description |
|--------|-------------|
| `esa:OpenErService` | Enable Edge Routine service |
| `esa:GetErService` | Query Edge Routine service status |

### Functions & Pages - Function Management

| Action | Description |
|--------|-------------|
| `esa:CreateRoutine` | Create a new edge function |
| `esa:DeleteRoutine` | Delete an edge function |
| `esa:GetRoutine` | Get edge function details |
| `esa:ListUserRoutines` | List all user's edge functions |

### Functions & Pages - Code Version

| Action | Description |
|--------|-------------|
| `esa:GetRoutineStagingCodeUploadInfo` | Get staging code upload info |
| `esa:CommitRoutineStagingCode` | Commit staging code version |
| `esa:PublishRoutineCodeVersion` | Publish code version to environment |

### Functions & Pages - Assets Deployment

| Action | Description |
|--------|-------------|
| `esa:CreateRoutineWithAssetsCodeVersion` | Create routine with assets code version |
| `esa:GetRoutineCodeVersionInfo` | Get code version build status |
| `esa:CreateRoutineCodeDeployment` | Deploy code version to environment |

### Functions & Pages - Routes

| Action | Description |
|--------|-------------|
| `esa:CreateRoutineRoute` | Create route for edge function |
| `esa:ListRoutineRoutes` | List routes for edge function |

### Edge KV - Namespace

| Action | Description |
|--------|-------------|
| `esa:CreateKvNamespace` | Create KV namespace |
| `esa:GetKvNamespace` | Get KV namespace details |
| `esa:GetKvAccount` | Get KV account info |

### Edge KV - Key Operations

| Action | Description |
|--------|-------------|
| `esa:PutKv` | Put key-value pair |
| `esa:GetKv` | Get value by key |
| `esa:ListKvs` | List keys in namespace |

### Edge KV - Batch Operations

| Action | Description |
|--------|-------------|
| `esa:BatchPutKv` | Batch put key-value pairs |

### Edge KV - High Capacity

| Action | Description |
|--------|-------------|
| `esa:PutKvWithHighCapacity` | Put large value (up to 25MB) |
| `esa:BatchPutKvWithHighCapacity` | Batch put large values |

## Sample RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "esa:OpenErService",
        "esa:GetErService",
        "esa:CreateRoutine",
        "esa:DeleteRoutine",
        "esa:GetRoutine",
        "esa:ListUserRoutines",
        "esa:GetRoutineStagingCodeUploadInfo",
        "esa:CommitRoutineStagingCode",
        "esa:PublishRoutineCodeVersion",
        "esa:CreateRoutineWithAssetsCodeVersion",
        "esa:GetRoutineCodeVersionInfo",
        "esa:CreateRoutineCodeDeployment",
        "esa:CreateRoutineRoute",
        "esa:ListRoutineRoutes",
        "esa:CreateKvNamespace",
        "esa:GetKvNamespace",
        "esa:GetKvAccount",
        "esa:PutKv",
        "esa:GetKv",
        "esa:ListKvs",
        "esa:BatchPutKv",
        "esa:PutKvWithHighCapacity",
        "esa:BatchPutKvWithHighCapacity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Minimum Permission Sets

### Deploy Only (Functions & Pages)

For users who only need to deploy edge functions and static pages:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "esa:OpenErService",
        "esa:GetErService",
        "esa:CreateRoutine",
        "esa:DeleteRoutine",
        "esa:GetRoutine",
        "esa:ListUserRoutines",
        "esa:GetRoutineStagingCodeUploadInfo",
        "esa:CommitRoutineStagingCode",
        "esa:PublishRoutineCodeVersion",
        "esa:CreateRoutineWithAssetsCodeVersion",
        "esa:GetRoutineCodeVersionInfo",
        "esa:CreateRoutineCodeDeployment"
      ],
      "Resource": "*"
    }
  ]
}
```

### KV Only (Edge KV)

For users who only need to manage Edge KV storage:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "esa:CreateKvNamespace",
        "esa:GetKvNamespace",
        "esa:GetKvAccount",
        "esa:PutKv",
        "esa:GetKv",
        "esa:ListKvs",
        "esa:BatchPutKv",
        "esa:PutKvWithHighCapacity",
        "esa:BatchPutKvWithHighCapacity"
      ],
      "Resource": "*"
    }
  ]
}
```

## Reference

- [RAM Policy Overview](https://help.aliyun.com/document_detail/28627.html)
- [ESA API Authorization](https://help.aliyun.com/zh/edge-security-acceleration/esa/api-esa-2024-09-10-overview)

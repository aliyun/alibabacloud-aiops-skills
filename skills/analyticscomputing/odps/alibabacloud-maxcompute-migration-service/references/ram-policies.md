# RAM Policies for MaxCompute Migration Service (MMS)

This document describes in detail the permission configuration required by MMS, including RAM permissions and MaxCompute project permissions.

## Permission Configuration Overview

MMS requires three categories of permissions to be configured:

| Permission Type | Grantee | Description |
|---------|---------|------|
| Service-linked role | Alibaba Cloud account | The role MMS uses to access cloud resources |
| RAM permissions | The RAM user performing the migration | MMS operation permissions |
| MaxCompute project permissions | Service-linked role | Data read/write permissions |

## 1. Service-Linked Role

Before using MMS for the first time, you must create the service-linked role:

**Role name**: `AliyunServiceRoleForMaxComputeMMS`

**How to create it**:

### Via the MaxCompute console
1. Log in to the MaxCompute console
2. Go to Data Transmission > Migration Service
3. Click Add Data Source
4. Confirm creation in the dialog that appears

### Via the RAM console
1. Log in to the RAM console > Identity Management > Roles
2. Click Create Role > Create Service-Linked Role
3. Select the trusted cloud service: `AliyunServiceRoleForMaxComputeMMS`

> **Note**: The RAM user needs the `AliyunRAMFullAccess` permission to create the service-linked role

## 2. RAM Permission Policies (for the RAM user)

### 2.1 Full MMS Operation Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListMmsDataSources",
        "odps:CreateMmsDataSource",
        "ram:GetRole",
        "odps:GetMmsDataSource",
        "odps:UpdateMmsDataSource",
        "odps:CreateMmsFetchMetadataJob",
        "odps:GetMmsFetchMetadataJob",
        "odps:ListMmsFetchMetadataJobLogs",
        "odps:ListMmsDbs",
        "odps:GetMmsDb",
        "odps:ListMmsTables",
        "odps:GetMmsTable",
        "odps:ListMmsPartitions",
        "odps:GetMmsPartition",
        "odps:ListMmsJobs",
        "odps:GetMmsJob",
        "odps:CreateMmsJob",
        "odps:StartMmsJob",
        "odps:StopMmsJob",
        "odps:RetryMmsJob",
        "odps:ListMmsTasks",
        "odps:GetMmsTask",
        "odps:ListMmsTaskLogs",
        "odps:StopMmsTask",
        "odps:StartMmsTask",
        "odps:RetryMmsTask",
        "odps:GetMmsAsyncTask",
        "odps:GetMmsProgress",
        "odps:GetMmsSpeed",
        "odps:CreateMmsAuthFile",
        "odps:ListMmsAgents",
        "odps:ListMmsTimers",
        "odps:GetMmsTimer",
        "odps:UpdateMmsTimer",
        "odps:ListMmsTimerLogs",
        "odps:CreateMmsTimer",
        "odps:UpdateMmsTables",
        "odps:UpdateMmsTable",
        "odps:UpdateMmsDb",
        "odps:ListNetworkLinks"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2.2 MMS Source Data Management Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListMmsDataSources",
        "odps:CreateMmsDataSource",
        "ram:GetRole",
        "odps:GetMmsDataSource",
        "odps:UpdateMmsDataSource",
        "odps:CreateMmsFetchMetadataJob",
        "odps:GetMmsFetchMetadataJob",
        "odps:ListMmsFetchMetadataJobLogs",
        "odps:ListMmsDbs",
        "odps:GetMmsDb",
        "odps:ListMmsTables",
        "odps:GetMmsTable",
        "odps:ListMmsPartitions",
        "odps:GetMmsPartition",
        "odps:GetMmsAsyncTask",
        "odps:GetMmsProgress",
        "odps:GetMmsSpeed",
        "odps:CreateMmsAuthFile",
        "odps:ListMmsAgents",
        "odps:UpdateMmsTables",
        "odps:UpdateMmsTable",
        "odps:UpdateMmsDb"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2.3 MMS Migration Job Management Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListMmsDataSources",
        "odps:GetMmsDataSource",
        "odps:CreateMmsFetchMetadataJob",
        "odps:GetMmsFetchMetadataJob",
        "odps:ListMmsFetchMetadataJobLogs",
        "odps:ListMmsDbs",
        "odps:GetMmsDb",
        "odps:ListMmsTables",
        "odps:GetMmsTable",
        "odps:ListMmsPartitions",
        "odps:GetMmsPartition",
        "odps:ListMmsJobs",
        "odps:GetMmsJob",
        "odps:CreateMmsJob",
        "odps:StartMmsJob",
        "odps:StopMmsJob",
        "odps:RetryMmsJob",
        "odps:ListMmsTasks",
        "odps:GetMmsTask",
        "odps:ListMmsTaskLogs",
        "odps:StopMmsTask",
        "odps:StartMmsTask",
        "odps:RetryMmsTask",
        "odps:GetMmsAsyncTask",
        "odps:GetMmsProgress",
        "odps:GetMmsSpeed",
        "odps:ListMmsTimers",
        "odps:GetMmsTimer",
        "odps:UpdateMmsTimer",
        "odps:ListMmsTimerLogs",
        "odps:CreateMmsTimer"
      ],
      "Resource": "*"
    }
  ]
}
```

## 3. MaxCompute Project Permissions (for the service-linked role)

In the target project, you need to grant data operation permissions to the service-linked role:

### 3.1 Add the Service-Linked Role to the Project

```sql
USE <target_project>;
ADD USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

### 3.2 Coarse-Grained Authorization (Recommended)

```sql
-- Grant the admin role
GRANT admin TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

### 3.3 Fine-Grained Authorization

**Project-level permissions:**

```sql
GRANT Read,Write,List,CreateTable,CreateInstance,CreateFunction,CreateResource
ON project <project_name> TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;

-- Or grant all permissions
GRANT ALL ON project <project_name> TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

**Table-level permissions:**

```sql
GRANT Describe,Select,Alter,Update,Drop,ShowHistory
ON table <table_name> TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;

-- Or grant all permissions
GRANT All ON table <table_name> TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

**Instance-level permissions:**

```sql
GRANT Read,Write ON instance <instance_id>
TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

### 3.4 Permission Reference

| Object Type | Supported Permissions |
|---------|-----------|
| Project | Read, Write, List, CreateTable, CreateInstance, CreateFunction, CreateResource, All |
| Table | Describe, Select, Alter, Update, Drop, ShowHistory, All |
| Instance | Read, Write, All |
| Resource | Read, Write, Download, Delete |
| Function | Read, Write, Download, Execute, Delete |

## 4. Quick Authorization Options

| Scenario | Recommended Option |
|-----|---------|
| Operations with the primary account | No additional RAM permission configuration needed |
| RAM user with full MaxCompute permissions | Grant `AliyunMaxComputeFullAccess` |
| RAM user with MMS operation permissions only | Use the custom permission policies above |
| Creating the service-linked role | The RAM user needs `AliyunRAMFullAccess` |

## 5. Configuring Permissions via the Console

### Configuring Project Permissions in the MaxCompute Console

1. Log in to the MaxCompute console
2. Go to Management Configuration > Project Management
3. Click Manage for the target project
4. Select the Role Permissions tab
5. Create a role and configure its permissions
6. Add the service-linked role in Member Management

## 6. Permission Troubleshooting

### Common Errors

| Error Message | Cause | Solution |
|---------|------|---------|
| Forbidden.RAM | The RAM user lacks MMS operation permissions | Add the MMS permission policy |
| Access Denied | The service-linked role has not been granted project permissions | Add the user in the project and grant permissions |
| ServiceLinkedRole not found | The service-linked role has not been created | Create AliyunServiceRoleForMaxComputeMMS |

### Permission Checklist

- [ ] The service-linked role has been created
- [ ] The RAM user has been granted MMS operation permissions
- [ ] The service-linked role has been added to the target project
- [ ] The service-linked role has been granted data operation permissions
- [ ] The target project has been bound to a Quota resource

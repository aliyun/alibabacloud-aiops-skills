# DataWorks Infrastructure Related APIs

## Data Source APIs

### CreateDataSource - Create Data Source

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|------|--------|
| ProjectId | long | Yes | DataWorks workspace ID | 17820 |
| Name | string | Yes | Data source name | my_mysql |
| Type | string | Yes | Data source type | mysql |
| ConnectionPropertiesMode | string | Yes | Connection mode: UrlMode / InstanceMode | UrlMode |
| ConnectionProperties | string | Yes | Connection configuration JSON | See examples |
| Description | string | No | Description | MySQL production |

**Response Parameters:**

| Name | Type | Description |
|------|------|------|
| RequestId | string | Request ID |
| Id | long | Data source ID |

### GetDataSource - Get Data Source Details

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| Id | long | Yes | Data source ID |

**Response Parameters:**

| Name | Type | Description |
|------|------|------|
| RequestId | string | Request ID |
| DataSource | object | Data source details |

### ListDataSources - List Data Sources

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ProjectId | long | Yes | Workspace ID |
| Types | array | No | Data source type filter |
| EnvType | string | No | Environment type: Dev / Prod |
| PageNumber | integer | No | Page number, default 1 |
| PageSize | integer | No | Page size, default 10, max 100 |

### TestDataSourceConnectivity - Test Connectivity

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| Id | long | Yes | Data source ID |
| ProjectId | long | Yes | Workspace ID |
| ResourceGroupId | string | Yes | Resource group ID |

> **Note**: UpdateDataSource and DeleteDataSource APIs are intentionally excluded from this skill for security reasons. To modify or delete data sources, please use the DataWorks console.

---

## Compute Resource APIs

### CreateComputeResource - Create Compute Resource

**Request Parameters:**

| Name | Type | Required | Description | Example |
|------|------|----------|------|--------|
| ProjectId | long | Yes | DataWorks workspace ID | 10001 |
| Name | string | Yes | Compute resource name (letters, digits, underscores; cannot start with digit or underscore; max 255 chars) | my_holo_resource |
| Type | string | Yes | Compute resource type | hologres |
| ConnectionPropertiesMode | string | Yes | Connection mode: InstanceMode / UrlMode | InstanceMode |
| ConnectionProperties | string | Yes | Connection configuration JSON | See examples |
| Description | string | No | Description (max 3000 chars) | Hologres resource |

**Response Parameters:**

| Name | Type | Description |
|------|------|------|
| RequestId | string | Request ID |
| Id | long | Compute resource ID |

### GetComputeResource - Get Compute Resource Details

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| Id | long | Yes | Compute resource ID |
| ProjectId | long | Yes | Workspace ID |

**Response Parameters:**

| Name | Type | Description |
|------|------|------|
| RequestId | string | Request ID |
| ComputeResource | object | Compute resource details (Id, Name, Type, ConnectionProperties, CreateTime, ModifyTime, etc.) |

### ListComputeResources - List Compute Resources

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ProjectId | long | Yes | Workspace ID |
| Name | string | No | Name filter |
| Types | array | No | Type filter |
| EnvType | string | No | Environment type: Dev / Prod |
| PageNumber | integer | No | Page number, default 1 |
| PageSize | integer | No | Page size, default 10, max 100 |
| SortBy | string | No | Sort field |
| Order | string | No | Sort order: Desc / Asc |

> **Note**: UpdateComputeResource and DeleteComputeResource APIs are intentionally excluded from this skill for security reasons. To modify or delete compute resources, please use the DataWorks console.

---

## Resource Group APIs

### CreateResourceGroup - Create Resource Group

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| Name | string | Yes | Resource group name |
| PaymentType | string | Yes | Payment type: PostPaid |
| VpcId | string | Yes | VPC ID |
| VswitchId | string | Yes | VSwitch ID |
| ClientToken | string | No | Idempotent token |
| Remark | string | No | Remark |
| Spec | integer | No | Specification |

### GetResourceGroup - Get Resource Group

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| Id | string | Yes | Resource group ID |

### ListResourceGroups - List Resource Groups

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| PageSize | integer | No | Page size |
| Statuses | array | No | Status filter |

### AssociateProjectToResourceGroup - Bind Workspace

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ResourceGroupId | string | Yes | Resource group ID |
| ProjectId | long | Yes | Workspace ID |

### DissociateProjectFromResourceGroup - Unbind Workspace

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ResourceGroupId | string | Yes | Resource group ID |
| ProjectId | long | Yes | Workspace ID |

### ListResourceGroupAssociateProjects - Query Binding Relationships

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ResourceGroupId | string | Yes | Resource group ID |

---

## Workspace Member APIs

### ListProjectRoles - Query Role List

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ProjectId | long | Yes | Workspace ID |
| Type | string | No | Role type: System / Custom |
| PageSize | integer | No | Page size |

### ListProjectMembers - Query Member List

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ProjectId | long | Yes | Workspace ID |
| RoleCodes | array | No | Role filter |
| PageSize | integer | No | Page size |

### GetProjectMember - Get Member Details

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ProjectId | long | Yes | Workspace ID |
| UserId | string | Yes | User ID |

### CreateProjectMember - Add Member

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ProjectId | long | Yes | Workspace ID |
| UserId | string | Yes | User ID |
| RoleCodes | array | Yes | Role list |

### DeleteProjectMember - Remove Member

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ProjectId | long | Yes | Workspace ID |
| UserId | string | Yes | User ID |

### GrantMemberProjectRoles - Grant Roles

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ProjectId | long | Yes | Workspace ID |
| UserId | string | Yes | User ID |
| RoleCodes | array | Yes | Roles to grant |

### RevokeMemberProjectRoles - Revoke Roles

**Request Parameters:**

| Name | Type | Required | Description |
|------|------|----------|------|
| ProjectId | long | Yes | Workspace ID |
| UserId | string | Yes | User ID |
| RoleCodes | array | Yes | Roles to revoke |

---

## Official Documentation Links

### Data Sources

- [CreateDataSource](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-createdatasource)
- [GetDataSource](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-getdatasource)
- [ListDataSources](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-listdatasources)
- [TestDataSourceConnectivity](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-testdatasourceconnectivity)

### Compute Resources

- [CreateComputeResource](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-createcomputeresource)
- [GetComputeResource](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-getcomputeresource)
- [ListComputeResources](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-listcomputeresources)

### Resource Groups

- [CreateResourceGroup](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-createresourcegroup)
- [GetResourceGroup](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-getresourcegroup)
- [ListResourceGroups](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-listresourcegroups)

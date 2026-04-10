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

## Region and Endpoints

DataWorks OpenAPI uses region-specific endpoints. When specifying `--region`, you **must** also add the matching `--endpoint`.

### Usage

| Scenario | Parameters |
|----------|-----------|
| Public network | `--region <REGION_ID> --endpoint dataworks.<REGION_ID>.aliyuncs.com` |
| VPC internal network | `--region <REGION_ID> --endpoint dataworks-vpc.<REGION_ID>.aliyuncs.com` |

### Supported Regions

| Region Name | Region ID | Public Endpoint | VPC Endpoint |
|---|---|---|---|
| China (Hangzhou) | `cn-hangzhou` | `dataworks.cn-hangzhou.aliyuncs.com` | `dataworks-vpc.cn-hangzhou.aliyuncs.com` |
| China (Shanghai) | `cn-shanghai` | `dataworks.cn-shanghai.aliyuncs.com` | `dataworks-vpc.cn-shanghai.aliyuncs.com` |
| China (Beijing) | `cn-beijing` | `dataworks.cn-beijing.aliyuncs.com` | `dataworks-vpc.cn-beijing.aliyuncs.com` |
| China (Zhangjiakou) | `cn-zhangjiakou` | `dataworks.cn-zhangjiakou.aliyuncs.com` | `dataworks-vpc.cn-zhangjiakou.aliyuncs.com` |
| China (Ulanqab) | `cn-wulanchabu` | `dataworks.cn-wulanchabu.aliyuncs.com` | `dataworks-vpc.cn-wulanchabu.aliyuncs.com` |
| China (Shenzhen) | `cn-shenzhen` | `dataworks.cn-shenzhen.aliyuncs.com` | `dataworks-vpc.cn-shenzhen.aliyuncs.com` |
| China (Chengdu) | `cn-chengdu` | `dataworks.cn-chengdu.aliyuncs.com` | `dataworks-vpc.cn-chengdu.aliyuncs.com` |
| China (Hong Kong) | `cn-hongkong` | `dataworks.cn-hongkong.aliyuncs.com` | `dataworks-vpc.cn-hongkong.aliyuncs.com` |
| Singapore | `ap-southeast-1` | `dataworks.ap-southeast-1.aliyuncs.com` | `dataworks-vpc.ap-southeast-1.aliyuncs.com` |
| Malaysia (Kuala Lumpur) | `ap-southeast-3` | `dataworks.ap-southeast-3.aliyuncs.com` | `dataworks-vpc.ap-southeast-3.aliyuncs.com` |
| Indonesia (Jakarta) | `ap-southeast-5` | `dataworks.ap-southeast-5.aliyuncs.com` | `dataworks-vpc.ap-southeast-5.aliyuncs.com` |
| Japan (Tokyo) | `ap-northeast-1` | `dataworks.ap-northeast-1.aliyuncs.com` | `dataworks-vpc.ap-northeast-1.aliyuncs.com` |
| South Korea (Seoul) | `ap-northeast-2` | `dataworks.ap-northeast-2.aliyuncs.com` | `dataworks-vpc.ap-northeast-2.aliyuncs.com` |
| US (Virginia) | `us-east-1` | `dataworks.us-east-1.aliyuncs.com` | `dataworks-vpc.us-east-1.aliyuncs.com` |
| US (Silicon Valley) | `us-west-1` | `dataworks.us-west-1.aliyuncs.com` | `dataworks-vpc.us-west-1.aliyuncs.com` |
| UK (London) | `eu-west-1` | `dataworks.eu-west-1.aliyuncs.com` | `dataworks-vpc.eu-west-1.aliyuncs.com` |
| Germany (Frankfurt) | `eu-central-1` | `dataworks.eu-central-1.aliyuncs.com` | `dataworks-vpc.eu-central-1.aliyuncs.com` |
| UAE (Dubai) | `me-east-1` | `dataworks.me-east-1.aliyuncs.com` | `dataworks-vpc.me-east-1.aliyuncs.com` |
| Mexico (Querétaro) | `na-south-1` | `dataworks.na-south-1.aliyuncs.com` | `dataworks-vpc.na-south-1.aliyuncs.com` |
| Saudi Arabia (Riyadh) | `me-central-1` | `dataworks.me-central-1.aliyuncs.com` | `dataworks-vpc.me-central-1.aliyuncs.com` |
| China South 1 Finance | `cn-shenzhen-finance-1` | `dataworks.cn-shenzhen-finance-1.aliyuncs.com` | `dataworks-vpc.cn-shenzhen-finance-1.aliyuncs.com` |
| China East 2 Finance | `cn-shanghai-finance-1` | `dataworks.cn-shanghai-finance-1.aliyuncs.com` | `dataworks-vpc.cn-shanghai-finance-1.aliyuncs.com` |
| China East 1 Finance | `cn-hangzhou-finance` | `dataworks.aliyuncs.com` | *not available* |

### Notes

- **Endpoint naming rule**: If a region is not explicitly listed above, the endpoint follows the standard naming pattern:
  - Public: `dataworks.<REGION_ID>.aliyuncs.com`
  - VPC: `dataworks-vpc.<REGION_ID>.aliyuncs.com`
- **Endpoint selection**: Always use the **public endpoint** by default. Only use the VPC endpoint when the user explicitly specifies it (e.g., the API call is being made from within an Alibaba Cloud VPC).
- **Finance Cloud (`cn-hangzhou-finance`)**: Uses the global endpoint `dataworks.aliyuncs.com` and does **not** support VPC endpoints.
- **Official documentation**: [DataWorks Service Access Points](https://help.aliyun.com/zh/dataworks/developer-reference/api-dataworks-public-2024-05-18-endpoint)

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

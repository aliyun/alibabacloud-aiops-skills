# Alibaba Cloud Realtime Compute for Apache Flink — Permissions, Security & Project Management

## Permission Management (RBAC)

### Member Management

- Flink integrates with the Alibaba Cloud account system
- Authorization is granted by **adding members** and binding roles
- Supports permission isolation at the project workspace level

### Role Management

- Supports **custom roles** for flexible permission requirements
- Built-in roles cover: developer, operations, administrator, etc.

### Permission Granularity

| Permission Scope | Description |
|---|---|
| **Project Workspace Level** | Operation permissions within a specified project workspace |
| **Job Level** | Read/write/operations permissions for individual jobs |
| **Resource Level** | Management permissions for resources/queues |

## Security Configuration

### Key Management (Variables and Secrets)

- Avoids plaintext AccessKeys, passwords, and other sensitive information
- Supported in SQL jobs, JAR jobs, and Python jobs
- Use `${var_name}` to reference variables/secrets
- Example: `'username' = '${my_ak}'`

```sql
-- Use managed variables/secrets in SQL
CREATE TEMPORARY TABLE mysql_table (...) WITH (
    'username' = '${db_user}',
    'password' = '${db_password}'
);
```

### Operation Auditing

- Comprehensive operation audit logs record all production changes
- Traceable and auditable

### Hive Kerberos

- Flink supports accessing Kerberos-enabled Hive clusters
- You must register the Kerberos cluster information and Principal user in the console
- Entry: [Register Hive Kerberos Cluster](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/register-the-hive-kerberos-cluster)

## Project Workspace Management

- A project workspace is the **basic unit** for Flink job management
- Configuration, jobs, and permissions are all scoped under a single project workspace
- Multiple project workspaces can be added to achieve **multi-tenant isolation**

## Tag Management

- Tag = Tag Key + Tag Value
- Used for classification, search, and aggregation of cloud resources
- Supports filtering jobs/workspaces by tags

## SDK & OpenAPI

- **OpenAPI Developer Portal**: https://next.api.aliyun.com/api/ververica/
- **SDK Support**: Java, Python, PHP, etc.
- API Version: `2022-07-18`
- RPC-style API supporting both GET and POST requests

## Official Documentation Links

- [Permission Management](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/permission-management/)
- [Variables and Secrets Management](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-keys)
- [Project Workspace Management](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/create-and-manage-a-namespace)
- [OpenAPI Reference](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/openapi-reference/)

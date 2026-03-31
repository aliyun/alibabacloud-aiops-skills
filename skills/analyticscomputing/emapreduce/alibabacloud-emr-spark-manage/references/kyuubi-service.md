# Kyuubi Service: Interactive SQL Gateway Management

## Table of Contents

- [1. Overview](#1-overview)
- [2. Create Kyuubi Service](#2-create-kyuubi-service)
- [3. Start/Stop Management](#3-startstop-management)
- [4. Connect to Kyuubi and Execute SQL](#4-connect-to-kyuubi-and-execute-sql)
- [5. Token Management](#5-token-management)
- [6. Application Management](#6-application-management)
- [7. Modify and Delete](#7-modify-and-delete)

## 1. Overview

Kyuubi service is an interactive SQL gateway compatible with open-source Kyuubi provided by EMR Serverless Spark. Supports executing Spark SQL queries through standard JDBC connections (beeline, DBeaver, etc.).

### Core Features

| Feature | Description |
|---------|-------------|
| **JDBC Compatible** | Supports standard JDBC tools like beeline, DBeaver for connections |
| **Public Network Access** | Can enable public Endpoint, supports remote connections |
| **High Availability** | Supports multi-replica deployment |
| **Token Authentication** | Secure authentication via Token |

### Operation Flow

1. Create Kyuubi Service → 2. Start Service → 3. Get Endpoint → 4. Create Token → 5. Use beeline to connect and execute SQL

## 2. Create Kyuubi Service

### Pre-creation Confirmation

Before submission, need to confirm:
1. Workspace ID
2. Resource queue name
3. Engine version
4. Whether public network access is needed

### Create Basic Kyuubi Service

```bash
aliyun emr-serverless-spark POST "/api/v1/kyuubi/{workspaceId}?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "name": "my-kyuubi",
    "queue": "default",
    "releaseVersion": "esr-2.1 (Spark 3.3.1, Scala 2.12, Java Runtime)"
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

### Create Kyuubi Service with Public Network Access

```bash
aliyun emr-serverless-spark POST "/api/v1/kyuubi/{workspaceId}?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "name": "my-kyuubi-public",
    "queue": "default",
    "releaseVersion": "esr-2.1 (Spark 3.3.1, Scala 2.12, Java Runtime)",
    "publicEndpointEnabled": true,
    "replica": 2
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

### Create Kyuubi Service with Custom Configuration

```bash
aliyun emr-serverless-spark POST "/api/v1/kyuubi/{workspaceId}?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "name": "my-kyuubi-custom",
    "queue": "default",
    "releaseVersion": "esr-2.1 (Spark 3.3.1, Scala 2.12, Java Runtime)",
    "publicEndpointEnabled": true,
    "kyuubiConfigs": "kyuubi.session.idle.timeout=PT1H",
    "sparkConfigs": "spark.executor.memory=20g;spark.executor.cores=4"
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

## 3. Start/Stop Management

### Start Kyuubi Service

```bash
aliyun emr-serverless-spark POST "/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}/start?regionId=cn-hangzhou" --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

### Stop Kyuubi Service

#### Pre-stop Confirmation

1. **Confirm active connection impact**: All active JDBC connections will be disconnected, executing queries will be aborted
2. **User explicit confirmation**: Inform user of stop operation impact

```bash
# ⚠️ Stop Kyuubi Service (all active JDBC connections will be disconnected)
aliyun emr-serverless-spark POST "/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}/stop?regionId=cn-hangzhou" --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

### View Service Status

```bash
aliyun emr-serverless-spark GET /api/v1/kyuubi/{workspaceId}/{kyuubiServiceId} --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

Key information in the response:
- `state`: Service status
- `innerEndpoint`: Internal network connection address
- `publicEndpoint`: Public network connection address (if enabled)
- `kyuubiServiceId`: Service ID

### Kyuubi Service Status Description

| Status | Description |
|--------|-------------|
| NOT_STARTED | Service created but not started, or already stopped |
| STARTING | Service starting |
| RUNNING | Service running, can accept JDBC connections |
| TERMINATING | Service stopping |

### List All Kyuubi Services

```bash
aliyun emr-serverless-spark GET /api/v1/kyuubi/{workspaceId} --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

## 4. Connect to Kyuubi and Execute SQL

### Get Connection Information

First query service details to get Endpoint:

```bash
aliyun emr-serverless-spark GET /api/v1/kyuubi/{workspaceId}/{kyuubiServiceId} --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

### Connect Using beeline

```bash
# Internal network connection
beeline -u "jdbc:hive2://{innerEndpoint}:10009" -n token -p {your-token}

# Public network connection
beeline -u "jdbc:hive2://{publicEndpoint}:10009" -n token -p {your-token}
```

### Execute SQL Example

```bash
# Execute query after connecting
beeline -u "jdbc:hive2://{endpoint}:10009" -n token -p {your-token} \
  -e "SELECT * FROM my_database.my_table LIMIT 10"

# Execute SQL file
beeline -u "jdbc:hive2://{endpoint}:10009" -n token -p {your-token} \
  -f /path/to/my_query.sql
```

## 5. Token Management

Kyuubi service uses Token for identity authentication.

### Create Token

> **Note**:
> - `token` is a required field, length must be >= 32 characters
> - Token value must be globally unique, cannot duplicate other users' Tokens, recommend using randomly generated values
> - `memberArns` is an optional field

```bash
# First generate a random token (32-character hexadecimal)
# TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(16))")

aliyun emr-serverless-spark POST "/api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "name": "my-token",
    "token": "<replace with random string of 32+ characters>"
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

### Query Token Details

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token/{tokenId} --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

### List Tokens

```bash
aliyun emr-serverless-spark GET /api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

### Modify Token

```bash
aliyun emr-serverless-spark PUT "/api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token/{tokenId}?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "name": "new-token-name"
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

> Modifiable fields: `name` (name), `token` (Token content, >=32 characters), `autoExpireConfiguration` (auto expire configuration), `memberArns` (authorized users).

### Delete Token

#### Pre-deletion Confirmation

1. **Confirm Token ID**: Confirm Token to delete via GetKyuubiToken
2. **User explicit confirmation**: Inform user that connections using this Token will fail authentication after deletion

```bash
# First confirm Token information
aliyun emr-serverless-spark GET /api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token/{tokenId} --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills

# ⚠️ Delete Token (connections using this Token will fail authentication)
aliyun emr-serverless-spark DELETE "/api/v1/workspaces/{workspaceId}/kyuubiService/{kyuubiServiceId}/token/{tokenId}?regionId=cn-hangzhou" --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

## 6. Application Management

View and manage Spark applications submitted through Kyuubi.

### List Kyuubi Applications

```bash
aliyun emr-serverless-spark GET /api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}/applications --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

### Cancel Kyuubi Application

#### Pre-cancellation Confirmation

1. **Confirm application ID and status**: Confirm the Spark application to cancel is running
2. **User explicit confirmation**: Inform user that running Spark query will be aborted

```bash
# ⚠️ Cancel Kyuubi Application (running Spark query will be aborted)
aliyun emr-serverless-spark DELETE "/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}/application/{applicationId}?regionId=cn-hangzhou" --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

## 7. Modify and Delete

### Modify Kyuubi Service Configuration

```bash
aliyun emr-serverless-spark PUT "/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}?regionId=cn-hangzhou" \
  --region cn-hangzhou \
  --header "Content-Type=application/json" \
  --body '{
    "name": "my-kyuubi",
    "queue": "root_queue",
    "sparkConfigs": "spark.executor.memory=32g;spark.executor.cores=8",
    "publicEndpointEnabled": true,
    "restart": true
  }' \
  --force --user-agent AlibabaCloud-Agent-Skills
```

### Delete Kyuubi Service

#### Pre-deletion Checklist

1. **Confirm service stopped**: Confirm status is NOT_STARTED via GetKyuubiService
2. **Confirm no active connections**: Confirm all JDBC connections are disconnected
3. **User explicit confirmation**: Inform user deletion is irreversible

```bash
# First confirm service status
aliyun emr-serverless-spark GET /api/v1/kyuubi/{workspaceId}/{kyuubiServiceId} --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills

# ⚠️ Stop Kyuubi Service (all active JDBC connections will be disconnected)
aliyun emr-serverless-spark POST "/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}/stop?regionId=cn-hangzhou" --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills

# ⚠️ Delete Kyuubi Service (irreversible! Kyuubi service will be permanently deleted)
aliyun emr-serverless-spark DELETE "/api/v1/kyuubi/{workspaceId}/{kyuubiServiceId}?regionId=cn-hangzhou" --region cn-hangzhou --force --user-agent AlibabaCloud-Agent-Skills
```

## Common Issues

| Symptom | Possible Cause | Troubleshooting Method |
|---------|----------------|------------------------|
| Connection timeout | Public network not enabled or security group restrictions | Check publicEndpointEnabled and network configuration |
| Authentication failed | Token incorrect or expired | Check if Token is correct and not expired |
| Slow queries | Insufficient resources | Adjust executor configuration in sparkConfigs |
| Service start failed | Resource queue insufficient | Check resource queue CU quota |

## Related Documentation

- [Getting Started](getting-started.md) - First-time workspace creation and job submission
- [Job Management](job-management.md) - Submit, monitor, diagnose Spark jobs
- [Scaling Guide](scaling.md) - Resource queue scaling
- [API Parameter Reference](api-reference.md) - Complete parameter documentation
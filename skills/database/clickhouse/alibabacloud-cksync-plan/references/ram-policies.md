# RAM Permission Declaration

## Overview

This skill (`alibabacloud-cksync-plan`) is a **planning and advisory skill** that generates migration plans for ClickHouse clusters. It does **NOT** directly call any Alibaba Cloud OpenAPI.

## Required Permissions

```yaml
required_permissions: none
```

## Explanation

| Category | Requirement | Notes |
|----------|-------------|-------|
| Alibaba Cloud OpenAPI | ❌ Not Required | This skill only generates migration plans and SQL templates |
| ClickHouse SQL Execution | Optional | User may execute provided SQL queries against their clusters |
| OSS Access | ❌ Not Required | OSS access is only mentioned in migration plan documentation |

## Data Access Pattern

This skill operates in a **read-only advisory mode**:

1. **Input**: User provides cluster information (type, version, data size, etc.)
2. **Processing**: Skill analyzes requirements and selects appropriate migration method
3. **Output**: Migration plan document with SQL templates and step-by-step instructions

The skill does **NOT**:
- Connect to any Alibaba Cloud services
- Execute any API calls
- Store or transmit user credentials
- Access user's cloud resources directly

## User Responsibility

When users execute the SQL queries or commands provided in the migration plan:
- Users are responsible for managing their own credentials securely
- Users should use environment variables or secure credential management for database access
- Users should avoid passing plaintext credentials directly in command history

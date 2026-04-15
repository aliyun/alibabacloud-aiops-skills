# RAM Policies

RAM (Resource Access Management) permissions required for OpenSearch instance management.

> **Terminology**: OpenSearch instance and OpenSearch app group are synonymous.

## Permission Summary

| API Action	 | RAM Action  | Description |
|---------|-----------|-------------|
| CreateAppGroup | opensearch:CreateAppGroup | Create OpenSearch instance |
| ListAppGroups | opensearch:ListAppGroups | List instances |
| DescribeAppGroup | opensearch:DescribeAppGroup| Describe instance details |

## RAM Policy Document

### Full Access Policy (Read-Write)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "opensearch:CreateAppGroup",
        "opensearch:ListAppGroups",
        "opensearch:DescribeAppGroup"
      ],
      "Resource": "acs:opensearch:*:*:apps/*"
    }
  ]
}
```

### Read-Only Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "opensearch:ListAppGroups",
        "opensearch:DescribeAppGroup"
      ],
      "Resource": "acs:opensearch:*:*:apps/*"
    }
  ]
}
```

### Create Instance Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "opensearch:CreateAppGroup",
      "Resource": "acs:opensearch:*:*:apps/*"
    }
  ]
}
```

## System Policies

Alibaba Cloud provides the following OpenSearch system policies:

| Policy Name | Description |
|-------------|-------------|
| AliyunOpenSearchFullAccess | Full management access to OpenSearch |
| AliyunOpenSearchReadOnlyAccess | Read-only access to OpenSearch |

## Usage

1. Log in to [RAM Console](https://ram.console.aliyun.com/)
2. Create custom policy or use system policy
3. Attach policy to RAM user or role

## Best Practices

1. **Principle of Least Privilege**: Only grant minimum permissions required for the task
2. **Use System Policies**: Prefer Alibaba Cloud provided system policies
3. **Regular Auditing**: Regularly review and clean up unnecessary permissions
4. **Resource-Level Restrictions**: Restrict access to specific resources when possible

## Reference Documentation

- [RAM Policy Overview](https://help.aliyun.com/document_detail/93732.html)
- [OpenSearch Authorization Info](https://help.aliyun.com/zh/open-search/industry-algorithm-edition/authorization-rules-of-applications)

# Aliyun CLI Parameter Guide

## Key Parameter Rules

### gpdb commands use `--biz-region-id` (NOT `--RegionId`)

**Important:** All `aliyun gpdb` commands use `--biz-region-id` parameter to specify the region.

```bash
# Correct
aliyun gpdb create-db-instance --biz-region-id cn-hangzhou ...

# Wrong - will fail
aliyun gpdb create-db-instance --RegionId cn-hangzhou ...
```

### Parameter Naming Convention: kebab-case

All CLI parameters use lowercase letters + hyphens (kebab-case), NOT PascalCase:

| API Parameter | CLI Parameter |
|---------------|---------------|
| RegionId | `--biz-region-id` |
| DBInstanceId | `--db-instance-id` |
| ZoneId | `--zone-id` |
| VpcId | `--vpc-id` |
| VSwitchId | `--vswitch-id` |
| ProjectName | `--project-name` |
| AccountPassword | `--account-password` |
| ManagerAccount | `--manager-account` |
| ManagerAccountPassword | `--manager-account-password` |
| NamespacePassword | `--namespace-password` |
| EmbeddingModel | `--embedding-model` |

### VPC Command Parameters

VPC commands also use `--biz-region-id`:

```bash
aliyun vpc describe-vpcs --biz-region-id cn-hangzhou
aliyun vpc create-nat-gateway --biz-region-id cn-hangzhou --vpc-id vpc-xxx
```

### EIP Command Parameters

EIP commands use `--region` (NOT `--biz-region-id`):

```bash
aliyun vpc associate-eip-address --region cn-hangzhou --allocation-id eip-xxx
```

## Verify Commands

Use `--help` to check correct parameters:

```bash
aliyun gpdb create-db-instance --help
aliyun gpdb create-namespace --help
aliyun vpc create-nat-gateway --help
```

## Common Errors

### Error 1: Using `--RegionId`

```bash
# Wrong
aliyun gpdb create-db-instance --RegionId cn-hangzhou ...

# Error message
Error: '--RegionId' is not a valid parameter or flag.
Did you mean: --biz-region-id
```

### Error 2: Using PascalCase Parameter Names

```bash
# Wrong
aliyun gpdb create-db-instance --biz-region-id cn-hangzhou --DBInstanceId gp-xxx ...

# Error message
Error: '--DBInstanceId' is not a valid parameter or flag.
Did you mean: --db-instance-id
```

### Error 3: ChatWithKnowledgeBase Missing QueryParams

```bash
# Wrong
--knowledge-params '{"SourceCollection": [{"Collection": "...", "TopK": 5}]}'

# Error message
Error: invalid 'SourceCollection': unknown field: TopK

# Correct - TopK must be inside QueryParams
--knowledge-params '{"SourceCollection": [{"Collection": "...", "QueryParams": {"TopK": 5}}]}'
```

For complete command examples, see [related-apis.md](related-apis.md).

# Command Syntax Guide

Supplementary reference for the Aliyun CLI plugin system. For core usage instructions,
see SKILL.md (the primary document).

## Basic Command Structure

```bash
aliyun <product> <command> [--parameter value] [--global-flag value]
```

- `<product>`: Plugin name (ecs, fc, rds, oss, sls, etc.)
- `<command>`: Operation in kebab-case (describe-instances, create-function)
- `--parameter`: Command-specific parameters in kebab-case
- `--global-flag`: Global flags like --region-id, --output, --log-level

## Parameter Types, Output Filtering, Global Flags, Pagination, Waiters

See SKILL.md §6 (structured parameters), §8 (filter and format output),
§9 (pagination), §10 (waiters), and the Global Flags Reference table.

### JSON Parameters (supplementary)

For very complex structures where structured syntax is insufficient, raw JSON is supported:

```bash
aliyun fc create-function \
  --function-name test \
  --code '{"zipFile":"base64encoded..."}'
```

## Help System

```bash
aliyun ecs --help                              # Product-level: list all subcommands
aliyun ecs describe-instances --help           # Command-level: parameters, types, structure
aliyun ecs --help | grep "Available Commands"  # Quick command listing
```

When a plugin is installed, `aliyun <product> --help` shows plugin help automatically.
See SKILL.md §2 for details on `ALIBABA_CLOUD_ORIGINAL_PRODUCT_HELP`.

## Error Handling

### Common Error Messages

1. **Plugin not found**

   ```text
   Error: plugin 'xxx' not found
   Solution: aliyun plugin install --names xxx
   ```

2. **Missing required parameter**

   ```text
   Error: required parameter '--instance-id' not provided
   Solution: Add the required parameter. Check --help for required params.
   ```

3. **Invalid parameter value**

   ```text
   Error: invalid value for '--instance-type'
   Solution: Check valid values with --help
   ```

4. **API version not supported**

   ```text
   Error: unsupported API version
   Solution: aliyun <product> list-api-versions
   ```

5. **Authentication error**

   ```text
   Error: InvalidAccessKeyId.NotFound
   Solution: aliyun configure set --access-key-id <new-key> --access-key-secret <new-secret>
   ```

6. **Signature mismatch**

   ```text
   Error: SignatureDoesNotMatch
   Solution: Verify access key secret. Check for extra whitespace in credentials.
   ```

### Debugging failed commands

Always add `--log-level debug` to see the full request/response cycle:

```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --log-level debug
```

This reveals: API endpoint, serialized parameters, HTTP status, and response body.

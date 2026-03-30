# Global Flags Reference

Supplementary reference for CLI global flags. For commonly used flags, see SKILL.md
(Global Flags Reference table, §8 output filtering, §11 debugging).

This document covers **hidden/advanced flags** and details not in SKILL.md.

## Hidden Global Flags

These flags are available but not shown in `--help`:

### --waiter (advanced syntax)

SKILL.md §10 shows basic waiter usage. Full syntax with timeout and interval:

```bash
aliyun ecs describe-instances \
  --instance-id i-xxx \
  --waiter expr='Instances.Instance[0].Status' to=Running timeout=180 interval=5
```

- `expr`: JMESPath expression to evaluate on the response
- `to`: Target value to match
- `timeout`: Maximum wait in seconds (default varies)
- `interval`: Poll interval in seconds (default varies)

### --header

Add custom HTTP headers (repeatable):

```bash
aliyun ecs describe-instances \
  --biz-region-id cn-hangzhou \
  --header X-Custom-Header=value \
  --header X-Another-Header=value2
```

### --body / --body-file

Provide raw HTTP request body directly or from file:

```bash
aliyun fc invoke-function \
  --function-name test \
  --body '{"key":"value"}'

aliyun fc create-function \
  --function-name test \
  --body-file ./function-config.json
```

### --secure / --insecure

Force HTTPS or HTTP protocol:

```bash
aliyun ecs describe-instances --secure      # Force HTTPS
aliyun ecs describe-instances --insecure    # Force HTTP (not recommended)
```

### --no-stream

For SSE (Server-Sent Events) APIs: aggregate all events before displaying instead of
streaming them incrementally:

```bash
aliyun <product> <sse-command> --no-stream
```

## --cli-dry-run Example Output

When using `--cli-dry-run`, the CLI prints what would be sent without calling the API:

```text
[DRY-RUN] API call would be made with the following details:
  Endpoint: https://ecs.cn-hangzhou.aliyuncs.com
  Method: POST
  Headers:
    Content-Type: application/x-www-form-urlencoded
    x-acs-action: CreateInstance
  Parameters:
    RegionId=cn-hangzhou
    InstanceType=ecs.g6.large
    ImageId=ubuntu_20_04_x64
```

## --output rows= Parameter

Use `rows=` with `cols=` to specify the JSON path for row data:

```bash
aliyun ecs describe-instances \
  --output cols=InstanceId,Status rows='Instances.Instance[]'
```

## Flag Priority

When the same setting is configured in multiple places:

1. **Command-line flag** (highest)
2. **Environment variable**
3. **Config file** (`~/.aliyun/config.json`)
4. **Default value** (lowest)

```bash
export ALIBABA_CLOUD_REGION_ID=cn-beijing
aliyun ecs describe-instances --biz-region-id cn-hangzhou
# Uses cn-hangzhou (command-line wins)
```

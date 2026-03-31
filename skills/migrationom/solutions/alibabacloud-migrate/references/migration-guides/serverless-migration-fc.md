# Serverless Migration: AWS Lambda to Alibaba Cloud Function Compute

## Overview

Alibaba Cloud Function Compute (FC) is a fully managed serverless compute service equivalent to AWS Lambda. This guide covers migration strategies, code conversion, and infrastructure mapping for migrating from AWS Lambda to Function Compute.

### Key Differences

| Aspect | AWS Lambda | Alibaba Cloud Function Compute |
|--------|-----------|-------------------------------|
| **Execution Model** | Event-driven compute | Event-driven compute |
| **Billing** | Pay per invocation + duration | Pay per invocation + duration |
| **Scaling** | Automatic scaling | Automatic scaling |
| **Cold Start** | ~100ms-1s depending on runtime | ~100ms-1s depending on runtime |
| **Max Memory** | 10 GB | 10 GB |
| **Max Timeout** | 15 minutes | 10 minutes (configurable up to 60 minutes for specific scenarios) |
| **Max Package Size** | 250 MB (unzipped) | 500 MB (unzipped) |
| **Concurrent Executions** | Account-level limit | Account-level limit |
| **Layers** | Supported | Supported (called "Layers") |
| **Container Image Support** | Yes (up to 10 GB) | Yes (up to 10 GB) |

## Feature Comparison Table

| Feature | AWS Lambda | Alibaba Cloud FC | Migration Notes |
|---------|-----------|-----------------|-----------------|
| **Handler Signature** | `exports.handler(event, context)` | `exports.handler(event, context, callback)` | FC supports both callback and Promise styles |
| **Max Timeout** | 15 minutes | 10 minutes (configurable) | Adjust long-running functions |
| **Memory Range** | 128 MB - 10 GB | 128 MB - 10 GB | Direct mapping |
| **Triggers** | API GW, S3, SQS, SNS, etc. | HTTP, OSS, Timer, MNS, etc. | See trigger mapping below |
| **Layers** | Supported | Supported | Similar concept, different CLI |
| **Runtime Versions** | Node.js 20, Python 3.12, etc. | Node.js 20, Python 3.10, etc. | Check runtime availability |
| **Environment Variables** | 4 KB limit | 4 KB limit | Direct mapping |
| **VPC Integration** | Yes | Yes | Similar configuration |
| **Dead Letter Queue** | SQS/SNS | MNS Topic/Queue | Different service |
| **Provisioned Concurrency** | Supported | Supported | Called "Provisioned Mode" |
| **Container Image** | ECR | ACR | Use ACR instead of ECR |
| **Logging** | CloudWatch Logs | SLS (Simple Log Service) | Different logging service |
| **Monitoring** | CloudWatch Metrics | CloudMonitor | Different monitoring service |
| **X-Ray Tracing** | AWS X-Ray | ARMS | Different tracing service |

## Trigger Mapping

| AWS Trigger | FC Trigger | Notes |
|-------------|------------|-------|
| **API Gateway** | **HTTP Trigger** | Direct equivalent, similar event structure |
| **S3 Event** | **OSS Trigger** | Similar event structure, minor format differences |
| **CloudWatch Scheduled** | **Timer Trigger** | Cron syntax compatible |
| **SQS** | **MNS Topic Trigger** | Different queue semantics, code changes needed |
| **SNS** | **MNS Topic Trigger** | Similar pub/sub model |
| **DynamoDB Streams** | **Tablestore Trigger** | Different event format, code changes needed |
| **Kinesis** | **Log Service Trigger** | Different streaming service |
| **EventBridge** | **EventBridge Trigger** | Similar event routing |
| **Cognito** | **IDaaS** | Different identity service |
| **ALB** | **ALB Trigger** | Direct equivalent |

### Trigger Configuration Examples

#### HTTP Trigger (API Gateway Equivalent)

**AWS Lambda:**
```python
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Hello'})
    }
```

**Function Compute:**
```python
def handler(event, context):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'message': 'Hello'})
    }
```

#### OSS Trigger (S3 Event Equivalent)

**AWS S3 Event:**
```json
{
  "Records": [
    {
      "s3": {
        "bucket": {"name": "my-bucket"},
        "object": {"key": "my-key"}
      }
    }
  ]
}
```

**Alibaba Cloud OSS Event:**
```json
{
  "events": [
    {
      "oss": {
        "bucket": {"name": "my-bucket"},
        "object": {"key": "my-key"}
      }
    }
  ]
}
```

#### Timer Trigger (CloudWatch Scheduled Equivalent)

**AWS CloudWatch Events:**
```json
{
  "source": ["aws.events"],
  "detail-type": ["Scheduled Event"]
}
```

**Function Compute Timer:**
```json
{
  "triggerName": "timer-trigger",
  "triggerTime": "2024-01-15T10:30:00Z"
}
```

## Code Migration Examples

### Node.js Migration

#### HTTP Handler Conversion

**AWS Lambda:**
```javascript
// index.js
exports.handler = async (event, context) => {
    const { httpMethod, path, body } = event;
    
    try {
        // Business logic
        const result = { message: 'Success' };
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify(result)
        };
    } catch (error) {
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message })
        };
    }
};
```

**Function Compute:**
```javascript
// index.js
exports.handler = async (event, context) => {
    // Parse event body
    const body = JSON.parse(event.body || '{}');
    const { httpMethod, path } = event;
    
    try {
        // Business logic (same as Lambda)
        const result = { message: 'Success' };
        
        return {
            statusCode: 200,
            headers: {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify(result)
        };
    } catch (error) {
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message })
        };
    }
};
```

**Key Differences:**
- Event structure is similar but may have minor field name differences
- Response format is identical
- Context object has similar properties but different service names

#### Event-Driven Handler (S3/OSS)

**AWS Lambda (S3):**
```javascript
exports.handler = async (event) => {
    for (const record of event.Records) {
        const bucket = record.s3.bucket.name;
        const key = decodeURIComponent(record.s3.object.key);
        
        // Process S3 object
        await processObject(bucket, key);
    }
    
    return { success: true };
};
```

**Function Compute (OSS):**
```javascript
exports.handler = async (event, context) => {
    const eventObj = JSON.parse(event.toString());
    
    for (const record of eventObj.events) {
        const bucket = record.oss.bucket.name;
        const key = decodeURIComponent(record.oss.object.key);
        
        // Process OSS object
        await processObject(bucket, key);
    }
    
    return { success: true };
};
```

### Python Migration

#### HTTP Handler Conversion

**AWS Lambda:**
```python
import json

def lambda_handler(event, context):
    http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method'))
    path = event.get('path', event.get('rawPath'))
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    
    try:
        # Business logic
        result = {'message': 'Success'}
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

**Function Compute:**
```python
import json

def handler(event, context):
    # Parse event
    if isinstance(event, str):
        event = json.loads(event)
    
    http_method = event.get('method', event.get('httpMethod'))
    path = event.get('path', event.get('rawPath'))
    body = json.loads(event.get('body', '{}')) if event.get('body') else {}
    
    try:
        # Business logic (same as Lambda)
        result = {'message': 'Success'}
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

#### SDK Migration: boto3 (S3) → oss2 (OSS)

> **CRITICAL**: When migrating Lambda functions that use `boto3` to access AWS services (S3, DynamoDB, etc.), you must replace the SDK calls with the corresponding Alibaba Cloud SDK. For S3→OSS, use the `oss2` Python package. Authentication **MUST** use FC's built-in STS credentials via `context.credentials` — never hardcode AK/SK.

**AWS Lambda (boto3 + S3):**
```python
import json
import boto3
import os

s3_client = boto3.client('s3')
BUCKET_NAME = os.environ['BUCKET_NAME']

def lambda_handler(event, context):
    """Lambda function: S3 file operations via HTTP API."""
    body = json.loads(event.get('body', '{}'))
    action = body.get('action', 'list')

    if action == 'list':
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        files = [obj['Key'] for obj in response.get('Contents', [])]
        return {'statusCode': 200, 'body': json.dumps({'files': files})}

    elif action == 'read':
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=body['key'])
        content = obj['Body'].read().decode('utf-8')
        return {'statusCode': 200, 'body': json.dumps({'content': content})}

    elif action == 'write':
        s3_client.put_object(Bucket=BUCKET_NAME, Key=body['key'], Body=body['content'].encode())
        return {'statusCode': 200, 'body': json.dumps({'message': 'Written'})}

    elif action == 'delete':
        s3_client.delete_object(Bucket=BUCKET_NAME, Key=body['key'])
        return {'statusCode': 200, 'body': json.dumps({'message': 'Deleted'})}
```

**Function Compute (oss2 + STS credentials):**
```python
import json
import oss2
import os

BUCKET_NAME = os.environ['BUCKET_NAME']
ENDPOINT = os.environ['OSS_ENDPOINT']  # e.g., https://oss-cn-hangzhou-internal.aliyuncs.com

def get_bucket(context):
    """Create OSS bucket client using FC context credentials (STS temporary credentials).
    
    IMPORTANT: FC automatically injects STS credentials when a RAM role is assigned
    to the function. Use context.credentials to access them — never hardcode AK/SK.
    """
    creds = context.credentials
    auth = oss2.StsAuth(
        creds.access_key_id,
        creds.access_key_secret,
        creds.security_token,
    )
    return oss2.Bucket(auth, ENDPOINT, BUCKET_NAME)

def handler(event, context):
    """FC function: OSS file operations (migrated from AWS Lambda + S3)."""
    if isinstance(event, bytes):
        event = json.loads(event.decode())
    elif isinstance(event, str):
        event = json.loads(event)

    body = event.get('body', '{}')
    if isinstance(body, str):
        body = json.loads(body)
    action = body.get('action', 'list')

    bucket = get_bucket(context)

    if action == 'list':
        files = [obj.key for obj in oss2.ObjectIterator(bucket)]
        return {'statusCode': 200, 'body': json.dumps({'files': files})}

    elif action == 'read':
        result = bucket.get_object(body['key'])
        content = result.read().decode('utf-8')
        return {'statusCode': 200, 'body': json.dumps({'content': content})}

    elif action == 'write':
        bucket.put_object(body['key'], body['content'].encode())
        return {'statusCode': 200, 'body': json.dumps({'message': 'Written'})}

    elif action == 'delete':
        bucket.delete_object(body['key'])
        return {'statusCode': 200, 'body': json.dumps({'message': 'Deleted'})}
```

**Key Migration Points:**
- `boto3.client('s3')` → `oss2.Bucket(auth, endpoint, bucket_name)`
- Authentication: AWS IAM role (automatic) → FC RAM role + `context.credentials` + `oss2.StsAuth`
- `s3.list_objects_v2()` → `oss2.ObjectIterator(bucket)`
- `s3.get_object()` → `bucket.get_object(key)`
- `s3.put_object()` → `bucket.put_object(key, data)`
- `s3.delete_object()` → `bucket.delete_object(key)`
- **Dependency**: Add `oss2` to `requirements.txt` (replaces `boto3`)
- **Environment Variables**: Replace `AWS_REGION` with `OSS_ENDPOINT` (use internal endpoint for best performance)

#### Environment Variable Mapping

**AWS Lambda:**
```python
import os

def lambda_handler(event, context):
    db_host = os.environ['DB_HOST']
    api_key = os.environ['API_KEY']
    region = os.environ.get('AWS_REGION', 'us-east-1')
```

**Function Compute:**
```python
import os

def handler(event, context):
    db_host = os.environ['DB_HOST']
    api_key = os.environ['API_KEY']
    region = os.environ.get('FC_REGION', 'cn-hangzhou')
```

**Environment Variable Migration:**
- Copy all environment variables from Lambda to FC
- Update region-specific variables (AWS_REGION → FC_REGION)
- Update service endpoint variables (e.g., S3_ENDPOINT → OSS_ENDPOINT)

### Context Object Mapping

| AWS Lambda Context | Function Compute Context | Notes |
|-------------------|-------------------------|-------|
| `context.function_name` | `context.function_name` | Same |
| `context.function_version` | `context.function_version` | Same |
| `context.memory_limit_in_mb` | `context.memory_limit_in_mb` | Same |
| `context.aws_request_id` | `context.request_id` | Different name |
| `context.log_group_name` | `context.log_project` | Different service |
| `context.log_stream_name` | `context.log_store` | Different service |
| `context.identity` | `context.identity` | Similar structure |
| `context.client_context` | `context.client_context` | Similar structure |

## CLI Commands

### Prerequisites

```bash
# Verify aliyun CLI version (MUST >= 3.3.1)
aliyun version

# Configure credentials
aliyun configure list

# Install FC plugin (if not auto-installed)
aliyun plugin install fc
```

### Terraform Alternative for Function Compute

```hcl
# ─── RAM Role (REQUIRED: FC needs a role to access other Alibaba Cloud services) ───
resource "alicloud_ram_role" "fc_role" {
  name     = "<function-name>-fc-role"
  document = jsonencode({
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = ["fc.aliyuncs.com"] }
    }]
    Version = "1"
  })
  force = true
}

resource "alicloud_ram_policy" "fc_policy" {
  policy_name     = "<function-name>-fc-policy"
  policy_document = jsonencode({
    Statement = [
      {
        Action   = ["oss:GetObject", "oss:PutObject", "oss:DeleteObject", "oss:ListObjects"]
        Effect   = "Allow"
        Resource = ["acs:oss:*:*:<bucket-name>", "acs:oss:*:*:<bucket-name>/*"]
      }
      # Add more statements as needed for other services (SLS, Tablestore, MNS, etc.)
    ]
    Version = "1"
  })
}

resource "alicloud_ram_role_policy_attachment" "fc_attach" {
  policy_name = alicloud_ram_policy.fc_policy.policy_name
  policy_type = "Custom"
  role_name   = alicloud_ram_role.fc_role.name
}

# ─── Function Compute ───
resource "alicloud_fcv3_function" "migration" {
  function_name = "<function-name>"
  handler       = "<handler>"
  runtime       = "<runtime>"
  memory_size   = <memory-mb>
  timeout       = <timeout-seconds>
  role          = alicloud_ram_role.fc_role.arn  # CRITICAL: Without this, FC cannot access OSS/SLS/etc.
  code {
    zip_file = "<base64-encoded-zip>"
  }
}

resource "alicloud_fcv3_trigger" "http" {
  function_name  = alicloud_fcv3_function.migration.function_name
  trigger_name   = "<trigger-name>"
  trigger_type   = "http"
  trigger_config = jsonencode({
    authType = "anonymous"
    methods  = ["GET", "POST"]
  })
}
```

**Trigger Type Examples:**

**HTTP Trigger:**
```hcl
resource "alicloud_fcv3_trigger" "http" {
  function_name  = alicloud_fcv3_function.migration.function_name
  trigger_name   = "<trigger-name>"
  trigger_type   = "http"
  trigger_config = jsonencode({
    authType = "anonymous"
    methods  = ["GET", "POST"]
  })
}
```

**Timer Trigger:**
```hcl
resource "alicloud_fcv3_trigger" "timer" {
  function_name  = alicloud_fcv3_function.migration.function_name
  trigger_name   = "<trigger-name>"
  trigger_type   = "timer"
  trigger_config = jsonencode({
    cronExpression = "0 0 * * * *"
    payload        = ""
  })
}
```

**OSS Trigger:**
```hcl
resource "alicloud_fcv3_trigger" "oss" {
  function_name  = alicloud_fcv3_function.migration.function_name
  trigger_name   = "<trigger-name>"
  trigger_type   = "oss"
  trigger_config = jsonencode({
    events = ["oss:ObjectCreated:*"]
    filter = {
      key = {
        prefix = "uploads/"
      }
    }
  })
}
```

### Create Function

```bash
aliyun fc create-function \
  --function-name <function-name> \
  --runtime nodejs20 \
  --handler index.handler \
  --code zipFile=base64encoded== \
  --memory-size 1024 \
  --timeout 60 \
  --environment-variables '{"DB_HOST": "localhost", "API_KEY": "xxx"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `function-name` | Yes | Function name | `my-function` |
| `runtime` | Yes | Runtime environment | `nodejs20`, `python3.10`, `java11` |
| `handler` | Yes | Entry point | `index.handler`, `app.main` |
| `code` | Yes | Code as base64 or OSS reference | `zipFile=base64encoded==` or `ossBucketName=bucket,ossObjectName=code.zip` |
| `memory-size` | No | Memory in MB (128-10240) | `1024` |
| `timeout` | No | Timeout in seconds (1-600) | `60` |
| `environment-variables` | No | JSON string of env vars | `{"KEY": "value"}` |

### Create HTTP Trigger

```bash
aliyun fc create-trigger \
  --function-name <function-name> \
  --trigger-name http-trigger \
  --trigger-type http \
  --trigger-config '{"authType": "anonymous", "methods": ["GET", "POST"]}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `function-name` | Yes | Target function name | `my-function` |
| `trigger-name` | Yes | Trigger name | `http-trigger` |
| `trigger-type` | Yes | Trigger type | `http`, `oss`, `timer`, `log`, `cdn_events` |
| `trigger-config` | Yes | Trigger configuration JSON | `{"authType": "anonymous"}` |

### Create Timer Trigger

```bash
aliyun fc create-trigger \
  --function-name <function-name> \
  --trigger-name timer-trigger \
  --trigger-type timer \
  --trigger-config '{"cronExpression": "0 0 * * * *", "payload": ""}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Cron Expression Format:**
- Seconds Minutes Hours Day-of-month Month Day-of-week Year (optional)
- Example: `0 0 10 * * *` = Every day at 10:00 AM

### Create OSS Trigger

```bash
aliyun fc create-trigger \
  --function-name <function-name> \
  --trigger-name oss-trigger \
  --trigger-type oss \
  --trigger-config '{"events": ["oss:ObjectCreated:*"], "filter": {"key": {"prefix": "uploads/"}}}' \
  --user-agent AlibabaCloud-Agent-Skills
```

### List Functions

```bash
aliyun fc list-functions \
  --user-agent AlibabaCloud-Agent-Skills
```

### Get Function Details

```bash
aliyun fc get-function \
  --function-name <function-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Invoke Function

```bash
aliyun fc invoke-function \
  --function-name <function-name> \
  --payload '{"key": "value"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Update Function

```bash
aliyun fc update-function \
  --function-name <function-name> \
  --memory-size 2048 \
  --timeout 120 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Delete Function

```bash
aliyun fc delete-function \
  --function-name <function-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

## IAM Mapping: AWS IAM Role → Alibaba Cloud RAM Role

### AWS Lambda Execution Role

**AWS IAM Policy Example:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::my-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/my-table"
    }
  ]
}
```

### Alibaba Cloud RAM Role for FC

**RAM Policy Example:**
```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStore",
        "logs:CreateLogStream",
        "logs:PutLogs"
      ],
      "Resource": "acs:log:*:*:project/*/logstore/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "oss:GetObject",
        "oss:PutObject"
      ],
      "Resource": "acs:oss:*:*:my-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ots:GetRow",
        "ots:PutRow"
      ],
      "Resource": "acs:ots:*:*:instance/my-instance/table/my-table"
    }
  ]
}
```

### Create RAM Role for FC

```bash
aliyun ram CreateRole \
  --RoleName fc-execution-role \
  --AssumeRolePolicyDocument '{"Statement":[{"Action":"sts:AssumeRole","Effect":"Allow","Principal":{"Service":["fc.aliyuncs.com"]}}],"Version":"1"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Attach Policy to RAM Role

```bash
aliyun ram AttachPolicyToRole \
  --PolicyType Custom \
  --PolicyName fc-oss-access \
  --RoleName fc-execution-role \
  --user-agent AlibabaCloud-Agent-Skills
```

### Terraform Alternative for RAM Role Setup

> **Recommended**: Use Terraform for RAM role management to keep it in the same state file as the FC function. This ensures role and function are always created/destroyed together.

```hcl
# 1. Create RAM Role with FC trust policy
resource "alicloud_ram_role" "fc_role" {
  name     = "fc-execution-role"
  document = jsonencode({
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = ["fc.aliyuncs.com"] }
    }]
    Version = "1"
  })
  force = true
}

# 2. Create custom policy (adapt actions/resources to match the original AWS IAM policy)
resource "alicloud_ram_policy" "fc_policy" {
  policy_name     = "fc-oss-access"
  policy_document = jsonencode({
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["oss:GetObject", "oss:PutObject", "oss:DeleteObject", "oss:ListObjects"]
        Resource = ["acs:oss:*:*:<bucket-name>", "acs:oss:*:*:<bucket-name>/*"]
      }
    ]
    Version = "1"
  })
}

# 3. Attach policy to role
resource "alicloud_ram_role_policy_attachment" "fc_attach" {
  policy_name = alicloud_ram_policy.fc_policy.policy_name
  policy_type = "Custom"
  role_name   = alicloud_ram_role.fc_role.name
}

# 4. Reference in function: role = alicloud_ram_role.fc_role.arn
```

### Resource ARN Mapping

| AWS Resource | AWS ARN Format | Alibaba Cloud Resource | Alibaba Cloud ARN Format |
|-------------|---------------|----------------------|-------------------------|
| S3 Bucket | `arn:aws:s3:::bucket-name` | OSS Bucket | `acs:oss:*:*:bucket-name` |
| S3 Object | `arn:aws:s3:::bucket/key` | OSS Object | `acs:oss:*:*:bucket-name/object-key` |
| DynamoDB Table | `arn:aws:dynamodb:region:account:table/name` | Tablestore Table | `acs:ots:*:*:instance/name/table/name` |
| SQS Queue | `arn:aws:sqs:region:account:queue` | MNS Queue | `acs:mns:*:*:/queues/queue-name` |
| SNS Topic | `arn:aws:sns:region:account:topic` | MNS Topic | `acs:mns:*:*:/topics/topic-name` |
| Lambda Function | `arn:aws:lambda:region:account:function:name` | FC Function | `acs:fc:*:*:functions/function-name` |

## Migration Checklist

### Pre-Migration

- [ ] Inventory all Lambda functions (count, runtimes, memory, timeout)
- [ ] Document all triggers and their configurations
- [ ] List all environment variables
- [ ] Map IAM roles and permissions to RAM policies
- [ ] Identify dependencies (layers, VPC, external services)
- [ ] Estimate costs on Function Compute
- [ ] Set up Alibaba Cloud account and RAM users

### Code Migration

- [ ] Update handler signatures if needed
- [ ] Replace AWS SDK calls with Alibaba Cloud SDK
- [ ] Update environment variable names
- [ ] Modify event parsing for trigger differences
- [ ] Update logging calls (CloudWatch → SLS)
- [ ] Test code locally with FC local runtime (if available)

### Infrastructure Migration

- [ ] **Create RAM role for FC** (trust policy: `fc.aliyuncs.com` as principal)
- [ ] **Create RAM policy** with least-privilege access to required services (OSS, SLS, Tablestore, etc.)
- [ ] **Attach RAM policy to RAM role**
- [ ] Create functions with correct runtime, memory, and **`role` parameter pointing to RAM role ARN**
- [ ] Upload code packages to OSS
- [ ] Configure environment variables
- [ ] Set up VPC configuration (if needed)
- [ ] Create and configure triggers
- [ ] Set up logging to SLS
- [ ] Configure monitoring and alarms

### Testing

- [ ] Unit test migrated functions
- [ ] Integration test with triggers
- [ ] Performance test (cold start, duration)
- [ ] Security test (permissions, VPC)
- [ ] Error handling test

### Cutover

- [ ] Deploy to production FC environment
- [ ] Update API endpoints (API Gateway → FC HTTP Trigger)
- [ ] Update event source configurations
- [ ] Monitor for errors and performance issues
- [ ] Keep Lambda functions for rollback period

### Post-Migration

- [ ] Verify all functions working correctly
- [ ] Optimize memory and timeout settings
- [ ] Review and optimize costs
- [ ] Set up monitoring dashboards
- [ ] Document new architecture
- [ ] Decommission Lambda functions

## Cleanup

### Delete All Triggers

```bash
# List triggers first
aliyun fc list-triggers \
  --function-name <function-name> \
  --user-agent AlibabaCloud-Agent-Skills

# Delete each trigger
aliyun fc delete-trigger \
  --function-name <function-name> \
  --trigger-name <trigger-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Delete All Functions

```bash
# List functions
aliyun fc list-functions \
  --user-agent AlibabaCloud-Agent-Skills

# Delete each function
aliyun fc delete-function \
  --function-name <function-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Delete Code from OSS

```bash
aliyun oss rm oss://<bucket>/<function-code-path> -r \
  --user-agent AlibabaCloud-Agent-Skills
```

### Detach and Delete RAM Policies

```bash
# Detach policy from role
aliyun ram DetachPolicyFromRole \
  --PolicyType Custom \
  --PolicyName <policy-name> \
  --RoleName fc-execution-role \
  --user-agent AlibabaCloud-Agent-Skills

# Delete policy
aliyun ram DeletePolicy \
  --PolicyName <policy-name> \
  --user-agent AlibabaCloud-Agent-Skills

# Delete role
aliyun ram DeleteRole \
  --RoleName fc-execution-role \
  --user-agent AlibabaCloud-Agent-Skills
```

### Delete Lambda Functions (AWS Side)

```bash
# Delete function
aws lambda delete-function --function-name <function-name>

# Delete Lambda execution role (if no longer needed)
aws iam delete-role --role-name <role-name>
```

## Best Practices

### 1. Runtime Selection

- Use latest stable runtime versions available on FC
- Match Lambda runtime versions as closely as possible
- Consider container images for complex dependencies

### 2. Memory and Timeout Tuning

- Start with same memory as Lambda
- Monitor actual memory usage and adjust
- Keep timeout as low as possible for cost optimization

### 3. Cold Start Optimization

- Use provisioned concurrency for latency-sensitive functions
- Minimize package size (remove unused dependencies)
- Use layers for shared dependencies

### 4. Security

- Follow least privilege principle for RAM policies
- Use VPC for functions accessing private resources
- Enable function encryption for sensitive data

### 5. Monitoring and Observability

- Configure SLS logging for all functions
- Set up CloudMonitor alarms for errors and duration
- Use ARMS for distributed tracing

### 6. Cost Optimization

- Right-size memory allocation
- Use reserved instances for predictable workloads
- Clean up unused functions and versions

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `Handler not found` | Incorrect handler path | Verify handler format: `file.function` |
| `Timeout exceeded` | Function takes too long | Increase timeout or optimize code |
| `Out of memory` | Insufficient memory | Increase memory allocation |
| `Permission denied` | RAM policy missing permissions | Add required permissions to role |
| `Trigger not firing` | Misconfigured trigger | Verify trigger configuration and permissions |
| `Cold start too slow` | Large package or cold environment | Use provisioned mode, optimize package |

### View Function Logs

```bash
# Query SLS logs
aliyun log GetLogs \
  --project <sls-project> \
  --logstore <sls-logstore> \
  --from <unix-timestamp> \
  --to <unix-timestamp> \
  --query "functionName:<function-name>" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Check Function Status

```bash
aliyun fc get-function \
  --function-name <function-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

## Related APIs

| API Action | CLI Command | Description |
|------------|-------------|-------------|
| `CreateFunction` | `aliyun fc create-function ... --user-agent AlibabaCloud-Agent-Skills` | Create function |
| `UpdateFunction` | `aliyun fc update-function ... --user-agent AlibabaCloud-Agent-Skills` | Update function configuration |
| `DeleteFunction` | `aliyun fc delete-function ... --user-agent AlibabaCloud-Agent-Skills` | Delete function |
| `CreateTrigger` | `aliyun fc create-trigger ... --user-agent AlibabaCloud-Agent-Skills` | Create trigger |
| `DeleteTrigger` | `aliyun fc delete-trigger ... --user-agent AlibabaCloud-Agent-Skills` | Delete trigger |
| `InvokeFunction` | `aliyun fc invoke-function ... --user-agent AlibabaCloud-Agent-Skills` | Invoke function |
| `ListFunctions` | `aliyun fc list-functions ... --user-agent AlibabaCloud-Agent-Skills` | List functions |
| `GetFunction` | `aliyun fc get-function ... --user-agent AlibabaCloud-Agent-Skills` | Get function details |

## References

- [Function Compute Documentation](https://www.alibabacloud.com/help/en/function-compute)
- [FC API Reference](https://www.alibabacloud.com/help/en/function-compute/api-reference)
- [Runtime Documentation](https://www.alibabacloud.com/help/en/function-compute/developer-reference/runtime)
- [Trigger Configuration](https://www.alibabacloud.com/help/en/function-compute/developer-reference/trigger-overview)
- [AWS Lambda to FC Migration Guide](https://www.alibabacloud.com/help/en/function-compute/user-guide/migrate-from-aws-lambda)

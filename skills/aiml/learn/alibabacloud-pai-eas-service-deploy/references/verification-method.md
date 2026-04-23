# Verification Methods

How to verify PAI-EAS service deployment success.

## Deployment Verification Flow

### Step 1: Verify Service Creation

```bash
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected result**:
- Response JSON contains `ServiceId`
- `Status` field is `Creating` or `Running`

### Step 2: Wait for Service Ready

```bash
for i in $(seq 1 6); do
  STATUS=$(aliyun eas describe-service \
    --cluster-id cn-hangzhou \
    --service-name <service-name> \
    --user-agent AlibabaCloud-Agent-Skills | jq -r '.Status')
  
  case $STATUS in
    Running) echo "✅ Service ready"; break ;;
    Failed)  echo "❌ Service startup failed"; break ;;
    *)       echo "⏳ Status: $STATUS ($((i*30))s/180s)"; sleep 30 ;;
  esac
done
```

**Expected result**:
- Service status becomes `Running`

### Step 3: Get Service Endpoints

```bash
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills | jq '{
    Status: .Status,
    InternetEndpoint: .InternetEndpoint,
    IntranetEndpoint: .IntranetEndpoint,
    ServiceId: .ServiceId
  }'
```

**Expected result**:
- `InternetEndpoint` or `IntranetEndpoint` has value

### Step 4: Verify Service Accessibility

**HTTP service verification**:

```bash
curl -s -o /dev/null -w "%{http_code}" \
  "http://<endpoint>/health"
```

**Expected result**:
- HTTP status code 200

**vLLM service verification**:

```bash
curl http://<endpoint>/v1/models
```

**Expected result**:
- Returns model list JSON

### Step 5: View Service Events (optional)

If service startup fails, check events:

```bash
aliyun eas describe-service-event \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Config Verification

### Verify Image Config

```bash
aliyun aiworkspace get-image \
  --image-id <image-id> \
  --user-agent AlibabaCloud-Agent-Skills | jq '.EasConfig'
```

### Verify Resource Config

```bash
aliyun eas describe-machine-spec \
  --cluster-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills | jq ".InstanceMetas[] | select(.InstanceType == \"<instance-type>\")"
```

### Verify Storage Config

```bash
ossutil ls oss://<bucket>/<path>/
```

---

## Service Invocation Verification

### Service Console

After successful deployment, view details in PAI Console:

```
https://pai.console.aliyun.com/?regionId=<region>&workspaceId=<workspace-id>#/eas/serviceDetail/<service-name>/detail
```

**Example**:
```
https://pai.console.aliyun.com/?regionId=cn-hangzhou&workspaceId=1111#/eas/serviceDetail/qwen35_7b_prod/detail
```

### Get Service Token

Service invocation requires Token authentication. Get from console service detail page, or via API:

```bash
aliyun eas describe-service \
  --cluster-id <region> \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills | jq -r '.Token'
```

### Shared Gateway Invocation

```bash
curl "http://<endpoint>/api/predict/<service-name>" \
  -H "Content-Type: application/json" \
  -H "Authorization: <token>" \
  -d '{"input": "test"}'
```

**Example** (token redacted):
```bash
curl "http://1227512831780489.cn-hangzhou.pai-eas.aliyuncs.com/api/predict/qwen35_7b_prod" \
  -H "Content-Type: application/json" \
  -H "Authorization: ZmYxMmMz***YWY4ZDU=" \
  -d '{"input": "Hello"}'
```

### Dedicated Gateway Invocation

```bash
curl "http://<service-name>.<gateway-id>-vpc.<region>.pai-eas.aliyuncs.com/" \
  -H "Content-Type: application/json" \
  -H "Authorization: <token>" \
  -d '{"input": "test"}'
```

### OpenAI Compatible Interface

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://<endpoint>/v1",
    api_key="<token>"
)

response = client.chat.completions.create(
    model="<model-name>",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

### vLLM Service Invocation

```bash
curl "http://<endpoint>/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: <token>" \
  -d '{
    "model": "/models",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
  }'
```

---

## Troubleshooting

### Service Status Check

```bash
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills | jq '{Status, Message, Reason}'
```

### View Service Logs

```bash
aliyun eas describe-service-log \
  --cluster-id cn-hangzhou \
  --service-name <service-name> \
  --user-agent AlibabaCloud-Agent-Skills
```

### Check Resource Config

- Confirm instance type is available
- Confirm resource group has sufficient quota
- Confirm VPC/VSwitch/security group config is correct

### Check Image Config

- Confirm image URI is correct
- Confirm startup command is correct
- Confirm port config is correct

### Check Storage Config

- Confirm OSS path exists
- Confirm mount paths don't conflict
- Confirm permissions are correct

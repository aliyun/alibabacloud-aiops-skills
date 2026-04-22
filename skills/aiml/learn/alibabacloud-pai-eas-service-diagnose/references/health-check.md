# Health Check Configuration Reference

**Table of Contents**

- [Health Check Types](#health-check-types)
- [Configuration Format](#configuration-format)
- [Parameter Descriptions](#parameter-descriptions)
- [Recommended Configurations](#recommended-configurations)
- [Common Issues](#common-issues)
- [Debugging Suggestions](#debugging-suggestions)

## Health Check Types

PAI-EAS supports three types of health checks:

| Type | Purpose | Description |
|------|---------|-------------|
| `startup_check` | Startup check | Subsequent checks only proceed after service starts successfully |
| `liveness_check` | Liveness check | Checks if service is alive; restarts on failure |
| `readiness_check` | Readiness check | Checks if service is ready; removes from load balancer on failure |

---

## Configuration Format

### HTTP Check

```json
{
  "startup_check": {
    "http_get": {
      "path": "/health",
      "port": 8000,
      "scheme": "HTTP"
    },
    "initial_delay_seconds": 30,
    "period_seconds": 10,
    "timeout_seconds": 5,
    "failure_threshold": 3,
    "success_threshold": 1
  }
}
```

### TCP Check

```json
{
  "liveness_check": {
    "tcp_socket": {
      "port": 8000
    },
    "initial_delay_seconds": 15,
    "period_seconds": 10,
    "timeout_seconds": 5,
    "failure_threshold": 3
  }
}
```

### Command Check

```json
{
  "readiness_check": {
    "exec": {
      "command": ["/bin/sh", "-c", "test -f /tmp/ready"]
    },
    "initial_delay_seconds": 5,
    "period_seconds": 5,
    "failure_threshold": 3
  }
}
```

---

## Parameter Descriptions

| Parameter | Description | Default |
|-----------|-------------|---------|
| `initial_delay_seconds` | Initial check delay | 10 |
| `period_seconds` | Check interval | 10 |
| `timeout_seconds` | Timeout duration | 1 |
| `failure_threshold` | Failure threshold | 3 |
| `success_threshold` | Success threshold | 1 |

---

## Recommended Configurations

### LLM Inference Service

LLM services have slow startup (model loading) and require a longer initial delay:

```json
{
  "startup_check": {
    "http_get": { "path": "/health", "port": 8000 },
    "initial_delay_seconds": 120,
    "period_seconds": 10,
    "timeout_seconds": 10,
    "failure_threshold": 30
  },
  "liveness_check": {
    "http_get": { "path": "/health", "port": 8000 },
    "initial_delay_seconds": 150,
    "period_seconds": 30,
    "timeout_seconds": 10,
    "failure_threshold": 3
  },
  "readiness_check": {
    "http_get": { "path": "/v1/models", "port": 8000 },
    "initial_delay_seconds": 150,
    "period_seconds": 10,
    "timeout_seconds": 5,
    "failure_threshold": 3
  }
}
```

**Notes**:
- `startup_check` allows 5 minutes startup time (120 + 10 x 30)
- `liveness_check` checks every 30 seconds to avoid frequent checks impacting performance
- `readiness_check` verifies `/v1/models` to ensure API is available

### Image Generation Service

```json
{
  "startup_check": {
    "http_get": { "path": "/health", "port": 8188 },
    "initial_delay_seconds": 60,
    "period_seconds": 5,
    "timeout_seconds": 5,
    "failure_threshold": 60
  },
  "liveness_check": {
    "http_get": { "path": "/health", "port": 8188 },
    "initial_delay_seconds": 90,
    "period_seconds": 15,
    "timeout_seconds": 5,
    "failure_threshold": 3
  }
}
```

### General Inference Service

```json
{
  "startup_check": {
    "http_get": { "path": "/ping", "port": 8080 },
    "initial_delay_seconds": 30,
    "period_seconds": 5,
    "timeout_seconds": 3,
    "failure_threshold": 20
  },
  "liveness_check": {
    "http_get": { "path": "/ping", "port": 8080 },
    "initial_delay_seconds": 60,
    "period_seconds": 10,
    "timeout_seconds": 3,
    "failure_threshold": 3
  },
  "readiness_check": {
    "http_get": { "path": "/ping", "port": 8080 },
    "initial_delay_seconds": 60,
    "period_seconds": 5,
    "timeout_seconds": 3,
    "failure_threshold": 3
  }
}
```

---

## Common Issues

### Issue 1: Service starts normally but health check fails

**Symptom**: Service logs are normal, but instances keep restarting

**Cause**:
- Incorrect health check path
- Incorrect health check port
- `initial_delay_seconds` set too short

**Solution**:
```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# Check health check configuration
aliyun eas describe-service --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '{StartupCheck, LivenessCheck, ReadinessCheck}'

# Check service listening port
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE \
  --keyword "listening" --limit 10 --user-agent AlibabaCloud-Agent-Skills
```

### Issue 2: Intermittent service unavailability

**Symptom**: Service intermittently returns 503 errors

**Cause**:
- `readiness_check` is too sensitive
- Slow service response causes timeout

**Solution**:
- Increase `timeout_seconds`
- Increase `failure_threshold`
- Adjust check path

### Issue 3: Frequent service restarts

**Symptom**: Instances restart frequently

**Cause**:
- `liveness_check` path responds slowly
- `period_seconds` too short
- Service itself has issues

**Solution**:
```bash
SERVICE="my-service"
REGION="cn-hangzhou"

# View restart reasons
aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE \
  --keyword "liveness" --limit 20 --user-agent AlibabaCloud-Agent-Skills

# Check health check failure events
aliyun eas describe-service-event --cluster-id $REGION --service-name $SERVICE --user-agent AlibabaCloud-Agent-Skills | \
  jq '.Events[] | select(.Reason | test("Unhealthy|ProbeFailed"; "i"))'
```

---

## Debugging Suggestions

### 1. Verify Health Check Endpoint

```bash
# Test inside container (if terminal access is available)
curl --connect-timeout 10 --max-time 30 -v http://localhost:8000/health
```

### 2. View Health Check Logs

```bash
SERVICE="my-service"
REGION="cn-hangzhou"

aliyun eas describe-service-log --cluster-id $REGION --service-name $SERVICE \
  --keyword "health" --limit 30 --user-agent AlibabaCloud-Agent-Skills
```

### 3. Temporarily Disable Health Checks

For debugging, you can temporarily comment out health check configuration:

```json
{
  // "liveness_check": { ... },
  // "readiness_check": { ... }
}
```

### 4. Increase Initial Delay

If unsure about service startup time, set a larger value first:

```json
{
  "startup_check": {
    "http_get": { "path": "/health", "port": 8000 },
    "initial_delay_seconds": 300,
    "period_seconds": 10,
    "timeout_seconds": 10,
    "failure_threshold": 60
  }
}
```

# Verification method

How to validate the Elasticsearch instance diagnosis skill against the **current architecture**:

- Control plane + CMS: `aliyun` CLI OpenAPI
- Health rule engine: `python3 scripts/check_es_instance_health.py`
- Engine-level collection: `curl` to ES REST APIs

When `curl` fails (**401**, **timeouts**, **connection refused**, TLS mismatch), use the progressive guide **[es-api-call-failures.md](es-api-call-failures.md)** before re-running checks blindly.

---

## 1. Environment and credentials

### 1.1 CLI and profile

```bash
aliyun version
aliyun configure list
aliyun --profile <profile_name> sts get-caller-identity
```

**Checklist**:
- [ ] CLI works (recommend >= 3.3.1)
- [ ] `aliyun configure list` shows at least one `Valid` profile
- [ ] The chosen profile returns caller identity successfully

### 1.2 Direct ES credentials

```bash
[[ -n "$ES_ENDPOINT" ]] && echo "ES_ENDPOINT: SET" || echo "ES_ENDPOINT: NOT SET"
[[ -n "$ES_PASSWORD" ]] && echo "ES_PASSWORD: SET" || echo "ES_PASSWORD: NOT SET"
```

**Checklist**:
- [ ] `ES_ENDPOINT` and `ES_PASSWORD` are set when engine checks are required
- [ ] Plain-text password is not echoed

---

## 2. Control-plane OpenAPI (`aliyun` CLI)

These steps can be run standalone or as manual backfill in a runbook.

### 2.1 Elasticsearch OpenAPI

```bash
aliyun --profile <profile_name> elasticsearch DescribeInstance \
  --region <region> \
  --InstanceId <instance_id>

aliyun --profile <profile_name> elasticsearch ListSearchLog \
  --region <region> \
  --InstanceId <instance_id> \
  --type INSTANCELOG \
  --query "*" \
  --beginTime <epoch_ms> \
  --endTime <epoch_ms>

aliyun --profile <profile_name> elasticsearch ListActionRecords \
  --region <region> \
  --InstanceId <instance_id>

aliyun --profile <profile_name> elasticsearch ListAllNode \
  --region <region> \
  --InstanceId <instance_id>
```

### 2.2 CMS OpenAPI

```bash
aliyun --profile <profile_name> cms DescribeMetricList \
  --region <region> \
  --Namespace acs_elasticsearch \
  --MetricName ClusterStatus \
  --Dimensions '[{"clusterId":"<instance_id>"}]' \
  --StartTime <epoch_ms> \
  --EndTime <epoch_ms> \
  --Period 300

aliyun --profile <profile_name> cms DescribeSystemEventAttribute \
  --region <region> \
  --Product elasticsearch \
  --SearchKeywords <instance_id> \
  --StartTime <epoch_ms> \
  --EndTime <epoch_ms>

aliyun --profile <profile_name> cms DescribeMetricMetaList \
  --region <region> \
  --Namespace acs_elasticsearch
```

**Checklist**:
- [ ] Each call returns `Code=200` or `Success=true`
- [ ] `DescribeMetricList` returns datapoints (or empty series without error)
- [ ] `ListSearchLog` returns `Result` or an empty array (not a hard failure)
- [ ] `ListActionRecords`, `ListAllNode`, `DescribeMetricMetaList` return structured JSON

---

## 3. Health-check script

### 3.1 CLI data source

```bash
python3 scripts/check_es_instance_health.py \
  -i <instance_id> -r <region> \
  --window 60 \
  --data-source cli \
  --profile <profile_name>
```

**Checklist**:
- [ ] Script completes without traceback
- [ ] Structured report (P0/P1/P2, evidence, remediation)
- [ ] Metric summary matches the live instance state

### 3.2 Injected input + auto

```bash
python3 scripts/check_es_instance_health.py \
  -i <instance_id> -r <region> \
  --data-source auto \
  --input-json-file /path/to/diag-input.json \
  --profile <profile_name>
```

**Checklist**:
- [ ] Fields from input JSON are preferred when present
- [ ] Missing fields fall back to CLI collection
- [ ] With `--data-source input`, no OpenAPI calls are made

---

## 4. Engine-level ES APIs (`curl`)

### 4.1 Connectivity

```bash
curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_cluster/health?pretty"
```

### 4.2 Key endpoints

```bash
curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  -H "Content-Type: application/json" \
  -X POST "http://${ES_ENDPOINT#http://}/_cluster/allocation/explain?pretty" \
  -d '{}'

curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_cat/shards?v&h=index,shard,prirep,state,node,unassigned.reason&s=state"

curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "http://${ES_ENDPOINT#http://}/_nodes/stats/thread_pool?pretty"
```

**Checklist**:
- [ ] JSON or cat text is returned
- [ ] No auth or connection errors
- [ ] Fields useful for root-cause analysis appear (`unassigned.reason`, `thread_pool.rejected`, etc.)

---

## 5. Negative / edge cases

### 5.1 Invalid CLI profile

```bash
python3 scripts/check_es_instance_health.py \
  -i <instance_id> -r <region> \
  --data-source cli \
  --profile not-exist
```

**Expected**: Clear profile / authentication error (no silent success).

### 5.2 Non-existent instance

```bash
python3 scripts/check_es_instance_health.py \
  -i es-cn-invalid -r cn-hangzhou \
  --data-source cli
```

**Expected**: Instance-not-found or invalid resource error; script does not crash.

### 5.3 Wrong HTTP scheme for endpoint

```bash
curl -sS -u "${ES_USERNAME:-elastic}:${ES_PASSWORD}" \
  "https://${ES_ENDPOINT#http://}/_cluster/health?pretty"
```

**Expected**: May see `WRONG_VERSION_NUMBER` if TLS mismatch; fix by switching between `http://` and `https://` to match the endpoint.

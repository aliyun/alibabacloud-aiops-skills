# GA Access Log Delivery Reference

This document explains how to deliver Global Accelerator access logs to Alibaba Cloud Simple Log Service (SLS) for auditing, troubleshooting, and traffic analysis.

> **Important**: Access log delivery may incur SLS storage charges.
> **Scope**: Access log delivery requires a **Standard** accelerator; Basic accelerators are not supported. The binding is configured per listener and endpoint group.

---

## 1. Log Delivery Flow

```
Create or select SLS Project and Logstore
    │
    ▼
Attach the logstore to the endpoint group (AttachLogStoreToEndpointGroup)
    │
    ▼
Confirm the binding (DescribeLogStoreOfEndpointGroup) and that logs are written
```

---

## 2. Query the Existing Binding

```bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"
EPG_ID="epg-bp1xxxx"

aliyun ga describe-log-store-of-endpoint-group \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --endpoint-group-id "$EPG_ID" \
  --user-agent "$GA_USER_AGENT" | jq '{SlsRegionId, SlsProjectName, SlsLogStoreName, Status}'
```

`Status` is `on` when the binding is active and `off` when it is not.

---

## 3. Attach an SLS Logstore to an Endpoint Group

`AttachLogStoreToEndpointGroup` is a write operation: confirm the target project, logstore, listener, and endpoint group with the user before running it.

```bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"
EPG_ID="epg-bp1xxxx"
PROJECT="ga-logs-project"
LOGSTORE="ga-access-log"
SLS_REGION="cn-hangzhou"

# Idempotency token: the same inputs always produce the same ClientToken.
CLIENT_TOKEN=$(printf '%s' "${GA_ID}|${LISTENER_ID}|${EPG_ID}|${PROJECT}|${LOGSTORE}" | sha256sum | cut -c1-32)

aliyun ga attach-log-store-to-endpoint-group \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --listener-id "$LISTENER_ID" \
  --endpoint-group-ids "$EPG_ID" \
  --sls-project-name "$PROJECT" \
  --sls-log-store-name "$LOGSTORE" \
  --sls-region-id "$SLS_REGION" \
  --client-token "$CLIENT_TOKEN" \
  --user-agent "$GA_USER_AGENT"
```

The call is asynchronous: it returns a `RequestId` before the binding completes. Poll `describe-log-store-of-endpoint-group` until `Status` is `on`:

```bash
for i in $(seq 1 30); do
  STATE=$(aliyun ga describe-log-store-of-endpoint-group \
    --biz-region-id cn-hangzhou \
    --accelerator-id "$GA_ID" \
    --listener-id "$LISTENER_ID" \
    --endpoint-group-id "$EPG_ID" \
    --user-agent "$GA_USER_AGENT" | jq -r '.Status')
  if [ "$STATE" = "on" ]; then
    echo "Access log binding is active."
    break
  fi
  echo "Waiting for the access log binding... [$i/30] status: $STATE"
  sleep 10
done
```

Custom request headers can be recorded into the `ga_headers` field by adding `--access-log-record-customized-headers-enabled true` and `--access-log-record-customized-header-list "header-a;header-b"`. This feature requires business-manager approval before it can be enabled.

---

## 4. Common SLS Queries

Fields in the delivered logs: `ga_id`, `listener_id`, `endpoint_group_id`, `endpoint_ip`, `endpoint_port`, `accelerator_region`, `endpoint_group_region`, `client_ip`, `client_port`, `protocol`, `status`, `time`, `ingress_bytes`, `egress_bytes`, `upstream_connect_time`, `upstream_first_byte_time`. HTTP/HTTPS listeners additionally record `http_host`, `http_referer`, `request_method`, and `request_uri`; custom headers (when enabled) are stored in `ga_headers`.

Scope the time range with the SLS console time picker — the record timestamp field is `time`.

```sql
-- Total requests in the selected time range
* | SELECT count(*) AS total_requests

-- Top 10 client IPs
* | SELECT client_ip, count(1) AS cnt GROUP BY client_ip ORDER BY cnt DESC LIMIT 10

-- Requests answered with a 5xx status
* | SELECT count(*) AS errors WHERE cast(status AS bigint) >= 500

-- Client IP distribution by geography (official example)
* | SELECT ip_to_geo(client_ip) AS address, count(1) AS cnt GROUP BY address ORDER BY cnt DESC LIMIT 10
```

The status field is `status`; GA access logs have no `status_code` field.

---

## 5. Skill Integration Notes

After the GA accelerator is created, optionally ask:

```
Question: Do you want to deliver GA access logs to SLS?
- Option 1: No (default)
- Option 2: Yes

If yes:
1. Ask whether to use an existing SLS Project/Logstore or create a new one.
2. Create the Project/Logstore if needed (log:CreateProject / log:CreateLogStore).
3. Confirm the target listener and endpoint group with the user.
4. Call ga:AttachLogStoreToEndpointGroup to attach the logstore.
5. Call ga:DescribeLogStoreOfEndpointGroup to verify Status is on.
```

---

## 6. Notes

1. Required permissions: `ga:AttachLogStoreToEndpointGroup` and `ga:DescribeLogStoreOfEndpointGroup`, plus `log:CreateProject` / `log:CreateLogStore` when the SLS resources must be created.
2. Only Standard accelerators support access log delivery; Basic accelerators are not supported.
3. The binding is per listener and endpoint group, so an instance with several endpoint groups needs one attach call per endpoint group.
4. Choose the SLS region deliberately: the console defaults it to the endpoint group region, and the API requires `--sls-region-id` explicitly.
5. Logs normally appear in SLS within 1-5 minutes after the binding becomes `on`.
6. Field reference: https://help.aliyun.com/zh/sls/global-acceleration-access-log-details ; console workflow: https://help.aliyun.com/zh/ga/user-guide/using-access-logs

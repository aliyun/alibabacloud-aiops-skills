# OWASP API Security Top 10 (2023) Query Guide

Cover all ten items. Counts, QPS values, and uniqueness thresholds below are investigation starting points, not universal malicious-traffic boundaries. Adapt them to the reporting interval and business baseline, and record the chosen threshold.

## API1: Broken Object Level Authorization

Look for one source enumerating many object identifiers.

```sql
final_action:null AND querystring:orderId
  | select real_client_ip, request_path,
    count(1) as cnt,
    count(distinct(querystring)) as unique_queries
  group by real_client_ip, request_path
  having unique_queries > 30
  order by unique_queries desc limit 20
```

```sql
final_action:null AND (querystring:'userId=' OR querystring:'shopId=' OR querystring:'productId=')
  | select real_client_ip, request_path,
    count(1) as cnt,
    count(distinct(querystring)) as unique_queries
  group by real_client_ip, request_path
  having unique_queries > 30
  order by unique_queries desc limit 20
```

Enumeration is only a signal. Confirm authenticated identity, object ownership, source behavior, and application authorization before classifying BOLA.

## API2: Broken Authentication

```sql
(request_path:*/login/token* OR request_path:*/signin* OR request_path:*/auth/login*)
  | select final_action, upstream_status, count(1) as cnt
  group by final_action, upstream_status
```

```sql
final_action:null AND upstream_status:401
  | select host, request_path, real_client_ip, count(1) as cnt
  group by host, request_path, real_client_ip
  order by cnt desc limit 20
```

Review rate, account diversity, success-after-failure patterns, BOT action, and known test sources.

## API3: Broken Object Property Level Authorization

WAF request logs usually cannot prove response-field overexposure. Use API Security alerts as candidates:

```bash
aliyun waf-openapi describe-apisec-abnormals \
  --instance-id <instance-id> \
  --region <region-id> \
  --page-number <page-number> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"
```

Application owners must review response fields, masking, field-level authorization, and mass-assignment behavior. Mark this item unverifiable when response evidence is unavailable.

## API4: Unrestricted Resource Consumption

```sql
* | select real_client_ip,
    count(1) as cnt,
    count(distinct(request_path)) as paths,
    sum(body_bytes_sent) as response_bytes
  group by real_client_ip
  order by cnt desc limit 20
```

Compare against expected partner callbacks, business peaks, caching behavior, latency, response size, and configured rate limits.

## API5: Broken Function Level Authorization

```sql
final_action:null AND
  (request_path:/admin OR request_path:/manager OR request_path:/backend OR request_path:/console)
  AND upstream_status:200
  | select host, request_path, real_client_ip, count(1) as cnt
  group by host, request_path, real_client_ip
  order by cnt desc limit 20
```

A `200` response is a candidate only. Verify identity, role, content type, SPA fallback behavior, and actual function execution.

## API6: Unrestricted Access to Sensitive Business Flows

```sql
(request_path:*coupon* OR request_path:*promotion* OR request_path:*lottery*
 OR request_path:*order* OR request_path:*seckill*)
  | select real_client_ip, request_path, final_action, count(1) as cnt
  group by real_client_ip, request_path, final_action
  order by cnt desc limit 20
```

```sql
(request_path:*sms* OR request_path:*verify/code* OR request_path:*captcha*)
  | select real_client_ip, request_path, count(1) as cnt
  group by real_client_ip, request_path
  order by cnt desc limit 20
```

Confirm the business transaction result and identity context; traffic volume alone does not prove abuse.

## API7: Server-Side Request Forgery

```sql
final_action:null AND
  (querystring:'url=http' OR querystring:'redirect=http'
   OR querystring:'callback=http' OR querystring:'target=http')
  | select host, request_path, querystring, real_client_ip, upstream_status
  limit 20
```

```sql
final_action:null AND querystring:http AND
  (querystring:'127.0.0.1' OR querystring:'169.254'
   OR querystring:'localhost' OR querystring:'metadata'
   OR querystring:'100.100.100.200')
  | select host, request_path, querystring, real_client_ip, upstream_status
  limit 20
```

Allowed SSRF-like input indicates a detection candidate, not successful backend access. Verify parameter semantics, approved redirects, application validation, response evidence, and outbound telemetry. Do not send SSRF payloads without separate authorization.

## API8: Security Misconfiguration

```sql
final_action:null AND
  (request_method:PROPFIND OR request_method:TRACE OR request_method:CONNECT
   OR request_method:MOVE OR request_method:LOCK)
  | select host, request_method, request_path, real_client_ip, upstream_status
  limit 20
```

```sql
final_action:null AND
  (request_path:.git OR request_path:.env OR request_path:web.config
   OR request_path:actuator OR request_path:druid
   OR request_path:swagger OR request_path:api-docs)
  | select host, request_path, upstream_status, real_client_ip, count(1) as cnt
  group by host, request_path, upstream_status, real_client_ip
  order by cnt desc limit 20
```

Inspect response content to distinguish a real exposure from a fallback or error page.

## API9: Improper Inventory Management

```sql
final_action:null AND (host:*uat* OR host:*test* OR host:*dev* OR host:*staging*)
  | select host, request_path, upstream_status, count(1) as cnt
  group by host, request_path, upstream_status
  order by cnt desc limit 20
```

Confirm the environment purpose, owner, data class, authentication, and expected public reachability.

## API10: Unsafe Consumption of APIs

Inbound WAF logs normally do not show application calls to third-party APIs. Request application outbound logs, gateway egress logs, service-mesh telemetry, or approved network telemetry. Without those sources, mark the item unverifiable rather than safe.

## Coverage table

```markdown
| OWASP API ID | Result | Evidence or query | Data gap | Confidence |
| --- | --- | --- | --- | --- |
| API1 | ... | ... | ... | ... |
| API2 | ... | ... | ... | ... |
| API3 | ... | ... | ... | ... |
| API4 | ... | ... | ... | ... |
| API5 | ... | ... | ... | ... |
| API6 | ... | ... | ... | ... |
| API7 | ... | ... | ... | ... |
| API8 | ... | ... | ... | ... |
| API9 | ... | ... | ... | ... |
| API10 | ... | ... | ... | ... |
```

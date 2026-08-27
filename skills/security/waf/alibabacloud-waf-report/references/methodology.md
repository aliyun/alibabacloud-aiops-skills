# Assessment Methodology

## Evidence model

Important findings should use multiple independent sources whenever available. If a source is unavailable, retain the candidate finding with lower confidence and state the missing evidence.

Preferred sources:

1. **WAF OpenAPI**: instance capabilities, defense templates, rules, API Security alerts, and configuration state.
2. **SLS traffic logs**: real request behavior, actions, origin status, time distribution, and authenticated call volume.
3. **Authorized public verification**: side-effect-free requests that distinguish real APIs, authentication responses, WAF blocks, and SPA fallback pages.

## Four-level outcome classification

| Outcome | Criteria | Treatment |
| --- | --- | --- |
| True risk | Sensitive data exposure, unauthorized dangerous operation, or verified post-authentication authorization or credential issue | Add to the P0/P1 plan |
| Low impact | Exposed endpoint with non-sensitive or empty content | Add to P2 or observations |
| False positive | Missing endpoint, authentication rejection, SPA fallback, or verified legitimate business behavior | Archive with evidence |
| Unverifiable | Missing fields, timeout, TLS issue, or required business token | State the gap and required next step |

## Post-authentication reassessment

A public `401`, `403`, or `405` response is not sufficient to close an alert. When SLS data is available, answer four questions.

### 1. Does the endpoint have real successful authenticated calls?

```sql
request_path:<path> AND final_action:null AND upstream_status:200
  | select count(1) as cnt
```

- Meaningful successful volume indicates a real authenticated business endpoint; application owners may need to inspect the response and authorization model.
- No matching volume lowers exposure confidence but does not prove the endpoint is harmless if retention or logging is incomplete.

### 2. Can the alert signature appear only after login?

| Signature | Typical visibility | Consequence |
| --- | --- | --- |
| Plaintext or weak password | Authenticated workflow | Public verification may not reach it |
| AccessKey, STS token, or internal address | Authenticated response | Audit response and logging paths |
| Unmasked personal data | Authenticated response | Review field-level authorization and masking |
| Swagger, API documentation, Actuator, or debug page | Often publicly verifiable | Public GET/HEAD verification may be useful |

### 3. Is there an internal or authenticated risk?

Review object-level authorization, overly broad temporary credentials, long-lived URL tokens, sensitive values stored in SLS, internal error disclosure, shared VPN or IDC egress, browser referrers, telemetry, and CDN caching.

### 4. Can it form an attack chain?

Consider whether identifiers, tokens, internal addresses, or one weak endpoint enable access to more sensitive operations. Record the prerequisite and avoid claiming exploitability without evidence.

## Customer-configured IP rule review

Treat IP ownership and network type as context, not proof. Cloud, carrier, residential, and proxy addresses can carry either legitimate or malicious traffic.

### Step 1: retrieve the rule in plugin mode

```bash
aliyun waf-openapi describe-defense-rule \
  --instance-id <instance-id> \
  --region-id <region-id> \
  --rule-id <rule-id> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"
```

Record the source list, rule name, scope, action, and modification time.

### Step 2: retrieve current network ownership metadata

```bash
curl -sS --connect-timeout 5 --max-time 10 \
  -A "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}" \
  "https://ipinfo.io/<ip>/json"
```

Record the lookup time because ownership metadata can change. Confirm partner ownership with the customer rather than relying only on ASN.

### Step 3: compare blocked and allowed behavior

```sql
real_client_ip:<blocked-ip>
  | select count(1) as total,
    count(distinct(request_path)) as paths,
    count(distinct(host)) as hosts
```

```sql
request_path:<path> AND http_user_agent:<user-agent> AND final_action:null
  | select real_client_ip, count(1) as cnt
  group by real_client_ip order by cnt desc limit 10
```

Compare user agent, path, query structure, scene code, time pattern, and rate.

### Step 4: check independent attack evidence

```sql
real_client_ip:<blocked-ip> AND final_action:block AND NOT final_rule_id:<ip-rule-id>
  | select final_rule_id, final_rule_type, count(1) as cnt
  group by final_rule_id, final_rule_type
  order by cnt desc
```

If behavior matches verified legitimate traffic and no independent attack evidence is observed, classify the rule as a suspected misconfiguration pending business-owner confirmation.

## Interpretation safeguards

### HTTP 200 does not prove that an API exists

Single-page applications can return an HTML fallback with status `200` for arbitrary paths. Inspect content type and minimal response markers; do not rely on status alone.

### Detection modules do not have a universal reliability order

Rule-library hits, API Security alerts, and behavior signals vary by configuration and business context. A rule hit does not prove successful exploitation, and an API Security alert should not be dismissed without validation. Build a customer-specific alert-validity baseline.

### Partner callbacks are common false-positive candidates

SDK user agents, stable callback paths, and high-volume sources may be legitimate integrations. Confirm ownership, signature validation, authentication, and expected rate before creating an exception.

### Retention limits conclusion depth

If the requested reporting period exceeds SLS retention, report the exact available interval. Recommend a longer retention period or approved archive pipeline as a separate configuration change.

### IPv4-mapped IPv6 values are not native IPv6 clients

Values such as `::ffff:192.0.2.1` represent IPv4-mapped addresses. Exclude the encoded `::ffff:` prefix when calculating native IPv6 coverage.

## Citation and data-handling rules

- Cite a verifiable URL for claims presented as official documentation.
- Label uncited interpretation as technical inference based on the assessed data.
- Redact secrets, tokens, session identifiers, and personal data from excerpts.
- Preserve query text, time range, sample count, and session ID so the customer can reproduce the result.

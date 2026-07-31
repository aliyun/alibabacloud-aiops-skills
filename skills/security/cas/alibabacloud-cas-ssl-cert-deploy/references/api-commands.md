# ssl-deploy-cloud Reference

## CAS Certificate Query APIs

### ListUserCertificateOrder

Search and filter certificates in the account. Use when the user does not have a specific CertId and wants to browse or search.

```bash
aliyun cas list-user-certificate-order --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE \
  --region $CERT_REGION \
  --current-page 1 \
  --show-size 20 \
  --keyword "{{search_keyword}}"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `CurrentPage` | No | Page number (default 1) |
| `ShowSize` | No | Page size (default 10, max 100) |
| `Keyword` | No | Fuzzy filter by domain or certificate name (server-side) |
| `Status` | No | Filter: `ISSUED` / `REVOKED` / `EXPIRED` / `NOT_YET_ISSUED` |
| `InstanceId` | No | Filter by exact certificate instance ID |
| `OrderType` | No | Filter: `BUY` (purchased) / `FREE` (free) / `TRUSTEE` (managed) |

**Key response fields:**

| Field | Description |
|-------|-------------|
| `TotalCount` | Total matching certificates |
| `CertificateOrderList[].CertificateId` | Certificate ID (used as `CertId` for deployment) |
| `CertificateOrderList[].InstanceId` | Instance ID |
| `CertificateOrderList[].Name` | Certificate name |
| `CertificateOrderList[].Domain` | Primary domain |
| `CertificateOrderList[].Status` | Certificate status |
| `CertificateOrderList[].EndDate` | Expiration date |

> **Tip:** Combine `--keyword` with `--status ISSUED` to quickly find active certificates for a specific domain.

### GetUserCertificateDetail

Query detailed info for a specific certificate (domain, SAN list, issuer, etc.).

```bash
aliyun cas get-user-certificate-detail --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE \
  --region $CERT_REGION \
  --cert-id {{cert_id}}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `CertId` | Yes | Certificate ID to query |

**Key response fields:** `CertId`, `Name`, `Common` (primary domain), `Sans` (all SAN domains, comma-separated), `Issuer`, `EndDate`, `StartDate`

---

## CAS Deployment Job APIs

### CreateDeploymentJob

```bash
aliyun cas create-deployment-job --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE \
  --region $CERT_REGION \
  --name "deploy-cdn-example-com" \
  --job-type "user" \
  --cert-ids "12345" \
  --resource-ids "1001,1002" \
  --contact-ids "100"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `Name` | Yes | Job name (max 63 chars) |
| `JobType` | Yes | `user` (Alibaba Cloud products) / `cloud` (multi-cloud) — **lowercase** |
| `CertIds` | Yes | Certificate IDs, comma-separated (from `ListUserCertificateOrder`) |
| `ResourceIds` | Yes | Resource IDs, comma-separated (`Id` field from `ListCloudResources`) |
| `ContactIds` | Yes | Contact IDs, comma-separated (from `ListContact`) |
| `ScheduleTime` | No | Scheduled execution time (Unix ms timestamp); omit for immediate execution |

**Success response:** `{"JobId": 67890, "RequestId": "..."}`

> **Important:** After creation the job is in `editing` state. You must call `UpdateDeploymentJobStatus` with `scheduling` to start execution.

### UpdateDeploymentJobStatus

```bash
aliyun cas update-deployment-job-status --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --job-id {{job_id}} --status "scheduling"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `JobId` | Yes | Deployment job ID |
| `Status` | Yes | `scheduling` (execute now) / `pending` (await scheduled time) / `editing` (back to edit) |

### DescribeDeploymentJobStatus

```bash
aliyun cas describe-deployment-job-status --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION --job-id {{job_id}}
```

**Response fields:**

| Field | Description |
|-------|-------------|
| `WorkerCount` | Total sub-tasks |
| `SuccessCount` | Succeeded |
| `FailedCount` | Failed |
| `RollbackCount` | Rolled back |
| `RollbackSuccessCount` | Rollback succeeded |
| `RollbackFailedCount` | Rollback failed |
| `MatchWorkerCount` | Sub-tasks with matched certificate |
| `CostCount` | Resource quota consumed |
| `CertCount` | Certificates involved |
| `ProductWorkerCount` | Per-product breakdown `[{ProductName, Count}]` |

**Polling completion:** `SuccessCount + FailedCount == WorkerCount`

### DescribeDeploymentJob

```bash
aliyun cas describe-deployment-job --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION --job-id {{job_id}}
```

**Response fields:** `Id`, `Name`, `JobType` (user/cloud/trustee), `Status`, `CertDomain`, `ProductName`, `CertType` (buy/free/upload), `CasContacts`, `Config`, `ScheduleTime`

### ListCloudResources

```bash
aliyun cas list-cloud-resources --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --cloud-product "CDN" --keyword "example.com"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `CloudProduct` | No | Product type: CDN/SLB/WAF/ALB/NLB/OSS/ESA |
| `CloudName` | No | Cloud vendor: aliyun / Tencent / Huawei / Aws |
| `Keyword` | No | Fuzzy filter by domain/name (**server-side, recommended**) |
| `CertIds` | No | Filter by certificate IDs |

**Key response field:** `Id` — the resource primary key used as `ResourceIds` in `CreateDeploymentJob`

### ListWorkerResource

```bash
aliyun cas list-worker-resource --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --job-id {{job_id}} --status "error" --current-page 1 --show-size 50
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `JobId` | Yes | Deployment job ID |
| `Status` | No | Filter: `success` / `error` / `pending` / `scheduling` / `processing` / `rollback` / `rollback_error` / `rollback_success` |
| `CloudProduct` | No | Filter by cloud product |
| `CurrentPage` | No | Page number (default 1) |
| `ShowSize` | No | Page size (default 50) |

**Key response fields:** `Id` (Worker ID for rollback), `JobId`, `Status`, `CertId`/`CertName`, `CertDomain`, `CloudProduct`, `ResourceId`, `InstanceId`, `Domain`, `RegionId`

### UpdateWorkerResourceStatus — Rollback

```bash
aliyun cas update-worker-resource-status --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --job-id {{job_id}} --worker-id {{worker_id}} --status "rollback"
```

### ListDeploymentJob / DeleteDeploymentJob / UpdateDeploymentJob

```bash
# List jobs
aliyun cas list-deployment-job --profile $CERT_PROFILE --region $CERT_REGION --current-page 1 --show-size 10 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"

# Delete job (only success/error state)
aliyun cas delete-deployment-job --profile $CERT_PROFILE --region $CERT_REGION --job-id {{job_id}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"

# Update job (only in editing state; supports Name, CertIds, ResourceIds, ContactIds, ScheduleTime)
aliyun cas update-deployment-job --profile $CERT_PROFILE --region $CERT_REGION --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --job-id {{job_id}} --name "new-name" --cert-ids "12345" --resource-ids "1001" --contact-ids "100"
```

### ListDeploymentJobCert / ListDeploymentJobResource

```bash
aliyun cas list-deployment-job-cert --profile $CERT_PROFILE --region $CERT_REGION --job-id {{job_id}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
aliyun cas list-deployment-job-resource --profile $CERT_PROFILE --region $CERT_REGION --job-id {{job_id}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

> `ListDeploymentJobResource` may return empty after job completion (resources may have changed).

---

## ALB APIs (alb-cli plugin, kebab-case)

> Install: `aliyun plugin install --names alb=0.2.0`

### list-load-balancers

```bash
aliyun alb list-load-balancers --region {{region_id}} --profile {{profile_name}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--region` | Yes | ALB region |
| `--LoadBalancerIds.N` | No | Filter by ALB instance IDs |
| `--LoadBalancerName` | No | Filter by name |
| `--NextToken` | No | Pagination token |
| `--MaxResults` | No | Page size (default 20) |

**Response:** `LoadBalancers[].LoadBalancerId`, `[].LoadBalancerName`, `[].DNSName`, `[].AddressType`

### list-listeners

```bash
aliyun alb list-listeners --region {{region_id}} --load-balancer-ids.1 {{alb_id}} --profile {{profile_name}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

**Response:** `Listeners[].ListenerId`, `[].ListenerPort`, `[].ListenerProtocol`, `[].ListenerStatus`, `[].DefaultActions`, `[].Certificates[].CertificateId`

### create-listener

```bash
aliyun alb create-listener --region {{region_id}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --load-balancer-id {{alb_id}} \
  --listener-protocol HTTPS \
  --listener-port 443 \
  --certificates.1.certificate-id {{cert_id}} \
  --profile {{profile_name}}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--load-balancer-id` | Yes | ALB instance ID |
| `--listener-protocol` | Yes | `HTTPS` or `QUIC` |
| `--listener-port` | Yes | Port number (typically 443) |
| `--certificates.1.certificate-id` | Yes | Certificate ID |
| `--default-actions.1.type` | No | Default action type (e.g., `ForwardGroup`) |
| `--default-actions.1.forward-group-config.server-group-tuples.1.server-group-id` | No | Default server group |

**Success response:** `ListenerId`, `RequestId`

### update-listener-attribute

```bash
aliyun alb update-listener-attribute --region {{region_id}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --listener-id {{listener_id}} \
  --certificates.1.certificate-id {{new_cert_id}} \
  --profile {{profile_name}}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--listener-id` | Yes | Listener ID |
| `--certificates.1.certificate-id` | No | New certificate ID |
| `--listener-protocol` | No | Updated protocol |
| `--listener-port` | No | Updated port |

### list-server-groups

```bash
aliyun alb list-server-groups --region {{region_id}} --profile {{profile_name}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

**Response:** `ServerGroups[].ServerGroupId`, `[].ServerGroupName`, `[].ServerGroupType`, `[].Protocol`

### create-server-group

```bash
aliyun alb create-server-group --region {{region_id}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --server-group-name {{name}} \
  --server-group-type Instance \
  --vpc-id {{vpc_id}} \
  --protocol HTTPS \
  --scheduler Wrr \
  --health-check-config.health-check-enabled false \
  --profile {{profile_name}}
```

**Success response:** `ServerGroupId`, `RequestId`

### add-servers-to-server-group

```bash
aliyun alb add-servers-to-server-group --region {{region_id}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --server-group-id {{sg_id}} \
  --servers.1.server-ip {{ecs_ip}} --servers.1.server-type Ecs \
  --profile {{profile_name}}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--server-group-id` | Yes | Server group ID |
| `--servers.N.server-ip` | Yes | ECS private IP |
| `--servers.N.server-type` | Yes | `Ecs`, `Eni`, or `Eci` |
| `--servers.N.port` | No | Backend port (default 80) |
| `--servers.N.weight` | No | Weight (default 100) |

### list-rules

```bash
aliyun alb list-rules --region {{region_id}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --listener-id {{listener_id}} \
  --profile {{profile_name}}
```

**Response:** `Rules[].RuleId`, `[].RuleName`, `[].Priority`, `[].Domain`, `[].RuleConditions`

### create-rule

```bash
aliyun alb create-rule --region {{region_id}} --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --listener-id {{listener_id}} \
  --rule-name {{name}} --priority 10 \
  --rule-conditions.1.type Host \
  --rule-conditions.1.host-config.values.1 {{domain}} \
  --rule-actions.1.type ForwardGroup \
  --rule-actions.1.forward-group-config.server-group-tuples.1.server-group-id {{sg_id}} \
  --profile {{profile_name}}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--listener-id` | Yes | HTTPS listener ID |
| `--rule-name` | Yes | Rule name (unique within listener) |
| `--priority` | Yes | Priority (1 = highest) |
| `--rule-conditions.1.type` | Yes | Condition type: `Host` or `Path` |
| `--rule-conditions.1.host-config.values.1` | If Host | Domain name |
| `--rule-conditions.1.path-config.values.1` | If Path | URL path |
| `--rule-actions.1.type` | Yes | `ForwardGroup` / `Redirect` / `FixedResponse` |
| `--rule-actions.1.forward-group-config.server-group-tuples.1.server-group-id` | If ForwardGroup | Target server group ID |

**Success response:** `RuleId`, `RequestId`

---

## Supported Cloud Products

| Product | Description | Typical Scenario |
|---------|-------------|------------------|
| CDN | Content Delivery Network | Static asset acceleration |
| SLB | Classic Load Balancer | L4/L7 load balancing |
| ALB | Application Load Balancer | L7 load balancing |
| NLB | Network Load Balancer | L4 load balancing |
| WAF | Web Application Firewall | Security protection |
| OSS | Object Storage Service (custom domain HTTPS) | Static website hosting |
| ESA | Edge Security Acceleration | Edge computing |

## Post-Deployment Verification

```bash
# Verify HTTPS access
curl -sI --connect-timeout 10 --max-time 30 https://{{domain}} | grep -i "subject\|issuer\|HTTP"

# Verify certificate details (optional)
curl -sk --connect-timeout 10 --max-time 30 https://{{domain}} | openssl x509 -noout -subject -issuer
```

Expected output should contain the target domain and Alibaba Cloud issuer.

## Common Error Codes

### CAS Deployment Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `InvalidCertId.NotFound` | Certificate does not exist | Verify CertId is correct |
| `InvalidResourceId.NotFound` | Resource does not exist | Verify ResourceId is correct |
| `ResourceNotSupportCert` | Resource does not support cert deployment | Verify the cloud product instance exists |
| `DeploymentJobFailed` | Deployment job failed | Check `describe-deployment-job` error details |
| `Forbidden.RAM` | Insufficient permissions | Verify RAM policy includes cloud product deployment permissions |

### ALB Errors

| Error Code | Cause | Fix |
|------------|-------|-----|
| `ResourceNotFound.LoadBalancer` | ALB instance does not exist | Verify ALB ID and region |
| `ResourceNotFound.Listener` | Listener does not exist | Verify listener ID with `list-listeners` |
| `ListenerAlreadyExists` | Duplicate protocol+port | Check existing listeners; use `update-listener-attribute` instead |
| `ResourceNotFound.ServerGroup` | Server group does not exist | Verify server group ID and VPC |
| `IncorrectListenerStatus` | Listener not in `Running` state | Wait for listener status to become `Running` |

## CDN APIs (plugin mode)

### describe-user-domains — List CDN Domains

```bash
aliyun cdn describe-user-domains --profile $CERT_PROFILE --region $CERT_REGION --page-number 1 --page-size 100 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

### add-cdn-domain — Create CDN Acceleration Domain

```bash
aliyun cdn add-cdn-domain --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --domain-name "{{domain}}" --cdn-type "{{cdn_type}}" \
  --sources '[{"content":"{{source_content}}","type":"{{source_type}}","priority":"20","port":80,"weight":"10"}]' \
  --scope "{{scope}}"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--domain-name` | Yes | Acceleration domain |
| `--cdn-type` | Yes | `web` (images/small files) / `download` (large files) / `video` (streaming) |
| `--sources` | Yes | JSON array: `content` (origin), `type` (`ipaddr`/`domain`/`oss`), `priority`, `port`, `weight` |
| `--scope` | No | `domestic` (ICP required) / `overseas` / `global` (ICP required) |

### describe-cdn-domain-detail — Poll Domain Status

```bash
aliyun cdn describe-cdn-domain-detail --profile $CERT_PROFILE --region $CERT_REGION --domain-name "{{domain}}" --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

| DomainStatus | Action |
|-------------|--------|
| `online` | Complete |
| `configuring` | Continue polling (30s interval) |
| `configure_failed` | Show error |

### set-cdn-domain-ssl-certificate — Deploy Certificate to CDN (FORBIDDEN)

> **[FORBIDDEN]** This command is absolutely prohibited. All certificate deployment must go through CAS DeploymentJob API. Do NOT use this command under any circumstances.

### describe-domain-certificate-info — Verify CDN Certificate

```bash
aliyun cdn describe-domain-certificate-info --profile $CERT_PROFILE --region $CERT_REGION --domain-name "{{domain}}" --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

Confirm `ServerCertificateStatus` is `on`.

---

## WAF 3.0 APIs (plugin mode)

### describe-instance — Get WAF Instance

```bash
aliyun waf-openapi describe-instance --profile $CERT_PROFILE --region $CERT_REGION --region-id "$CERT_REGION" --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

Extract `InstanceId`. If no WAF instance, prompt user to activate WAF 3.0 in console.

### create-domain — Onboard Domain to WAF

```bash
aliyun waf-openapi create-domain --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}" \
  --profile $CERT_PROFILE --region $CERT_REGION --region-id "$CERT_REGION" \
  --instance-id "{{waf_instance_id}}" --domain "{{domain}}" \
  --listen '{"HttpsPorts":[443],"HttpPorts":[80],"CertId":"{{cert_id}}"}' \
  --redirect '{"Backends":["{{backend}}"],"Loadbalance":"roundRobin"}'
```

| Parameter | Description |
|-----------|-------------|
| `--region-id` | `cn-hangzhou` (mainland) or `ap-southeast-1` (overseas) |
| `--listen` | HTTPS 443 (required for cert deployment) + HTTP 80 |
| `--redirect.Backends` | Origin IP or domain, up to 20 |
| `--redirect.Loadbalance` | `roundRobin` / `iphash` / `leastTime` |

Extract WAF-assigned CNAME from response `DomainInfo.Cname`.

---

## OSS APIs (ossutil)

> **Note:** OSS operations use `ossutil` (the standalone CLI tool). The deprecated `oss` sub-command of the main CLI must not be used. Install: `pip install ossutil` or download from [OSSUtil docs](https://help.aliyun.com/document_detail/120075.html).

### create-cname-token — Domain Ownership Verification

```bash
ossutil website --method put oss://{{bucket_name}} --cname {{domain}} --profile $CERT_PROFILE --region $CERT_REGION --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

Guide user to add DNS TXT record: `_dnsauth.{{domain}}` → `{{cname_token}}`.

### put-cname — Bind Custom Domain

```bash
ossutil website --method put oss://{{bucket_name}} --cname {{domain}} --profile $CERT_PROFILE --region $CERT_REGION --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

### put-cname — Bind Domain with Certificate

```bash
ossutil website --method put oss://{{bucket_name}} --cname {{domain}} \
  --certificate {{cert_id}} --cert-content "{{cert_pem}}" --private-key "{{key_pem}}" --force \
  --profile $CERT_PROFILE --region $CERT_REGION --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cas-ssl-cert-deploy/{session-id}"
```

---

## Helper Error Codes

### CDN Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `RetErrorSourceCircle` | Origin is already a CDN domain | Change origin server |
| `DomainOwnerVerifyFail` | Domain ownership not verified | Add DNS TXT record |
| `DomainOverLimit` | Domain limit reached (default 50) | Submit ticket |
| `RecordCheckNotAvailable` | Domain not ICP-filed + mainland region | Complete ICP or switch to `overseas` |

### WAF Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Waf.Pullin.ResourceExsit` | Domain already onboarded | Proceed to deployment |
| `RegionId` error | Invalid region | Use `cn-hangzhou` or `ap-southeast-1` |

### OSS Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `NeedVerifyDomainOwnership` | Domain not verified | Execute CreateCnameToken step |
| `CnameAlreadyExists` | Domain bound to another Bucket | Unbind first |
| `NoSuchCnameInRecord` | Domain not ICP-registered | Complete ICP filing |


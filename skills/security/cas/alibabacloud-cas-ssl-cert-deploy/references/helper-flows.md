# Helper Flows — SSL Certificate Deployment

> ⚠️ **CRITICAL: These helper flows are for RESOURCE CREATION ONLY — NOT for certificate deployment.**
>
> After creating resources via these flows, you MUST return to the CAS DeploymentJob path (`create-deployment-job` → `update-deployment-job-status` → `describe-deployment-job-status`) for certificate deployment.
>
> **The following APIs appearing in these flows are for resource setup ONLY and MUST NOT be used for certificate deployment:**
> - `alb create-listener` / `update-listener-attribute` — creates/updates ALB listener (resource setup), NOT a deployment path
> - `cdn add-cdn-domain` — creates CDN domain (resource setup), NOT a deployment path
> - `waf create-domain` / `modify-domain` — creates/updates WAF domain (resource setup), NOT a deployment path
> - `slb create-load-balancer` — creates SLB instance (resource setup), NOT a deployment path
>
> After resource creation completes, immediately call `list-cloud-resources` to discover the new resource, then proceed to Step 4 (CAS DeploymentJob).

Product-specific auto-configuration flows for certificate deployment.

---

## ALB HTTPS Listener Auto-Configuration

> ⚠️ **This is resource creation, NOT certificate deployment.** After completing listener creation, you MUST return to `list-cloud-resources` → CAS DeploymentJob path. Do NOT use `update-listener-attribute` to deploy certificates.

When deploying certificates to ALB with no matching HTTPS listener, auto-create via ALB API. See the detailed API command reference for full parameters.

### ALB Flow

```
Select ALB instance (list-load-balancers)
    ↓
Check HTTPS listeners (list-listeners)
    ↓
Has HTTPS listener → Update certificate (update-listener-attribute)
No HTTPS listener → Create listener (create-listener)
    ↓
Check domain forwarding rules (list-rules)
    ↓
No matching rule → Create rule (create-rule)
```

### ALB Key Parameters

- **Certificate ID format:** ALB uses `{CertId}-{region}`, e.g. `12345678-cn-hangzhou`. Concatenate: `${CERT_CERT_ID}-${CERT_REGION}`
- **Plugin install:** `aliyun plugin install --names aliyun-cli-alb`

### ALB Output

Set: `ALB_INSTANCE_ID={{alb_id}}`, `ALB_LISTENER_ID={{listener_id}}`.

### ALB Error Handling

| Error | Resolution |
|-------|-----------|
| No Active ALB instances | Guide user to create in console |
| `CertificateId` format error | Must be `{CertId}-{region}` |
| `ListenerPort` conflict | Port occupied, change or stop conflicting listener |
| `RuleName` duplicate | Add timestamp suffix |
| `Priority` conflict | Query existing rules and adjust |

---

## CDN Acceleration Domain Auto-Creation

> ⚠️ **This is resource creation, NOT certificate deployment.** After completing domain creation, you MUST return to `list-cloud-resources` → CAS DeploymentJob path. Do NOT use `add-cdn-domain` or any CDN-specific API to deploy certificates.

When deploying certificates to CDN with no matching resources, auto-create acceleration domain. See the detailed API command reference for full parameters.

### CDN Flow

```
Collect config (domain, business type, origin, scope)
    ↓
Origin pre-check (prevent circular reference)
    ↓
Create domain (add-cdn-domain)
    ↓
Poll domain status until online (3-8 min)
```

### CDN Key Parameters

- **Business type (CdnType):** `web` (images/small files, default) / `download` (large files) / `video` (streaming)
- **Origin type:** `ipaddr` (IP) / `domain` (domain) / `oss` (OSS bucket)
- **Scope:** `domestic` (mainland China, ICP required) / `overseas` (no ICP) / `global` (ICP required)

### CDN Output

Set: `CDN_DOMAIN={{domain}}`, `CDN_PRODUCT=cdn`, `CDN_STATUS=online`.

### CDN Error Handling

| Error | Resolution |
|-------|-----------|
| `RetErrorSourceCircle` | Origin is already CDN domain, change origin |
| Domain not ICP-filed + mainland China | Complete ICP filing or switch to `overseas` |
| `DomainOwnerVerifyFail` | Add DNS TXT record for ownership verification |
| `DomainOverLimit` | Domain limit reached (default 50), submit ticket |

---

## WAF 3.0 Domain Auto-Onboarding

> ⚠️ **This is resource creation, NOT certificate deployment.** After completing domain onboarding, you MUST return to `list-cloud-resources` → CAS DeploymentJob path. Do NOT use `create-domain` or `modify-domain` to deploy certificates.

When deploying certificates to WAF with no matching resources, auto-onboard domain to WAF 3.0. See the detailed API command reference for full parameters.

### WAF Flow

```
Get WAF instance ID (describe-instance)
    ↓
Create domain (create-domain with cert + origin config)
    ↓
Output WAF CNAME for DNS configuration
```

### WAF Key Parameters

- **RegionId:** `cn-hangzhou` (mainland China) or `ap-southeast-1` (overseas)
- **Listener ports:** HTTP 80, HTTPS 443 (required for certificate deployment)
- **Load balancing:** `roundRobin` / `iphash` / `leastTime`

### WAF Output

Set: `WAF_DOMAIN={{domain}}`, `WAF_CNAME={{cname}}`.

> Prompt user to configure DNS CNAME to the WAF CNAME address.

### WAF Error Handling

| Error | Resolution |
|-------|-----------|
| No WAF instance | Activate WAF 3.0 in console |
| `Waf.Pullin.ResourceExsit` | Domain already onboarded, proceed to deployment |
| `RegionId` error | WAF 3.0 only supports `cn-hangzhou` and `ap-southeast-1` |

---

## OSS Custom Domain Binding

> ⚠️ **This is resource creation, NOT certificate deployment.** After completing domain binding, you MUST return to `list-cloud-resources` → CAS DeploymentJob path. Do NOT use OSS-specific APIs to deploy certificates.

When deploying certificates to OSS with no matching custom domain, auto-bind via API. See the detailed API command reference for full parameters.

### OSS Flow

```
Check bucket availability
    ↓
Domain ownership verification (DNS TXT record)
    ↓
Bind custom domain (put-cname)
    ↓
Optionally associate certificate
```

### OSS Output

Set: `OSS_BUCKET={{bucket_name}}`, `OSS_DOMAIN={{domain}}`.

> Prompt user to CNAME to `{{bucket_name}}.oss-{{region}}.aliyuncs.com`.

### OSS Error Handling

| Error | Resolution |
|-------|-----------|
| Bucket doesn't exist | Create Bucket in console first |
| `NeedVerifyDomainOwnership` | Execute domain verification step |
| `CnameAlreadyExists` | Domain bound to another Bucket, unbind first |



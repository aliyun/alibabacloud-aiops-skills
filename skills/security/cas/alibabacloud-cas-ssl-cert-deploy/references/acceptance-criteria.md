# Acceptance Criteria — alibabacloud-cas-ssl-cert-deploy

**Scenario**: Deploy SSL certificates to Alibaba Cloud products via CAS DeploymentJob API
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product Names — verify product subcommands exist

| Product | CLI Prefix | Valid |
|---------|-----------|-------|
| CAS | `aliyun cas` | ✅ |
| CDN | `aliyun cdn` | ✅ |
| ALB | `aliyun alb` | ✅ |
| WAF | `aliyun waf-openapi` | ✅ |

### 2. Commands — verify action subcommands exist (plugin mode, kebab-case)

| Command | Valid |
|---------|-------|
| `aliyun cas create-deployment-job` | ✅ |
| `aliyun cas update-deployment-job-status` | ✅ |
| `aliyun cas describe-deployment-job-status` | ✅ |
| `aliyun cas list-cloud-resources` | ✅ |
| `aliyun cas list-worker-resource` | ✅ |
| `aliyun cas get-user-certificate-detail` | ✅ |
| `aliyun cdn add-cdn-domain` | ✅ |
| `aliyun cdn set-cdn-domain-sslcertificate` | ✅ |
| `aliyun alb create-listener` | ✅ |
| `aliyun waf-openapi create-domain` | ✅ |

### 3. Parameters — verify parameter names and formats

| Parameter | Format | Notes |
|-----------|--------|-------|
| `--job-type` | lowercase `user` or `cloud` | ❌ `User`, `USER` |
| `--cert-ids` | comma-separated IDs | e.g. `12345,67890` |
| `--resource-ids` | comma-separated IDs | from `ListCloudResources` `Id` field |
| `--contact-ids` | comma-separated IDs | from `list-contact` |
| `--cloud-product` | product code | `CDN`, `SLB`, `ALB`, `WAF`, `OSS`, `ESA` |
| `--keyword` | domain string | server-side fuzzy filter |
| `--status` | state string | `scheduling`, `pending`, `editing`, `rollback` |

---

## Correct CAS Workflow

#### ✅ CORRECT
1. `create-deployment-job` → returns `JobId`, job in `editing` state
2. `update-deployment-job-status --status scheduling` → starts execution
3. `describe-deployment-job-status` → poll until `SuccessCount + FailedCount == WorkerCount`
4. If failures: `list-worker-resource --status error` → diagnose

#### ❌ INCORRECT
- Creating job and expecting it to execute without `update-deployment-job-status` (job stays in `editing`)
- Using `--job-type "User"` (must be lowercase)
- Skipping `--contact-ids` (required parameter)

---

## ALB Certificate ID Format

#### ✅ CORRECT
```bash
--certificates.1.certificate-id "${CERT_CERT_ID}-${CERT_REGION}"
# e.g., 12345678-cn-hangzhou
```

#### ❌ INCORRECT
```bash
--certificates.1.certificate-id "${CERT_CERT_ID}"
# Missing region suffix causes format error
```

---

## Common Anti-Patterns

| Anti-Pattern | Correct Approach |
|-------------|-----------------|
| Deploy cert to non-matching domain | Only deploy to resources with matching domain (in SAN list) |
| Skip `update-deployment-job-status` | Must call after `create-deployment-job` to start execution |
| Use `--job-type "User"` (capitalized) | Use `--job-type "user"` (lowercase only) |
| Assume ALB cert ID = CAS cert ID | ALB requires `{CertId}-{region}` format |
| Deploy to CDN without ICP filing (mainland) | Check ICP filing first for mainland China CDN domains |
| Skipping [HITL-MUST] confirmations | Always use AskUserQuestion at every HITL checkpoint before proceeding |
| Using PascalCase flags (`--Name`, `--ContactIds`, `--WorkerId`) | Use kebab-case (`--name`, `--contact-ids`, `--worker-id`) for all CAS commands |
| Terminating workflow on NotFound errors | Follow error recovery paths: list alternatives, confirm with user, resume workflow |

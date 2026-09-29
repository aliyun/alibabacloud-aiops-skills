# Verification Method: WAF Domain Certificate Status Check

Step-by-step verification method and pass criteria. Every WAF/CAS API command must carry
`--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/{session-id} skill-version/{skill-version}"`
(both values per the Observability section in SKILL.md), with `sleep 0.3` between calls for throttling.
Append `--cli-dry-run` to any command to confirm the target Endpoint and request shape without sending it.

## Step 0: Environment and credentials

```bash
aliyun version          # >= 3.3.3
aliyun configure list   # a valid profile exists (AK / STS / OAuth)
aliyun plugin install --names aliyun-cli-waf-openapi   # WAF commands
aliyun plugin install --names aliyun-cli-cas           # WAF 3.0 certificate expiry resolution
```

**Pass criteria**: version is sufficient, a valid credential exists, and both plugins are installed. If a
credential is missing, STOP — do not continue the check.

## Step 1: Instance and WAF generation (Phase 1)

```bash
aliyun waf-openapi describe-instance --biz-region-id <region>
aliyun waf-openapi describe-instance-info --api-version 2019-09-10 --biz-region-id <region>
```

**Verification points**:
- 3.0 returns `InstanceId` → WAF 3.0 path; 2.0 returns `InstanceInfo.InstanceId` → WAF 2.0 path;
- both return an instance → ask which generation to check, or run both and label every row (constraint 6);
- neither returns an instance → "no WAF instance in this region"; stop, do not probe other regions.

## Step 2: Enumerate onboarded domains (Phase 2)

```bash
# WAF 3.0 (paged)
aliyun waf-openapi describe-domains --biz-region-id <region> --instance-id <instance_id> \
  --page-number 1 --page-size 50
# WAF 2.0
aliyun waf-openapi describe-domain-names --api-version 2019-09-10 --biz-region-id <region> \
  --instance-id <instance_id>
```

**Verification points**:
- WAF 3.0: page until the collected `Domains[].Domain` count reaches `TotalCount`;
- single-domain check: add `--domain <domain>` (3.0) or pass `--domain` to `describe-certificates` (2.0);
- an empty list is a real "no onboarded domains" result — state it, do not treat it as an error.

## Step 3: Certificate bindings and expiry (Phase 3)

```bash
# WAF 3.0: per-domain listen config
aliyun waf-openapi describe-domain-detail --biz-region-id <region> --instance-id <instance_id> \
  --domain <domain>
# WAF 3.0 → CAS: resolve expiry (CertFilter=true is MANDATORY)
aliyun cas get-user-certificate-detail --cert-id <numeric_cert_id> --cert-filter true --region <cas_region>
# WAF 2.0: expiry included, no CAS needed
aliyun waf-openapi describe-certificates --api-version 2019-09-10 --biz-region-id <region> \
  --instance-id <instance_id> --domain <domain>
```

**Verification points**:
- WAF 3.0: read `Listen.HttpsPorts` (empty → `https-not-enabled`), `Listen.CertId`,
  `Listen.SM2Enabled`/`SM2CertId`. `HttpsPorts` non-empty but no `CertId`/`SM2CertId` → `no-cert-bound`;
- CAS: `EndDate` (YYYY-MM-DD) drives the classification; `Expired=true` overrides a date-based "healthy";
  strip the region suffix from `SM2CertId` before the CAS call; if CAS cannot resolve the CertId →
  `expiry-not-retrieved`, never a guessed date;
- **`--cert-filter true` is present on every CAS call** — certificate content / private key is never returned;
- WAF 2.0: classify the `IsUsing=true` certificate; convert `EndTime` (Unix ms, UTC) before comparing.

## Step 4: Classification (Phase 4)

**Verification points**:
- `expired` (expiry < today, or CAS `Expired=true`) sorts first; then `expiring` (0 ≤ days ≤ warn_days,
  ascending); then `healthy`; `no-cert-bound` / `expiry-not-retrieved` are flagged for action;
  `https-not-enabled` is informational only;
- days remaining are computed against today's date; the warn window defaults to 30 days unless the customer
  set another value;
- every row cites an actually retrieved value (CertId, EndDate/EndTime, days left) or is marked
  "not retrieved" with the reason.

## Step 5: Final check with the script

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} python3 scripts/check_cert_status.py --region <region> --json
```

**Pass criteria**:
- exit code `0` → every checked domain is healthy or https-not-enabled; nothing needs attention;
- exit code `1` → `summary` counts at least one `expired` / `expiring` / `no-cert-bound` /
  `expiry-not-retrieved` row, matching the manual classification;
- exit code `2` → query failure, no WAF instance in the region, or an invalid region; human intervention;
- any row with `status=expiry-not-retrieved` carries a `notes` entry explaining why — never counted healthy.

## Overall success criteria

| Result | Ruling |
|--------|--------|
| All domains healthy / https-not-enabled | Report the inventory with the earliest expiry; no action needed |
| ≥1 expired | Report expired rows first with the deploy-a-replacement path; this is an active HTTPS risk |
| ≥1 expiring (≤ warn_days) | Report with the renew-now path; recommend re-running after redeploy |
| no-cert-bound with HTTPS on | Report as an actionable misconfiguration with the bind-a-certificate path |
| expiry-not-retrieved | Report the raw CertId + reason (deleted / cross-account / region mismatch); never a guessed expiry |
| Query failure / no instance | Mark "not retrieved" with its impact; emit no per-domain verdict |

# Acceptance Criteria: alibabacloud-waf-domain-cert-status-check

**Scenario**: read-only certificate expiry inventory for WAF-onboarded domains (WAF 3.0 + WAF 2.0)
**Purpose**: skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — WAF commands use `waf-openapi`; WAF 3.0 expiry uses `cas`

The WAF plugin is `aliyun-cli-waf-openapi`; there is no `waf` product subcommand. WAF 3.0 certificate
expiry is resolved through the `cas` plugin (`aliyun-cli-cas`).

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou
aliyun cas get-user-certificate-detail --cert-id 123 --cert-filter true --region cn-hangzhou
```

#### ❌ INCORRECT
```bash
aliyun waf describe-domains --region cn-hangzhou
```
`'waf' is not a valid product` — wrong product name, the command fails outright.

## 2. Command — the commands this skill is allowed to use (all read-only)

WAF 3.0: `describe-instance` / `describe-domains` / `describe-domain-detail`
WAF 2.0 (`--api-version 2019-09-10`): `describe-instance-info` / `describe-domain-names` /
`describe-certificates`
CAS: `get-user-certificate-detail` (always with `--cert-filter true`)

#### ❌ INCORRECT
Any `modify-*` / `create-*` / `delete-*` / `upload-*` / `deploy-*` command — this skill is read-only and
delivers renewal / deployment as console paths only. Calling CAS `get-user-certificate-detail` **without**
`--cert-filter true` is also incorrect (it would return certificate content and private key).

## 3. Version — WAF 2.0 must carry `--api-version 2019-09-10`

The `waf-openapi` plugin defaults to `2021-10-01` (WAF 3.0). WAF 2.0 actions require the explicit flag.

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-certificates --api-version 2019-09-10 --biz-region-id cn-hangzhou \
  --instance-id waf_xxx --domain www.example.com
```

#### ❌ INCORRECT
```bash
aliyun waf-openapi describe-certificates --version 2019-09-10 --force ...
```
`--version` is not the plugin's version switch, and `--force` bypasses the plugin and sends a **real** RPC
request even with `--cli-dry-run`. Use `--api-version`; never combine `--force` with a dry run.

## 4. Parameters — plugin mode uses lowercase-hyphen parameters

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-domains --biz-region-id cn-hangzhou --instance-id waf_xxx \
  --page-number 1 --page-size 50
```

#### ❌ INCORRECT
```bash
aliyun waf-openapi describe-domains --RegionId cn-hangzhou --InstanceId waf_xxx
```
PascalCase belongs to the legacy API style; plugin mode reports an unknown flag.

## 5. Error-prone parameters

#### Region parameter
- ✅ `--biz-region-id cn-hangzhou` (maps to the API's RegionId; only `cn-hangzhou` / `ap-southeast-1`)
- ❌ Using the global `--region` in place of WAF's RegionId parameter

#### CAS certificate id
- ✅ `--cert-id 123` — the numeric prefix of `Listen.CertId`; strip a region suffix (`123-cn-hangzhou` → `123`)
- ❌ Passing the raw suffixed SM2CertId, or omitting `--cert-filter true`

#### CAS region
- ✅ `--region cn-hangzhou` for a Chinese-mainland WAF; `ap-southeast-1` for an international WAF
- ❌ Reusing `--biz-region-id` for CAS, or a CAS region unrelated to the WAF region

## 6. Observability — every WAF/CAS API command must carry `--user-agent`

#### ✅ CORRECT
```bash
aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-domain-cert-status-check/<session-id> skill-version/<skill-version>"
```
The script receives both values via
`SKILL_SESSION_ID=<session-id> SKILL_VERSION=<skill-version> python3 scripts/check_cert_status.py ...`
(the version is supplied by the Agent — see the Observability section in SKILL.md).

#### ❌ INCORRECT
- Omitting `--user-agent`, or omitting the `skill-version/<skill-version>` component
- Using `aliyun configure ai-mode` (deprecated)
- Using `export ALIBABA_CLOUD_USER_AGENT=...` (deprecated; does not survive across separate bash invocations)

## 7. Credential and key-material safety

- ✅ Use `aliyun configure list` only, to check credential status
- ❌ Reading / printing AK/SK, asking the user to paste AK/SK into the conversation, or writing literal
  credentials with `aliyun configure set`
- ❌ Printing certificate content (`Cert`) or any private key (`Key` / `EncryptPrivateKey` /
  `SignPrivateKey`) in a report or conversation, even truncated

## 8. Parameter confirmation

- ✅ Confirm `region` (and the WAF generation when both exist) with the user before executing
- ❌ Assuming a default region, or silently picking WAF 3.0 vs 2.0 when both instances exist, then going
  straight to a verdict

---

# Correct Script Patterns

## 1. Invocation
```bash
SKILL_SESSION_ID=<session-id> SKILL_VERSION=<skill-version> python3 scripts/check_cert_status.py --region <region>
```
Exit codes: `0`=every checked domain healthy or https-not-enabled; `1`=at least one domain expired /
expiring / no-cert-bound / expiry-not-retrieved; `2`=query failure / no WAF instance / invalid region.

## 2. Expiry resolution discipline

#### ✅ CORRECT
- WAF 3.0: `Listen.CertId` is resolved through CAS; `EndDate` / `Expired` drive the classification;
  `Expired=true` overrides a date-based "healthy"
- WAF 2.0: `Certificates[].EndTime` (Unix ms) is converted before comparing; the `IsUsing=true`
  certificate is the one classified
- A CertId CAS cannot resolve → `expiry-not-retrieved` with the reason in `notes`

#### ❌ INCORRECT
- Reporting a WAF 3.0 domain as "healthy" because it "has a CertId", without resolving the expiry
- Guessing or fabricating an expiry date when CAS returns nothing
- Reading `expiry-not-retrieved` as "no certificate" or "healthy"

## 3. Classification ruling

#### ✅ CORRECT
- `expired` first, then `expiring` ascending by days left, then the rest
- `no-cert-bound` (HTTPS on, no cert) flagged as an actionable finding
- `https-not-enabled` reported as informational, never as a risk

#### ❌ INCORRECT
- Counting `https-not-enabled` as a failure, or burying an `expired` row below healthy ones
- Silently dropping an SM2 (Chinese national cryptography) certificate row

## 4. Conclusion discipline

#### ✅ CORRECT
- Query failure / empty result → mark "not retrieved" and state the impact on the conclusion
- A trust / handshake / chain symptom rather than a date → route to a certificate-chain / TLS flow, do not
  force an expiry verdict
- After the customer renews and redeploys → re-run the check to confirm the new expiry reached WAF

#### ❌ INCORRECT
- Inferring "the domain has no certificate" from an empty/failed query and closing the case
- Promising that certificate hosting / auto-renewal is active or will succeed (preconditions apply)
- Claiming a self-signed certificate can be bound to WAF (it cannot)

## 5. Read-only stance

- ✅ Renewal / upload / deploy / re-bind delivered as console paths; offer to re-run the read-only check
- ❌ Executing any write action, or calling a write API of WAF or CAS on the customer's behalf

## 6. Output language

- ✅ The report to the customer is written in the customer's language (Chinese for domestic tickets), and
  console navigation paths keep their original Chinese console wording, e.g.:

  ```
  数字证书管理服务控制台 → 证书管理 → SSL 证书管理 → 云产品部署 → 选择 WAF
  ```
- ❌ Replying in English to a Chinese-speaking customer, or translating console menu names so the customer
  cannot find them in the UI

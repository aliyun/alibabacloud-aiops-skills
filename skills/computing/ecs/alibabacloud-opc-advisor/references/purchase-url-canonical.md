# Purchase / Console Entry-Point Canonical Registry

> The **single source of truth** when advisor/deploy references any entry-point URL. Runtime URL construction and naming-convention inference are forbidden.
> Iron Rule #36: must verify URL reachability before outputting prescriptions containing URLs (see iron-rules, rule #36).

## 1. Field Meta-Spec

Every entry must populate the following schema:

```yaml
- entry_id: <unique short code>
  entry_type: purchase_single | landing_aggregate | console
  product: <corresponding product code>
  url: <full parameterized URL>
  required_account_type: personal | company | any
  required_real_name: true | false
  last_verified_at: 2026-06-26
  verified_by: PM-${name}
  notes: <optional>
```

## 2. Canonical Entry-Point Registry

### 2.1 Class A — Single-SKU Direct Purchase (purchase_single)

| entry_id | product | url | required_account_type |
|----------|---------|-----|----------------------|
| `token_plan_25k` | Bailian Token Plan 25k (`百炼`) | `https://common-buy.aliyun.com/token-plan` | any |
| `token_plan_100k` | Bailian Token Plan 100k (`百炼`) | `https://common-buy.aliyun.com/token-plan` | any |
| `pds_enterprise_200g` | PDS Enterprise Edition 200 GB (`阿里云盘企业版`) | `https://common-buy.aliyun.com/?commodityCode=pds_trc_public_cn&regionId=cn-beijing` | any |
| `esa_free` | ESA Edge Security Acceleration Free (`ESA 边缘安全加速免费版`) | `https://esa.console.aliyun.com/commonBuy` | any |
| `ecs_e_promo` | ECS Economy e series promo (RuleId 20906709) | `https://common-buy.aliyun.com/ecs/?RuleId=20906709` | any |
| `oss_40g_promo` | OSS 40 GB package | `https://common-buy.aliyun.com/?commodityCode=oss` | any |
| `oss_500g_promo` | OSS 500 GB package | `https://common-buy.aliyun.com/?commodityCode=oss` | any |

### 2.2 Class B — Aggregation Landing Page (landing_aggregate)

| entry_id | product | url | Notes |
|----------|---------|-----|-------|
| `opc_products` | OPC One-Person-Company Package Shelf (`OPC 一人公司套餐货架`) | `https://opc.aliyun.com/products` | Multi-SKU shelf + storyline + jumps to single-SKU purchase |
| `aliyun_elastic` | Alibaba Cloud Elastic Compute Overview (`阿里云弹性计算`) | `https://www.aliyun.com/product/ecs` | Marketing page, not direct purchase |

### 2.3 Class C — Console / Management (console)

| entry_id | product | url | Purpose |
|----------|---------|-----|---------|
| `beian_console` | ICP Filing Console (`ICP 备案控制台`) | `https://beian.aliyun.com` | Domain ICP filing |
| `ram_console` | RAM Access Console (`RAM 访问控制台`) | `https://ram.console.aliyun.com` | Sub-account/role/policy management |
| `actiontrail_console` | ActionTrail Audit (`操作审计`) | `https://actiontrail.console.aliyun.com` | Incident investigation (deploy-skill IR three-step card) |
| `smartservice_ticket` | Ticket Service (`工单服务`) | `https://smartservice.console.aliyun.com/service/create-ticket` | Submit ticket (legacy workorder.console.aliyun.com is decommissioned) |
| `realname_console` | Real-Name Verification (`实名认证`) | `https://account.console.aliyun.com/v2/#/realName` | Q5 fallback |
| `billing_console` | Billing Center (`费用中心`) | `https://usercenter2.aliyun.com/finance/expense-report` | Balance query, invoicing |
| `cdt_upgrade` | CDT Upgrade (prerequisite for public traffic pack) | `https://cdt.console.aliyun.com` | Click "Upgrade" to enable; CLI v3.4.1 has no cdt product code — must be manual |
| `openapi_explorer` | OpenAPI Explorer (4+1 Path E) | `https://api.aliyun.com` | Zero-friction fallback — browser-based form API calls |
| `aliyun_app_download` | Alibaba Cloud Mobile App (`阿里云 App`) | `https://promotion.aliyun.com/ntms/act/aliyunapp.html` | Zero-friction fallback — mobile console equivalent |

## 3. Reference Rules

- User-facing copy must use `[display text](URL)` markdown link format for URLs
- URL field names by entry_type: Class A → `purchase_url`, Class B → `landing_url`, Class C → `console_url`. **Mixing is forbidden.**
- YAML references use entry_id, not hardcoded URLs

## 4. Lint Validation

- Scan all SKILL.md / YAML URLs → each must have a matching entry in §2
- No match → error, require PM verification to add or correct
- `last_verified_at` exceeds 90 days → warning, prompt re-verification
- Field name mismatch (e.g., `landing_url` pointing to a Class A entry) → error

## 5. A/B/C Entry Classification Rules

| Form | Definition | URL Characteristics |
|------|-----------|---------------------|
| **A. Single-SKU Direct Purchase** | URL goes directly to single-product checkout, contains commodityCode | Store full parameterized URL per §1 schema |
| **B. Aggregation Landing Page** | Multi-SKU shelf; user selects then jumps to A | Missing commodityCode is **legitimate** (it's an aggregation page) |
| **C. Console** | Management interface for purchased resources | Field uses `console_url`; if it also supports purchasing, dual-tag |

# Account Ownership Impact Matrix

> Q5 `account_type` answer routes to this table — look up product availability, ICP filing entity, invoice header, ControlPolicy risk.

## 1. Three Account-Ownership States

| account_type | Definition | Real-Name Entity | ICP Filing Capability | Invoice Header |
|---|---|---|---|---|
| `personal_real_name` | Personal real-name verified (individual ID card) Alibaba Cloud account | Natural person | ✅ Personal-entity filing (non-commercial personal website) | Individual name (cannot issue company invoice) |
| `company_real_name` | Company real-name verified (business license) Alibaba Cloud account; includes individual business (`个体工商户`) | Legal-entity company / individual business | ✅ Enterprise-entity filing (commercial websites allowed) | Full company name + tax ID |
| `unknown` | Advisor did not ask / user unsure | — | — | — |

**Advisor Q5 fallback**: if user answers `unknown` → advisor must first guide them to "Console → Real-Name Verification page" to check, then return to Q5. **Assuming a default is forbidden.**

## 2. Product × Account-Ownership Availability Matrix

| Product | personal_real_name | company_real_name | Notes |
|---------|-------------------|-------------------|-------|
| ECS / OSS / RDS / ESA / ALB / SWAS | ✅ | ✅ | All available, no entity difference |
| **PDS Enterprise Edition** (`pds_trc_public_cn`) (`阿里云盘企业版`) | ✅ | ✅ | Personal real-name can purchase (verified 2026-06-26) |
| **Bailian Token Plan** (`百炼`) | ✅ | ✅ | Personal can use, but Token Plan invoice header is personal; company invoicing requires switching to company account |
| **ICP Filing** | ✅ Personal non-commercial | ✅ Enterprise commercial | Personal entity forbidden for commercial content (e-commerce/paid membership/ad network); enterprise entity fully open |
| **ICP Commercial License** (`增值电信业务许可证`) | ❌ | ✅ Company only, individual business also ineligible | Required for online transactions/advertising/paid content |
| **Domain .gov.cn / .org.cn** | ❌ | ✅ Specific entities only | Regular companies may also be ineligible — requires corresponding qualifications |
| **CDT Public Traffic Pack** | ✅ | ✅ | No entity difference |
| **OPC Package Promotional Pricing** | ✅ | ✅ | Personal accounts can also enjoy RuleId promotions |

## 3. ControlPolicy Risk Assessment (triggered only for company_real_name)

Company accounts may be globally blocked by enterprise Organization ControlPolicy for the following high-frequency actions — **advisor must warn in the prescription before outputting**:

- `ecs:AuthorizeSecurityGroup` (open SSH/HTTP inbound)
- `ecs:CreateKeyPair` (generate SSH key pair)
- `ram:CreateRole` / `ram:AttachRolePolicy` (create OPC deploy role)
- `oss:PutBucket` (create bucket)
- `rds:CreateDBInstance` (create RDS)

**Advisor response**: Q5=company_real_name → add to prescription header:
```
如果你公司账号挂在组织下，部分动作可能被组织策略拦截。deploy 会自动 DryRun 预检；如遇 Forbidden.RAM 错误，会自动走 fallback_route（OpenAPI Explorer 或控制台手工）。
```

**Forbidden recommendations**: advising user to "ask IT admin to disable org policy" or "switch to individual business account" — the former is overstepping, the latter is compliance evasion.

## 4. Teardown Permission Path Differences

| account_type | Teardown Path | Difference |
|---|---|---|
| personal_real_name | Direct AssumeRole opc-deploy-role → run teardown YAML | No org policy interference, all resources directly deletable |
| company_real_name + no organization | Same as above | No difference |
| company_real_name + organization (Resource Directory member) | AssumeRole may Forbidden on some delete actions | Must fallback: advisor outputs "manual console deletion checklist + ResourceCenter tag filter Created-By-OPC-Deploy" |

## 5. Invoice & Reconciliation Constraints

- personal_real_name: all charges go to personal invoice. **Forbidden** to promise "can issue company invoice"
- company_real_name: invoice header = real-name company full name + tax ID; advisor prescription using "reimburse via invoice" language only when company_real_name
- Switching account for invoicing → must migrate resources (cannot cross-account borrow invoices); advisor prompts: `如果你打算用公司报销但当前是个人账号，建议先用公司账号实名再下单`

## 6. ICP Filing Entity Differences (linked to the product-concept dictionary)

| Filing Entity | Commercial Allowed | Max Domains | Review Duration | Alibaba Cloud ICP Entry |
|---|---|---|---|---|
| Personal non-commercial | ❌ Forbidden: e-commerce/paid/ads/membership | 5 domains per entity | 7–20 business days | `https://beian.aliyun.com` |
| Enterprise non-commercial | Same as above | Same | Same | Same |
| Enterprise commercial | ✅ Fully open | Same | 20–30 business days (includes commercial license) | Same + `增值电信业务许可证` filed separately |

**Advisor fallback**: user states "I want paid membership/e-commerce" + Q5=personal_real_name → must output: `建议先切换公司账号实名再继续；个人账号无法做经营性 ICP，会触发后续整改通知。`

## 7. Advisor Prescription Header Template

```
账号归属：${Q5_account_type localized}
ICP 主体：${corresponding entity}
发票抬头：${corresponding header}
组织策略风险：${none / possible — deploy will pre-check}

------
（以下是 SKU 推荐处方正文）
```

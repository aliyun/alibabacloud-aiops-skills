# Iron Rules — Complete Checklist

> All rules are mandatory. Any violation is a red-line output defect — must be rejected and redone.

## Wording & Terminology (#1, #7, #8)

### #1 No Bare Technical Jargon
Never use cloud product acronyms (ECS/RDS/OSS/ALB/ESA/SLB/PDS/VPC/c9i) in isolation. Always present as `plain-language role (cloud product name)` format (see the glossary).

### #7 ECS: Spec Only, Never Series Name
Show users only spec like "ECS 2-core 4 GB". **Never mention series names** such as c9i/g9i/r9i.

### #8 Ask Business Load Using "Simultaneous Users" Only
Use the concurrent-users bijection table to map to SKU.
- **Simultaneous-users question** → clarify "during peak minute, how many people have it open at the same time" + everyday-life anchor
- **Second-clarification rule**: if answer is suspiciously high or ambiguously spans tiers, must follow up
- **Never use QPS / concurrency / TPS or other technical terms**
- **Scope boundary notice**: beyond general scenarios → **do not issue SKU**, output a boundary notice instead

---

## Flow Control (#2, #3, #4, #5, #6)

### #2 Determine Branch Before Writing Prescription
After user describes their goal, first classify into a routing branch. **Never skip branch determination and jump directly to recommending a package.**

### #3 Exactly One SKU Per User
Must output **exactly one of the 7 SKUs**. **Never list multiple options for comparison.**

### #4 Doctor-Writes-Prescription Style
The plain-language section must follow the five-section template (Diagnosis / Prescription / What You Get / How to Get Started / When to Upgrade).

### #5 Starter Uses QoderWork CN Pro Desktop
Starter users are guided to the ECS Economy e + QoderWork CN Pro Desktop path.
- Users who already have Codex/WorkBuddy or similar desktop assistants may skip QWCN Pro
- **Never let Starter users set up environments, install software, or run commands themselves**

### #6 Lite/Pro: Decouple Business to Dedicated ECS
AI assistant (OpenClaw) stays on the lightweight server; business deploys to a dedicated ECS. ECS is the "dedicated business storefront." **Never describe it as "branch store offloading traffic from the main store."**

---

## Pricing & Quotation (#9, #10, #12, #13, #15, #24)

### #9 Prices Must Be Exact
Pull exact Beijing-region fixed values from the SKU matrix. **Forbidden: "approximately" / "starting from" / "reference" or any vague wording.** Add footnote: "other regions may vary ±5%."

### #10 Token Plan Upgrade Advice Required
All SKUs containing a Token Plan must include upgrade advice (Standard → Advanced → Premium). **Forbidden: "takes effect instantly without interruption" marketing language** — upgrading must show `current monthly fee vs new monthly fee → user confirms before execution`; downgrading must state "takes effect after current billing cycle ends."

### #12 Disclaimer Required
All SKU quotations must include: `💡 Prices are for reference; actual amount is subject to checkout.` Promotional prices add: `subject to promotion availability at time of order.`

### #13 starter_webui Does Not Ask Promotion History
Advisor recommends ECS Economy e at the campaign price on the primary path. Whether the user qualifies is discovered automatically by the deploy agent at pricing time. If not eligible, auto-fallback to `ECS pay-by-traffic + 100 Mbps peak` at the fallback yearly price. **SWAS ¥45/mo fallback is deprecated.**

### #15 Price Summary Must Not Mix Billing Cycles
Products with different billing cycles **must never be simply summed**. Correct approach: use "initial launch cost" listing each item's cycle, or group by billing cycle.

### #24 fallback_ecs_config Structured Field
starter_webui / starter_app prescriptions **must** include the `fallback_ecs_config` structured field:

```yaml
fallback_ecs_config:
  instance_type: ecs.e-c1m1.large
  disk: { category: cloud_essd_entry, size_gb: 40 }
  internet: { charge_type: PayByTraffic, max_bandwidth_out: 100 }
  region_anchor: cn-beijing
  expected_price_yearly: 284.99
  expected_price_monthly_avg: 23.75
```

---

## User-Facing Presentation (#14, #25, #26)

### #14 Unified Presentation — A/B Dual-Path Closing
All prescriptions must close with A/B dual paths:
- **A. Let me place the order for you** (assisted path): user verbal confirmation is sufficient
- **B. Buy it yourself on the page** (self-service path): provide exact card name + configuration adjustment notes

4 cards map to 7 SKUs:
- starter_webui → `「OPC Starter 套餐 - 网络名片版」`
- starter_app → `「OPC Starter 套餐 - AI 应用版」`
- lite_* → `「OPC Lite 套餐」`
- pro_* → `「OPC Pro 套餐」`

### #25 Asset Inventory Must Be Complete
The `metaphor ↔ Alibaba Cloud official name` cross-reference list at the end of the prescription **must enumerate every resource actually included in the current SKU** (ECS / VPC / VSwitch / SecurityGroup / KeyPair / System Disk / ESA / OSS / RDS / ALB / ESS, etc.).

### #26 ICP Filing Script: Deferred + Escape Hatch
In the "How to Get Started" section, before asking about domain, **first** present the three-branch choice (A. Register domain & file ICP / B. Direct IP access, no filing / C. Overseas region, no filing), **then** explain the filing process.

---

## Security & Compliance (#16, #17, #18, #19, #20, #21, #22, #29)

### #16 Security Triage Required + PII Hard-Upgrade
Diagnosis section must include: "Will your product involve users **registering accounts or making payments**?"
- 🔴 Yes + data storage → **must output lite_seed minimum**, no self-rationalization to downgrade in thinking
- Only escape: user explicitly states "≤5 users + stores no data"

### #17 Must Ask Data Compliance Before Region Selection
"Where are your users mainly located?" → Mainland China (mainland node + ICP filing) / Overseas (Hong Kong/Singapore) / Both (mainland + ESA global acceleration).
- **Domain suffix hard cross-check**: .io/.dev/.app/.me + mainland → hard block

### #18 Asset Inventory (Official Names) Passback
Prescription ending must include the `metaphor ↔ Alibaba Cloud official name` cross-reference list. **Elevated to P1 mandatory output — never omit.**

### #19 Emergency Three-Step Card — Owned by Deploy Skill
The emergency three-step incident card (① Disable leaked AK → ② Check ActionTrail audit → ③ Submit ticket) is an **incident-response artifact owned by the downstream `alibabacloud-opc-deploy` skill** — it belongs where credentials are actually created and resources go live. **Advisor does NOT render this card** (advisor is read-only selection; there are no live credentials to protect yet). Do not include it in advisor prescriptions.

### #20 Regular Backup Reminder for Critical Data
Under "When to Upgrade" section, always append: `📦 Back up important data regularly.`

### #21 SSL Certificate Renewal Guidance
- Free certificates (ESA Let's Encrypt/DigiCert): auto-renews, no action needed
- Custom/uploaded certificates: state expiration date + manual renewal reminder

### #22 Credential Security Linkage
Credential mode mentions only "scan-to-authorize / RamRoleArn temporary credentials." **Never** write permanent AK anywhere.

### #29 Application-Layer Hardening Not Promised by Advisor
Advisor commits only to infrastructure layer (HTTPS / region / RDS TDE / VPC isolation). Application-layer items are output as a checklist for the user to implement.

---

## SKU Sizing Triage (#32)

### #32 Step 1.5 SKU Sizing Questionnaire v3.2 (2 asked + 5 inferred)

After Step 1 produces candidates but before Step 2 finalizes the prescription, determine the 7 sizing fields via **2 user-facing questions + 5 inferred** (see sku-sizing-questionnaire.md §1 for the full schema):

- **Asked (only if the prompt lacks the signal):** Q-scale (merged Q1 PV + Q3 concurrent, lifestyle anchors) and Q-userdata (merged Q2a registration/payment + Q2b upload).
- **Inferred (non-blocking, surfaced as assumptions):** Q4_public, Q5_account_type (default `personal_real_name`), Q6_vlm (via the §3 keyword dictionary), and the Q2a/Q2b split from the description.

The 7 internal fields and their upgrade triggers (used for deploy-side reverse validation):

| Field | Content | Upgrade Trigger |
|----------|---------|-----------------|
| Q1_pv (derived from Q-scale) | Monthly traffic volume | <500 = starter, 500–5k = lite_seed, 5k–50k = lite_growth, 50k–100k = pro_steady, >100k = pro_burst / decline(>1M) |
| Q2a_has_registration | Has user registration/payment? | Yes → ≥ lite_seed |
| Q2b_has_ugc_upload | Has upload/comments? | Yes → ≥ lite_seed + 38-item hardening checklist |
| Q3_qps (from Q-scale) | Peak concurrent users | <5 = starter, 5–15 = lite_seed, 15–80 = lite_growth, 80–200 = lite_traction, 200+ = pro |
| Q4_public (inferred) | Open to mainland China public internet | Yes → ICP filing + public exposure + content-safety prerequisites (geo routing in the domain & ICP reference) |
| Q5_account_type (inferred/defaulted) | Alibaba Cloud real-name type | unknown → guide user to confirm first |
| Q6_vlm (inferred) | Recognition/detection/generation vs plain text | Recognition/detection/generation → upgrade to lite_growth |

**Hard stop:** never fabricate a missing Q-scale or Q-userdata — if the prompt lacks the signal, ask it. Q4/Q5/Q6 may be inferred and surfaced as assumptions.

**Reverse-validation 7 fields** mandatory: Q1_pv / Q2a_has_registration / Q2b_has_ugc_upload / Q3_qps / Q4_public / Q5_account_type / Q6_vlm. Missing → deploy rejects. (Advisor fills these from 2 asked + 5 inferred; the deploy contract is unchanged.)

---

## Product Concepts & URLs (#30, #31)

### #30 Product Concept Dictionary Pre-Lookup
Any user-facing URL / product name / account system must be cross-checked against the product-concept dictionary. Never guess based on naming conventions.

### #31 Entry-Point Field Meta-Spec
Any user-facing URL **must be a full parameterized URL — bare domains forbidden**:
- **Class A purchase_single**: must contain `commodityCode` + `regionId`
- **Class B console**: product console sub-path, no mandatory parameters
- **Class C landing_aggregate**: aggregation landing page, no mandatory parameters

See the purchase-URL canonical reference for details.

---

## UGC Hardening (#33)

### #33 UGC 38-Item Full Checklist Hard Constraint
Q2a = yes OR Q2b = yes → prescription **must output the complete 38-item UGC hardening checklist by reference**, path: the UGC hardening checklist reference. **Inline simplified versions forbidden.**

---

## Metaphor Table (#34)

### #34 Metaphor↔Official-Name Table Required
The `metaphor ↔ Alibaba Cloud official name` cross-reference table is hardened to mandatory output — prevents agent randomization omissions. (The emergency three-step card is NOT an advisor output — it is owned by the deploy skill; see #19.)

---

## Account Ownership (#35)

### #35 Account Ownership Field in Prescription Header
Prescription YAML header must contain:

```yaml
advisor_recommendation:
  sku: lite_seed
  account_type: personal_real_name | company_real_name | individual_business | unknown
  region: cn-beijing
  estimated_monthly_price_cny: 596.54
```

- `unknown` → add warning, guide user to confirm real-name status first
- `personal_real_name` → exclude **commercial ICP only** (operating/commercial-site filing requires a company account; if the user wants paid membership/e-commerce, guide them to switch to company real-name first). PDS Enterprise Edition (`阿里云盘企业版`) is **purchasable by personal real-name accounts** — do NOT exclude it (verified 2026-06-26; see the account-type-impact reference).

---

## Image Selection (#28)

### #28 Image Selection Contract: Pin to ImageFamily with Minor Version

```yaml
image:
  family: acs:alibaba_cloud_linux_3_2104_lts_x64
  os_series: Alibaba Cloud Linux 3.2104 LTS
  arch: x64
  family_pinned_at: "2026-06-25"
  next_review_due: "2026-12-25"
```

Naming convention: `acs:` prefix + all-lowercase + underscore-separated + includes full minor version. See the SKU matrix § Image section (shared by all ECS-containing SKUs).

---

## HTTPS (#27)

### #27 HTTPS Auto-Renewal Prerequisite Wording
Do not directly promise "auto-renews, no action needed." Must prepend the ESA activation assumption:
> "I'll also enable ESA Free for you; once hooked up, HTTPS auto-renews hands-free. If ESA activation fails, I'll fall back to manual renewal and remind you when it's due."

---

## Domain & ICP Filing (#11)

### #11 Unified Domain Recommendation + ICP Based on Region
All users receive a unified domain purchase recommendation. Mainland China regions require ICP filing; non-mainland regions do not.

---

## scope_declaration (#23)

### #23 scope_declaration — Internal YAML Only (NOT User-Visible)

```yaml
scope_declaration:
  can_do:
    - "帮你选阿里云 OPC 套餐 + 算月费"
    - "帮你下单买云资源（ECS / RDS / OSS / ESA 等）"
    - "把你已经写好的代码部署到刚买的服务器"
    - "部署后教你登录控制台 + 怎么续费（出事三步卡等应急指引由部署环节 alibabacloud-opc-deploy 提供）"
  cannot_do:
    - "帮你写业务代码（注册/登录/支付/上传等应用逻辑）"
    - "帮你做业务运维（数据库表设计 / API 调试 / 业务报警）"
    - "承诺应用层加固（密码加密 / 隐私页——需在你的代码里做）"
    - "替你做业务决策（要不要做某功能 / 用什么技术栈）"
```

**Output position: internal YAML only — passed to the downstream `alibabacloud-opc-deploy` skill. NEVER render `scope_declaration` (the `我能做什么` / `不能做什么` block) as user-visible text.** The end user is non-technical; a capability-boundary block only adds noise. Scope/boundary is conveyed to the user implicitly through the prescription itself, and the explicit boundary block lives in the deploy skill.

---

## URL Reachability Verification (#36)

### #36 Must Verify URL Reachability Before Outputting Prescriptions with URLs

When the advisor outputs any prescription containing purchase links / console links / product entry points:

1. **If network access is available** → perform HTTP HEAD/GET on the URL, confirm non-4xx/5xx. If dead, search the Alibaba Cloud official site for the current correct address before outputting.
2. **If network access is unavailable** → must annotate `last_verified_at: YYYY-MM-DD` (from the purchase-URL canonical reference §2), prompt user to click-verify themselves.
3. **Never construct URLs by naming convention** — all entry points must come from the purchase-URL canonical reference §2 truth table or be live-verified.

# Aliyun CLI Capability Gating Matrix

> Companion to deploy SKILL.md **Phase -1.5 (SKU product CLI reachability static gate)** and iron-rule #25.
>
> **Purpose**: before the deploy skill enters Phase 0, statically decide against this matrix whether "the products to provision this time" can be automated via the aliyun CLI; unreachable (false) or semi-automatic (partial) goes straight to the fallback_route (usually a console deep link + manual user confirmation), instead of letting the model trial-and-error.
>
> **Maintenance rule**: once a month, release lint runs a smoke test (at minimum calling List* / Describe* to verify), and backfills the result into the last_verified_at field.

| Product code | API name | Deploy-side coverage | last_verified_at | fallback_route | Notes |
|---|---|---|---|---|---|
| ecs | ECS | full | 2026-06-25 | — | RunInstances / DescribeInstances / Delete* fully covered |
| vpc | VPC | full | 2026-06-25 | — | DescribeVpcs / CreateVpc / DeleteVpc fully covered; QuotaExceeded.Vpc reuses Phase 2.1 step ② |
| sg | VPC SecurityGroup | full | 2026-06-25 | — | CreateSecurityGroup / AuthorizeSecurityGroup fully covered |
| keypair | ECS KeyPair | full | 2026-06-25 | — | CreateKeyPair returns the private key in the response (`PrivateKeyBody`); pipe it to disk, never to stdout (iron-rule #30) |
| rds | RDS | full | 2026-06-25 | — | CreateDBInstance fully covered; uses PrePaid + Month |
| oss | OSS | partial | 2026-08-26 | https://common-buy.aliyun.com/?commodityCode=ossbag&regionId=china-common | OSS must be activated once by the user before ANY bucket call works. Buying a storage package on the fallback_route activates the service at the same time, so one manual step covers both. Bucket create + config then run via `ossutil` (E2E-verified on CLI 3.4.11: `ossutil mb`, `ossutil api put-bucket-encryption`, `put-bucket-versioning`, `put-bucket-tags`). ⚠️ **Activation cannot be detected read-only** (E2E-measured): on an unactivated account `ossutil ls` and `ossutil api list-buckets` both SUCCEED and `get-bucket-info` answers `404 NoSuchBucket` — only a write reveals it, `PutBucket` → `403 UserDisable`. That is why this row is partial: the Step 0.2b read-only probe CANNOT catch it, so activation is announced in the Phase -1.5 reachability summary and **confirmed at Step 1.3** (`confirm-authorize.md`) together with the resource list, before any paid call. Do not stop at -1.5 for this one — the user should see the plan and the total before being sent off to buy anything. The buy page defaults to `标准 - 同城冗余存储` and its selections do not travel in the URL, so a preset link is impossible; Step 1.3 spells out every pick. |
| alb | ALB | full | 2026-06-25 | — | CreateLoadBalancer fully covered |
| ess | ESS | full | 2026-06-25 | — | CreateScalingGroup fully covered |
| swas | SWAS | full | 2026-06-25 | Console https://swas.console.aliyun.com | only the explicit lite_seed path is kept; the starter fallback is deprecated |
| ram | RAM | full | 2026-06-25 | — | CreatePolicy / AttachPolicyToUser fully covered |
| bssopenapi | Billing | full | 2026-06-25 | — | DescribePrice / DescribeInstanceBill fully covered |
| cms | CloudMonitor | full | 2026-06-25 | — | PutMetricRuleTargets / PutResourceMetricRule (traffic-alarm dependency) |
| esa | ESA (Edge Security Acceleration) | full | 2026-08-26 | https://esa.console.aliyun.com/commonBuy | **Provisioning is fully CLI-reachable for every tier**. `PurchaseRatePlan` / `SwitchSiteAccess` work; `esa` has no regional endpoint, so always pass `--endpoint esa.cn-hangzhou.aliyuncs.com`. **Pricing:** use `describe-rate-plan-price --plan-name <medium\|entranceplan> --period 1 --amount 1` and read `PriceModel.RatePlan.PlanPriceList[0].Price` (discounted, actually charged) — NOT `TotalPrice` (list). Measured: `medium` → TotalPrice 375.0 / DiscountPrice 255.0 / **Price 120.0**, rule `RuleDescId 20958767` `产品新用户专享优惠，限购1个`; `entranceplan` → 0.0. **The discount is applied server-side from ACCOUNT eligibility — there is no promo parameter to pass, and `--rule-desc-id` (or any similar spelling) is SILENTLY DROPPED from the request rather than rejected.** Consequence: never hardcode an ESA price anywhere; eligibility is per-account (same trap as the ECS ¥99/yr promo) so another account may pay the full ¥375 — inquire before every charge. For MANUAL enablement — including the ERROR GATE "handle it in the console yourself" option — send the user to the commonBuy fallback_route above (that is the page where they enable the free/standard plan). The general `https://esa.console.aliyun.com/` is ONLY for managing an ALREADY-active ESA (add-site / WAF config); never hand it out as the "enable ESA yourself" link. **⚠️ Free-plan quota, and why an EXPIRED instance still blocks you (E2E-measured):** an account gets exactly ONE free-plan instance, and an **expired** one keeps occupying that quota — the console offers no manual release, and it only frees up automatically **15 days after expiry**. So `PurchaseRatePlan` for the free plan can fail `QuotaExceed.FreePlan` on an account that visibly has no usable ESA. This is invisible to every read-only probe: with the quota exhausted, `esa list-user-rate-plan-instances` returns an **empty result, not an error**, so Phase -1.5 and the Step 0.2b probe both pass and the failure only lands at the paid call. On `QuotaExceed.FreePlan` the handling is not yours to improvise — it is fixed by the error table in SKILL.md: state the truth (the slot is held by an instance that expired on `<date>`, it releases automatically 15 days later, you cannot work around it), then **skip this one item and carry on with the remaining resources**. Do not promise to "open a new free plan for you", do not hand out a console link for this case, and do not turn it into a question the user has to answer — a blocked free add-on is not a decision they need to make mid-deployment. **Quote the expiry date verbatim from the API response field** — do not re-derive, round, or recall it from earlier in the conversation; the date was misreported three times in one round (said 8/17 and 8/20 when the API said 8/21). The same rule covers every date and quota number you relay: copy the API's own string. |
| pds | PDS (Pangu) | partial | 2026-08-26 | https://common-buy.aliyun.com/?commodityCode=pds_trc_public_cn&regionId=cn-beijing | the primary account must enable the drive before the API can be called; sub-accounts lack the permission. The fallback_route above is the actual PURCHASE page (`commodityCode=pds_trc_public_cn`) and is the same link every sku-params yaml PDS step hands out — keep them identical. `https://pds.console.aliyun.com/` is ONLY for managing an ALREADY-active drive; never hand it out as the "enable PDS yourself" link (same trap as the esa row). Specs used: 200 GB for starter_app / lite_*, 500 GB for pro_*. |
| bailian | `Token Plan AI 模型订阅计划` | false | 2026-06-25 | https://common-buy.aliyun.com/token-plan | Token-billing plan purchase has no matching OpenAPI; must go through the console |
| dashscope | DashScope Model Service | false | 2026-06-25 | https://dashscope.console.aliyun.com | billing-tier purchase has no CLI channel |
| sls | SLS Log Service | full | 2026-06-25 | — | CreateProject / CreateLogStore fully covered |
| dms | DMS | partial | 2026-06-25 | https://dms.aliyun.com | instance registration can go via CLI; the web SQL Console must be entered manually |
| domain | Domain | partial | 2026-06-25 | https://wanwang.aliyun.com | registration can call the API; filing/real-name must be done by the user |
| icp | ICP Filing | false | 2026-06-25 | https://beian.aliyun.com | the whole filing flow is manual; the CLI has no capability |

## Field definitions

- **full**: the CLI can complete provisioning + config + verification end-to-end; the deploy skill can close the loop fully automatically.
- **partial**: the CLI can only complete part of the main flow; the deploy skill must hand the partial segment to the user in the console (output a deep link + screenshot instructions + wait for the user to reply "ok" before continuing).
- **false**: the CLI cannot provision the product at all; the deploy skill immediately takes the fallback_route and does not enter the Phase 0 automation branch.

## Binding with the SKU yaml

Every product code appearing in a `references/sku-params/*.yaml` products list must be findable in this matrix. If any product hits partial/false:
- partial → append that step to `state.manual_steps`; deploy enters a "waiting for the user to finish in the console" suspended state.
- false → deploy directly declines the order, telling the user:

```text
这个 SKU 包含 ${product}，目前 CLI 还开不了，需要你在控制台点几下：${fallback_route}。开完回来跟我说一声，我接着帮你拼后面的资源。
```

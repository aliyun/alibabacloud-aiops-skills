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
| oss | OSS | full | 2026-06-25 | — | PutBucket / ossutil both available |
| alb | ALB | full | 2026-06-25 | — | CreateLoadBalancer fully covered |
| ess | ESS | full | 2026-06-25 | — | CreateScalingGroup fully covered |
| swas | SWAS | full | 2026-06-25 | Console https://swas.console.aliyun.com | only the explicit lite_seed path is kept; the starter fallback is deprecated |
| ram | RAM | full | 2026-06-25 | — | CreatePolicy / AttachPolicyToUser fully covered |
| bssopenapi | Billing | full | 2026-06-25 | — | DescribePrice / DescribeInstanceBill fully covered |
| cms | CloudMonitor | full | 2026-06-25 | — | PutMetricRuleTargets / PutResourceMetricRule (traffic-alarm dependency) |
| esa | ESA (Edge Security Acceleration) | partial | 2026-06-26 | https://esa.console.aliyun.com/commonBuy | PurchaseRatePlan / SwitchSiteAccess work, but the PlanName=medium pricing endpoint is unstable; the commonBuy link is most stable (the old commonbuy.aliyun.com/?commodityCode=esa path 404s, unified to esa.console.aliyun.com/commonBuy). For MANUAL enablement — including the ERROR GATE "handle it in the console yourself" option — always send the user to the commonBuy fallback_route above (that is the page where they enable the free/standard plan). The general `https://esa.console.aliyun.com/` is ONLY for managing an ALREADY-active ESA (add-site / WAF config); never hand it out as the "enable ESA yourself" link. |
| pds | PDS (Pangu) | partial | 2026-06-25 | https://www.aliyun.com/product/pds | the primary account must enable the drive in the console before the API can be called |
| bailian | Bailian Token Plan | false | 2026-06-25 | https://common-buy.aliyun.com/token-plan | Token-billing plan purchase has no matching OpenAPI; must go through the console |
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

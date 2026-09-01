# Phase 0 · Step 0.2b: Policy coverage probe (MANDATORY before any paid call)

> **This is a hard gate, not an optional check.** It is the ONLY thing standing between a narrow-policy
> credential and a half-paid, half-denied deployment.
>
> - **Entry**: a usable credential resolved in Step 0.2 (or freshly configured in Step 0.3).
> - **Exit**: every product in THIS SKU's product set answered without 403 → go to Phase 0.4 (`image-resolution.md`).
> - **On any 403**: STOP. Do not enter Phase 1, Phase 2, Phase 3, or any paid step. Hand the user a
>   whole-policy replacement JSON and wait.
> - Product set comes from Phase -1.5 (`preflight.md`). Zero cost: every command below is read-only and
>   creates nothing.
>
> ⚠️ **Naming**: when you save these commands as a script, name it **`ran_scripts/04-permission-check.sh`**
>   (log `04-permission-check.log`). Do **not** derive the script name from this reference file's own name —
>   `probe` / `policy-probe` / `探测` / `探针` are internal labels and must never appear in a filename, a
>   state key, or any line the user can read (iron-rule #6 naming table, Hard Gate #6 item (b)). In
>   user-facing prose call this step `先试一下权限够不够`.

## Probe commands (one per product in the SKU's set)

```text
Run one Describe/List per product in the SKU's product set (derived in Phase -1.5 from the sku-params
yaml). These are unconditional Describe calls on the policy — a permission failure means the policy
lacks that product.

⚠️ **How to detect a permission failure (E2E-measured — do NOT match an exact Code list)**: the error
Code differs per product, so judge on `StatusCode: 403` OR the presence of `Forbidden` / `NoPermission` /
`not authorized` anywhere in the response. Codes actually observed:
    rds → `Forbidden`            alb → `Forbidden.LoadBalancer`    ess → `Forbidden.Unauthorized`
    swas-open → `NoPermission`                                     vpc/ecs → `Forbidden.RAM`
    oss → plain text, **no Code field at all** (ossutil is a standalone tool, not an OpenAPI plugin)
  Matching only "NoPermission" or only "Forbidden.RAM" will silently pass a product that is actually
  denied — that is the exact failure this gate exists to prevent.
  ⚠️ `UserDisable` is the ONE 403 that is NOT a permission failure — see the note below this block.

  ecs    → aliyun ecs describe-regions --profile <p>   (already ran in Step 0.4-connectivity; counts)
  vpc    → aliyun vpc describe-vpcs --biz-region-id <region> --profile <p>
  rds    → aliyun rds describe-db-instances --biz-region-id <region> --profile <p>
  oss    → aliyun ossutil ls --profile <p>
           # ⚠️ The legacy `oss` verb is DEPRECATED — the CLI answers it with a notice telling you to
           #    switch to `ossutil`. Always use `ossutil`: it is a standalone tool, not an OpenAPI
           #    plugin, so fs-style verbs (`ls` / `mb` / `cp`) sit alongside `ossutil api <verb>`.
           #    E2E-measured: `ossutil ls` returns "Bucket Number is: N" (plain text, not JSON).
           # ⚠️ Because the output is plain text, a 403 here does NOT arrive as a JSON error Code —
           #    match the message text, and never treat "unparseable output" as a pass.
           # ⚠️ This probe proves PERMISSIONS ONLY — it does NOT prove OSS is activated. E2E-measured on
           #    an unactivated account: `ossutil ls` and `ossutil api list-buckets` both SUCCEED and
           #    `get-bucket-info` answers 404 NoSuchBucket, while `PutBucket` fails 403 UserDisable.
           #    Activation is handled up front by the Phase -1.5 manual handover, never by this probe.
  alb    → aliyun alb list-load-balancers --profile <p>
  ess    → aliyun ess describe-scaling-groups --biz-region-id <region> --profile <p>
  swas   → aliyun swas-open list-instances --biz-region-id <region> --profile <p>
  esa    → aliyun esa list-user-rate-plan-instances --endpoint esa.cn-hangzhou.aliyuncs.com --profile <p>
           # ⚠️ E2E-measured: without --endpoint this fails with "endpoint not configured for product
           #    'esa' in region 'cn-beijing'". esa is centrally deployed — always pin the cn-hangzhou
           #    endpoint regardless of the deploy region.

Do NOT probe products NOT in this SKU's set (e.g., a starter deploy must NOT probe rds/oss/alb/ess) —
asking a starter user for RDS permissions is a least-privilege violation.
⚠️ A flag error / endpoint error / unparseable output is NOT a pass and NOT a permission failure either:
fix the command per the flag conventions in cli-meta.md and re-run, then judge the permission result.
⚠️ A first call may report `Plugin 'aliyun-cli-<product>' is required ... but not installed` — that is the
plugin auto-installing (Step 0.1b), not a permission result. Re-run the same command once and judge that.
Report EVERY failing product — stopping at the first 403 makes the user fix one permission at a time.
```

## `UserDisable` is not a permission failure

Code `UserDisable` (E2E-measured `EC 0003-00000801`, observed on OSS `PutBucket`) means **the product is
not activated on the account**, not that the policy is too narrow. Handing a policy replacement JSON for
it sends the user in circles: they swap the policy and it still fails. Route it to that product's
activation `fallback_route` in `cli_capability_matrix.md`, and wait for the user to confirm — the same
hand-over Phase -1.5 should already have done. Never fold it in with the 403 permission cases above.

## Outcome

```text
- All probes succeed (200 or empty-list, both fine) → go to Phase 0.4.

- A probe returns 5xx / InternalError → this is NOT a permission result and must never be scored as
  one. Retry the IDENTICAL command once (iron-rule #26's per-goal budget); if it fails again, stop and
  tell the user it is an Alibaba Cloud server-side hiccup, offer "wait and retry" or the ticket link,
  and mark this product's coverage as UNKNOWN — not passed, not failed. Do NOT switch the call form
  (kebab ↔ PascalCase), the endpoint, or install a plugin in order to "get a result": rewriting the
  command until something returns 200 produces a green light that proves nothing (iron-rule #35).

- The two attempts for one product DISAGREE (one errors, another form returns 200) → the product is
  INCONCLUSIVE. Report both outcomes to the user, quote the error code verbatim, say plainly that
  because they disagree you are not treating the permission as confirmed, and stop. Never record
  `权限检查通过` for that product in the conversation, the state file, or any output file
  (iron-rule #35).

- Any probe returns 403 / NoPermission / Forbidden.RAM → STOP, show the user which product(s) lack
  coverage, then hand them a **whole-policy replacement JSON scoped to THIS SKU** (never an
  incremental patch, never the all-SKU superset — see "Scope the policy to the settled SKU" in the
  RAM policy reference). Rationale: RAM policies are versioned (up to 5 versions), so replacing the
  document wholesale is both a supported operation and far less error-prone than making a
  non-technical user hunt for the one missing action — an incremental patch reliably misses the
  companion permissions (e.g. adding `rds:CreateDBInstance` but not `rds:AddTagsToResource`, which
  then fails at the tagging step).

  "你目前的权限不覆盖 ${product_plain_names}（${product_codes}），创建这些资源时会被拒绝。
   我按你这次的套餐给你重新生成了一份完整的权限清单，你整份替换过去就行：
   ① 打开 https://ram.console.aliyun.com/policies → 找到 ${policy_name} → 「创建新版本」
   ② 把下面这份 JSON 整份粘进去，勾选「设为当前版本」后保存
   ③ 存好回来跟我说一声，我接着开通

   <emit the scoped policy JSON here as a fenced json block in the actual reply>

   （不用自己找该加哪一行——整份换掉就是最新的了。改完有报错就把报错贴给我。）"

  Keeping a copy at `outputs/ram-policy-<sku>.json` is welcome as a record, but the fenced JSON block
  in the reply is the thing that matters — the file never replaces it, exactly as with the resource
  list in Hard Gate #1.

  ⚠️ Emit the actual scoped JSON inline, unprompted. Never say "参考我之前发你的文档" and leave the user
  to diff it themselves, and never wait for the user to ask for the JSON — handing it over IS the
  guidance, not an option you offer.
  ⚠️ Do NOT attempt to read or patch the policy for the user: opc-deploy-role has no
  `ram:CreatePolicyVersion` (and must not — a role that can widen its own permissions defeats the whole
  least-privilege design). E2E-measured, even `ram:GetPolicy` is ImplicitDenied for this role, so you
  CANNOT read the current document back; do not burn retries trying. Generate the full SKU-scoped JSON
  from the RAM policy reference instead.
  ⚠️ User-facing wording: never say "探针 / 门控 / gate / 覆盖度 / probe" — the user only sees the plain
  copy above.

  Do NOT proceed to Phase 1 or any paid step until the probe passes.
```

# Phase -1 / -1.5: Preflight

> Runs AFTER the SKU is settled (Phase -2, `sku-resolution.md`) and BEFORE Phase 0.
>
> - **Entry**: a legal SKU is settled.
> - **Exit**: account confirmed + real-name verified + deploy capability taken over + every product in this
>   SKU checked against the CLI capability matrix, with any manual product opened and user-confirmed
>   → go to Phase 0 (`cli-install.md`).
> - Both phases below need the settled SKU: Step -1.2's bridging copy enumerates the package contents, and
>   Phase -1.5 reads that SKU's product list. If you got here without a SKU, go back to Phase -2.

### Phase -1: Preconditions (Alibaba Cloud account + real-name verification + desktop tool)

```text
Step -1.1: Confirm the Alibaba Cloud account
  Ask the user: "你有阿里云账号吗？"
  - yes → continue
  - no → guide registration:
    "先注册一个阿里云账号（免费）：
     👉 https://account.aliyun.com/register/qr_register.htm
     注册完告诉我。"
    Wait for the user to confirm, then continue.

Step -1.1b: Confirm real-name verification status
  ⚠️ A China-site account MUST complete real-name verification before it can purchase cloud products (personal or enterprise verification both work); without it, later resource creation fails outright — verify up front.
  Ask the user: "你的阿里云账号完成实名认证了吗？"
  - verified → continue
  - not verified / unsure → guide:
    "买云服务器前，阿里云要求先完成实名认证（中国站规定），几分钟就好：
     👉 https://help.aliyun.com/zh/account/account-verification-overview
     （阿里云控制台 → 账号中心 → 实名认证，按引导完成个人或企业认证即可）
     认证通过后告诉我，我再帮你创建资源。"
    Wait for the user to confirm verification passed, then continue.

Step -1.2: Take over code-deployment capability (decide by runtime self-introspection, never ask)
  Code deployment relies on a desktop AI assistant. `qwcn-pro` (QoderWork CN Pro, ¥59/month) is **desktop
  software, not a cloud resource** — it is absent from the CLI capability matrix, deploy cannot provision
  it, and it is NOT part of any package quote. The user subscribes to it separately if they need it.
  Decide which branch applies by checking your OWN capabilities — do NOT ask the user:

    Do I have a local-execution capability (a Bash / terminal / file-write tool acting on the user's machine)?
      YES → I AM the desktop AI assistant. record has_desktop_tool = true.
      NO  → chat-only runtime (web page, no local shell). record has_desktop_tool = false.
                Do NOT assume the user has a desktop tool, and do NOT ask them whether they have one —
                guide the download instead (below).

  ⚠️ Never ask "你是不是已经在用 Codex / WorkBuddy / QoderWork 这类桌面 AI 助手了？" — in the YES branch the
  answer is your own runtime, and in the NO branch asking changes nothing because you guide the download
  either way. advisor resolves this identical fact the same way (its a1-zero-start Step 2 / iron-rule #5);
  if the two sides diverge the user gets interrogated about something the product already knows.

  has_desktop_tool = true → take over the current-assistant identity + give the bridging explanation (starter_webui example):
    "你的套餐里包含：一台服务器 + 全球加速。
     代码部署上去这件事，我（你正在用的这个 AI 助手）就能帮你远程搞定，不需要额外买东西。
     接下来我先帮你把云端资源开好（服务器 + ESA 加速）。"

  has_desktop_tool = false → give the bridging explanation + guide the download as a SEPARATE self-purchase:
    "你的套餐里包含：一台服务器 + 全球加速。
     服务器创建好之后，需要一个能远程操作服务器的桌面 AI 助手来帮你部署代码。
     推荐 QoderWork CN Pro（¥59/月，你自己下载订阅，不含在这个套餐里）：
     👉 https://qoder.com.cn/qoderwork
     （可以先创建服务器，回头再装桌面工具也行）"
  ⚠️ The package price is identical in both branches — the ¥59 never enters the quote. Never present it as
  a package component, and never add it to the total shown at the payment gate.
```

### Phase -1.5: SKU product CLI reachability static gate (iron-rule #25)

```text
⚠️ STATIC LOOKUP ONLY (iron-rule #25): this entire gate is a TABLE READ of cli_capability_matrix. Running ANY aliyun CLI command here to probe/verify reachability (describe-instances / describe-vpcs / list-instances / describe-db-instances, etc.) is a critical violation. The first real CLI call happens in Phase 0.

Step -1.5.1: Read the product list for the SKU
  Precondition: the SKU name is already settled (Phase -2 guarantees this). If it somehow is not, go back
  to Phase -2 (sku-resolution) and settle it first —
  NEVER treat the full product superset below as this deployment's list when there is no SKU.
  Take the subset for the settled SKU: from the advisor prescription or that SKU's default config (references/sku-params/<sku>.yaml),
  extract the Alibaba Cloud products this SKU actually involves.
  (The full superset this skill may touch: ECS / VPC / RDS / OSS / SWAS / ESA / ALB / ESS /
   Token Plan / PDS / CloudMonitor — each SKU uses only a subset,
   e.g. lite_seed does not include ALB/ESS — but it DOES include Token Plan / PDS as manual items (ESA is
   NOT manual: it is CLI-provisioned automatically, see the capability matrix row),
   so read the yaml's own product list rather than guessing from the tier name.)
  ⚠️ Keep this product list — Phase 0.2b probes exactly this set, and the RAM policy handed to the user is
  scoped to exactly this set.

Step -1.5.2: Statically check the CLI capability gating matrix (cli_capability_matrix)
  For each product, look up the cli_supported field line by line:
    - true     → fully CLI-automatable
    - partial  → some APIs work via CLI (e.g., PDS needs primary-account enablement then sub-account CLI continuation; the OSS package must be bought on a page before any bucket call)
    - false    → no CLI path at all (e.g., Token Plan AI 模型订阅计划 → console manual)

Step -1.5.3: Any partial/false hit → immediately explain to the user + take the fallback_route
  ⚠️ Your reachability summary to the user MUST explicitly name each console-only / manual product (e.g. Token Plan AI 模型订阅计划). Do NOT summarize only the CLI-reachable products (e.g. "ECS / VPC / RDS / OSS 全部可达") while silently dropping the manual one — omitting it leaves the user with an incomplete deployment.
  User-facing copy template (friendly + plain metaphors, no technical jargon):
    "你这个套餐里有 ${产品比喻名}（${正式名}），这部分目前没法用 CLI 一键开——
     需要你去 ${控制台/分享链接} 手动开一下，开完告诉我，我接着把剩下的资源装好。
     ${fallback_route 链接}"

  Typical fallbacks:
    - Token Plan AI 模型订阅计划 (false) → share link https://bailian.console.aliyun.com/?tab=app#/api-key (user self-enables)
    - PDS Alibaba Cloud Drive Enterprise (partial) → purchase page https://common-buy.aliyun.com/?commodityCode=pds_trc_public_cn&regionId=cn-beijing (primary account only; sub-accounts lack permission). This is the SAME link the sku-params yaml steps already hand out. Do NOT send the user to https://pds.console.aliyun.com/ to enable it — that console is for managing an ALREADY-active drive, same trap as the ESA row in the capability matrix.
    - ESA (all tiers) → **fully CLI-provisionable, do NOT send the user to the console for it.** An earlier
      version of this line claimed the ESA medium promo required the console "because PurchaseRatePlan has no
      RuleDescId parameter". The premise is true but the conclusion was WRONG and is now corrected
      (re-verified 2026-08-26, read-only): the discount does not need to be passed at all — it is applied
      **server-side from the account's own eligibility**. `esa describe-rate-plan-price --plan-name medium`
      returned `TotalPrice 375.0 / DiscountPrice 255.0 / Price 120.0` with rule `RuleDescId 20958767`
      「产品新用户专享优惠，限购1个」 attached, without any promo argument. So `purchase-rate-plan` reaches the
      same discounted price the console would. Two consequences: ① never quote a fixed ESA promo price —
      eligibility is per-account, so another account may pay the full ¥375; inquire every time.
      ② passing `--rule-desc-id` is pointless and invisible — the CLI **silently drops** it (and every similar
      spelling) from the request rather than erroring, so a yaml that "passes the promo id" is lying to you.
      The console fallback_route stays valid only as an `fallback_manual` for when the API call itself fails.
    - OSS storage package (partial) → https://common-buy.aliyun.com/?commodityCode=ossbag&regionId=china-common
      ⚠️ ANNOUNCE ONLY HERE — this is the one manual item that does NOT stop and wait at -1.5. Naming it in
      the reachability summary is enough; the blocking confirmation belongs to Step 1.3 in
      `confirm-authorize.md`, alongside the resource list and the total. Stopping here would send the user
      off to buy something before they have seen the plan or the price.
      Why it is partial at all: buying the package also activates OSS, and OSS MUST be activated before any
      bucket call — an unactivated account passes every read-only OSS call and only fails at the first write
      (403 UserDisable), so the Step 0.2b probe cannot catch it.
      The buy page presets 同城冗余 and its selections do not travel in the URL, so no preset link is
      possible; the field-by-field picks live in Step 1.3.

Step -1.5.4: Wait for the user to confirm the manual step is done → continue to Phase 0
  In state, mark manual_steps.<product>: { opened_at: ..., user_confirmed: true }
  ⚠️ NEVER discover the SKU is unworkable only after Phase 0 credential config — this gate must be up front.
```

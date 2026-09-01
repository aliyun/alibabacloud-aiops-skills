# Phase 1: Confirm + authorize

> Runs after Phase 0.4 image resolution, before Phase 2. The SKU was already settled in Phase -2
> (`sku-resolution.md`) — this phase does NOT re-identify it.
>
> - **Entry**: SKU settled, credential green, policy probe passed, image locked.
> - **Exit**: resource list shown + component removal handled + **payment second-confirmation obtained** +
>   Step 1.5 self-check all green → go to Phase 2 (`network.md`).
> - This phase owns the money conversation. Nothing here creates a resource.

```text
Step 1.2: Load the parameter file (default)
  starter_webui → default to references/sku-params/starter_webui.yaml (ECS primary path)
  other SKUs → references/sku-params/<sku>.yaml

Step 1.2.5: starter_webui / starter_app price-inquiry gate (SWAS fallback deprecated)
  ① First inquiry (promo config: 3 Mbps fixed bandwidth):
    aliyun ecs describe-price --profile opc --biz-region-id cn-beijing \
      --resource-type instance --instance-type ecs.e-c1m1.large \
      --price-unit Year --period 1 \
      --system-disk-category cloud_essd_entry --system-disk-size 40 \
      --internet-charge-type PayByBandwidth --internet-max-bandwidth-out 3 --amount 1
    ⚠️ Note: DescribePrice accepts PriceUnit=Year + Period=1;
       but RunInstances at creation MUST use PeriodUnit=Month + Period=12 (the two APIs use different param formats!).
       Passing PeriodUnit=Year to RunInstances errors with InvalidPeriodType.ValueNotSupported.

  Parse the result:
    Check whether Promotions.Promotion[] contains RuleId=20906709 with TradePrice ≈ 99.0
    ① hit → silently continue on the starter_webui.yaml (or starter_app.yaml) ECS promo path
       show the user: "询价确认 ✓ 这次能拿到 ECS ¥99/年活动价（命中 RuleId=20906709）"
       ⚠️ Do NOT pass PromotionOptions.RuleId to RunInstances — the RunInstances API has no such parameter and the CLI rejects it ("is not a valid parameter or flag"). The economy-e ¥99/yr long-term promo applies automatically on the API creation path for eligible accounts; the DescribePrice RuleId=20906709 hit above only confirms eligibility. Verify the actual charge in the order/summary after creation.

    ② miss (TradePrice > 99 or no Promotion hit) →
       **no longer fall back to SWAS ¥45/month** —
       read the fallback_ecs_config field from the advisor prescription (without advisor context, use deploy's
       built-in defaults: InstanceType=ecs.e-c1m1.large / 40G cloud_essd_entry system disk /
       PayByTraffic + 100 Mbps peak — same values as the advisor contract), immediately run a second inquiry (pay-by-traffic + 100M peak):

       aliyun ecs describe-price --profile opc --biz-region-id cn-beijing \
         --resource-type instance --instance-type ecs.e-c1m1.large \
         --price-unit Year --period 1 \
         --system-disk-category cloud_essd_entry --system-disk-size 40 \
         --internet-charge-type PayByTraffic --internet-max-bandwidth-out 100 --amount 1

       Expect TradePrice ≈ 284.99 (Beijing); >20% deviation is a hard stop.
       After getting the price, present the fallback option AND run the PAYMENT GATE (Hard Gate #1) on this path too — the closing question below IS the charge authorization, not a config toggle:

       "我刚试着询价了一下：这次没拿到 ¥99/年优惠（成交价是 ¥XXX）。
        多半是因为你之前在阿里云用过同类优惠（云服务器包1年99元每用户限1台）。

        给你切到一个按流量计费的备选配置：
        → ECS 经济型e · 2核2G · 40G ESSD Entry 系统盘
        → **按使用流量计费 + 100Mbps 峰值带宽**（类似手机流量套餐——不用包月，按实际用量算）
        → 年费 ¥284.99/年（约 ¥23.75/月，北京已询价确认）
        → 部署完成后我会自动帮你装一个出流量告警（CloudMonitor），防止万一被刷流量账单跳

        💡 价格供参考，实际以最终下单为准。

        🌐 网站端口（80/443）将对公网开放，互联网上的访客都能访问你的站点；远程登录（SSH）只对你自己的 IP 开放。
        即将从你的阿里云账户扣款 ¥284.99（包年/包月），确认付款？"

       ⚠️ Do NOT self-continue into creation. After emitting the prompt above, STOP and wait; proceed to network setup / RunInstances ONLY after the user replies with an explicit charge authorization. Presenting the fallback config is NOT authorization, and the promo-miss explanation is context, NOT authorization — this is exactly the spot a weak model wrongly skips (it runs RunInstances autonomously without ever emitting this prompt). The amount ¥284.99 must be the actual second-inquiry TradePrice.
       user explicitly authorizes the charge → switch to the fallback yaml (the variant=traffic_fallback branch inside starter_webui.yaml, or a separate starter_webui_traffic.yaml); the RunInstances params MUST **exactly match** the second inquiry (close the "inquiry ¥284.99 → actual charge ¥1988.39" gap)
       user declines / has not authorized yet → go back and let the user re-pick a tier via advisor or decide themselves, **no second fallback to SWAS**

       Phase 4 auto-adds a CloudMonitor outbound-traffic alarm (threshold 50GB/day):
       aliyun cms put-metric-rule-targets --rule-id opc-${ecs_instance_id}-traffic-alarm ...

    ③ the inquiry itself returns no price (Throttling.User / 429 / 5xx, or a parameter error that survives the
       single cli-meta correction) → there is NO price, therefore there is nothing to authorize. Do not grind for one.
       Budget is iron-rule #26: call #1 + exactly one retry = 2 calls, at most one sleep of ≤15s, then STOP.
       Forbidden on this branch: escalating backoff (sleep 15 → 45 → 60 is 4 calls against one goal, 2× over the cap);
       switching call form to get a different answer (a 200 from a form the failed call did not use is iron-rule #35's
       silent-false-green, not a price); and quoting the yaml's static monthly figure as a stand-in, which is a
       fabricated price. This branch has a real exit — the deployment stays resumable. Emit this and stop:

       "刚才查价格没成功：询价接口这会儿在限流，是服务端侧的临时状况，不是你账号的问题。
        我按规矩只重试了一次就停下了，没有反复刷接口。

        现在的状态：没有创建任何资源，也没有产生任何扣款。
        你选的套餐和地域我都记着，随时可以接着做。

        你说一声「继续」，我就从查价格这一步往下走。
        如果一直查不到，也可以开工单：https://smartservice.console.aliyun.com/service/create-ticket"

       ⚠️ Never cross the PAYMENT GATE without a price you just obtained live. No price → no authorization request.
       ⚠️ The SKU / region / config settled in the earlier phases are already in state, so a later 「继续」 resumes
          at this step instead of restarting Phase 0.

Step 1.3: Show the resource list + confirm
  Display in plain language using the final chosen yaml's user_summary field.
  Always include "💡 价格供参考，实际以最终下单为准" + when a promo is hit, append "以下单时活动可用性为准".
  Component-removal opt-out gate (deploy-side backstop, does not depend on advisor context):
    The SKU name does not carry the component removals negotiated on the advisor side, so proactively backstop here to avoid provisioning resources the user already declined (wasting money).
    Removable-component mapping (only items that actually create CLI resources and affect billing):
      - lite_seed / lite_growth / lite_traction / pro_steady / pro_burst → swas-openclaw (the "AI 助理那台", the SWAS instance)
      - starter_webui / starter_app → no CLI-removable item (qwcn-pro is a desktop tool, handled in Phase -1.2, creates no cloud resource)
    Handling logic:
      ① context/visible prescription already shows the user removed an item (e.g. the advisor prescription wrote "已去掉 AI 助理那台")
         → pre-apply directly: skip that yaml step + deduct from the list and quote, only inform "已按你之前的选择去掉 AI 助理那台", do not re-ask.
      ② no removal signal (cross-session / deploy-only / user did not mention) → for a SKU containing a removable item, proactively give one opt-out:
         "你的套餐里含 AI 助理那台（云上常驻运维助手 OpenClaw）。
          如果你已经有自建的云上运维 agent，可以去掉这台省钱；需要保留吗？"
         user answers remove → skip the corresponding yaml step (e.g. SWAS CreateInstances) + re-inquire price (deduct that component) + mark state removed_components: [swas-openclaw] (teardown/later management recognizes it)
         user answers keep / default → create everything
    ⚠️ Removal must complete **before** the payment second-confirmation below, so the price shown at second-confirmation is the post-removal final price.
  **Split the list into 自动 / 手动 — and do NOT gate on the manual half here.**
  Every SKU's resource list MUST be presented as two clearly separated blocks, because the two halves have
  different money semantics and different execution timing:

  我自动帮你开（这些会从你账户扣款，逐笔列在下面）：
    ✦ …（每行：比喻名（正式名） → 金额 + 计费周期）
    本次由我代扣：¥X

  需要你自己开（不在本次扣款内，我会带着你一步步弄）：
    ✦ AI 能力（Token Plan AI 模型订阅计划）… → 你自己在页面买
    ✦ 存储空间（阿里云盘 PDS）… → 你自己在页面买
    ✦ 大仓库的存储包（OSS）… → 你自己在页面买
    你自己另买：¥Y

  **Execution order (this is the whole point — do not reorder it):**
  1. 先把「自动」那半**全部创建完**（Phase 3 的付费流程，受 PAYMENT GATE 管辖）。
  2. 再回头**逐个引导用户开「手动」那半**，PDS / OSS 给到字段级的具体指引（下面两段）。
  3. **用户明确说 OSS 开好了之后**，才去建桶（Phase 3 的建桶步骤，见 `provision.md` 的 Step 3c）。

  ⚠️ **手动项在本步骤只是「交代清楚」，不是通行闸。** 用户此刻回「先不买 / 晚点买」完全正常：记录下来、一行确认、
  **继续走付款确认和自动资源创建**。把手动项当成付款前置会堵住整条流程，
  而且会让用户在还没看到方案和总价时就被推去买东西。

  Self-purchase item — OSS storage package (only for SKUs that contain OSS: lite_seed / lite_growth /
  lite_traction / pro_steady / pro_burst):
    OSS has no CLI purchase channel AND must be activated before any bucket call, so it is the user's own
    one-click step. List it in the 手动 block above with its price, and give the field-by-field instructions
    below **once**. Then move on — the blocking check lives at the bucket step, not here.
    ⚠️ A preset link is impossible: the page defaults to 标准-同城冗余 and its selections do not travel in
    the URL. So spell out every pick, field by field, and never just paste the link:
      "OSS 存储包这一笔要你自己在页面上买一下（买的同时就把 OSS 开通了，一步到位）：
       https://common-buy.aliyun.com/?commodityCode=ossbag&regionId=china-common
       打开后按这几项选，其它保持默认：
       ① 商品类型：OSS 资源包
       ② 资源包类型：标准 - 本地冗余存储 ← 页面默认是「同城冗余」，一定要改，选错了抵扣不到等于白买
       ③ 地域：中国内地通用
       ④ 规格：${40 GB · 约 ¥9/年 | 500 GB}
       ⑤ 购买时长：1 年
       买完回来跟我说一声。我先把能自动开的都装好，到建仓库那一步再用得上它。"
    Spec per SKU: lite_seed / lite_growth / lite_traction → 40 GB; pro_steady / pro_burst → 500 GB.
    Why 本地冗余 is mandatory: a package only offsets the storage type it names (the buy page says so under
    抵扣规则 and each type's 场景描述), and every sku-params yaml creates LRS buckets.
    If the user says they already have OSS activated with enough quota, accept it and move on — never make
    them buy a second package.
    ⚠️ **Say it once, then stop asking.** The instruction block above is emitted **one
    time**. Record the outcome in state (`self_purchase.oss_package` = `bought` | `already_active` |
    `deferred`) and **never re-issue the block or re-ask in later turns**:
      - bought / already active → mark it and proceed.
      - 「先不买」/「晚点买」/「等一下再说」 → mark `deferred`, acknowledge in ONE line
        (`好，OSS 这笔你晚点买。我先把能自动开的都装好，到建仓库那步再提醒你一次。`) and **continue** —
        a deferred OSS package does NOT block the payment gate, the network step, or any automatic creation.
      - the ONE permitted re-mention is at the bucket step in `provision.md` (Step 3c), and only when the
        state is still `deferred`.
    Repeating the full purchase block, or re-asking 「买了吗」 across turns, is this rule's violation.
  **Payment second-confirmation logic**:
    After showing the resource list, the first confirmation only confirms creation intent ("确认开始创建？").
    Before entering Phase 3 to run RunInstances/CreateInstances (i.e., before the actual charge),
    a second explicit payment confirmation is required:
      "🌐 网站端口（80/443）将对公网开放，互联网上的访客都能访问你的站点；SSH 只对你自己的 IP 开放。
       即将从你的阿里云账户扣款 ¥XX（[计费周期说明]），确认付款？"
    user answers "确认" → execute creation
    user answers no → pause, ask why
    **Exception**: if the API returns InsufficientBalance, no second confirmation is needed —
    directly tell the user the top-up amount + link, then re-execute after top-up.

    ⚠️ **Multi-order SKUs (Lite / Pro): ¥XX is a total that will be charged as N separate orders.**
    Only starter is one paid call. For every SKU with more than one paid product, before asking for
    authorization you MUST:
      a) run each product's own DescribePrice (ecs / swas-open / rds / oss …) and list one line per paid
         order with its amount + billing period — never estimate, never reuse the yaml `monthly_price`
         marketing string;
      b) **write the addition formula out loud** — a plain-text line like
             `70 + 783.64 + 1262 + 54 = 2169.64`
         placed just above the payment prompt, so both you and the user can eyeball whether the sum
         equals the ¥XX in the prompt. This is an emitted step, not a mental check:
         the earlier "amounts must sum to the ¥XX" phrasing was routinely skipped and produced a
         ¥54-off total that only the user caught. **If the formula doesn't equal ¥XX, DO NOT edit the
         total to match; re-run DescribePrice for every line and rebuild the list from scratch.**
      c) **the total is ALWAYS re-summed from the current DescribePrice results** — never sourced from,
         nor patched against, the yaml's `monthly_price` field or any other static reference. Those
         numbers exist only for advisor's sizing conversation; the payment total is a live-inquiry sum.
         On any correction (removed component, refreshed price), throw away the old total and re-add the
         current line items — do NOT do `old_total ± delta` (patching the static
         ¥2524.55 by +¥54 yielded ¥2578.55, ¥60 off the true ¥2518.50).
      d) if the payment list mixes billing cycles (monthly + annual + pay-as-you-go), keep each line
         labelled inline (`/月` vs `/年` vs `按量`) and DO NOT collapse them into a single unlabelled
         total; annual amounts must not be summed with monthly amounts as if they had the same unit.
      e) say plainly that these are separate orders charged one by one (e.g. "这几笔是分开下单的，会一笔
         一笔扣，每扣一笔我都会告诉你"), so the user is not surprised by several deductions;
      f) note that renewal is also per-order (they expire and renew separately).
    The user may prefer one bundled order via the OPC purchase page — that is a legitimate alternative to
    offer if they ask, but never a way to skip this confirmation.

Step 1.4: Determine the region
  Default: cn-beijing
  user specifies another → use the specified value

Step 1.5: Pre-execution hard-gate self-check (HARD BLOCK · every item must pass before Phase 3)
  ⚠️ This self-check is a hard gate, not a soft hint, not a "suggested review".
     Any item not passing → stop immediately, discard the current execution plan, forbid calling any create/charge API;
     first return to the corresponding Phase to fill the gap, then re-run this self-check; only enter Phase 3 when all pass.
     NEVER "just create it first".
  [ ] 1. SKU settled and one of the legal 7 (else back to Phase -2 / advisor)
  [ ] 2. Phase -1.5 CLI-reachability gate passed; partial/false items went through fallback and were user-confirmed
  [ ] 3. Step 0.2b policy coverage probe run for THIS SKU's product set and all-green (no 403 / NoPermission / Forbidden.RAM outstanding)
  [ ] 4. credential profile type = RamRoleArn (verified via aliyun configure list); AK/SK never read/echoed throughout; one profile pinned for the whole run
  [ ] 5. resource list + monthly price shown, with the "💡 价格供参考，实际以最终下单为准" disclaimer appended
  [ ] 6. payment second-confirmation obtained ("即将扣款 ¥X，确认付款？" the user explicitly answered confirm; insufficient-balance top-up path excepted)
  [ ] 7. starter inquiry: the RunInstances order params exactly match the final DescribePrice params (close the inquiry↔charge gap)
  [ ] 8. out-of-scope requests hard-rejected per iron-rule #23 built-in scope cannot_do and pointed back to the desktop AI assistant (if any)
  [ ] 9. component-removal opt-out handled: a SKU with a removable item (Lite/Pro's "AI 助理那台") was pre-applied per context or given one opt-out; the final to-create set matches the quoted monthly price
  [ ] 10. OSS-bearing SKU (lite_* / pro_*): the OSS storage package was **listed in the 手动 block and its field-by-field instructions given once**, and `state.self_purchase.oss_package` carries a resolved value (`bought` / `already_active` / `deferred`). **`deferred` PASSES this item** — it does not block Phase 3. Rationale: an unactivated account cannot be detected by any read-only call (every read succeeds; only the `PutBucket` write returns 403 UserDisable), so the real check can only live AT the bucket step (`provision.md` Step 3c), and gating Phase 3 on it here would stall the whole deployment over one optional storage package (E2E-measured).
  [ ] 11. the authorized total covers ONLY the orders THIS skill charges. Self-purchase items (Token Plan / PDS / the OSS package) sit in their own `另需你自己购买（不在本次扣款内）` block and are NOT inside the addition formula, and the two figures were stated apart (`本次由我代扣：¥X` vs `你自己另买：¥Y`). A `type: manual` yaml step never enters the total.
  [ ] 12. every message sent so far in this session passes the language + terminology check: Chinese prose throughout, and no internal label (Phase / Preflight / Gate / probe / 探针 / RamRoleArn / AssumeRole / STS / StsToken / bootstrap / iron-rule / state file / yaml) leaked into user-facing text. If any earlier message leaked, do not silently continue — restate that part in plain Chinese now.
```

# OPC Cloud Advisor Self-Check Checklists

## Universal Checklist (must pass before every output)

- [ ] Does the full text contain any bare use of ECS / RDS / OSS / ALB / ESA / VPC / PDS technical terms? (Must use `「plain-language role」(cloud product name)` format)
- [ ] Does **c9i / g9i / r9i** or any ECS series name appear? (Never allowed — only say specs like "ECS 2-core 4 GB")
- [ ] Does it **list multiple SKUs for the user to choose from**? (Must give exactly one precise recommendation)
- [ ] Are prices taken as exact values from the SKU matrix, or made up from memory? (Must take fixed values from the table)
- [ ] **Are prices qualified with "approximately" / "starting from" / "reference"?** (Forbidden — must quote exact amounts)
- [ ] **Does every SKU quotation include the `「💡 价格供参考，实际以最终下单为准」` disclaimer?** (Iron Rule #12)
- [ ] **Do promotional prices (e.g., ECS ¥99/year, ESA medium ¥99) add "subject to promotion availability at time of order"?**
- [ ] **Does the prescription section include A/B dual-path closing?** (Iron Rule #14: A = let me place the order / B = self-service at opc.aliyun.com/products)
- [ ] **Does Path B give the exact card name?** (4 main cards: `网络名片版` / `AI 应用版` / Lite / Pro)
- [ ] **Does Path B mention which default checkboxes to keep/remove?** (e.g., starter_webui: "if using Cursor, uncheck the default QoderWork ¥59/month")
- [ ] **Does user-facing copy expose internal terms like "deploy tool" or "deploy agent"?** (Iron Rule #14: forbidden)
- [ ] **Has domain pricing been stripped of hardcoded values?** (Unified: "prices vary by suffix")
- [ ] **Does the upgrade prompt point to console/assisted path, not purchase page?** (Cross-tier upgrades go through ECS/RDS console, not re-purchasing)
- [ ] **Is Token Plan upgrade advice included?** (All Token-containing SKUs must include: Standard → Advanced → Premium. **Forbidden: "takes effect instantly" marketing — must show current vs new monthly cost, then user confirms**)

### Security Awareness Check (F-Group, 6 items)

- [ ] **F-01 Security triage**: Asked "Will your product involve users **registering accounts or making payments**"? If yes, does the prescription include the "Data Security Hardening" section (forced HTTPS + recommend upgrade to lite if payments + privacy policy page)?
- [ ] **F-02 Asset inventory passback**: Does the prescription footer include the `metaphor ↔ Alibaba Cloud official name` cross-reference list? Only listing resources actually in the current SKU?
- [ ] **F-03 Emergency three-step card is NOT an advisor output**: The incident card (disable AK / ActionTrail audit / submit ticket) is owned by the downstream `alibabacloud-opc-deploy` skill (iron-rule #19) — advisor prescriptions must NOT render it.
- [ ] **F-04 Region selection asks data compliance**: Before choosing region, asked "where are your users mainly located" (mainland / overseas / both)?
- [ ] **F-04 Domain suffix hard cross-check**: User with .io/.dev/.app/.me suffix + selected mainland China region → hard blocked with alternative?
- [ ] **F-05 Regular backup reminder**: Under "When to Upgrade" section, includes `「📦 重要数据建议定期备份」`?
- [ ] **F-06 SSL renewal script**: When HTTPS is involved, gives appropriate script by certificate source (free cert = auto-renews / custom cert = expiry date + manual renewal reminder)?
- [ ] **Credential linkage**: When advisor guides credential setup, **does NOT** write "prepare your AccessKey ID and Secret" or any permanent AK wording? (Unified: points to deploy-phase RamRoleArn temporary credentials flow)

### UX Softening Check (5 user-facing copy rules)

- [ ] **System disk phrasing unified**: "X GiB system disk" (first mention adds `类似你电脑的系统盘`)? No ESSD / PL0 / Entry / SSD / cloud-disk technical terms?
- [ ] **OpenClaw placement**: starter_webui / starter_app copy does NOT mention OpenClaw? (Starter does not include OpenClaw path)
- [ ] **SSH wording**: lite/pro copy about server login uses `登录到服务器` + appends `通常由 OpenClaw 帮你操作，你不用自己敲`? Starter shows no login info?
- [ ] **SWAS network script**: Host lightweight plan states `200Mbps 峰值带宽 · 套餐内含流量，不另收费（类似手机流量套餐）`?
- [ ] **ECS network script**: States `100Mbps 峰值带宽 · 流量按使用量计费，每月送 220GB 免费额度（类似手机流量套餐——超出免费额度才计费）`?
- [ ] **RDS storage**: User-facing unified as `XGB 数据存储空间` — no general_essd / ESSD literals?
- [ ] **OSS Endpoint**: User-facing step report shows only bucket name, no Endpoint / internal Endpoint exposed?

## Branch A Specific Checklist

- [ ] **Top-level entry determination done?** (A1 vs A2 must be classified first — cannot skip)
- [ ] A2 branch **launch-readiness validation done?** ("Already published vs local demo" confirmed)

## Starter Specific Checklist

- [ ] **Starter: Q6 (AI) is inferred from keywords (chat/bookkeeping/resume = text AI → `starter_app`; no AI signal → `starter_webui`); the deprecated "have you used promotions before" question is NOT asked (deploy-side pricing handles it). Only ask one question if AI usage is genuinely ambiguous — otherwise 0 blocking questions for starter.**
- [ ] **starter_webui default recommends ECS Economy e + QWCN Pro + ESA Free?**
- [ ] starter_webui disclaimer section uses unified wording? (`「ECS ¥99/年如果没命中，我会自动给你切到按流量计费的备选配置 ¥284.99/年（北京），同时帮你装一个出流量告警防过冲」` — never expose deploy tool names)
- [ ] starter_webui Path B mentions "self-service page only has the ¥99/year option; ¥284.99/year pay-by-traffic fallback is auto-applied by deploy" limitation? (Only when user asks or clarification needed; normally Path B does not proactively state this — Path A handles it)
- [ ] YAML output **does NOT** have a `variant` field? (variant is determined by deploy-side pricing result — advisor no longer outputs it)
- [ ] **starter_app includes Token Plan Standard + PDS 200 GB?** (product calls AI)
- [ ] **Does NOT recommend OpenClaw / SWAS to Starter users (unless deploy-side pricing activates fallback)?**
- [ ] **Does NOT recommend OSS static hosting to Starter?** (starter_static path deprecated)
- [ ] For users with Codex/WorkBuddy etc., does Path B clearly state "can uncheck the default QoderWork ¥59/month"?

## ECS Sizing Checklist (Lite/Pro)

- [ ] **Only said "ECS X-core X GB"** — no series name mentioned?
- [ ] **Simultaneous users phrasing correct?** (`高峰期那一分钟内同时打开` + everyday-life anchor)
- [ ] **No QPS / concurrency / TPS technical terms used?**
- [ ] **Second clarification done when answer is high or spans tiers?**
- [ ] **Post-mapping scaling path mentioned?** (upgrade or add instance; ECS supports live migration)
- [ ] **Lite ECS spec matches correctly?** seed=2-core 4 GB / growth=2-core 4 GB (no upgrade!) / traction=4-core 8 GB
- [ ] **Lite RDS spec matches correctly?** seed=1-core 2 GB / growth=2-core 4 GB / traction=4-core 8 GB
- [ ] **Pro spec**: steady=4-core 8 GB ×2 / burst=8-core 16 GB ×2–3 (auto-scaling)
- [ ] **Path B configuration adjustment notes complete?** (lite_growth=change RDS / lite_traction=change ECS+RDS / pro_burst=change ECS+enable auto-scaling)

## A2 Specific Checklist

- [ ] **"How to migrate" section has 3 steps?** (Purchase → Deploy/migrate data → DNS switchover)
- [ ] **Migration-period notes given by scenario?** (ICP filing/service-account whitelist/data backup/grayscale)
- [ ] **Tier-jump determination doesn't make decision for user?** (Sensitive signals go into upgrade-trigger §5 — never forcibly change tier)
- [ ] **"Keep old platform running a few days as fallback" mentioned?**

## Red Lines (any single violation = output must be rejected and redone)

- [ ] **No c9i / g9i / r9i / SAE or other technical jargon appeared?**
- [ ] **Did NOT recommend OpenClaw / OSS static to Starter?** (These paths deprecated; starter_webui SWAS fallback is the exception)
- [ ] **Did NOT use "branch store offloading traffic from main store" or similar wrong metaphors?**
- [ ] **Did NOT list multiple SKUs / multiple plans for user comparison?**
- [ ] **Did NOT fabricate prices (must take exact values from the SKU matrix)?**
- [ ] **Did NOT use "approximately" / "starting from" vague pricing words?**
- [ ] **Did NOT omit the `「💡 价格供参考，实际以最终下单为准」` disclaimer?**
- [ ] **Did NOT force a SKU beyond OPC scope?** (Local model running/GPU/50+ person company → output boundary notice)
- [ ] **Did NOT write lite_growth ECS as 4-core 8 GB?** (growth ECS = 2-core 4 GB; only RDS upgrades)
- [ ] **Did NOT recommend pro_geo?** (Deprecated — only steady/burst remain)
- [ ] **Did NOT quote Pro monthly price as ¥2607/¥3351 (old values)?** (Updated to ¥2524.55/¥3258.19)
- [ ] **User-facing copy does NOT contain "deploy tool" / `由 deploy 自动...` or other internal terms?**
- [ ] **Prescription section does NOT omit A/B dual-path closing?**
- [ ] **Domain prompt does NOT hardcode prices** (e.g., `¥55/年起`)? (Unified: "prices vary by suffix")
- [ ] **Did the agent resolve the 2 high-stakes fields (Q-scale, Q-userdata) — asked via `AskUserQuestion` when the prompt lacked the signal, or used the stated signal — and fill all 7 internal fields (2 asked + 5 inferred) before producing the prescription?** (Forbidden: fabricating a missing Q-scale/Q-userdata instead of asking — `inferred from user prompt` for a high-stakes field without a stated signal is a hard violation. Q4/Q5/Q6 MAY be inferred and surfaced as assumptions.)
- [ ] **Were vague-quantifier / refusal answers handled via second-clarification or the conservative/elastic binary choice before SKU mapping?** (Forbidden: silently defaulting to a mid-tier without surfacing the assumption)
- [ ] **Did the agent respect the absolute block — no single-turn prescription?** If Q-scale/Q-userdata was not resolvable from the prompt, the first turn MUST contain ONLY the `AskUserQuestion` call(s) and no SKU/prescription. A prescription in the first turn is allowed ONLY when the prompt states both Q-scale and Q-userdata signals.
- [ ] **If the user questioned a SKU component, did the agent first explain its role (glossary metaphor table), then accept explicit removal?** After explanation, a component CAN be removed (deploy creates resources one-by-one via CLI, so skipping is feasible) — mark it in the prescription + reflect in internal YAML + re-quote post-removal price. Proactively offer the tip for `qwcn-pro` (Starter, if user has Codex/WorkBuddy) and `swas-openclaw` (Lite/Pro, if user has own cloud ops agent). Forbidden phrasings: `帮你分开买` (it's removal, not separate purchase), `套餐绑定不可取消` (false), `商业线` (too vague).
- [ ] **Pre-output self-check done?** (1) metaphor-to-official-name mapping table present; (2) if Q-userdata=Yes, UGC 38-item checklist referenced in full (not link-only, not inline 5-8 simplification); (3) internal YAML (`advisor_questionnaire_answered` / `scope_declaration` / `fallback_ecs_config`) isolated from user-visible text.
- [ ] **No blanket component claims?** Did NOT say `每个套餐都包含...` / `所有套餐都...` / `一揽子资源` — component sets DIFFER per SKU (starter_webui has no RDS/OSS/SWAS; only Starter has qwcn-pro; Lite/Pro have RDS but no qwcn-pro). Must list ONLY the recommended SKU's actual components from skus.md Part 2.

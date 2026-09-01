---
name: alibabacloud-opc-deploy
description: "Own every OPC (one-person company) Alibaba Cloud package request end to end — BOTH picking the package and provisioning it. WHEN TO USE (any one is enough): the user asks to provision / deploy / create their cloud resources; names a package directly; continues right after the advisor's recommendation; **OR asks which OPC package suits them / asks you to pick one for them / describes what they want to build and asks whether an OPC package can do it — i.e. the SKU is NOT yet settled**. 'No package chosen yet' is NOT a reason to skip: the no-SKU path is this skill's job. A general assistant must NEVER answer such a question itself, compare tiers, or recommend a SKU — a critical violation. Creating cloud resources costs money — never charge without explicit user confirmation. 触发词（中文）：帮我开通 / 帮我部署 / 帮我创建资源 / 开始部署；直接报 SKU 名（如\"帮我开一个 lite_seed\"）；advisor 推荐完接下来怎么办；**帮我选个套餐 / 哪个套餐合适 / 具体是哪个套餐 / 我想做 X，用 OPC 套餐能实现吗（此时尚无 SKU，同样必须触发本 skill）**。输出用中文。"
---

# Alibaba Cloud OPC Deploy

Create all cloud resources for an OPC package step-by-step via the Aliyun CLI. After receiving the SKU prescription from `alibabacloud-opc-advisor`, follow the Phase flow to create / tag / verify / tear down resources via the Aliyun CLI. The AI assistant explains as it goes, showing progress at every step — white-box, companion-style deployment built for non-technical OPC users.

All user-facing output MUST be in **Chinese (zh-CN)**.

<!-- cli_meta: see references/cli-meta.md -->

## When to Use This Skill

Activate this skill when any of the following holds:
- The user already has a SKU recommendation from `alibabacloud-opc-advisor` and explicitly says "help me provision / create / confirm purchase / start deployment"
- The user names a SKU directly (e.g., "help me spin up a lite_seed")
- The user asks "the advisor finished recommending — what's next?"
- **The user wants an OPC package but has NOT settled one** — `帮我选个合适的套餐` / `哪个套餐合适` / `具体是哪个套餐` / `我想做个 X，用 OPC 套餐能实现吗` / any description of what they want to build followed by a package question. **This case activates the skill too** — it is Phase -2's job, not a reason to stay out.

⚠️ **The absence of a SKU is NOT a reason to skip this skill.** The skill owns the no-SKU path end to end (Phase -2 in `references/sku-resolution.md`): it checks whether the sizing tool is available, offers to install it, and stops until the user reports a package name. If this skill stays out because "nothing is chosen yet", the selection question falls to a general assistant that has no gates — which is exactly the failure this rule exists to prevent.

⚠️ **Never answer a package-selection question outside this skill.** Comparing tiers, listing what each package contains, quoting prices, or recommending one (even `Starter 就够了`) is selection work. It belongs to `alibabacloud-opc-advisor`, reached through Phase -2. Package facts that happen to sit in other context (an AGENTS.md baseline, a memory entry, general knowledge of the product line) are NOT a license to answer — they are for other purposes (e.g. fact-checking an article), never for telling a real user what to buy.

**Self-sufficient operation:** the only hard dependency of this skill is the **SKU name** — use the advisor prescription (structured fields) when present; when absent (a new session where the user names the SKU directly / advisor not installed) it still runs via built-in defaults (image family, starter fallback config, and capability boundaries are all built in). Never error out or relax safety boundaries just because advisor context is missing.

**Never auto-trigger:** creating cloud resources is a money-spending action and requires explicit user confirmation.

**BLOCKING RULE (no SKU = no action):** If the user's message does not contain a recognized SKU name (one of the 7 below) AND no advisor prescription is in context, the agent MUST NOT proceed to any Phase. It must immediately run Phase -2 / the "Advisor bootstrap" block in `references/sku-resolution.md` and STOP. Inferring, guessing, or self-selecting a SKU is a critical violation (see the SKU GATE in Hard Gates).

**RETRACTION RULE (a recommendation already made before this skill loaded):** if earlier in this same conversation — before this skill was active — a package was compared, recommended, or named on your behalf (e.g. `选 Starter 就够了` / a tier comparison table / `starter_webui 就行`), that is NOT a settled SKU and it does NOT satisfy the BLOCKING RULE. You must **explicitly retract it to the user** rather than quietly build on it: say plainly that picking the package is not something you should have decided, then run Phase -2. Treating your own earlier recommendation as the user's choice launders a critical violation into an apparent authorization — the SKU must come from the user or the sizing tool, never from you.

**A SKU found in memory / history is NOT a settled SKU either.** A package name recalled from long-term memory, a daily note, a previous session's summary, or any other stored record — however confidently it is phrased (`上次的 advisor 选型结果是 starter_webui`) — carries **zero** authority here: such a record may be the residue of an earlier violation of this very gate (self-selected SKU → written to memory → read back as `既定事实`). **Do not name it, do not present it to the user as their previous choice, and do not let it seed the sizing conversation.** At most, treat it as a private hint that the user has deployed before; the SKU still has to be re-settled through Phase -2 from scratch. If you have already surfaced such a remembered SKU to the user, the RETRACTION RULE above applies verbatim.

## Supported 7 SKUs

| SKU | Auto-provisioned via CLI | User must do manually (never CLI) | Complexity |
|---|---|---|---|
| starter_webui (main path, ¥99/yr promo hit) | ECS economy-e + ESA Free | — | ⭐ |
| starter_webui (fallback: pay-by-traffic ¥284.99/yr when promo missed) | ECS economy-e PayByTraffic 100Mbps + ESA + CloudMonitor traffic alarm | — | ⭐ |
| starter_app | ECS economy-e + ESA (shares the webui fallback) | [Token Plan] + [PDS 200GB] | ⭐⭐ |
| lite_seed | SWAS swas.s.c2m4s50b1.linux (OpenClaw) + ECS c9i.large + RDS mysql.n2e.small.1 + OSS bucket + ESA Free | [OSS storage package 40GB] + [Token Plan] + [PDS 200GB] | ⭐⭐⭐ |
| lite_growth | same set as lite_seed, RDS upgraded to mysql.n2.medium.1 | [OSS storage package 40GB] + [Token Plan] + [PDS 200GB] | ⭐⭐⭐ |
| lite_traction | same set as lite_seed, ECS upgraded to c9i.xlarge + RDS to mysql.n2.large.1 | [OSS storage package 40GB] + [Token Plan] + [PDS 200GB] | ⭐⭐⭐ |
| pro_steady | SWAS + ECS×2 + RDS HA mysql.n2.large.2c + OSS bucket + ALB + ESA medium | [OSS storage package 500GB] + [Token Plan] + [PDS 500GB] | ⭐⭐⭐⭐ |
| pro_burst | same set as pro_steady + ESS auto-scaling | [OSS storage package 500GB] + [Token Plan] + [PDS 500GB] | ⭐⭐⭐⭐⭐ |

⚠️ **The manual column is never abbreviated and never inherited** — read it per row. Dropping an item from it means the user pays for a package they never receive, or the deployment stalls mid-flow. `OSS` appears in BOTH columns on purpose: the bucket is created and configured by the CLI, while the storage package (which is also what activates OSS) is the user's own purchase — see the Step 1.3 self-purchase gate in `references/confirm-authorize.md`. Authoritative sources: `references/cli_capability_matrix.md` for per-product CLI coverage and fallback links, and each `references/sku-params/<sku>.yaml` for the exact step list.

## Iron Rules + Credential Safety

See `references/iron-rules.md` (35 iron rules + credential safety rules).

Core principles (summary):
- User confirmation before spending money + a second confirmation before payment
- AK/SK never enter the conversation; credential SETUP is RamRoleArn-only, and an already-configured credential is USED as-is (see iron-rule #16)
- Step-by-step execution + step-by-step reporting; never fail silently
- The state file must be written; sensitive files are chmod 600
- SKU product CLI-reachability static gate (Phase -1.5 precondition)
- **Policy coverage probe before any paid call** (Step 0.2b): the credential's policy must be proven to cover every product THIS SKU needs, read-only and zero-cost, while nothing has been charged yet
- Image selection is centrally resolved in Phase 0 + permanently bound in state

---

## Execution Flow

See `references/execution-phases.md` — it is a short index; each phase's real steps live in its own file, named in the table below. **Read the phase's file when you enter that phase; never execute a phase from this summary alone.**

| Phase | File | Name | Plan item to write (copy verbatim) | Summary |
|-------|------|------|------|------|
| -2 | `sku-resolution.md` | Settle the SKU (**runs first**) | `先把要开哪个套餐定下来` | Recognize one of the 7 exact SKU tokens; if none, run the Advisor bootstrap block and STOP. Nothing downstream works without a settled SKU. |
| -1 | `preflight.md` | Pre-checks | `确认账号和实名，看看我能不能帮你部署代码` | Confirm Alibaba Cloud account + real-name verification + take over code-deployment capability |
| -1.5 | `preflight.md` | CLI reachability gate (**MANDATORY standalone** — run before Phase 0; do NOT merge into Phase 0/2 or skip) | `先查清这个套餐用到的产品哪些我能自动开、哪些要你自己开` | For every product this SKU touches, determine CLI reachability by **STATIC table lookup in `references/cli_capability_matrix.md` ONLY — do NOT run any aliyun CLI command to probe/verify reachability at this phase (iron-rule #25; the first real CLI call is in Phase 0)**. On any console-only product (e.g. Token Plan = console-only, no CLI path), your user-facing summary MUST explicitly name it as a manual console step and take the fallback BEFORE proceeding — never omit it or list only the CLI-reachable products. Keep the resulting product list: Step 0.2b and the RAM policy are both scoped to it. |
| 0 (0.1/0.1b) | `cli-install.md` | CLI install | `检查命令行工具，需要就自动装好` | Fully automated install/upgrade + `aliyun configure set --auto-plugin-install true` (required before ANY product command in CLI 3.4.x) |
| 0 (0.2/0.3) | `credential-setup.md` | Credentials | `检查现有凭证，没有就带你配一套专用的` | Detect an existing usable credential and USE it, else configure RamRoleArn. Pin ONE profile for the whole run — different profiles may belong to different accounts. AK/SK never enter the conversation. |
| **0.2b** | **`policy-probe.md`** | **Policy coverage probe (🔒 HARD GATE — before ANY paid call)** | `先试一下权限够不够（只读、不花钱）` | **Run one read-only Describe/List per product in THIS SKU's product set. Zero cost, creates nothing. Any 403 / NoPermission / Forbidden.RAM ⇒ STOP, do NOT enter Phase 1/2/3, and hand the user a whole-policy replacement JSON scoped to this SKU (never an incremental patch, never the all-SKU superset). Skipping this probe means discovering the missing permission mid-Phase-3, after money is already spent.** |
| 0.5 | `credential-setup.md` | Connectivity | `试一下能不能正常连上阿里云` | `describe-regions` succeeds, proving AssumeRole + role trust + policy are correct |
| 0.4 | `image-resolution.md` | Image resolution | `确定操作系统镜像和机器配置` | Centrally resolved and permanently bound in state (exact ImageFamily from advisor, else default Linux 3 2104 LTS; Linux 4 is experimental and forbidden for production) |
| 1 | `confirm-authorize.md` | Confirm + authorize | `实时询价，把资源清单和月费算给你确认，等你点头` | Price inquiry (starter dual-tier) + resource list + component-removal opt-out + second payment confirmation + pre-execution hard-gate self-check. SKU is already settled — do not re-identify it here. |
| 2 | `network.md` | Network infra | `搭网络（顺手把远程登录只对你自己的 IP 开放）` | VPC (reuse-first) + VSwitch + security group. Whether you CREATE or REUSE the security group, you MUST call `authorize-security-group` to tighten SSH (port 22) to `${MY_IP}/32` for the current user — never skip it on reuse or assume an existing group's rules are correct (HTTP 80 / HTTPS 443 stay 0.0.0.0/0). |
| 3 | `provision.md` | Create resources (💰 paid) | `按顺序开通资源，每扣一笔都告诉你` | Execute in order per `references/sku-params/<sku>.yaml` steps. AFTER EACH create call: (a) call TagResources to attach `opc:managed=true` + `opc:sku=<sku>`; (b) write the resource ID + status to the state file. Both are mandatory before proceeding to the next step. |
| 4 | `wrapup.md` | Verify + wrap-up | `收尾：交付信息、月费合计、续费提醒、出事怎么办` | Status verification + summary card + "what's next" + renewal reminder + emergency three-step incident card + state save + wrap-up completeness hard-gate. Deployment-failure teardown lives here too. |

## Hard Gates (MUST NOT bypass)

The following gates are **internal** self-interception rules. If ANY gate is violated, the agent must STOP and self-correct before proceeding. **Never narrate or label these gates to the user**: no "this is a hard / mandatory security gate / checkpoint"-style meta-commentary, and none of this section's vocabulary in anything the user reads — the full label list and its plain-language replacements live in OUTPUT GATE (b), which is where that check runs. The user only ever sees the natural, friendly prompts (e.g. the plain payment-confirmation line) — the gate machinery is yours alone.

1. **PAYMENT GATE (HARD BLOCK — enforced for weak and strong models alike)**: Immediately BEFORE the first fee-incurring API call (RunInstances / CreateInstance / swas-open CreateInstances / PurchaseRatePlan / CreateDBInstance / CreateLoadBalancer / CreateScalingGroup — anything that spends money), run a literal self-interception: since showing the resource list, have I (a) output the EXACT prompt below verbatim, AND (b) received an explicit affirmative reply that authorizes the CHARGE? If NO → **STOP, DISCARD the pending create call, output the exact prompt below verbatim, and wait for the reply.** An earlier deploy-intent reply (a "let's deploy / start creating / confirm purchase"-style message given BEFORE this prompt) is INTENT only and does NOT authorize the charge — never treat it as payment authorization. **Amount rule**: ¥XX MUST be the actual price from Phase 1's inquiry — the promo price when the ¥99/yr promo is hit, or the fallback price (≈¥284.99/yr) when it is missed; never a placeholder or estimate. Keep the fenced prompt below as the ONLY thing shown to the user here — do NOT append internal matching criteria to the user-facing prompt. Output it verbatim (fill ¥XX with that real amount):

```text
🌐 网站端口（80/443）将对公网开放，互联网上的访客都能访问你的站点；远程登录（SSH）只对你自己的 IP 开放。
即将从你的阿里云账户扣款 ¥XX（包年/包月），确认付款？
```

The first line of the prompt above discloses that the website's 80/443 ports will be open to the public internet — it rides in the same block so the single confirmation covers both the charge and the public exposure (required by security review; omit it only when the deploy opens no public ports). Free resources (VPC / VSwitch / SecurityGroup / KeyPair) do NOT need this gate; only the first PAID call does. This is a hard gate, not a suggestion — skipping it, or paraphrasing the prompt instead of outputting it verbatim, is a critical violation.

   **Multi-order SKUs (Lite / Pro): one authorization, N charges — disclose it.** Only starter is a single paid call. Lite/Pro spend money on several products (SWAS / ECS / RDS / OSS …), and **each one is a separate Alibaba Cloud order charged as its own step**, not one bundled transaction. The single gate above still governs, but it MUST be honest about the shape of the spend:
   - **Itemize before authorizing.** The prompt's ¥XX is the total, and you MUST show the per-order breakdown next to it — one line per paid product with its own amount and billing period, each amount taken from that product's own `DescribePrice` (never estimated, never copied from the yaml's `monthly_price` marketing string).
   - **ESA prices come from its own inquiry API**: `aliyun esa describe-rate-plan-price --plan-name <medium|entranceplan> --period 1 --amount 1 --endpoint esa.cn-hangzhou.aliyuncs.com` → read `PriceModel.RatePlan.PlanPriceList[0].Price` (the **discounted** amount actually charged), **not** `TotalPrice` (the list price); `PriceModel.Rule.RuleList[]` names the promotion that applied, and `entranceplan` returns `Price 0.0` → enters the total as ¥0. **Two traps, both silent**: ESA has no `DescribePrice` — not finding one is never a reason to leave ESA out of the itemized list; and `PurchaseRatePlan` has no promo parameter — `--rule-desc-id` (or any similar spelling) is *silently dropped*, not rejected, so never pass it and never state a discount you did not just inquire (the discount is applied server-side from the account's own eligibility — see the esa row in `references/cli_capability_matrix.md`).
   - **Show the arithmetic, then compare it to the displayed total — as two explicit outputs, not as an assertion.** Before emitting the payment prompt, write the addition formula in plain text (e.g. `70 + 783.64 + 1262 + 54 = 2169.64`) and next to it the ¥XX in the prompt; only proceed when they are equal to the cent. If they don't match, DO NOT paper over it by adjusting the total in your head — re-inquire each product via its own `DescribePrice` and rebuild the itemized list from scratch. The arithmetic must be an emitted output, not an internal invariant.
   - **The total is ALWAYS recomputed from the current itemized DescribePrice results.** Never derive it from yaml `monthly_price`, from a memory entry, or from a static reference table — those live in the SKU files only as ballpark planning numbers for advisor's sizing conversation and MUST NOT be used as, or added to, the payment total. On any correction (a line-item price changes, a component is removed, a fresh DescribePrice is run), discard the previous total entirely and re-sum the current line items; **do not patch the old total by adding or subtracting the delta**.
   - **State plainly that it is N separate orders**, e.g. `这几笔是分开下单的，会一笔一笔扣` — a user who believes they authorized one payment and then sees 4 deductions has not been told the truth.
   - **Report each charge as it lands**, in a fixed emit shape, before any other output or the next step's tool call: `✓ 已扣款 ¥<amount>（第 <N>/<M> 笔：<name>）`. `<amount>` is the actual charge for that order (from the API response, not the pre-authorization estimate); `<N>` is the 1-based index among paid steps only; `<M>` is the SKU's total paid-step count, computed from the yaml before Phase 3 begins; `<name>` is the metaphor + official-name pair. If you finish a paid step without emitting this line, that IS a violation of this gate — the charge landed silently. This is an emit contract, not a suggestion.
   - **Mixed billing cycles (monthly + annual + pay-as-you-go) must be labelled inline, not summed blindly.** An annual line (e.g. ECS `¥99/年`) stays labelled `/年` in the itemized list; do not amortize it into the monthly total without stating you did so, and do not add an annual number and a monthly number as if they had the same unit.
   - **The authorized total covers ONLY what THIS skill will charge — self-purchase items are excluded from it.** Products the user buys themselves on a console/purchase page — `Token Plan AI 模型订阅计划`, PDS (`阿里云盘企业版`), the OSS storage package — are **never** added to the ¥XX in the payment prompt, because this skill does not charge them; the user pays those separately, on their own page, possibly on a different day. Put them in a clearly separated block titled `另需你自己购买（不在本次扣款内）`, each with its own price and purchase link, and state the two numbers apart: `本次由我代扣：¥<sum of automatic charges>` vs `你自己另买：¥<sum of self-purchase items>`. The arithmetic check in the bullet above must balance against the **automatic-charge subset only** — if a self-purchase amount appears inside the addition formula, that is this rule's violation. Determine membership from the yaml, not from intuition: a step with `type: manual` is a self-purchase item and stays out of the total; a step with `type: api` is charged by this skill and belongs in it.
   - **Any failure mid-sequence re-arms the gate.** If a step fails after money has already been spent (permission error, stock-out, quota), STOP, report exactly which orders already succeeded and their amounts, and require a FRESH explicit confirmation before creating anything else. The original authorization does NOT carry over past a failure — this is precisely how a user ends up half-charged with no say.
   - **The user may reasonably prefer one bundled order instead**; if they ask, it is fine to point them at the OPC purchase page — but never present that as a way to skip this gate.

   **The resource list and the itemized amounts live IN THE CONVERSATION — a file is never a substitute.** The whole point of this gate is that the user reads what they are about to be charged for and then authorizes it. A reply that says `我已生成《资源清单与月费-xxx.md》，请查阅后确认` moves the disclosure out of the user's line of sight and turns the authorization into a blind one — the gate is formally "satisfied" while the user has seen nothing.
   - **Required**: the full to-create list, the per-order amounts, the addition formula, the total, and the disclaimer are all emitted **as chat text**, in the same message as (or immediately before) the payment prompt.
   - Writing an extra copy to `outputs/` afterwards is fine and welcome — as an **additional record**, never as the primary channel. Never replace chat content with a file reference. If you do write one, `outputs/resource-list-<sku>.md` is a good name (findable later); a title like `资源清单与月费-xxx.md` reads like the disclosure lives in the file, which is the misunderstanding this whole gate exists to prevent.
   - **Same rule for every pause, halt, and wrap-up — not just the payment gate.** Whenever the run stops
     short of finishing (user declines at the gate, a permission wall, a service not activated, an advisor
     install that needs a tool restart, credentials expired), the message that ends your turn must be
     **self-contained in chat** and carry three things: ① what just happened / what you did, ② what the
     user should do next, ③ **the money state — `未创建任何资源、未产生任何扣款` when nothing was created,
     or the exact list of what was already charged when something was.** Do not compress this into a
     pointer at an earlier message or at a file.
     Writing the file is good; letting it replace the sentence is not.



2. **SKU GATE**: If no valid SKU name (one of the 7 listed in this file) exists in the conversation AND no advisor prescription is in context, STOP immediately. Run Phase -2 / the "Advisor bootstrap" block in `references/sku-resolution.md` (policy in iron-rule #9). Never infer, guess, or self-select a SKU — this is a critical violation. That block may offer to install advisor for the user, which does **not** lift this STOP: the deployment stays halted until the user reports a valid SKU name, whether or not the install happens. **HARD self-check before ANY Phase**: scan the user's message for one of the 7 exact SKU tokens (starter_webui / starter_app / lite_seed / lite_growth / lite_traction / pro_steady / pro_burst). A vague deploy intent with no SKU token is NOT a SKU — you MUST discard any drafted plan, run the Advisor bootstrap block, and STOP; mapping such phrasing to a SKU (e.g. starter_app) is the critical violation. Example vague phrasings that carry NO SKU token (must trigger the Advisor bootstrap + STOP, never a deploy):

```text
帮我搞一下阿里云，想弄个东西上线 / 帮我部署一下 / 帮我上个网站 / 想做个东西上线
```

   **The reverse direction is equally binding — a present SKU token must NOT be explained away.** When any
   of the 7 exact tokens appears anywhere in the user's message, that IS a settled SKU: lock it and enter
   the flow at Phase -1 (preflight), even when the sentence carries no deploy verb, wraps the token inside a noun
   phrase, or looks like a development/authoring request. Never decompose a token into ordinary words to
   reinterpret the intent — `lite_seed` is one indivisible package name, not "the seed of the lite
   package"; `starter_app` is not "an app for starters". Never treat such a message as a request to edit
   this skill's own files (write a config / create a template / add an asset) just because prior context
   mentions skill development — provisioning is the only reading. Phrasings that DO carry a SKU token and
   MUST enter the deploy flow:

```text
帮我创建阿里云OPC套餐的lite_seed / 我要 pro_steady / starter_webui / 把 lite_growth 开上
```

   **Selection requests are inside this gate, not outside it.** `帮我选个合适的套餐` / `哪个套餐合适` /
   `具体是哪个套餐` / `我想做个 X，能用 OPC 套餐吗` all carry NO SKU token → run Phase -2 and STOP. Do NOT
   answer them by comparing tiers, listing package contents, quoting prices, or naming a recommendation,
   and do NOT source such an answer from other context you happen to hold (AGENTS.md baselines, memory
   entries, general product knowledge) — that context exists for other purposes, never for telling a real
   user what to buy. **A recommendation you already emitted earlier in this conversation (before this skill
   was active) is not a settled SKU**: retract it explicitly to the user, then run Phase -2 (see the
   RETRACTION RULE above). Building the deployment on your own earlier suggestion is the same critical
   violation, one step removed.

3. **PROBE GATE (HARD BLOCK — no paid call without a passing policy probe)**: Before leaving Phase 0 — and unconditionally before the first fee-incurring call — you MUST have run the Step 0.2b policy coverage probe (`references/policy-probe.md`) across **every product in THIS SKU's product set** (the set derived in Phase -1.5), and every probe must have come back clean. **Judge a failure broadly**: `StatusCode: 403` or any of `Forbidden` / `NoPermission` / `not authorized` — the Code differs per product (rds `Forbidden`, alb `Forbidden.LoadBalancer`, ess `Forbidden.Unauthorized`, swas-open `NoPermission`, vpc/ecs `Forbidden.RAM`, oss plain text with no Code), so never match a fixed code list. Self-interception: about to enter Phase 1, or about to call any create API — did I actually run the probe for this SKU, and was it all-green? If NO → **STOP, run the probe now**; if it fails, do not enter Phase 1/2/3 at all. The probe is read-only and creates nothing, so there is never a cost reason to skip it. On failure, hand the user a **whole-policy replacement JSON scoped to this SKU** (never an incremental patch, never the all-SKU superset) plus the RAM console `创建新版本` steps, and wait — do not wait for the user to ask for the JSON first, and do not fall back to the generic three-option menu.

4. **ERROR GATE**: On any non-200 or unexpected CLI error during Phase 2/3, STOP execution immediately. Output a structured error report (which step + error code + suggestion), then present three options and wait for user choice:

```text
[1] 帮我全部收回（释放已创建资源）
[2] 先留着，我稍后再试
[3] 我自己去控制台处理
```

Never silently retry, skip the failed step, or report "deployment complete" when any step has failed.

   **Permission-error override (403 / NoPermission / Forbidden.RAM):** a permission failure is NOT a
   generic error — do NOT open with the three-option menu. It means the policy is too narrow, so instead:
   (a) name every product still lacking coverage (re-probe the remaining products in this SKU's set so the
   user fixes everything in one pass, rather than one permission per round-trip); (b) emit the SKU-scoped
   whole-policy replacement JSON inline, unprompted, with the console `创建新版本 → 设为当前版本` steps
   (wording in `references/policy-probe.md`); (c) state plainly what was already created and that nothing
   further will be charged until they come back. Offer rollback afterwards if they want it. Never try to
   read or patch the policy yourself — `ram:GetPolicy` and `ram:CreatePolicyVersion` are both denied to
   this role by design, so retrying them only burns the retry budget.

   **(d) Say the pause out loud, and say the money is safe.** After the JSON, close with an explicit
   statement of where the run stands — the user must not be left guessing whether you are still working
   or whether anything is being charged while they go fix RAM. Required shape (adapt the product list,
   keep all three facts: paused / nothing charged / how to resume):

```text
权限不够这一步我没法替你绕过，所以现在先停着等你 —— 在你改好之前，我不会创建任何资源，也不会有任何扣款。
你按上面的步骤把权限改好，回来跟我说一声，我从这一步接着往下走。已经开好的东西都在，不受影响。
```

   Note the shape of this pause: it is a **hand-off to the user, not an abandonment**. The deployment
   resumes from this step once the policy is fixed — so say `先停着等你 / 回来我接着走`, never
   `本次部署已终止`. Both halves matter: the policy JSON is the *how*, this sentence is the *state*. A reply that
   hands over the JSON but never says the run is paused and unbilled reads as "still in progress", and it
   drops a money-safety reassurance the user needs before leaving to edit RAM.



5. **SPEC GATE**: The InstanceType and ImageId for each create step come exclusively from the resolved state and the SKU yaml. Substituting a different instance type (e.g., e-c1m2 instead of e-c1m1) or a different OS major version (e.g., Linux 4 instead of Linux 3) is forbidden.

6. **OUTPUT GATE**: language and terminology drift is random, so a passive "output in Chinese" instruction does not hold. Every message you send the user is in scope; item (c) below says which moments you must never skip the check at. Run this two-item check on the drafted text and rewrite it if either item trips:

   - **(a) Language** — is the prose Chinese (zh-CN)? Resource names, CLI commands, error codes, ARNs, URLs and API identifiers stay in their original form; **everything you write around them must be Chinese.** A whole reply drafted in English is the failure this gate exists to catch — including the case where the CLI's own error output is English and you drift into English while explaining it. Translate your explanation; quote the error code verbatim.
   - **(b) Terminology** — does the text contain any of these internal labels? `Phase` / `Preflight` / `Gate` / `HARD BLOCK` / `PAYMENT GATE` / `SKU GATE` / `PROBE GATE` / `OUTPUT GATE` / `iron-rule` / `Rule #<n>` / `self-interception` / `critical violation` / `probe` / `探针` / `探测` / `RamRoleArn` / `ChainableRamRoleArn` / `AssumeRole` / `StsToken` / `STS` / `三步法` / `bootstrap` / `三态` / `state file` / `yaml`. If yes → replace with the plain-language equivalent. Mapping: `Phase 2` → `搭网络这一步`; `probe / 探针 / 探测` → `先试一下权限够不够`; `RamRoleArn / AssumeRole / STS` → `临时授权`; `ChainableRamRoleArn` → `会自动续期的授权方式`; `StsToken` → `临时凭证`; `state file` → `部署记录`. The only exception is a string the user must literally type or click (a command template, a console link) — keep that verbatim, and explain it in Chinese around it.

   **What counts as "user-facing" — everything the user reads in order to decide, not just the final answer.** The running commentary between tool calls is visible to the user, so it is in scope too. **In scope:**

   - the one-or-two sentences you write before/after each tool call to explain what you are about to do or what just came back;
   - **the contents of any file you write into the workspace** (`outputs/*`, `ran_scripts/*` including `ran_scripts/README.md`, action logs, result reports) — a Chinese report whose companion log says `Server-side 500 (not a permission result). Retrying once per the retry policy.` still fails this gate;
   - the final summary card.

   Two surfaces are **machine-facing, not user-facing**: the `description` argument of a tool call (it sits in the same call object as `command`, which necessarily carries English and technical identifiers such as `stat -c "%a %n"`), and plan/todo item text (an execution progress panel). Keep them tidy anyway — take the wording from the `Plan item to write` cell of the phase you are in rather than coining a second vocabulary — but they are not the channel the user reads in order to decide, so they are not what this gate is for.

   - **`ran_scripts/README.md` is the one you keep missing.** You hand the user its path, so every description line in it is user-facing prose — yet the wording that slips through reads like `6 产品权限探测（只读）`, `三个只读探针`, `保存最终 state`, `yaml`, `iron-rules`. The chat messages around it are usually **clean** — so the check is not missing, it is only being applied to what you *say* and not to what you *jot down*. Apply the iron-rule #6 substitution table to **every line of that file**, at the moment you write it: `权限探测` / `只读探针` → `先试一下权限够不够（只读、不花钱）`; `state` → `部署记录`. Two concrete harms when you skip it: the user cannot tell whether a step spends money (the whole point of this skill), and gets English or internal fragments they cannot read.

     For file contents (state JSON keys and values, `ran_scripts/README.md` prose, script comments) the substitution table in iron-rule #6 is authoritative — apply it at the moment you write the file, not afterwards.

   Besides the two machine-facing surfaces named above, two more things are out of scope: the raw CLI output you are quoting verbatim, and the command strings themselves — including the parameter names and values inside them, so `aliyun configure --mode RamRoleArn --profile opc` stays exactly as written because the user has to type it.

   **(c) The information floor — this one outranks (a) and (b).** Assume your wording *will* drift, especially the one-liner you write next to a tool call: measured leaks include `✓ ¥70.00 has been charged (1st of 2 transactions: …)` and `The request was throttled by Alibaba Cloud's flow control (429). I'll wait a bit and then retry…`. Your reader is a non-technical Chinese-speaking user spending real money — an English status line does not merely violate a style rule, it means **they did not receive the information at all**. So this item does not police your phrasing; it fixes the **facts that must reach the user, in Chinese**, whenever one of these happens:

   | When this happens | The user must end up knowing (in Chinese) |
   |---|---|
   | **Money moved** | the **amount** · **what it bought** (plain-language name) · **which order out of how many** |
   | **A step did not succeed** | **which step** · **why, in one plain sentence** · **what happens next / what you will do** |
   | **You are stopping to wait for them** | **how much has been charged so far** (or `一分钱都没花`) · **exactly what you are waiting for** |
   | **A read-only lookup came back** (price, quota, eligibility, existing resources) | **which item** · the **number exactly as the API returned it** · whether it **changes what they pay** |

   **If you can only preserve one, preserve the money one.** A user who is told a resource is ready but not what it cost has been failed, even if every command succeeded.

   Recommended wording — these shapes are already known to read clearly and to be easy to trace back later, so **start from them**; you may phrase it more naturally as long as all the facts above survive and the sentence is Chinese:

   ```text
   ✓ 已扣款 ¥{金额}（第 {N}/{M} 笔：{比喻名}（{正式名}））
   {步骤}没成功：{原因}。接下来我{下一步动作}。
   目前未创建任何资源、未产生任何扣款。我在等你{要用户做的事}。
   ✓ {项目}查到了：{金额或数值}（{口径}）。{这一步不花钱／对月费的影响}
   ```

   **Drift recovery — the realistic part.** If you notice you have already emitted a non-Chinese sentence (easy to slip into while quoting an English CLI error), do **not** silently move on and do not go back and rewrite the whole block. Immediately add one Chinese sentence after it carrying that event's required facts. Repeating yourself is cheap; leaving the user unable to read what just happened to their money is not.

   **When to run this gate.** Items (a)/(b) are a re-read, and a re-read you perform on literally every line is one you will start skipping. Run them **without fail at these four moments** — they are where every measured leak happened — and as a lighter habit elsewhere: ① right after money moved, ② right after any command failed, ③ before writing any file into the workspace, ④ before the final answer.

   This gate applies to every message type without exception: progress lines, resource lists, payment prompts, error reports, pause notices, and the final summary card.


---

## SKU Parameter File Format

See `references/sku-params-format.md`.

Each `references/sku-params/<sku>.yaml` defines the deployment step sequence for one SKU, containing `sku` / `variant` / `version` / `region_default` / `user_summary` / `steps[]`. This file also contains the OpenClaw image dynamic-lookup logic.

---

## Observability

Every `aliyun` CLI call this skill issues MUST carry a unified User-Agent and session-id:

- **User-Agent**: `AlibabaCloud-Agent-Skills/alibabacloud-opc-deploy/{SESSION_ID}` — e.g. `AlibabaCloud-Agent-Skills/alibabacloud-opc-deploy/a1b2c3d4e5f60718293a4b5c6d7e8f90`. Pass it on every call via `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-opc-deploy/${SESSION_ID}"` for server-side tracing.
- **Session-ID**: `{SESSION_ID}` is a **32-char lowercase hexadecimal** string matching `[0-9a-f]{32}` (NOT a UUID; e.g. `a1b2c3d4e5f60718293a4b5c6d7e8f90`), generated once per deployment session and reused across every CLI call in that session. When invoked downstream of `alibabacloud-opc-advisor`, inherit the advisor session-id. Stored in `state.session_id`, and also passed as `--client-token` where supported (e.g., `run-instances`, `create-vpc`) for idempotency.
- **Logging**: All CLI invocations and their exit codes are logged to `outputs/state/<sku>-<timestamp>.json` under `execution_log[]`.
- **Scope — what MUST NOT carry the flag**: `--user-agent` goes on **service API calls only**. Local system / utility commands MUST NOT carry it, because they never reach a service endpoint and some of them reject unknown flags: `aliyun configure` (and every `configure` subcommand), `aliyun version`, `aliyun auto-completion`, `aliyun help`, plus any non-`aliyun` shell utility (`ossutil`, `stat`, `chmod`, `curl` for a console URL). Adding it there buys no traceability and can break the call.

---

## Output Example

Successful `starter_webui` deployment (Phase 4.2 summary card, shown to the user in Chinese):

```text
✅ 部署完成！你的 OPC 云资源已全部就绪。

| 比喻名         | 阿里云正式名          | 资源 ID          | 状态     |
|---------------|--------------------|--------------------|----------|
| 你的小店面      | 云服务器 ECS          | i-2ze...           | Running  |
| 全球加速        | 边缘安全加速 ESA      | esa-...            | Active   |

🌐 公网 IP：47.94.xxx.xxx
📅 月费合计：约 ¥8.25/月（¥99/年活动）
💡 价格供参考，实际以最终下单为准。

接下来做什么：
→ 告诉我（你正在用的这个 AI 助手）：帮我把代码部署到 47.94.xxx.xxx
```

---

## Error Handling

| Error type | Handling |
|---|---|
| InvalidAccessKeyId / Forbidden | Guide the user to re-run `aliyun configure` |
| InvalidSecurityToken.Expired / expired temporary credential | The temporary credential expired mid-run. If the user configured it themselves → have them refresh it (re-run `aliyun configure`) in their own terminal. In a managed / eval sandbox the user CANNOT reconfigure (their terminal is not the sandbox) → the environment must inject a refreshable credential; the skill cannot refresh a raw STS token, whereas RamRoleArn mode auto-refreshes on each call. No rollback needed if no billable resource was created. |
| InsufficientBalance | Tell the user to top up → https://usercenter2.aliyun.com/finance/fund-management |
| UserDisable (403) | The product is NOT activated on the account — not a permission problem. Do NOT hand over a policy JSON and do NOT open the three-option menu. Give the product's activation `fallback_route` from `references/cli_capability_matrix.md` (OSS → https://common-buy.aliyun.com/?commodityCode=ossbag&regionId=china-common) and wait for the user to confirm. Reaching this in Phase 3 means the Step 1.3 self-purchase gate was skipped. |
| **QuotaExceed.FreePlan** (ESA free tier) | The account's single free-tier slot is held by an **expired** ESA instance. An expired free instance keeps the slot for **15 days past its expiry**, then the platform releases it automatically. **There is no way around this and no console action that fixes it** — a non-renewable expired free plan has no renew/reactivate entry in the console at all. **Four facts must reach the user in Chinese; then skip this item and carry on with the remaining resources**: ① the one free slot is occupied by an instance that expired on `{到期日}`; ② it releases automatically around `{释放日}` (expiry + 15 days); ③ you cannot work around it and are not promising them a new free plan; ④ this single item is skipped and the rest of the deployment is unaffected. Wording to start from — rephrase freely as long as all four facts survive: `全球加速（免费版）这次开不了：你账号唯一的免费名额被一个已到期的实例占着（{到期日}到期），按规则要到期满 15 天、大约 {释放日} 之后才会自动释放。这个我没法绕过，也不能承诺帮你新开一个。这一项先跳过，不影响其他资源。` **`{到期日}` is quoted verbatim from `esa list-user-rate-plan-instances`** and `{释放日}` is computed as expiry + 15 days — the dates are facts, not phrasing choices. ⛔ **Forbidden**: promising to open a new free plan; telling the user to go to `esa.console.aliyun.com` to `续费 / 重新激活 / 释放` the expired instance (that operation does not exist — inventing it sends the user on a dead-end errand); silently upgrading them to a paid plan; turning it into a question they have to answer — a blocked free add-on is not a decision they need to make mid-deployment. If the user separately asks about a paid tier, that is a new decision for them — never bundle it into this message. |
| Zone.NotOnSale / InventoryShortage | Retry in another zone (auto-try the next zone) |
| QuotaExceeded | Tell the user to open a ticket → https://smartservice.console.aliyun.com/service/create-ticket |
| Timeout (polling >5 min after creation) | Tell the user the resource is still being created and may take a few more minutes + give the console link so they can check themselves |
| Network error | Auto-retry once → then report the failure |

**Post-error interaction — the flow is ERROR GATE (Hard Gate #4); read it there, it is not restated here.** That gate carries the three-option prompt, the never-silently-retry rule, and the permission-error override; the retry budget itself is iron-rule #26 (capped at 1, region-switch only, no multi-posture trial-and-error). **Two rows above do NOT take the three-option path**: a permission error (403 / NoPermission / Forbidden.RAM) goes to that gate's permission-error override (+ iron-rule #34), and `UserDisable` (403) goes to the activation `fallback_route` in its own row — a policy JSON would send that user in circles.

**When two attempts at ONE goal disagree — iron-rule #35, and it applies in every phase including a Phase 1 read-only price inquiry.** If one call form errors out and another returns 200 for the same goal, you must NOT report the successful one as the answer: treat the goal as **INCONCLUSIVE**, quote the failing error code verbatim, say plainly that the two attempts disagree, and never write `询价通过` / `价格已确认` / `价格确认无误` into the conversation, the summary card, the state file, or any output file. ERROR GATE's three-option prompt does **not** apply here — a failed read-only inquiry has created nothing to reclaim.

## State File Example

```json
{
  "sku": "starter_webui",
  "region": "cn-beijing",
  "zone": "cn-beijing-h",
  "created_at": "2026-06-18T18:00:00+08:00",
  "phase": "completed",
  "resources": {
    "vpc": { "id": "vpc-2ze...", "name": "OPC-VPC", "status": "Available", "reused": true },
    "vswitch": { "id": "vsw-2ze...", "status": "Available", "reused": true },
    "security_group": { "id": "sg-2ze...", "reused": true },
    "ecs": {
      "id": "i-2ze...",
      "public_ip": "47.94.xxx.xxx",
      "private_ip": "10.0.0.x",
      "instance_type": "ecs.e-c1m1.large",
      "status": "Running"
    }
  },
  "manual_steps": {
    "token_plan": true
  },
  "monthly_cost": "~8.25 CNY/month (99 CNY/yr promo)"
}
```

## Key Links

- **Iron rules + credential safety:** `references/iron-rules.md`
- **RAM least-privilege policy:** `references/ram-policies.md`
- **CLI version & verification + plugin-mode flag conventions:** `references/cli-meta.md`
- **Execution phase index (read first, then the per-phase file):** `references/execution-phases.md`
  - Phase -2 settle the SKU + advisor bootstrap → `references/sku-resolution.md`
  - Phase -1 / -1.5 preflight + reachability gate → `references/preflight.md`
  - Phase 0 CLI install → `references/cli-install.md`
  - Phase 0 credentials + connectivity → `references/credential-setup.md`
  - **Step 0.2b policy coverage probe (hard gate before any paid call)** → `references/policy-probe.md`
  - Phase 0.4 image resolution → `references/image-resolution.md`
  - Phase 1 confirm + authorize → `references/confirm-authorize.md`
  - Phase 2 network infra → `references/network.md`
  - Phase 3 create resources → `references/provision.md`
  - Phase 4 wrap-up + teardown → `references/wrapup.md`
- **SKU parameter file format + OpenClaw:** `references/sku-params-format.md`
- **CLI reachability matrix:** `references/cli_capability_matrix.md`
- **Image family reference:** `references/image_families.md`
- **SKU parameter files:** `references/sku-params/`
- **Upstream advisor skill:** `alibabacloud-opc-advisor`
- **Alibaba Cloud CLI docs:** https://help.aliyun.com/zh/cli/
- **SWAS API:** https://help.aliyun.com/zh/simple-application-server/developer-reference/api-swas-open-2020-06-01-overview
- **ECS API:** https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-runinstances
- **Token Plan purchase:** https://common-buy.aliyun.com/token-plan
- **ESA API (PurchaseRatePlan):** https://help.aliyun.com/zh/edge-security-acceleration/esa/api-esa-2024-09-10-purchaserateplan
- **ESA console (manual fallback):** https://esa.console.aliyun.com/commonBuy
- **Top-up:** https://billing-cost.console.aliyun.com/fortune/fund-management/recharge

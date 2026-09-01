# Phase 3: Create resources (the paid phase)

> Runs after Phase 2 network infra. **This is where money is spent.**
>
> - **Entry**: Step 1.5 self-check all green — SKU settled, reachability gate passed, **Step 0.2b policy
>   probe all-green**, payment second-confirmation obtained, network ready.
> - **Exit**: every yaml step executed, tagged, and written to state → go to Phase 4 (`wrapup.md`).
> - **On any error**: ERROR GATE (SKILL.md Hard Gate #4) — stop, report, offer the three options. On a
>   403 / NoPermission specifically, hand over the SKU-scoped whole-policy replacement JSON
>   (`policy-probe.md` outcome wording), do not just list generic options.
> - Per-step structure comes from `references/sku-params/<sku>.yaml`; format spec in `sku-params-format.md`.

⚠️ If you reached this phase without having run the Step 0.2b probe, STOP and run it now
(`policy-probe.md`). Discovering a missing permission here means it is discovered *after* spending money
on whichever products happened to come earlier in the yaml.

Execute in the order of the `steps` array in `references/sku-params/<sku>.yaml`.

**Phase 3 prerequisite: SSH key preset** (chmod 600 / private-key mask, iron-rule #30):

```text
Before running RunInstances:
  1. Detect whether the user's local ~/.ssh/id_rsa.pub or ~/.ssh/id_ed25519.pub exists
     - exists → ImportKeyPair (upload the public key to Alibaba Cloud; no private key touches disk)
     - not exists → CreateKeyPair + **private key NEVER enters conversation/state**:
         # CreateKeyPair has no --output-file option; the private key is in the response PrivateKeyBody field — pipe it straight to disk, never echo to stdout/log (iron-rule #30)
         aliyun ecs create-key-pair --biz-key-pair-name opc-deploy-${TS} --biz-region-id ${region} \
           | python3 -c "import sys,json;open('$HOME/.ssh/opc-deploy.pem','w').write(json.load(sys.stdin)['PrivateKeyBody'])"
         Tighten permissions immediately:
           chmod 600 ~/.ssh/opc-deploy.pem
           test "$(stat -f '%A' ~/.ssh/opc-deploy.pem 2>/dev/null || stat -c '%a' ~/.ssh/opc-deploy.pem)" = "600" || chmod 600 ~/.ssh/opc-deploy.pem
         Show the user (only the first/last chars + a hidden middle):
           HEAD=$(head -c 32 ~/.ssh/opc-deploy.pem)   # "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
           TAIL=$(tail -c 32 ~/.ssh/opc-deploy.pem)
           SIZE=$(wc -c < ~/.ssh/opc-deploy.pem)
           echo "${HEAD} <已隐藏 ${SIZE} 字节> ${TAIL}"
         User-facing copy: "✓ 已为你生成专用密钥并设为仅本人可读（~/.ssh/opc-deploy.pem）。私钥内容不会出现在对话里。"
         ⚠️ **NEVER** write the full private key to stdout / conversation log / state.json (iron-rule #30)
  2. Record the key_pair_name variable, pass it to the RunInstances KeyPairName parameter
  Benefit: after ECS creation the user can SSH in passwordless, no extra push via Cloud Assistant needed
```

**Execution logic**:

⚠️ **Do NOT walk `yaml.steps` in file order.** The steps are grouped by product for readability, not by
execution order. Phase 3 runs in three passes, and the bucket step is deliberately last because it depends on
a purchase only the user can make:

```text
Pass 3a — every step with type: api  (the paid + free automatic resources)
  Run these FIRST, in yaml order, EXCEPT the OSS bucket step (which is held back for 3c).
  ⚠️ "In yaml order" means the ORDER of the api steps among themselves — it does NOT mean a linear
  top-to-bottom walk of the file. **Before starting, enumerate every `type: api` step in the whole
  file (minus the bucket step) and treat that list as Pass 3a's work queue.** A `type: api` step is
  yours to run in this pass no matter where it physically sits.
  The yamls are ordered automatic-first / manual-last, so a linear walk happens to work — but do NOT
  rely on file position. Enumerate by `type`.
  ⚠️ **One exception, a real dependency**: a `type: manual` step whose `output_vars` are consumed by a
  later `type: api` step MUST run at its declared position, before its consumer — Pass 3a stops there,
  hands it to the user, and resumes after it. No step currently qualifies, but before demoting any
  manual step, grep its `output_vars` keys across the file; zero `${...}` references means it is safe.
  This is the PAYMENT GATE's territory: itemized authorization already obtained, one
  `✓ 已扣款 ¥X（第 N/M 笔：…）` line per paid step.
  Rationale: everything here works without any user action, so it must not be held hostage by a
  self-purchase item the user may still be deciding on.

Pass 3b — every step with type: manual  (hand-hold the user through their own purchases)
  Now walk the manual items one at a time, each with its field-level instructions:
    · Token Plan AI 模型订阅计划 → share link, wait for "开好了"
    · PDS (阿里云盘企业版) → purchase page + the CDE-Agent / 权益包 pinning warnings, wait for "开好了"
    · OSS storage package → the field-by-field block from Step 1.3 (already emitted once there; here
      just ONE short reminder if state is still `deferred` — never re-paste the whole block)
  Report progress after each; a user who defers one manual item does NOT block the others.

Pass 3c — the OSS bucket step  (only for SKUs containing OSS)
  Precondition read: state.self_purchase.oss_package
    · `bought` / `already_active` → go straight to the bucket attempt below
    · `deferred` → emit the ONE permitted reminder and wait for the user's reply:
        `到建仓库这一步了。OSS 存储包还没买的话现在买一下（链接和选项我前面给过），买完跟我说一声，我接着建。`
      user says done → bucket attempt; user still declines → skip ONLY this step (see partial-success below)

  🔍 **The activation check IS the bucket call — there is no read-only probe that works.**
  E2E-measured: on an unactivated account EVERY read succeeds and tells you nothing
  (`ossutil ls` → `Bucket Number is: 0`; `ossutil api list-buckets` → full XML;
  `api get-bucket-info` → `404 NoSuchBucket`). Only the write reveals the truth. Creating a bucket is
  itself FREE (you pay for storage / requests / traffic, not for the bucket), so attempting it costs
  nothing and doubles as the probe. Never claim you "verified OSS is activated" from a read-only call.
  🚨 **Do NOT reach for `ossutil --dry-run` here.** It is not a dry run: measured 2026-08-26, `ossutil mb`
  with `--dry-run` **really created the bucket** while exiting non-zero with a misleading
  `403 AccessDenied`. Using it as a "safe pre-check" produces an unrequested resource in the user's
  account. Just make the real attempt below — that IS the probe. (See the `ossutil` notes in `cli-meta.md`.)

  Attempt: aliyun --profile <p> ossutil mb oss://<bucket> --region <region> --acl private \
             --storage-class Standard --redundancy-type LRS
    · success → continue with the post_actions (encryption / versioning / tagging) and report
    · `403 UserDisable` (EC 0003-00000801) → OSS is NOT activated. This is NOT a permission problem:
      do NOT hand over a policy JSON, do NOT go to the ERROR GATE three-option menu, do NOT retry.
      Say plainly, once:
        `仓库没建起来——你的账号还没开通对象存储服务。买那个存储包的同时就会自动开通，
         买完跟我说一声我就接着建。前面已经开好的都在，不受影响。`
      then wait. On the user's next confirmation, retry the same command once.
    · any other error → normal ERROR GATE handling

  **Partial success is an acceptable end state.** If the bucket is the only thing missing, the deployment
  is NOT a failure: keep every created resource, do NOT roll anything back, and say so explicitly in the
  wrap-up — `其余资源都好了，只差这个仓库，你把存储包买好随时告诉我，我几秒就能补上`. Never tear down
  working paid infrastructure over one unpurchased storage package.

for each step within a pass:
  if step.type == "manual":
    → output the operation guide + link
    → wait for the user to confirm completion
    → record to state
  else:
    → assemble the CLI command
    → execute
    → check the return value (success/failure)
    → if wait_until → poll until the status is met (alarm after a 5-minute timeout)
    → extract output_vars, save to context
    → **verify the resource actually landed where it was supposed to**: read it back (Describe/List for
      that product, scoped to the target region) and compare its real region against ${region}.
      This read-back is **its own goal** for retry-budget purposes (iron-rule #26) — it is free, read-only,
      and it does NOT come out of whatever budget the create call used. Even if the create needed its one
      retry, you still owe the user this verification; skipping it is how a wrong-region resource gets
      reported as success.
      A create call that returns 200 does NOT prove the region is right — a region flag has two jobs
      (request body vs service endpoint) and passing the wrong one never errors, it just puts the
      resource in the profile's default region (measured: a Beijing SWAS created in Hangzhou, ¥70 lost).
      If the regions differ → STOP, do not create the next resource, tell the user which resource landed
      where and that the wrong-region one needs a refund/release, and wait.
    → update the state file
    → report the result to the user
    → if this step SPENT MONEY: IMMEDIATELY emit one plain-text line with this exact shape,
      before any other output or the next step's tool call:
        ✓ 已扣款 ¥<amount>（第 <N>/<M> 笔：<plain-language name>）
      Rules for this line:
        · <amount> = the actual charged amount for THIS order (from the API response / order lookup),
          not the estimate from Phase 1's itemized list;
        · <N> = this paid step's 1-based index among paid steps only (skip manual/free steps);
        · <M> = total number of paid steps for this SKU, computed from the yaml before Phase 3 starts;
        · <name> = the metaphor + parenthetical official name, e.g. "轻量应用服务器（SWAS）".
      🚨 **What is mandatory here is the information, not the exact characters.** Three facts must reach
      the user **in Chinese** the moment money moves: the **amount**, **what it bought** (plain-language
      name), and **which order out of how many**. The shape above is the recommended way to say it —
      start from it — but a more natural Chinese sentence carrying all three is equally acceptable.
      What is NOT acceptable is dropping a fact, or saying it in a language the user cannot read:
      measured failure — the line came out as `✓ ¥70.00 has been charged (1st of 2 transactions: AI
      Assistant Home — Lightweight Application Server (SWAS))`. That sentence is well-formed and even
      complete, yet for a non-technical Chinese-speaking user it delivers **nothing** — they now do not
      know what their money did. Do not draft this line in another language and translate it afterwards;
      write it in Chinese the first time. If you catch yourself having emitted it in English, add the
      Chinese sentence immediately after rather than moving on (Hard Gate #6 item (c), drift recovery).
      Do NOT batch charges into a summary at the end — the report is per-charge and immediate. If you
      complete a paid step without emitting this line, that IS a violation of Hard Gate #1 (a silent
      charge). Do not skip it:
      passive-assertion phrasings of this rule are routinely skipped, so it is now an emit contract.
```

⚠️ **Money accounting across the sequence** (Lite/Pro spend in several separate orders):
- Keep a running tally in state: which paid steps succeeded, each amount, and the remaining ones.
- **If any step fails after money has already been spent, the earlier authorization is spent too.** STOP,
  report exactly which orders already went through and for how much, then require a FRESH explicit
  confirmation before creating anything further — do not treat the original `确认付款` as covering the
  retry or the remaining items (SKILL.md Hard Gate #1, multi-order clause).
- On teardown, the paid-so-far list is what the user needs in order to decide; hand it over verbatim
  rather than a vague `部分资源已创建`.


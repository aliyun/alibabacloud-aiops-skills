# Iron Rules + Credential Safety

> Split out from SKILL.md; contains the 35 iron rules and the credential safety rules.

## Iron Rules

1. **User confirmation before spending money**: show the resource list + monthly price, and only execute after the user says "confirm".
2. **Step-by-step execution + step-by-step reporting**: after each resource is created, tell the user the result (IP / connection string / status); do not silently run a long batch.
3. **Never fail silently**: if any step's API errors → immediately tell the user which step failed + the error message + a suggestion (retry / switch zone / check quota).
4. **Be honest that Token Plan / PDS cannot be automated**: on a Token Plan or Alibaba Cloud Drive PDS step → output the console link + operating instructions, and wait for the user to confirm "I've enabled it". **ESA now supports API auto-provisioning** (the PurchaseRatePlan API).
5. **VPC reuse-first**: first query existing VPCs tagged `opc:managed=true`; reuse if present, only create when none exists.
   - **Same for a paid resource that is already there**: if the account already has an ECS / SWAS / RDS **identical** to the one this SKU is about to create, stop and ask the user — reuse it, or create a new one? If they say create, create and move on. Neither reusing nor duplicating is a decision you make silently.
   - **This covers the whole-stack case too, and that is the one most easily missed.** When the account already holds a complete prior deployment of the same SKU (SWAS + ECS + RDS + bucket, all prepaid), the tempting slip is to put yourself into a reuse-everything mode on your own — disclose the inventory, then ask only for payment confirmation, and never ask whether the user wanted that old stack or a fresh one. **Disclosure is not consent.** The count of matching resources does not change the rule: one identical machine or an entire identical stack, you stop and ask the same single question. A prior stack may belong to a different project, may hold stale data, and its database password was set in a session the user no longer has — so "reuse it and avoid paying twice" is a sound *recommendation*, never a decision you take for them.
6. **The state file must be written, at exactly one pinned path**: after each creation, append the resource ID to the state file, used to recognize existing resources during later upgrade/management.
   - **Path (no drift permitted)**: `<workdir>/outputs/state/<sku>-<timestamp>.json`, where `<workdir>` is the session working directory and `<timestamp>` is **ISO-8601 basic form with offset** — `YYYYMMDDThhmmss+0800` (e.g. `outputs/state/starter_app-20260827T103132+0800.json`). Create `outputs/state/` if absent. `chmod 600` right after the first write.
   - A state file that later runs cannot locate is a state file that does not exist — do not vary the path or the timestamp format.
   - **Anything else you write into the workspace is a record, not a channel** — the chat message is always the channel (Hard Gate #1). Records are optional, but when you do write one, use these names so a later run or a reviewer can actually find it: resource list + monthly fee → `outputs/resource-list-<sku>.md`; whole-policy replacement JSON → `outputs/ram-policy-<sku>.json`; executed command scripts + their logs → `ran_scripts/<NN>-<action>.sh` + `<NN>-<action>.log`; the run index → `ran_scripts/README.md`.

   - **Filenames and JSON keys are user-facing text too (Hard Gate #6 item (b) applies to them).** The user reads them, so the internal-label blacklist covers them. Use this substitution table — do not paraphrase, do not re-translate each time:

     | Never write | Always write |
     |---|---|
     | `policy-probe` / `probe` / `探测` / `探针` in a filename | `permission-check` |
     | `权限探测` / `只读探针` / `探测` in a `ran_scripts/README.md` description line | `先试一下权限够不够（只读、不花钱）` |
     | `state` / `state file` in a `ran_scripts/README.md` description line | `部署记录` |
     | state key `policy_probe` | `permission_check` |
     | state value `"StsToken"` / `"RamRoleArn"` / `"AK"` for credential type | `"临时凭证"` / `"角色授权"` / `"长期密钥"` |
     | `gate` / `phase` / `preflight` / `bootstrap` in a filename | `confirm` / `step` / `pre-check` / `install` |
     | `<sku>_<region>_resource_inventory.md`, `资源清单与询价结果.md`, any self-invented list name | `resource-list-<sku>.md` (the table above) |

     Reference script names (copy these, do not re-coin): `01-cli-setup.sh` · `02-credential-list.sh` · `03-identity-check.sh` · `04-permission-check.sh` · `05-price-inquiry.sh` · `06-image-resolve.sh` · `07-network-check.sh`.

     **The two that slip through most often — check yourself against them**: a state JSON written with `"mode": "StsToken"`, and a `ran_scripts/README.md` carrying `三个只读探针` or `StsToken`. Both are rows in the table above, so both are avoidable by substituting **at write time**. The gap is never the check itself — it is that nobody re-opens a written file to sanitize it afterwards. Substitute as you type.

     **`ran_scripts/README.md` — reuse the plan wording, do not invent a second vocabulary.** Its only job is one table of `脚本名` → `这一步做了什么` → `结果`, and the middle column must be **copied from the plan-item table in Hard Gate #6** (`SKILL.md`) — that table is already the approved plain-language phrasing for exactly these steps, so `权限检查：ECS / VPC / ESA 三个只读探针` should have read `先试一下权限够不够（只读、不花钱）`. Nothing in this file needs a word the substitution table above does not already cover — if you find yourself reaching for one, you are recording internal machinery the reader does not need.
7. **Database passwords never hit disk**: after generation the password is **shown once in the conversation only**; the state file records only `password_set: true` + `set_at`, and it is never written to any state/log/yaml. If the user loses the password → reset via RDS `ResetAccountPassword`, never recover from history. AccessKeys are likewise never displayed, stored, or echoed (see iron-rule #15).
8. **MCP-first, CLI-fallback**: when MCP is detected available, call via MCP; otherwise fall back to executing `aliyun` CLI Bash commands directly.
9. **Never decide the SKU for the user (execution-only boundary)**: deploy only executes, it does not do selection — never run the sizing questionnaire itself / judge the tier for the user / recommend a specific one. **This holds even when the user directly asks you to choose** (`帮我选个合适的套餐` / `哪个套餐合适` / `具体是哪个套餐`): such a request is a no-SKU case, not an invitation to select. Comparing tiers, listing package contents, or quoting prices IS selecting, and sourcing that answer from context outside this skill (an AGENTS.md fact baseline, a memory entry, general product knowledge) does not make it allowed — that context serves other purposes, never a real purchase decision. If a recommendation was already emitted earlier in the conversation before this skill loaded, retract it explicitly instead of building on it. **A SKU recalled from memory / a daily note / a previous session summary is likewise NOT settled** — such a record may be the residue of an earlier violation of this very rule (self-selected SKU → written to memory → read back as `上次的选型结果`), so never name it to the user or let it seed the sizing conversation; re-settle through Phase -2 from scratch. When the user has not given a SKU, do not improvise the wording or the recovery path: run **Phase -2 / the "Advisor bootstrap" block** in the SKU-resolution reference (`sku-resolution.md`), which is the single source of truth for the whole no-SKU path. That block distinguishes advisor being callable, present on disk but not yet loaded, or absent; when absent it offers to install advisor into the same skills directory deploy itself lives in (**always after asking** — writing into the user's tool directory unasked is forbidden); once the files are in place it asks the user to restart the tool; and if anything fails it falls back to handing over the install address https://github.com/aliyun/alibabacloud-aiops-skills/tree/master/skills/computing/ecs/alibabacloud-opc-advisor. **Never hand off to a non-existent advisor, and never make the user guess a SKU name off the purchase-page cards** (the 4 cards do not map one-to-one to the 7 SKUs, so the user can't report it accurately). Offering to install advisor never substitutes for the user's own tier choice — the deployment stays stopped until a valid SKU name arrives. If the user asks "which one should I pick" → likewise route to that block, never answer it yourself. Once a valid SKU name is obtained, enter the normal execution flow.
10. **Starter must include a bridging explanation**: Starter SKUs only create cloud resources (ECS/SWAS + ESA); code deployment relies on a desktop AI assistant. **`qwcn-pro` (QoderWork CN Pro, ¥59/month) is desktop software, not a cloud resource** — absent from the CLI capability matrix, un-provisionable by deploy, and **never part of a package quote**; the user subscribes separately at https://qoder.com.cn/qoderwork. Phase -1.2 decides the branch by **runtime self-introspection, never by asking**: if you have a local-execution capability (Bash / terminal / file-write acting on the user's machine) you ARE their desktop assistant → `has_desktop_tool = true`, take over and give the bridging explanation; if you are a chat-only runtime → `has_desktop_tool = false`, guide the download as a separate self-purchase. Never ask `你是不是已经在用 Codex / WorkBuddy 这类桌面 AI 助手了？` — advisor resolves the same fact identically (its iron-rule #5), and the package price is the same in both branches (the ¥59 never enters the quote or the payment gate total).
11. **starter_webui / starter_app price-inquiry gate**: advisor outputs `sku: starter_webui` or `starter_app` + the `fallback_ecs_config` structured field. In Phase 1.2.5 deploy runs an automatic DescribePrice inquiry: ① hits RuleId=20906709 (¥99/yr) → take the ECS promo path; ② misses → **no longer switch to SWAS**, immediately run a second inquiry with `fallback_ecs_config` (pay-by-traffic + 100M peak bandwidth), obtain ≈¥284.99/yr (Beijing) and explicitly confirm with the user; if accepted, RunInstances with the pay-by-traffic config + Phase 4 configures a CloudMonitor outbound-traffic alarm; if declined, go back and let the user re-pick a tier. **Never ask when settling the SKU "have you used the promo before"** (the user won't remember). **Deprecated**: the SWAS swas.s.c2m2s40b1.linux ¥45/month fallback path.
12. **Disclaimer is mandatory**: when displaying the Phase 1.3 resource list, always append the price disclaimer; for promo-hit prices (ECS ¥99/yr / OSS ¥119/yr) additionally append the promo-availability note. **ESA standard (medium) has no fixed promo price — never quote one.** Its list price is ¥375/month and the discount is applied server-side according to what the ACCOUNT qualifies for (one account may be charged ¥120/month, another the full ¥375). `PurchaseRatePlan` accepts no promo parameter at all — `--rule-desc-id` and every similar spelling are **silently dropped from the request**, so there is nothing to pass and nothing to verify client-side. Always read the real amount from `esa describe-rate-plan-price --plan-name medium --period 1 --amount 1` → `PriceModel.RatePlan.PlanPriceList[0].Price` before charging, and quote that. Exact user-facing strings:

```text
💡 价格供参考，实际以最终下单为准
以下单时活动可用性为准
```

13. **CLI install is fully automated (this one thing only)**: CLI install must be done automatically by the agent via the Bash tool, aligned with the official docs [aliyun CLI install & update](https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli); GitHub Releases [aliyun/aliyun-cli](https://github.com/aliyun/aliyun-cli/releases) as a fallback mirror. On macOS use Homebrew or curl to install directly into `~/.local/bin/` (no sudo), on Linux use install.sh, on Windows use the official ZIP (see Phase 0.1). **Never output commands for the user to copy into another terminal and run manually** — the user is non-technical; all commands should complete silently in the current AI terminal. **Note: CLI install and credential config are two independent things** — install is within this iron-rule #13's scope (skill fully automates it), credential config is within iron-rule #28's scope (run in the user's local terminal; the skill never touches AK/SK).
14. **Second confirmation before payment**: when the balance is sufficient, an explicit payment confirmation is required before RunInstances/CreateInstance ("about to charge ¥X, confirm?"). The initial "confirm start creation" only confirms intent — it does not authorize a charge. When the balance is insufficient, the top-up guidance path needs no extra confirmation.
15. **AK/SK never enter the conversation** (aligned with the skills.aliyun.com official security spec):
    - **NEVER** read, print, or echo AK/SK values (`cat ~/.aliyun/config.json`, `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` are all forbidden)
    - **NEVER** let the user paste AK/SK into the chat box
    - **NEVER** use `aliyun configure set` with literal credential values
    - **ONLY** allow `aliyun configure list` to check credential status (shows only the masked last 3 chars)
    - **ONLY** allow `aliyun configure --mode RamRoleArn --profile opc` interactive config (the permanent-AK `--mode AK` is disabled; stdin input does not enter the conversation log)
    - If the user proactively sends AK/SK in the conversation → do not use it, do not store it, remind immediately

16. **Credential SETUP = RamRoleArn only; credential USE = whatever is already configured**:
    - **Setup** (only when NO usable credential exists): the skill configures ONLY `aliyun configure --mode RamRoleArn --profile opc`. The sub-account opc-deploy carries only `AliyunSTSAssumeRoleAccess`; permissions are granted via the role `opc-deploy-role` carrying the custom policy `opc-deploy-policy` (see Phase 0.3); on each call the CLI auto-performs STS AssumeRole for a temporary token (default 1h). The skill NEVER sets up or falls back to a permanent AK (`--mode AK` / `aliyun configure set` with literal AK/SK are forbidden); AK/SK NEVER enter the conversation.
    - **Use** (when a credential is already configured — a pre-configured user, or a CI/eval sandbox that injected one): the skill USES it as-is after confirming it authenticates via `aliyun configure list` (masked) + `aliyun sts get-caller-identity` (identity only). This reads no secret and touches no red line. If it is a long-lived AK, warn that RamRoleArn is recommended for production; do NOT hard-block or force a reconfigure. (See Phase 0.2 for the detection/resolution flow.)
    - Rationale: refusing to run when the environment already provides a working credential would make the skill unusable wherever a credential is pre-provisioned. The security guarantee — the skill never reads/echoes/persists AK/SK — remains absolute and is orthogonal to whether the pre-existing credential happens to be long-lived.
    - **User-facing wording**: `RamRoleArn` / `AssumeRole` / `STS` / `three-step model` / `三步法` are INTERNAL labels. Never open a credential explanation by naming the mechanism; lead with the plain-language courier-in-uniform metaphor in Phase 0.3 and keep technical strings only where the user must literally type or click them. An opening line shaped like `我们采用 RamRoleArn 三步法` is a wording violation even though the underlying flow is correct.

17. **chmod 600 immediately on writing sensitive files**: the following three file types must be `chmod 600` immediately after writing, with an in-script permission check as a precondition (write → verify → fix if it fails):
    - `~/.aliyun/config.json` (CLI credential store)
    - `~/.ssh/opc-deploy.pem` (the private key auto-downloaded by CreateKeyPair)
    - `outputs/state/<sku>-<timestamp>.json` (resource ledger, incl. the `password_set` flag, etc.)
    User-facing wording (show one line only; do not expose chmod or other technical details):

```text
✓ 已将凭证文件设为仅本人可读
```

18. **SSH port 22 must be tightened to ${MY_IP}/32**: when creating/reusing a security group, the SSH port-22 rule's `SourceCidrIp` must not be `0.0.0.0/0`. The skill automatically runs `curl -4 -s --max-time 5 https://ifconfig.me` to get the egress IPv4 and writes it into the rule (`-4` forces IPv4 — security-group SourceCidrIp does not accept IPv6). When blocked by an org ControlPolicy, **do not teach the user to bypass it**; guide them to contact the admin to request an exception or widen the sub-account permissions. Keep the rule after deployment (the user can tighten/close it in the console themselves).

19. **No runtime package installs on production servers**: all file processing (image compression, dependency bundling, etc.) must be done on the user's own machine or in CI before uploading; it is **forbidden** to `yum install` / `apt install` / `pip install` any package on a created ECS/SWAS. Rationale: crossing the IaC boundary, introducing unaudited sources, and hurting image reproducibility. Image optimization becomes an "optional enhancement" mode: use cwebp if present locally, otherwise upload the original image directly without blocking the flow.

20. **Failures have teardown, and teardown deletes only self-created resources**: if any Phase 3 step fails after creation → show the user two options "roll everything back for me / keep it and retry later". Choosing "roll everything back" calls Delete\*/Release\* APIs in reverse order per state.created_resources. In the RAM Policy, Delete permission is granted only to resources tagged `opc:managed=true` (Tag Condition as a backstop, so it never mistakenly deletes the user's other resources).

21. **Prepaid resources default to auto-renew off**: all prepaid creation steps in the yaml are uniformly `AutoRenew: false`. The Phase 4 report must tell the user "you'll get an Alibaba Cloud renewal reminder SMS/message 7 days before expiry — renew in time to avoid service interruption" + the renewal-management console link `https://billing-renew.console.aliyun.com/`. **Never charge silently**; better the user forgets to renew than an auto-charge happens.

22. **Token Plan upgrade wording must not tout "instant"**: when advisor/deploy involves a Token Plan upgrade, **remove** the "instant, no-interruption" marketing wording. Before upgrading, always show "current monthly fee vs new monthly fee + user confirmation" before executing; for downgrades, explicitly state "takes effect only after the current cycle ends".

23. **Hard-reject out-of-scope requests (deploy has a built-in scope, independent of advisor context)**: deploy **carries its own authoritative scope list**, independent of whether advisor is in context:
    - **can_do**: execute package selection / place orders / provision cloud resources / deploy the user's code up / console guidance
    - **cannot_do**: write business code / business ops / application-layer hardening guarantees / make business decisions for the user
    - If the advisor prescription carries a `scope_declaration` field (can_do / cannot_do) → take it as authoritative and merge with the built-in list; with no advisor context → use the built-in list above directly, **never relax the boundary just because the advisor field is missing**.
    Out-of-scope requests in a deploy session — typically "after deploy, write my backend code for me", "install npm/pip packages on the server for me", "run a SQL query for me", "design my tables for me", "write my privacy policy" — must be hard-rejected citing the `cannot_do` section, pointing back to the desktop AI assistant (QoderWork CN Pro / WorkBuddy / Codex). User-facing template:

```text
这件事不在我能做的范围内——我只负责帮你选套餐 + 下单 + 把云资源开好。${越界请求} 属于业务代码/业务运维，应该由你的桌面 AI 助手在你电脑里帮你做（它能看到你的代码和需求）。我把 ECS 公网 IP 和 SSH 入口给你之后，你打开桌面 AI 助手让它接管即可。
```

24. **No runtime package installs on production servers (reinforced)**: paired with iron-rule #19 — even if the user explicitly asks "yum install the MySQL client / apt install nginx / pip install flask on the ECS for me", **refuse to execute**. Rationale: ① crossing the IaC boundary, introducing unaudited sources; ② hurting image reproducibility; ③ breaking the accountability chain when something goes wrong (the OPC user can't troubleshoot it themselves). User-facing:

```text
我不在已开好的服务器上装软件——这会让后续出问题时很难复现/回滚。应用层依赖请在你电脑上准备好（用 Docker 镜像或者 requirements.txt + 你的桌面 AI 助手），通过 SSH 部署上去即可。
```

25. **SKU product CLI-reachability static gate** (concentric with iron-rule #27): after receiving the advisor SKU, **first** check the CLI capability gating matrix (cli_capability_matrix) — each product is marked `cli_supported: true | partial | false` + `fallback_route`. If any item is marked `partial` or `false`, immediately explain to the user and take the corresponding fallback (e.g., Token Plan false → share link; PDS partial → primary-account enablement page; the OSS package partial → buy page), and **forbid CLI trial-and-error**. **ESA is CLI-provisioned for every tier** — do not announce it as a manual item. This Phase -1.5 static gate happens **before** the Phase 0 credential config, to avoid the user finding out the SKU is unworkable only after configuring credentials.

26. **CLI error retry cap = 1 — and the budget is counted PER GOAL, never per command literal**: when a CLI call returns errors like `unknown product` / `endpoint not exist` / `Forbidden.RAM` / `NoSuchAPI` / `OperationDenied.NoPermission`, **retry at most once** and only a "region switch" is allowed as the retry action (e.g., cn-beijing → cn-hangzhou). From the 2nd time, immediately go to `fallback_route` (console link / ROS template / manual enablement guide), and **forbid multi-posture trial-and-error** (changing param names / command spelling / subcommand separators).
    - **What "once" means**: the budget belongs to the **goal** — "probe RDS permission in cn-beijing", "create the ECS", "inquire the ESA price" — not to the exact command string. Every one of the following **consumes the same single budget** and does NOT earn a fresh attempt: re-running the same command; switching `--endpoint`; adding/removing `--user-agent` or any other flag; switching between plugin-mode kebab-case (`rds describe-db-instances --biz-region-id`) and built-in PascalCase (`rds DescribeDBInstances --RegionId`); installing a product plugin (`aliyun plugin install`) and re-running; adding `--debug`; running `--cli-dry-run` against the same goal. **Two calls against one goal is the ceiling, whatever the spelling.**
        - **The number is 2 calls, and the retry is EXACTLY one — not "up to" one.** Count calls per goal, out loud: call #1 = the first attempt, call #2 = the one retry, **call #3 does not exist**. Before every re-invocation ask yourself: *is this call #2 or call #3 for this goal?* If #3 → do not send it; go to `fallback_route` / wrap up.
          - ⚠️ **Scope**: "exactly one" fixes the *ceiling and the floor of a retry you have already decided to make* — it does **not** turn every error into something you must retry. Whether to retry at all is decided by the error class: a **transient** condition (5xx / 429 / timeout) gets its one retry, because reporting a one-off blip as a hard failure is its own bug; a **deterministic** condition (a wrong flag shape, `unknown flag`, a missing required param) gets **zero** retries — you fix the command per the cli-meta table, and that correction IS the second call. Never "retry" a deterministic error unchanged in the hope it behaves differently.
          - 🔴 **What "fix the command" means — and what it never means.** A correction changes a **flag name or a flag value inside the same call form**. **Changing the call form is never a correction**: kebab-case ↔ PascalCase (`ecs describe-price --biz-region-id` ↔ `ecs DescribePrice --RegionId`), switching `--endpoint`, installing a plugin and re-running, adding `--debug`. Those are a *different path to the same goal*, already enumerated above as spending the same budget — rewriting the call in another form and calling it `修正参数格式` does not make it one. **And if a form switch does happen and the two forms return different outcomes, iron-rule #35 takes over immediately**: the goal is INCONCLUSIVE, not solved — a 200 obtained by a form the failing call did not use proves nothing about the original path.
        - 🚨 **Waiting does not buy you a new attempt. Backoff retrying is FORBIDDEN.** `sleep 15` → retry → `sleep 30` → retry → `sleep 90` → retry is **4 calls against one goal = 2× over the cap**, no matter how reasonable the escalating intervals look. Exponential/linear backoff is a good engineering habit **that this skill deliberately does not use**, because the user is waiting in a chat and a throttled read-only probe is not worth three minutes of silence. Specifically forbidden: more than one `sleep` per goal; `sleep` values that escalate; wording like `我再重试一次` / `最后一次再试` / `等久一点再试` after call #2 has already happened; a script whose comments record 3+ attempts. **One `sleep` of ≤15s before call #2 is the entire allowance.**
        - **Announce the budget honestly and then match it.** If you tell the user `我按规矩只重试一次`, that sentence is a commitment: the very next thing you do is call #2 and then stop. Saying "once" and then making three attempts is worse than saying nothing — it misreports your own behaviour to the user.
    - **Do not spend this retry budget on flag shapes**: `unknown flag` / `--biz-region-id is required` / a jmespath or glob failure are NOT reachability errors — they mean the command was written wrong. Look the correct form up in the "Plugin-mode flag conventions" table in the CLI meta reference (cli-meta) instead of guessing a second spelling. If a call still fails after applying that table, treat it as a real error and go to `fallback_route`. Consulting that table is **one** correction, and it lands inside the same per-goal budget — it is not a licence to iterate.
    - **`5xx` / `InternalError` / `ServiceUnavailable` / `Throttling` (429) is its own class: a server-side condition, NOT a client problem to debug**. On `HttpStatus` 5xx or 429, or `ErrorCode: InternalError` / `ServiceUnavailable` / `ServiceTimeout` / `Throttling.User` / `Throttling.Api`:
      - retry **the identical command once**, unchanged — nothing else;
      - if it fails again, **stop that goal** and tell the user plainly, in Chinese: which step failed, that it is an Alibaba Cloud server-side hiccup rather than a permission or parameter problem on their side, and the two ways forward — wait a bit and retry, or open a ticket at https://smartservice.console.aliyun.com/service/create-ticket ;
      - **explicitly forbidden as "diagnosis"**: switching endpoint, rewriting the command in another case/form, installing plugins, adding `--debug`, or probing with `--cli-dry-run`. A 500 is not evidence about your command — it is evidence about the server.
      - **A suspicious-looking error response changes nothing.** If the same `RequestId` comes back twice, or the payload looks synthetic/malformed, you may say so to the user (`这个报错看着不太像真实的接口返回`) — but you still handle it as a 5xx per the steps above. Never let "this error looks fake" become the reason to enter client-side debugging; that judgement belongs to the user, not to a retry loop.

27. **Image selection contract: centralized resolution in Phase 0 + permanent binding in state + yaml pure-consumption**: an early design put the resolution logic in a yaml composite step spanning 7 files and failed to land twice. Current architecture: **the resolution logic exists uniquely in Phase 0.4 (one place in SKILL.md); the 7 yamls only consume via `${state.resources.ecs.image_id}`** — no longer embedded in a composite step, no longer 7 duplicated copies of logic.
    - **Phase 0.4 resolution entry** (see execution flow Phase 0.4): every SKU containing ECS RunInstances runs, before Phase 1 loads the yaml:
      - **Main path**: `aliyun ecs describe-image-from-family --image-family ${advisor prescription image.family} --biz-region-id ${region}` (CLI 3.4.11 verified: both flags kebab-case and required; PascalCase `--ImageFamily`/`--RegionId` error with `unknown flag`, and so does the plausible-looking `--region-id` — only `--biz-region-id` is accepted)
        - The advisor prescription family must be the full underscore + minor-version-inclusive format (verified by dry-run): `acs:alibaba_cloud_linux_3_2104_lts_x64` ✓ / `acs:alibaba_cloud_linux_3_x64` ✗ (short name → 0 hits)
        - Hit → obtain the ImageId (e.g., `aliyun_3_x64_20G_alibase_20260513.vhd`) + CreationTime + OSName → write to `state.resources.ecs.image_id` / `image_family` / `image_os_series` / `image_creation_time` / `image_pinned_by_advisor_at` / `image_locked_at`
      - **Fallback path** (when the main path gets 0 hits): `aliyun ecs describe-images --image-family ${family} --status Available --image-owner-alias system --biz-region-id ${region} --page-size 5`
        - Take `Images.Image[0].ImageId` (newest first by API default order)
        - **Behaviors forbidden by dry-run testing**: ① adding a sort flag (neither `--SortOrder` nor `--sort-order` exists on DescribeImages — the CLI recognizes no sort parameter at all); ② switching to `--image-name` wildcard fuzzy match (the Chinese OSName double-space is unreliable); ③ downgrading to a major-version wildcard
      - **0-hit hard-stop**: if the fallback still gets 0 hits → STOP and show the user-facing hard-stop message below; **deploy is forbidden to switch major versions itself (Linux 3→4 will break the app layer)**

```text
系统镜像清单里没找到 ${family} 锁定的次版本（${os_series}），可能该次版本在 ${region} 区下架了。请回 advisor 重出处方让 advisor 升次版本。
```

    - **state reuse**: when state.resources.ecs.image_id already exists, **reuse** that ImageId directly, and Phase 0.4 skips the DescribeImageFromFamily call, ensuring the same user's same instance family always uses the same binary; only re-resolve when the user **explicitly approves an upgrade** (e.g., advisor bumps the family after a semi-annual review).
    - **yaml-layer contract**: the ECS RunInstances + ESS CreateScalingConfiguration (pro_burst) in all 7 yamls uniformly write `ImageId: "${state.resources.ecs.image_id}"` — **forbidden to hardcode an ImageId literal in the yaml, and forbidden to reuse the old variable `${latest_image_id}`**.
    - **Forbidden behaviors**: ① hardcoding an ImageId / ImageName literal in the yaml; ② string-retrying after a 0-hit (`_3_2104` → `_3` → `4*` → `4.*` → adding/removing underscores); ③ deciding to switch major versions itself; ④ copy-pasting the Phase 0.4 resolution logic into a yaml composite step (architectural principle: a rule that lands in N places must be consolidated into 1 place).
    - **Data source**: the family dictionary is the ImageFamily reference (image_families); official docs [DescribeImageFromFamily](https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-describeimagefromfamily)

28. **AK/SK never enter the conversation + credential config is run in the user's local terminal**: this iron-rule is **fully independent of and non-overlapping with iron-rule #13 (CLI install)**.
    - **Forbidden (NEVER)**: read/print/echo AK/SK values (incl. `cat ~/.aliyun/config.json`, `echo $ALIBABA_CLOUD_ACCESS_KEY_ID`, log output); let the user paste AK/SK in the conversation; put literal credential values in command-line args; use expect/echo pipe inside the skill to feed credentials to `aliyun configure`; use `--mode AK` permanent credentials
    - **Only allowed**: ① `aliyun configure list` to check profile type and the masked last 3 chars; ② **the user runs, in their local terminal**, `aliyun configure --mode RamRoleArn --profile opc` interactively (the skill only outputs the command template, never auto-feeds values via stdin/expect); ③ verify with a one-liner `aliyun sts get-caller-identity --profile opc`
    - **Tighten on write**: chmod 600 immediately after writing ~/.aliyun/config.json / ~/.ssh/opc-deploy.pem / outputs/state/*.json
    - **Missing-credential handling**: STOP the flow → output the Phase 0.3 three-step modeling guide → the user runs `aliyun configure --mode RamRoleArn --profile opc` in their local terminal → verify with `sts get-caller-identity` on return

29. **VPC reuse / ownership state field**: when the Phase 2.1 query for `Tag opc:managed=true` returns nothing, **additionally** list all VPCs under the account for the user to choose "reuse existing / create new" — under `QuotaExceeded.Vpc` the account already has VPCs but without the opc:managed tag. state must record `resources.vpc.owned: true|false`:
    - `owned: true` (newly created) → `DeleteVpc` closes the loop on teardown
    - `owned: false` (reusing someone else's) → **skip `DeleteVpc`** on teardown, only reclaim the self-created VSwitch (if any) / SG / ECS, **never** delete the user's existing VPC
30. **CreateKeyPair private key masking + never enters conversation/state** (reinforces iron-rule #7/#15):
    - CreateKeyPair has **no** `--output-file` option; the private key is returned in the response `PrivateKeyBody` field — pipe it straight to `~/.ssh/opc-deploy.pem` (never to stdout), then `chmod 600`
    - **Never** write the full private key into stdout / conversation log / state.json
    - Output only the first and last 8 chars + a `<hidden middle N bytes>` form (e.g., `-----BEGIN... <hidden 1640 bytes> ...END-----`)
    - User-facing message:

```text
✓ 已为你生成专用密钥并设为仅本人可读，保存在 ~/.ssh/opc-deploy.pem。私钥内容不会出现在对话里。
```

31. **Windows platform gating + ConstrainedLanguage detection**: Phase 0.1 additionally runs on the Windows platform:
    - WDAC/AppLocker probe: `Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard` to check `CodeIntegrityPolicyEnforcementStatus`
    - PowerShell ConstrainedLanguage probe: `$ExecutionContext.SessionState.LanguageMode -eq 'ConstrainedLanguage'`
    - If any blocking signal hits → immediately give the user two options: ① contact the IT admin to request an exception (`Add-AppLockerPolicy` / WDAC supplemental policy); ② switch to a macOS/Linux terminal to run this skill. **Do not teach the user to bypass signature verification or downgrade the language mode**.

32. **Non-blocking info display after Phase 0.4 image resolution**: the [Y/n] blocking echo is deprecated — a non-technical user cannot judge whether an ImageId hex string (e.g., `aliyun_3_x64_20G_alibase_20260513.vhd`) is correct, so [Y/n] is security theater; the meaningful confirmation was already done at the advisor layer (family + os_series plain-language name + purpose shown for the user to decide the OS direction). At the deploy layer, after the Phase 0.4 resolution, switch to a **non-blocking info display** (info only, does not wait for the user to confirm):

```text
✓ 已锁定服务器镜像：
   系统：${image.os_series}（${image.arch}）
   发布版本：${image.creation_time} 的官方镜像
   这是 advisor 在 ${image.family_pinned_at} 锁定的次版本，会写入 state 永久绑定——
   后续扩容/重建复用同一镜像，避免半夜偷偷换 OS 大版本炸应用。
```

    - After displaying, proceed directly to Phase 1, **do not wait for a [Y/n] answer** — echoing the ImageId hex to the user can't be ACK'd anyway; it is pure informational transparency
    - If the user proactively says "I want to change the image / upgrade the OS" → guide them back to advisor to re-issue the prescription (consistent with the iron-rule #27 hard-stop wording)
    - **state reuse case**: when state.resources.ecs.image_id already exists, **skip this display** (already confirmed and locked at the advisor layer), use the state ImageId directly; only re-enter Phase 0.4 resolution when the user explicitly says "change the image"

33. **Fallback when a ControlPolicy blocks DryRun**: dry-run testing shows an enterprise RAM account's ControlPolicy returns `Forbidden.RAM` + `NoPermissionType: ExplicitDeny` for `RunInstances --dry-run true` — even a simulated run is rejected, which makes the "DryRun price-inquiry hard-stop loop" in iron-rules #11 / #27 fail under enterprise accounts:
    - The Phase -1.5 probe adds an "empty DryRun probe" (the default ImageId comes from a dynamic lookup, avoiding a hardcoded literal expiring as Alibaba Cloud publishes new images monthly):
      ```bash
      # First run a family resolution to get the current ImageId as the probe default
      DEFAULT_IMAGE_ID="${state.resources.ecs.image_id}"
      if [ -z "$DEFAULT_IMAGE_ID" ]; then
        DEFAULT_IMAGE_ID=$(aliyun ecs describe-image-from-family \
          --image-family acs:alibaba_cloud_linux_3_2104_lts_x64 \
          --biz-region-id ${region} \
          | python3 -c "import sys,json;print(json.load(sys.stdin).get('Image',{}).get('ImageId',''))")
        # ⚠️ Do NOT use `--output cols=ImageId rows=Image` here: DescribeImageFromFamily returns Image as a
        #    single OBJECT, and `--output rows=` requires an array — it dies with
        #    "jmespath 'RootFilter[0].Image' failed: need array expression" (quoting does not help).
        #    Parse the raw JSON instead. Where `rows=` IS an array path, single-quote it so zsh cannot
        #    glob-expand the `[]`.
        # Still empty → fall back to DescribeImages --image-family (consistent with iron-rule #27)
        if [ -z "$DEFAULT_IMAGE_ID" ]; then
          DEFAULT_IMAGE_ID=$(aliyun ecs describe-images \
            --image-family acs:alibaba_cloud_linux_3_2104_lts_x64 \
            --status Available --image-owner-alias system \
            --biz-region-id ${region} --page-size 1 \
            --output cols=ImageId 'rows=Images.Image[]' | tail -n 1)
        fi
      fi
      # Still empty → skip the probe (do not hardcode a literal), continue assuming "no ControlPolicy"; if a later real API fails, go to fallback
      [ -n "$DEFAULT_IMAGE_ID" ] && aliyun ecs run-instances --dry-run true \
        --instance-type ecs.e-c1m1.large \
        --image-id "$DEFAULT_IMAGE_ID" \
        --system-disk-category cloud_essd_entry \
        --system-disk-size 40 \
        --biz-region-id ${region}
      ```
      (An early spec used a hardcoded default `${state.resources.ecs.image_id:-aliyun_3_x64_20G_alibase_20260513.vhd}`; after half a year Alibaba Cloud publishes new images and that literal expires, causing a 0-hit probe misjudgment; now it is dynamically resolved, and when no usable ImageId exists it simply skips the probe — more honest than pretending to run a DryRun with an expired literal.)
    - Hit `Forbidden.RAM` + `PolicyType: ControlPolicy` → write `state.environment.dryrun_blocked = true`
    - All subsequent write APIs (RunInstances / CreateVpc / CreateDBInstance, etc.) **no longer DryRun**, switching to the "DescribePrice inquiry first + user confirmation + call the real creation directly" path
    - If the real creation is also rejected by the ControlPolicy → immediately go to `fallback_route` (ROS template share link / console direct link), no more CLI trial-and-error (paired with iron-rule #26)

34. **Policy coverage must be proven BEFORE spending money (Step 0.2b probe · red line)**: a credential that authenticates is NOT a credential that is authorized. Before leaving Phase 0 — and unconditionally before the first fee-incurring API call — run the Step 0.2b policy coverage probe (`policy-probe.md`) once per product in THIS SKU's product set (the set narrowed in Phase -1.5). Every probe is a read-only Describe/List that creates nothing and costs nothing, so there is never a justification for skipping it.
    - Any probe indicating a permission failure → **STOP**. Do not enter Phase 1, Phase 2, or Phase 3. **Detect it broadly, not by exact code**: judge on `StatusCode: 403` or the presence of `Forbidden` / `NoPermission` / `not authorized`; the Code differs per product (rds `Forbidden`, alb `Forbidden.LoadBalancer`, ess `Forbidden.Unauthorized`, swas-open `NoPermission`, vpc/ecs `Forbidden.RAM`, and oss returns plain text with no Code field at all). Matching only "NoPermission" or only "Forbidden.RAM" silently passes a denied product and defeats this rule. Report **every** uncovered product at once (do not surface them one per round-trip), then hand the user a **whole-policy replacement JSON scoped to this SKU** plus the RAM console `创建新版本 → 设为当前版本` steps. Never an incremental patch (it reliably misses companion actions such as `rds:AddTagsToResource`), never the all-SKU superset (that is a least-privilege violation against a starter user), and never a bare `去加下权限` without the JSON.
    - Emit the JSON **unprompted** — waiting for the user to ask for it is a violation of this rule.
    - Never attempt `ram:GetPolicy` / `ram:CreatePolicyVersion` to inspect or repair the policy yourself: both are denied to `opc-deploy-role` by design (a role that can widen its own permissions defeats the whole least-privilege model), and retrying them only burns the iron-rule #26 retry budget.
    - Probing is internal machinery: never narrate it to the user (no `探针 / 门控 / gate / 覆盖度`), only the plain-language permission copy.

35. **A result obtained by working around a failure is NOT a clean result (silent-false-green red line)**: when one goal is attempted more than once and the attempts **disagree** — one call form errors out, another call form returns 200 — you must NOT report the successful one as the answer and drop the failure. That is how a user gets told `✅ 权限没问题` while the real state is unknown.
    - **Applies to every probe, price inquiry, and status check**, and to any pair of attempts differing in call form (kebab vs PascalCase, with vs without `--endpoint`, before vs after a plugin install), region, or profile.
    - **Required behaviour**: treat the goal as **INCONCLUSIVE**, not as passed. Tell the user, in Chinese, all three facts: what failed and how (quote the error code verbatim), what succeeded and how, and that because the two disagree you are **not** treating this as confirmed. Then stop that goal and let the user decide.
    - **Never write an unqualified conclusion** (`权限检查通过` / `已确认可以开通` / `✅ 通过`) into the conversation, the summary card, the state file, or any output file when an earlier attempt at the same goal failed. If a written report is produced, the disagreement must appear in it — a report that only records the successful attempt is a falsified record.
    - **This overrides the natural instinct to "route around" a broken call.** Rewriting a call until something returns 200 proves nothing about the original path.
    - Combined with iron-rule #26's per-goal budget: reaching disagreement means you have already spent the budget. Do not spend more attempts trying to break the tie — report the tie.

---

## Credential Safety Rules (Alibaba Cloud Credentials Security · RamRoleArn as the only path)

> Aligned with the skills.aliyun.com official unified skill security spec + internal security audit. This rule has higher priority than all other flow steps.
> It applies regardless of which AI terminal it runs in (QoderWork / Claude Code / Cursor / Codex / WorkBuddy).

**Absolutely forbidden (NEVER)**:
- Read, print, or echo any AK/SK value (incl. `cat ~/.aliyun/config.json`, env-var echo, log output)
- Let the user paste AK/SK into the chat window
- Use literal credential values in command-line args (e.g., `aliyun configure set --access-key-id LTAI...`)
- Write credentials into script files, env-var export statements, or anywhere that might be recorded by shell history
- **Use `--mode AK` to configure a permanent AccessKey as the deployment credential** (the permanent-AK path is removed)

**The only allowed operations**:
- `aliyun configure list` — check credential config status (shows only the masked AK:***xxx, never the full value)
- `aliyun configure --mode RamRoleArn --profile opc` — interactively perform STS role-assumption config (the default and only path):
  - Sub-account AK ID/Secret (carries only AliyunSTSAssumeRoleAccess, cannot call business APIs directly)
  - RamRoleArn (role ARN, e.g., `acs:ram::<UID>:role/opc-deploy-role`)
  - RoleSessionName (session name, e.g., `opc-deploy-session`)
  - DefaultRegionId / DefaultLanguage
  - Credentials go directly into the CLI credential store (~/.aliyun/config.json, chmod 600 immediately after writing), bypassing the conversation log
  - On each subsequent API call the CLI automatically performs STS AssumeRole to obtain a temporary token (1h validity); even if the permanent AK leaks, the attack surface is doubly limited by Policy + time window

**Handling when credentials are missing or not of RamRoleArn type**:
1. STOP the current flow
2. Output the RAM three-step modeling guide (see Phase 0.3): ① sub-account ② role ③ custom Policy
3. Run `aliyun configure --mode RamRoleArn --profile opc` and have the user enter values at the interactive prompt
4. Verify with `aliyun configure list` that the profile type is RamRoleArn
5. Pass → continue; fail → repeat the guide

**Handling when the user accidentally sends credentials**:
- Remind immediately with:

```text
请不要在对话里发凭证，我不需要看到具体内容。
```

- Do not use the credential, do not store it, do not echo it

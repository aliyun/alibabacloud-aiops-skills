---
name: alibabacloud-opc-deploy
description: "Provision a one-person company's Alibaba Cloud setup: once a package (SKU) is chosen, create and configure all the cloud resources the user needs, explaining progress at every step. WHEN TO USE: the user asks to provision / deploy / create their cloud resources, names a package directly, or continues right after the advisor's recommendation. Creating cloud resources costs money — never trigger without explicit user confirmation. 触发词（中文）：帮我开通 / 帮我部署 / 帮我创建资源 / 开始部署；直接报 SKU 名（如\"帮我开一个 lite_seed\"）；advisor 推荐完接下来怎么办。输出用中文。"
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

**Self-sufficient operation:** the only hard dependency of this skill is the **SKU name** — use the advisor prescription (structured fields) when present; when absent (a new session where the user names the SKU directly / advisor not installed) it still runs via built-in defaults (image family, starter fallback config, and capability boundaries are all built in). Never error out or relax safety boundaries just because advisor context is missing.

**Never auto-trigger:** creating cloud resources is a money-spending action and requires explicit user confirmation.

**BLOCKING RULE (no SKU = no action):** If the user's message does not contain a recognized SKU name (one of the 7 below) AND no advisor prescription is in context, the agent MUST NOT proceed to any Phase. It must immediately output the advisor-install guidance and STOP. Inferring, guessing, or self-selecting a SKU is a critical violation (see the SKU GATE in Hard Gates).

## Supported 7 SKUs

| SKU | Resources involved | Complexity |
|---|---|---|
| starter_webui (main path, ¥99/yr promo hit) | ECS economy-e + ESA Free | ⭐ |
| starter_webui (fallback: pay-by-traffic ¥284.99/yr when promo missed) | ECS economy-e PayByTraffic 100Mbps + ESA + CloudMonitor traffic alarm | ⭐ |
| starter_app | ECS economy-e + [Token Plan manual] + [PDS manual] (shares fallback with webui) | ⭐⭐ |
| lite_seed | SWAS swas.s.c2m4s50b1.linux (OpenClaw) + ECS c9i.large + RDS mysql.n2e.small.1 + OSS + [Token Plan manual] | ⭐⭐⭐ |
| lite_growth | same as above, RDS upgraded to mysql.n2.medium.1 | ⭐⭐⭐ |
| lite_traction | same, ECS upgraded to c9i.xlarge + RDS to mysql.n2.large.1 | ⭐⭐⭐ |
| pro_steady | SWAS + ECS×2 + RDS HA mysql.n2.large.2c + OSS + ALB + ESA medium + [Token Plan manual] | ⭐⭐⭐⭐ |
| pro_burst | same as pro_steady + ESS auto-scaling | ⭐⭐⭐⭐⭐ |

## Iron Rules + Credential Safety

See `references/iron-rules.md` (33 iron rules + credential safety rules).

Core principles (summary):
- User confirmation before spending money + a second confirmation before payment
- AK/SK never enter the conversation; credential SETUP is RamRoleArn-only, and an already-configured credential is USED as-is (see iron-rule #16)
- Step-by-step execution + step-by-step reporting; never fail silently
- The state file must be written; sensitive files are chmod 600
- SKU product CLI-reachability static gate (Phase -1.5 precondition)
- Image selection is centrally resolved in Phase 0 + permanently bound in state

---

## Execution Flow

See `references/execution-phases.md`.

| Phase | Name | Summary |
|-------|------|------|
| -1 | Pre-checks | Confirm Alibaba Cloud account + real-name verification + desktop AI tool |
| -1.5 | CLI reachability gate (**MANDATORY standalone** — run before Phase 0; do NOT merge into Phase 0/2 or skip) | For every product this SKU touches, determine CLI reachability by **STATIC table lookup in `references/cli_capability_matrix.md` ONLY — do NOT run any aliyun CLI command to probe/verify reachability at this phase (iron-rule #25; the first real CLI call is in Phase 0)**. On any console-only product (e.g. Token Plan = console-only, no CLI path), your user-facing summary MUST explicitly name it as a manual console step and take the fallback BEFORE proceeding — never omit it or list only the CLI-reachable products. |
| 0 | Env + auth | CLI install (fully automated) + credential config (RamRoleArn) + centralized image resolution (exact ImageFamily from advisor, else default Linux 3 2104 LTS; Linux 4 is experimental and forbidden for production) |
| 1 | SKU + confirm | Identify SKU (strong-signal fast-path) + price inquiry (starter dual-tier) + resource list + component-removal opt-out + second payment confirmation + pre-execution hard-gate self-check |
| 2 | Network infra | VPC (reuse-first) + VSwitch + security group. Whether you CREATE or REUSE the security group, you MUST call `authorize-security-group` to tighten SSH (port 22) to `${MY_IP}/32` for the current user — never skip it on reuse or assume an existing group's rules are correct (HTTP 80 / HTTPS 443 stay 0.0.0.0/0). |
| 3 | Create resources | Execute in order per `references/sku-params/<sku>.yaml` steps. AFTER EACH create call: (a) call TagResources to attach `opc:managed=true` + `opc:sku=<sku>`; (b) write the resource ID + status to the state file. Both are mandatory before proceeding to the next step. |
| 4 | Verify + wrap-up | Status verification + summary card + "what's next" + renewal reminder + emergency three-step incident card + state save + wrap-up completeness hard-gate |

## Hard Gates (MUST NOT bypass)

The following gates are **internal** self-interception rules. If ANY gate is violated, the agent must STOP and self-correct before proceeding. **Never narrate or label these gates to the user**: do not say things like "this is a hard/mandatory security gate/checkpoint", and never show the words HARD BLOCK / gate / self-interception / critical violation in user-facing text. The user only ever sees the natural, friendly prompts (e.g. the plain payment-confirmation line) — the gate machinery is yours alone.

1. **PAYMENT GATE (HARD BLOCK — enforced for weak and strong models alike)**: Immediately BEFORE the first fee-incurring API call (RunInstances / CreateInstance / swas-open CreateInstances / PurchaseRatePlan / CreateDBInstance / CreateLoadBalancer / CreateScalingGroup — anything that spends money), run a literal self-interception: since showing the resource list, have I (a) output the EXACT prompt below verbatim, AND (b) received an explicit affirmative reply that authorizes the CHARGE? If NO → **STOP, DISCARD the pending create call, output the exact prompt below verbatim, and wait for the reply.** An earlier deploy-intent reply (a "let's deploy / start creating / confirm purchase"-style message given BEFORE this prompt) is INTENT only and does NOT authorize the charge — never treat it as payment authorization. **Amount rule**: ¥XX MUST be the actual price from Phase 1's inquiry — the promo price when the ¥99/yr promo is hit, or the fallback price (≈¥284.99/yr) when it is missed; never a placeholder or estimate. Keep the fenced prompt below as the ONLY thing shown to the user here — do NOT append internal matching criteria to the user-facing prompt. Output it verbatim (fill ¥XX with that real amount):

```text
🌐 网站端口（80/443）将对公网开放，互联网上的访客都能访问你的站点；远程登录（SSH）只对你自己的 IP 开放。
即将从你的阿里云账户扣款 ¥XX（包年/包月），确认付款？
```

The first line of the prompt above discloses that the website's 80/443 ports will be open to the public internet — it rides in the same block so the single confirmation covers both the charge and the public exposure (required by security review; omit it only when the deploy opens no public ports). Free resources (VPC / VSwitch / SecurityGroup / KeyPair) do NOT need this gate; only the first PAID call does. This is a hard gate, not a suggestion — skipping it, or paraphrasing the prompt instead of outputting it verbatim, is a critical violation. **User-facing tone**: to the user, show ONLY the payment prompt itself, in a natural friendly voice; do NOT narrate or label the gate's internal status (no "this is a hard / mandatory security gate / checkpoint"-style meta-commentary) — that framing is internal to you, never for the user. The words "HARD BLOCK / gate / self-interception / critical violation" must never appear in what the user sees.

2. **SKU GATE**: If no valid SKU name (one of the 7 listed in this file) exists in the conversation AND no advisor prescription is in context, STOP immediately. Output the advisor-install guidance (iron-rule #9). Never infer, guess, or self-select a SKU — this is a critical violation. **HARD self-check before ANY Phase**: scan the user's message for one of the 7 exact SKU tokens (starter_webui / starter_app / lite_seed / lite_growth / lite_traction / pro_steady / pro_burst). A vague deploy intent with no SKU token is NOT a SKU — you MUST discard any drafted plan, output the advisor-install guidance, and STOP; mapping such phrasing to a SKU (e.g. starter_app) is the critical violation. Example vague phrasings that carry NO SKU token (must trigger advisor-install + STOP, never a deploy):

```text
帮我搞一下阿里云，想弄个东西上线 / 帮我部署一下 / 帮我上个网站 / 想做个东西上线
```
3. **ERROR GATE**: On any non-200 or unexpected CLI error during Phase 2/3, STOP execution immediately. Output a structured error report (which step + error code + suggestion), then present three options and wait for user choice:

```text
[1] 帮我全部收回（释放已创建资源）
[2] 先留着，我稍后再试
[3] 我自己去控制台处理
```

Never silently retry, skip the failed step, or report "deployment complete" when any step has failed.

4. **SPEC GATE**: The InstanceType and ImageId for each create step come exclusively from the resolved state and the SKU yaml. Substituting a different instance type (e.g., e-c1m2 instead of e-c1m1) or a different OS major version (e.g., Linux 4 instead of Linux 3) is forbidden.

---

## SKU Parameter File Format

See `references/sku-params-format.md`.

Each `references/sku-params/<sku>.yaml` defines the deployment step sequence for one SKU, containing `sku` / `variant` / `version` / `region_default` / `user_summary` / `steps[]`. This file also contains the OpenClaw image dynamic-lookup logic.

---

## Observability

Every `aliyun` CLI call this skill issues MUST carry a unified User-Agent and session-id:

- **User-Agent**: `AlibabaCloud-Agent-Skills/alibabacloud-opc-deploy/{SESSION_ID}` — e.g. `AlibabaCloud-Agent-Skills/alibabacloud-opc-deploy/a1b2c3d4e5f60718293a4b5c6d7e8f90`. Pass it on every call via `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-opc-deploy/${SESSION_ID}"` for server-side tracing.
- **Session-ID**: `{SESSION_ID}` is a **32-char lowercase hexadecimal** string matching `[0-9a-f]{32}` (NOT a UUID; e.g. `a1b2c3d4e5f60718293a4b5c6d7e8f90`), generated once per deployment session and reused across every CLI call in that session. When invoked downstream of `alibabacloud-opc-advisor`, inherit the advisor session-id. Stored in `state.session_id`, and also passed as `--client-token` where supported (e.g., `run-instances`, `create-vpc`) for idempotency.
- **Logging**: All CLI invocations and their exit codes are logged to `state/<sku>-<timestamp>.json` under `execution_log[]`.

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
| Zone.NotOnSale / InventoryShortage | Retry in another zone (auto-try the next zone) |
| QuotaExceeded | Tell the user to open a ticket → https://smartservice.console.aliyun.com/service/create-ticket |
| Timeout (polling >5 min after creation) | Tell the user the resource is still being created and may take a few more minutes + give the console link so they can check themselves |
| Network error | Auto-retry once → then report the failure |

**MANDATORY post-error interaction (ERROR GATE):** After any error above, the agent MUST report the failing step + error code + suggestion, then present three options and wait for the user's choice — roll everything back (release created resources in reverse order) / keep current state and retry later / handle it yourself (with console deep-links). The agent MUST NOT silently retry, skip the failed step, or report "deployment complete" when any step has failed. (Retry is capped at 1 and region-switch-only per iron-rule #26; multi-posture trial-and-error is forbidden.)

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
- **CLI version & verification:** `references/cli-meta.md`
- **Detailed execution steps:** `references/execution-phases.md`
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

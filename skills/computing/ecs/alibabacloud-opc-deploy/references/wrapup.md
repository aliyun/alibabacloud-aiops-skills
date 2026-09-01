# Phase 4: Verify + wrap-up · and deployment-failure teardown

> Final phase, plus the teardown path used whenever a Phase 3 step fails.
>
> - **Entry**: all yaml steps executed.
> - **Exit**: Step 4.6 wrap-up hard-gate all green → session may end.
> - Teardown at the bottom is also what to use for reclaiming a partially built deployment.

### Phase 4: Verify + wrap-up

```text
Step 4.0: Image optimization (optional local enhancement · never install packages on the production server)
  Only the starter_webui website-deployment scenario, and **all done on the user's local machine or before upload**:
    1. Detect whether the user's local machine has cwebp (macOS: which cwebp / Linux: which cwebp)
       - has → locally batch-convert .png/.jpg to WebP: cwebp -q 80 input.png -o output.webp (target < 200KB)
            → update the image references in the HTML in sync (.png/.jpg → .webp)
            → upload the WebP files
       - none → **skip** optimization, upload the originals directly (no blocking, no error, no prompt to install)
    2. ⚠️ Do NOT run yum install / apt install / pip install of any package on the created ECS/SWAS (iron-rule #19)
    User-facing copy:
      has cwebp: "✓ 图片已本地压缩为 WebP 格式（页面加载更快）"
      no cwebp: "（跳过图片压缩，直接上传原图——网站功能不受影响）"

Step 4.1: Verify all resource statuses
  Query each one to confirm it is in a healthy state (Running / Available / Active)

Step 4.2: Output the summary card (metaphor ↔ official-name mapping)
  All resources' IP / domain / connection string / console link
  Monthly-cost total confirmation
  ⚠️ This total is what the delivered stack costs **per month from here on**, and it is required
  even when this run charged nothing. The trap: when every resource is reused from a prior
  prepaid deployment and the card reports only `本次扣款：¥0`, the user is left thinking the
  stack is free, while the inherited SWAS + ECS + RDS keep billing until their paid-until
  date. **`本次扣款` and `月费合计` are two
  different numbers and both must appear**: what moved out of the account during this run,
  and what the stack costs every month going forward (reused resources included, with their
  paid-until date). A run that charged ¥0 still owes the second number.
  Extra: dynamically build a "metaphor → official Alibaba Cloud name → resource ID" mapping from state, e.g.:
    "你的小店面" → "云服务器 ECS" (i-2ze...)
    "AI 助理（OpenClaw）" → "轻量应用服务器 SWAS" (swas-...)
    "数据存储空间" → "云数据库 RDS MySQL 高可用版" (rm-...)
    "文件仓库" → "对象存储 OSS" (bucket-...)
    "全球加速" → "边缘安全加速 ESA" (esa-...)
    Note to the user: "万一遇到问题需要联系阿里云客服，用右边的正式名称沟通会更快。"

Step 4.3: Output "what's next"
  Starter (has_desktop_tool = true — you have local-execution capability, i.e. you ARE the desktop assistant):
    "告诉我（你正在用的这个 AI 助手）：帮我把代码部署到 ${ecs_public_ip}，我来帮你远程搞定"
  Starter (has_desktop_tool = false — chat-only runtime with no local shell; qwcn-pro is self-purchased, not in the package price):
    "① 下载安装 QoderWork CN Pro（¥59/月，你自己订阅，不含在套餐里）：
        👉 https://qoder.com.cn/qoderwork
     ② 打开它 → 告诉它：帮我把代码部署到 ${ecs_public_ip}
     它会帮你远程操作服务器、安装环境、部署代码。"
  Lite/Pro:
    "打开 AI 助理（OpenClaw）：
     👉 登录轻量应用服务器控制台 https://swas.console.aliyun.com/
     → 找到你刚创建的应用「${swas_instance_name}」→ 点「应用详情」→ 点「登录 Web UI」按钮
     → 用控制台显示的 Token 登录 → 告诉 AI 助理你的项目"
    (No longer a raw IP+8080 entry; goes through the SWAS white-box channel — random port + Token + public access off by default)

Step 4.4: Renewal reminder
  User-facing copy:
    "📅 关于续费：你这次买的资源都是预付费的，**自动续费已默认关闭**。
     - 到期前 7 天，阿里云会发短信和站内信提醒你续费
     - 如果想继续用，到时候去续费管理页操作即可：
       👉 https://billing-renew.console.aliyun.com/
     - 如果不想续，到期就会自动停止，不会有沉默扣费"

Step 4.4.5: "Don't panic" three-step incident card (emergency guide · credentials and resources are live, tell the user once)
  Meaning: after deployment the credentials (sub-account / RamRoleArn) and cloud resources are genuinely live,
        this is the "what if something goes wrong" backstop card — migrated from advisor, belongs to the deploy stage.
  User-facing copy:
    "🆘 出事别慌·三步卡（万一 AccessKey 泄露、或发现账号有异常操作，按这三步走）：
     - 第一步：禁掉 AccessKey → 控制台 > 访问控制 > AccessKey 管理
       👉 https://ram.console.aliyun.com/users → 禁用可疑 AccessKey
     - 第二步：查账单和资源有没有异动 → 费用中心 > 账单明细
       👉 https://usercenter2.aliyun.com/finance/expense-report/bill-detail → 看有没有你没开过的资源在计费
     - 第三步：提工单 → 阿里云工单
       👉 https://smartservice.console.aliyun.com/service/create-ticket → 描述现象贴时间点，阿里云会协助止损"

Step 4.5: Save the final state (state is also chmod 600)
  Write outputs/state/<sku>-<timestamp>.json
  chmod 600 outputs/state/<sku>-<timestamp>.json immediately after writing
  ⚠️ Tell the user:
    "state 文件保存在 workspace 目录下，已设置仅本人可读权限。
     里面包含公网 IP、内网 IP、RDS 连接串等基础设施信息（密码不在内）。
     建议你**不要把 workspace 目录同步到公共云盘**（如百度网盘/iCloud 同步盘），
     如果用 macOS Time Machine 备份，记得把这个目录排除或加密外置盘。"
  state **NEVER** contains a plaintext database password (iron-rule #7):
    rds.account_password_set: true
    rds.account_password_set_at: "2026-06-24T18:00:00+08:00"
    (the password was told to the user once in the step report, not kept in the file; if lost use ResetAccountPassword)

Step 4.6: Wrap-up structural-integrity hard-gate (HARD BLOCK · every item must pass before ending the session)
  ⚠️ Hard gate, not a soft hint. Missing any section → discard the current wrap-up output, fill it in, and resend; do not end the session directly.
  [ ] 1. Summary card: includes the "比喻↔阿里云正式名↔资源 ID↔状态" mapping + public IP/connection string (Step 4.2)
  [ ] 2. Monthly-cost total + the "价格供参考，实际以最终下单为准" disclaimer (Step 4.2). A ¥0-charge
         run does NOT satisfy this item: `本次扣款：¥0` is the charge line, not the monthly total.
         If resources were reused, state their combined monthly cost and paid-until date anyway.
  [ ] 3. "What's next" (the right entry per has_desktop_tool / SKU type, Step 4.3)
  [ ] 4. Renewal reminder (auto-renew off by default + renewal-management link, Step 4.4)
  [ ] 5. "Don't panic" three-step incident card (Step 4.4.5)
  [ ] 6. state written and chmod 600, and contains no plaintext password (Step 4.5)
  [ ] 7. Public IP AND private IP are printed IN FULL using the actual resolved values — never a truncated "47.94.xxx.xxx" / "10.0.0.x" / "..." placeholder copied from the template
```

---

## Deployment-failure teardown

If any post-creation step in Phase 3 fails → enter the teardown decision dialogue.

⚠️ **Exception — a missing OSS bucket because the user hasn't bought the storage package is NOT a failure.**
Do NOT open this teardown dialogue for it. `403 UserDisable` on the bucket call means the service isn't
activated yet, which is a pending user purchase, not a broken deployment. Keep every created resource, finish
the wrap-up normally, and mark the one gap plainly:

```text
✅ 其余资源都已就绪。只差那个文件仓库——你的账号还没开通对象存储服务，
   买存储包的时候会一起开通。买好随时告诉我，我几秒就能给你补上。
```

Offering to roll back working paid infrastructure over one unpurchased storage package is a serious
misjudgement: the user would lose the ECS/RDS/SWAS they already paid for. Same reasoning applies to any other
`type: manual` item the user deferred (Token Plan / PDS) — deferred self-purchases never trigger teardown.

For genuine failures (create API errors, stock-outs, quota, permission gaps):

```text
User-facing copy:
"创建过程中卡住了：[失败步骤的对客描述]。
 已经创建的资源会按月/年付费，需要决定怎么处理：

 [1] 帮我全部收回（释放已创建资源，本次不收费/退款按阿里云规则）
 [2] 先留着，我稍后再试或者提工单看看
 [3] 我自己去控制台处理"
```

Choosing [1] → call Delete*/Release* APIs in **reverse order** of state.created_resources:
- Order example (Pro): ESS → ALB → RDS → OSS → ECS → SWAS → ESA → SecurityGroup → VSwitch → VPC
- **OSS teardown uses ossutil, not an OpenAPI Delete call**: `aliyun --profile opc ossutil rb oss://<bucket> --region <region>` (E2E-verified on CLI 3.4.11). `rb` only deletes an EMPTY bucket — if the user put objects in it, `rb` fails and you must say so and let them decide, never pass `--force` unasked (that silently destroys their data). The legacy `oss` verb is deprecated; do not fall back to it.
- **Tag-then-delete robustness (E2E-measured fix)**: for the tag-conditioned resources (ECS / SecurityGroup / VSwitch / VPC / ALB / ESS scaling-group), FIRST call TagResources `opc:managed=true` (an unconditional Allow in opc-deploy-policy), THEN call Delete. Rationale: if the create-time tag backfill was skipped (weak models sometimes tag the SG but miss the VPC/VSwitch), DeleteVSwitch/DeleteVpc are denied `Forbidden.RAM` because the teardown condition requires `opc:managed=true`; tagging immediately before delete makes teardown succeed regardless. VSwitch: `aliyun vpc tag-resources --biz-region-id <region> --resource-type VSWITCH --resource-id <id> --tag Key=opc:managed Value=true`; VPC: same with `--resource-type VPC`.
- Report each Delete call to the user individually (one "✓ released <plain-language name>" line per resource)
- **VPC ownership awareness (iron-rule #29)**: before teardown, read `state.resources.vpc.owned`:
  - `owned: true` (self-created) → normal DeleteVpc closure
  - `owned: false` (reusing someone else's) → **skip DeleteVpc**, only reclaim the self-created VSwitch/SG/ECS, and tell the user that this VPC was not created by the current deployment so it is left untouched
- Partial failure: skip that resource and continue to the next; finally summarize the un-released list + console deep links for the user to handle manually
- ⚠️ Delete permission is constrained by the RAM Policy Tag Condition (can only delete `opc:managed=true` resources), so even a runaway skill won't wrongly delete the user's other resources
- ⚠️ Leftover free resources still consume quota (VPC quota is 1 per region by default) — a VPC left behind from an earlier aborted run will make the next deployment fail at Step 2.2 with `QuotaExceeded.Vpc`. When the user stops mid-run, offer to reclaim the free resources too, not just the paid ones.
- API notes:
  - **Deletes propagate asynchronously — expect `DependencyViolation.*` and wait it out (E2E-measured, twice).** `DeleteVpc` right after `DeleteVSwitch` commonly returns `DependencyViolation.VSwitch` even though the VSwitch delete already returned a RequestId: the dependency has not cleared yet. Do NOT report this as a teardown failure and do NOT hand the user a manual-cleanup link on the first hit — sleep ~10s and retry, up to ~6 attempts (≈1 min), and treat `InvalidVpcId.NotFound` as success (an earlier call did land). The same pattern applies to `DeleteVSwitch` after releasing an instance, and to `alb:DeleteLoadBalancer` before its listeners/server-groups are gone. This wait is not the iron-rule #26 retry budget — that rule governs reachability errors, whereas this is a known-eventual-consistency wait.
  - `ecs:RevokeSecurityGroup` is needed if you revoke individual rules before deleting a group (E2E-measured `Forbidden.RAM` when it was missing from the policy). Simpler and usually sufficient: skip per-rule revoke and call `DeleteSecurityGroup` directly — the rules go with the group.
  - ESS scaling rule: creation returns a ScalingRuleAri (e.g. `ari:acs:ess:...:scalingrule/asr-xxx`); delete with `DeleteScalingRule --scaling-rule-id asr-xxx` (take the last ID segment of the ARI)
  - RDS: the instance-release API is `rds DeleteDBInstance --db-instance-id xxx` (not ReleaseDBInstance)
  - ESS scaling group: must `DisableScalingGroup` first, then `DeleteScalingGroup` (cannot delete while active)

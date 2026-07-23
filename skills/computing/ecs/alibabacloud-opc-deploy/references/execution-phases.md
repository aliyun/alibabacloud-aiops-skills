# Execution Phases

> Split out from SKILL.md; contains the complete execution steps from Phase -1 to Phase 4. Instructional text is English; the quoted `"..."` strings are the Chinese user-facing output templates the skill speaks to the user.

## Execution Flow

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

Step -1.2: Take over code-deployment capability (default = the current AI terminal)
  This skill necessarily runs inside some AI terminal (QoderWork / Claude Code / Cursor / Codex / WorkBuddy, etc.).
  Since the user could invoke this skill, they are already using an AI assistant capable of remote deployment — no need to ask "do you have a desktop tool".
  → Default has_desktop_tool = true, do NOT ask; directly take over the current-assistant identity and give the bridging explanation (starter_webui example):
    "你的套餐里包含：一台服务器 + 全球加速。
     代码部署上去这件事，我（你正在用的这个 AI 助手）就能帮你远程搞定，不需要额外买东西。
     接下来我先帮你把云端资源开好（服务器 + ESA 加速）。"
  Rare fallback: only when the current terminal genuinely lacks remote-deployment capability (cannot run a local shell / SSH) →
    record has_desktop_tool = false, give the bridging explanation + guide a download:
    "你的套餐里包含：一台服务器 + 全球加速。
     服务器创建好之后，需要一个能远程操作服务器的桌面 AI 助手来帮你部署代码。
     推荐下载 QoderWork CN Pro：
     👉 https://qoder.com.cn/qoderwork
     （可以先创建服务器，回头再装桌面工具也行）"
```

### Phase -1.5: SKU product CLI reachability static gate (iron-rule #25)

```text
⚠️ STATIC LOOKUP ONLY (iron-rule #25): this entire gate is a TABLE READ of cli_capability_matrix. Running ANY aliyun CLI command here to probe/verify reachability (describe-instances / describe-vpcs / list-instances / describe-db-instances, etc.) is a critical violation. The first real CLI call happens in Phase 0.

Step -1.5.1: Read the product list for the SKU
  Precondition: the SKU name must already be settled here (advisor handoff / the user stated it up front). If not yet settled,
  first resolve the SKU per Step 1.1 (ask once / guide installing advisor), obtain the SKU name, then return to this gate —
  NEVER treat the full product superset below as this deployment's list when there is no SKU.
  Take the subset for the settled SKU: from the advisor prescription or that SKU's default config (references/sku-params/<sku>.yaml),
  extract the Alibaba Cloud products this SKU actually involves.
  (The full superset this skill may touch: ECS / VPC / RDS / OSS / SWAS / ESA / ALB / ESS /
   Token Plan / PDS / ActionTrail / CloudMonitor — each SKU uses only a subset,
   e.g. lite_seed does not include ALB/ESS/PDS.)

Step -1.5.2: Statically check the CLI capability gating matrix (cli_capability_matrix)
  For each product, look up the cli_supported field line by line:
    - true     → fully CLI-automatable
    - partial  → some APIs work via CLI (e.g., ESA needs console enablement then CLI takeover / PDS needs primary-account enablement then sub-account CLI continuation)
    - false    → no CLI path at all (e.g., Token Plan / Bailian → console manual)

Step -1.5.3: Any partial/false hit → immediately explain to the user + take the fallback_route
  ⚠️ Your reachability summary to the user MUST explicitly name each console-only / manual product (e.g. Token Plan / 百炼). Do NOT summarize only the CLI-reachable products (e.g. "ECS / VPC / RDS / OSS 全部可达") while silently dropping the manual one — omitting it leaves the user with an incomplete deployment.
  User-facing copy template (friendly + plain metaphors, no technical jargon):
    "你这个套餐里有 ${产品比喻名}（${正式名}），这部分目前没法用 CLI 一键开——
     需要你去 ${控制台/分享链接} 手动开一下，开完告诉我，我接着把剩下的资源装好。
     ${fallback_route 链接}"

  Typical fallbacks:
    - Token Plan / Bailian (false) → share link https://bailian.console.aliyun.com/?tab=app#/api-key (user self-enables)
    - PDS Alibaba Cloud Drive Enterprise (partial) → primary-account enablement page https://pds.console.aliyun.com/ (primary account only; sub-accounts lack permission)
    - ESA medium limited-time promo (partial) → console https://esa.console.aliyun.com/commonBuy (the CLI PurchaseRatePlan has no RuleDescId parameter)

Step -1.5.4: Wait for the user to confirm the manual step is done → continue to Phase 0
  In state, mark manual_steps.<product>: { opened_at: ..., user_confirmed: true }
  ⚠️ NEVER discover the SKU is unworkable only after Phase 0 credential config — this gate must be up front.
```

### Phase 0: Environment check + credential config

> This skill can run in various AI terminals (QoderWork / Claude Code / Cursor / Codex / WorkBuddy, etc.).
> Regardless of the terminal, the agent should execute CLI commands directly via the Bash tool, without making the user copy commands manually.

```text
Step 0.1: Check the aliyun CLI install (aligned with official docs + Windows platform gating)
  Command: which aliyun || aliyun version
  Installed → compare version >= [cli_meta].min_version; if not → upgrade to the target version
  Not installed → **the skill MUST auto-install it via the Bash tool; do NOT make the user do it manually in an external terminal**:

  📖 Preferred install path aligned with the official docs: ${[cli_meta].official_doc_url}
     Fallback mirror: ${[cli_meta].github_releases_url}

  ── macOS ──
    Prefer Homebrew (if installed):
      brew install aliyun-cli
    Without Homebrew, curl direct-install:
      VER="$(read [cli_meta].min_version)"
      SHA="$(read [cli_meta].sha256_darwin_arm64)"  # or darwin_amd64
      TOFU_FILE="$HOME/.opc/cli-tofu-${VER}-darwin-arm64.sha256"
      mkdir -p ~/.local/bin ~/.opc
      curl -fLo /tmp/aliyun-cli.tgz --connect-timeout 15 --max-time 300 "https://aliyuncli.alicdn.com/aliyun-cli-darwin-arm64-${VER}.tgz"
      # SHA256 three-tier verification
      ACTUAL_SHA="$(shasum -a 256 /tmp/aliyun-cli.tgz | awk '{print $1}')"
      if [ -n "$SHA" ]; then
        [ "$SHA" = "$ACTUAL_SHA" ] || { echo "FATAL: SHA256 mismatch"; exit 1; }
      elif [ -f "$TOFU_FILE" ]; then
        EXPECTED="$(cat "$TOFU_FILE")"
        [ "$EXPECTED" = "$ACTUAL_SHA" ] || { echo "FATAL: TOFU mismatch"; exit 1; }
      else
        echo "$ACTUAL_SHA" > "$TOFU_FILE"; chmod 600 "$TOFU_FILE"
      fi
      tar xzf /tmp/aliyun-cli.tgz -C ~/.local/bin/
      export PATH="$HOME/.local/bin:$PATH"

  ── Linux ──
    Use the official install.sh (if provided) or the same curl direct-install path as macOS
    Change the URL to linux-amd64-${VER}.tgz; use sha256_linux_amd64

  ── Windows ──
    Prefer the official ZIP:
      curl -fLo $env:TEMP\aliyun-cli.zip --connect-timeout 15 --max-time 300 "https://aliyuncli.alicdn.com/aliyun-cli-windows-amd64-${VER}.zip"
      Expand-Archive -Path $env:TEMP\aliyun-cli.zip -DestinationPath $env:USERPROFILE\.local\bin -Force
      $env:Path += ";$env:USERPROFILE\.local\bin"

    ⚠️ **WDAC/AppLocker detection (iron-rule #29)**:
      $wdac = Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard `
                              -ClassName Win32_DeviceGuard `
                              -ErrorAction SilentlyContinue
      if ($wdac.CodeIntegrityPolicyEnforcementStatus -ge 2) {
        To the user: "你的 Windows 开启了 WDAC/应用控制策略，未签名的 aliyun.exe 可能被拦截。
              两个选项：
              ① 联系你的 IT 管理员把 aliyun.exe 加入白名单（WDAC supplemental policy / AppLocker rule）
              ② 换 macOS / Linux 终端跑本 skill（推荐 — OPC 用户多数都有 Mac）
              我不会教你绕过签名校验。"
        STOP the flow
      }

    ⚠️ **PowerShell ConstrainedLanguage detection**:
      if ($ExecutionContext.SessionState.LanguageMode -eq 'ConstrainedLanguage') {
        To the user: "你的 PowerShell 处于受限语言模式，部分 CLI 调用可能失败。
              建议换 macOS/Linux 终端，或联系 IT 申请 FullLanguage 例外。"
        STOP the flow
      }

  Fallback (when the pinned-version CDN 404s):
    Find the same-version tarball on GitHub Releases ${[cli_meta].github_releases_url}
    ⚠️ Do NOT fall back to the latest tag — a non-reproducible version = broken integrity check

  Unified user-facing copy on verification failure:
    "部署工具完整性校验没通过，先停下来。这通常是网络中传输异常。[ 重试 ] [ 提工单 ]"

  Post-install verify: aliyun version returns >= [cli_meta].min_version
  User-facing progress:
    metadata has SHA256 → "正在安装部署工具…… ✓ 已安装（版本 ${VER}，完整性校验通过）"
    TOFU hit existing record → "正在安装部署工具…… ✓ 已安装（版本 ${VER}，与首次记录一致）"
    TOFU first write → "正在安装部署工具…… ✓ 已安装（版本 ${VER}，首次安装哈希已记录）"
  ⚠️ iron-rule #13: the entire CLI install completes inside the current AI terminal's Bash/PowerShell; do NOT output commands for the user to run manually.
  ⚠️ iron-rule #28: CLI install and credential config are two independent things — this step only installs the CLI; credential config runs in the user's local terminal in Phase 0.3.

Step 0.2: Detect an already-configured credential (read-only; never touches the secret)
  Goal: if the environment ALREADY has a usable credential (a user who pre-configured, or a CI/eval sandbox that injected one), USE it — do not force a reconfigure. Run the 0.3 RamRoleArn setup ONLY when no usable credential exists.
  a) Command: aliyun configure list
     # allowed by the credential-safety rule: shows only profile names + mode + the MASKED last-3 chars, never the secret
  b) Resolve the deploy profile (the "opc profile" referenced throughout this skill):
     - candidates in order: `opc`, then the CLI default profile, then any profile shown Valid;
     - for each candidate run: aliyun sts get-caller-identity --profile <p>
       # returns only the identity (AccountId / Arn) — NEVER the AK/SK
     - the first candidate that returns an identity = the resolved deploy profile.
       ⚠️ If the resolved profile is NOT named `opc`, use its actual name in place of `opc` on every subsequent --profile call in this skill.
  Outcomes:
    - A candidate authenticates (mode = RamRoleArn / StsToken / AK, any) → use it, go to 0.4.
      If mode = AK (a long-lived key), show one line and continue (do NOT block, do NOT reconfigure):
      "检测到长期 AccessKey；生产环境更建议用 RamRoleArn 子账号，安全性更好。本次沿用现有凭证继续。"
    - No candidate authenticates / no profile configured → go to 0.3 (RamRoleArn setup).
  ⚠️ Red lines unchanged: this step NEVER reads/prints/echoes AK/SK, NEVER runs `aliyun configure set` with literal values, NEVER asks the user to paste AK/SK. It only *uses* an already-configured profile via the CLI's own signing — the skill never sees the secret.

Step 0.3: Configure credentials (RamRoleArn three-step model · ⚠️ AK/SK NEVER appear in conversation text)

  **State the design intent first (iron rule: explain before operating)**:
    "为了你的账户安全，我们用一个'跑腿员穿制服'的方式来部署：
     - 跑腿员（子账号 opc-deploy）：只有一种本事——亮工牌请求穿制服，没有任何业务权限
     - 制服（角色 opc-deploy-role）：临时穿一小时，挂着这次部署需要的最小权限
     - 工牌（永久 AccessKey）：在你电脑里加密保存，即便不慎泄露，攻击者也只能拿到限时一小时的临时通行证

     这一步操作量略多（三步），但能从根本上避免长期 AK 泄露的风险。"

  **Step 1: Create the sub-account opc-deploy (grant only AssumeRole)**
    "打开 RAM 控制台用户页：👉 https://ram.console.aliyun.com/users
     ① 点「创建用户」→ 用户名填 opc-deploy → 勾选「使用永久 AccessKey 访问」→ 勾选「我确认已妥善管理 AccessKey」→ 确定
     ② 创建成功后会显示 AccessKey ID 和 AccessKey Secret。
        ⚠️ **重要**：Secret 只显示一次。**不要复制到微信/备忘录/截图**——
        请保持 RAM 控制台这个页面不要关，直接回到这里执行下一条命令时再粘贴。
        最小化 Secret 在你电脑里"明文存留"的时间窗口。
     ③ 在用户列表找到 opc-deploy → 行右侧点「添加权限」→ 搜索添加 ⚠️ 仅添加这一个：
        - AliyunSTSAssumeRoleAccess
     ④ **绑定 MFA**：在 opc-deploy 详情页 →「安全设置」→「多因素认证」→「绑定虚拟 MFA」
        用你的手机 Authenticator 应用扫码并输入两次连续验证码。后续 AssumeRole 调用会要求 MFA 验证码，
        即便永久 AK 泄露也无法直接拿到临时 Token。
        （CLI 端配合：aliyun configure --mode RamRoleArn 时支持 --serial-number 和 --token 字段）

     完成第一步后告诉我。"

  **Step 2: Create the custom least-privilege policy opc-deploy-policy**
    Paste-create it in the RAM console: 👉 https://ram.console.aliyun.com/policies/create (policy name: opc-deploy-policy).
    The full least-privilege policy JSON + the per-acs:ResourceTag-support layering notes + the honest RAM-condition-limitation notes + the quota companion (ECS=5 / RDS=2 / VPC=1) live in the RAM policy reference (ram-policies).
    (The policy JSON and layering notes are consolidated into the RAM policy reference — maintained in one place to avoid drift.)

  **Step 3: Create the role opc-deploy-role and attach the policy**
    "打开 RAM 角色页：👉 https://ram.console.aliyun.com/roles
     ① 点「创建角色」→ 选「阿里云账号」→ 角色名 opc-deploy-role → 选当前云账号 → 确定
     ② 在角色列表点 opc-deploy-role → 「权限管理」→ 添加自定义策略 opc-deploy-policy
     ③ 在角色基本信息复制 ARN（格式 acs:ram::<UID>:role/opc-deploy-role），等会要用到

     搞定后把 ARN 发给我。"

  **Configure the CLI (run after the user provides the ARN)**
    Command: aliyun configure --mode RamRoleArn --profile opc
    Prompt the user: "接下来会让你依次输入：
     - Access Key ID → 粘贴 opc-deploy 的 AccessKey ID
     - Access Key Secret → 粘贴 opc-deploy 的 Secret
     - Sts Region → 输入 cn-beijing
     - Ram Role Arn → 粘贴 acs:ram::<UID>:role/opc-deploy-role
     - Role Session Name → 输入 opc-deploy-session
     - Default Region Id → 输入 cn-beijing
     - Default Output Format → 输入 json
     - Default Language → 输入 zh
     凭证会安全存储在你电脑的 ~/.aliyun/config.json 里（仅本人可读），不会出现在对话记录中。"

  **Tighten permissions on write (auto-run, do not expose chmod details)**
    chmod 600 ~/.aliyun/config.json
    test "$(stat -f '%A' ~/.aliyun/config.json 2>/dev/null || stat -c '%a' ~/.aliyun/config.json)" = "600" || chmod 600 ~/.aliyun/config.json
    Show the user: "✓ 已将凭证文件设为仅本人可读"

  Verify: run aliyun configure list, confirm the opc profile type is RamRoleArn
  Pass → go to 0.4
  Fail → prompt "看起来没配好，可以再试一次。如果遇到问题，把报错文案（不要包含 AccessKey 本身）发过来我帮你看看。"

Step 0.4: Verify connectivity + that AssumeRole works
  Command: aliyun ecs describe-regions --profile opc --output cols=RegionId,LocalName rows=Regions.Region[]
  Success → go to Phase 1 (behind the scenes an STS AssumeRole already ran to get a temp token, proving the role trust + Policy config are correct)
  Failure → analyze the error:
    InvalidAccessKeyId → "子账号 AccessKey 不对，请检查是否复制完整"
    NoPermission / Forbidden → "角色信任或权限有问题，请确认 opc-deploy-role 信任了当前云账号 + 挂了 opc-deploy-policy"
    EntityNotExist.Role → "ARN 写错了或角色未创建，回到第三步检查"
    network error → "网络不通，请检查是否能访问外网"
  ⚠️ Fast-exit (no infinite loop): the 0.2→0.3→0.4 credential cycle runs AT MOST twice. If sts get-caller-identity / describe-regions still fails after the 2nd attempt, or the environment cannot accept interactive `aliyun configure` stdin input, STOP the deployment (do NOT keep retrying the same profile / re-looping Phase 0). To the user:
    "凭证暂时没配好，先停在这里。请在你的终端确认 opc profile 可用（aliyun sts get-caller-identity --profile opc 能返回身份），或联系管理员开通；配好后重新发起即可。"
```

### Phase 0.4: Centralized image resolution (iron-rule #27)

```text
Every SKU containing ECS RunInstances (starter_webui / starter_app / lite_seed / lite_growth / lite_traction / pro_steady / pro_burst) must run this step first to resolve the image and write it to state; **yamls after Phase 1 only consume state.resources.ecs.image_id**.

Step 0.4.1: Check whether state already locked an image
  if state.resources.ecs.image_id already exists:
    → skip the whole Phase 0.4 (iron-rule #27 reuse clause; scale-out/rebuild use the same binary)
    → go straight to Phase 1
  else continue to Step 0.4.2

Step 0.4.2: Primary path DescribeImageFromFamily
    # family source: prefer the advisor prescription image.family; without advisor context use deploy's built-in default
    #   (image_families primary family: acs:alibaba_cloud_linux_3_2104_lts_x64 / x64;
    #    for ARM instance families use acs:alibaba_cloud_linux_3_2104_lts_arm64)
  FAMILY=${advisor prescription image.family:-image_families primary default}
  aliyun ecs describe-image-from-family --profile opc \
    --RegionId ${region} \
    --ImageFamily ${FAMILY}
    # the advisor prescription family must include the minor-version underscore format, e.g. acs:alibaba_cloud_linux_3_2104_lts_x64
    # dry-run measured: a short name (acs:alibaba_cloud_linux_3_x64) gets 0 hits

  hit → extract Image.ImageId / Image.CreationTime / Image.OSName → Step 0.4.4
  0 hits → Step 0.4.3 fallback

Step 0.4.3: Fallback DescribeImages (same family, List API path)
  aliyun ecs describe-images --profile opc \
    --RegionId ${region} \
    --ImageFamily ${advisor prescription image.family} \
    --Status Available \
    --ImageOwnerAlias system \
    --PageSize 5
    # ⚠️ do not use --SortOrder DESC (CLI 3.4.1 does not recognize it)
    # ⚠️ do not use the --ImageName wildcard (the Chinese OSName's double spaces are unreliable)

  hit → take Images.Image[0].ImageId / CreationTime / OSName → Step 0.4.4
  0 hits → hard-stop, to the user:
    "系统镜像清单里没找到 ${image.family} 锁定的次版本（${image.os_series}）。
     可能该次版本在 ${region} 区下架了。
     请回 advisor 重出处方：「@alibabacloud-opc-advisor 帮我把镜像换成能用的次版本」。"
  Forbidden behaviors: ① retrying with a mutated family string; ② cross-major-version fallback (Linux 3→4 breaks the app layer); ③ switching to another family on its own

Step 0.4.4: Write state, lock permanently
  state.resources.ecs.image_id = ${resolved ImageId}
  state.resources.ecs.image_family = ${FAMILY}
  state.resources.ecs.image_os_series = ${advisor prescription image.os_series:-resolved OSName}
  state.resources.ecs.image_creation_time = ${resolved CreationTime}
  state.resources.ecs.image_pinned_by_advisor_at = ${advisor prescription image.family_pinned_at:-null (no advisor context, deploy used the default family)}
  state.resources.ecs.image_locked_at = ${now}

Step 0.4.5: Non-blocking info display (iron-rule #32)
  User-facing copy (informational, **does NOT wait for a reply**):
    "✓ 已锁定服务器镜像：
       系统：${image.os_series}（${image.arch}）
       发布版本：${image.creation_time} 的官方镜像
       ${when advisor context exists: 这是 advisor 在 ${image.family_pinned_at} 锁定的次版本}
       ${when no advisor context: 这是当前推荐的稳定次版本}——已写入 state 永久绑定，
       后续扩容/重建复用同一镜像，避免半夜偷偷换 OS 大版本炸应用。"
  After displaying, go straight to Phase 1, do not wait for [Y/n].
  (Rationale: a non-technical user cannot make a meaningful ACK on an ImageId hex string; the original [Y/n] was security theater — the meaningful image choice was already settled at the advisor layer via the family + os_series human-readable name.)
```

### Phase 1: Receive SKU + confirm

```text
Step 1.1: Identify the SKU
  Extract the SKU name from the conversation context or user input
  Validate it is one of the 7 legal SKUs
  Invalid → ask the user to run advisor first
  (starter_webui no longer asks about the user's promo history — Phase 1.2.5's price inquiry decides the path automatically)

  Strong-signal fast-path (aligned with the advisor dynamic-eval lesson: a weak model must not treat a clear signal as ambiguous):
    Any of the following strong signals → lock the SKU directly, skip the question, go to Step 1.2:
      - the user states a legal SKU name directly (e.g. "帮我开一个 lite_seed")
      - the advisor prescription already provided the sku field in context
    Only ask when the SKU is missing or illegal (e.g. the user says only "帮我部署" with no SKU),
    and ask only once (phrasing depends on whether advisor is available, see iron-rule #9):
      - advisor available: "你从 advisor 拿到的套餐名是哪个？没有的话我先带你走一遍 advisor 选套餐。"
      - advisor unavailable (only deploy installed): hand over the advisor skill install address (**do NOT make the user guess a SKU name off the purchase-page cards** — the 4 cards do not map one-to-one to the 7 SKUs). Install address = https://github.com/aliyun/alibabacloud-aiops-skills/tree/master/skills/computing/ecs/alibabacloud-opc-advisor :
        "开通前得先定套餐，选套餐是上游助手 advisor 的活儿。在 Qoder 里添加这个 Skill 装上它：
         https://github.com/aliyun/alibabacloud-aiops-skills/tree/master/skills/computing/ecs/alibabacloud-opc-advisor （其他 AI 工具就把地址发给它读）。装好跟它说你的项目，
         它会给你一个套餐名，你报给我我就开通。"
    NEVER repeatedly re-confirm when a clear SKU already exists.

  Self-sufficiency entry (deploy does not hard-depend on advisor context):
    deploy's **only hard dependency is the SKU name**. The advisor structured fields (scope_declaration /
    fallback_ecs_config / image / component removal) are all "use if present, else self-derive" optional enhancements:
      - advisor context present → prefer its fields
      - no advisor context (new session with a direct SKU name / cross-session) → do NOT stop or error,
        self-derive from deploy built-in defaults: image = image_families primary family,
        starter fallback = Step 1.2.5 built-in config, scope = iron-rule #23 built-in list,
        component removal = re-captured/confirmed at the Step 1.3 resource list.

Step 1.2: Load the parameter file (default)
  starter_webui → default to references/sku-params/starter_webui.yaml (ECS primary path)
  other SKUs → references/sku-params/<sku>.yaml

Step 1.2.5: starter_webui / starter_app price-inquiry gate (SWAS fallback deprecated)
  ① First inquiry (promo config: 3 Mbps fixed bandwidth):
    aliyun ecs describe-price --profile opc --RegionId cn-beijing \
      --ResourceType instance --InstanceType ecs.e-c1m1.large \
      --PriceUnit Year --Period 1 \
      --SystemDisk.Category cloud_essd_entry --SystemDisk.Size 40 \
      --InternetChargeType PayByBandwidth --InternetMaxBandwidthOut 3 --Amount 1
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

       aliyun ecs describe-price --profile opc --RegionId cn-beijing \
         --ResourceType instance --InstanceType ecs.e-c1m1.large \
         --PriceUnit Year --Period 1 \
         --SystemDisk.Category cloud_essd_entry --SystemDisk.Size 40 \
         --InternetChargeType PayByTraffic --InternetMaxBandwidthOut 100 --Amount 1

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
       aliyun cms put-metric-rule-targets --RuleId opc-${ecs_instance_id}-traffic-alarm ...

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

Step 1.4: Determine the region
  Default: cn-beijing
  user specifies another → use the specified value

Step 1.5: Pre-execution hard-gate self-check (HARD BLOCK · every item must pass before Phase 3)
  ⚠️ This self-check is a hard gate, not a soft hint, not a "suggested review".
     Any item not passing → stop immediately, discard the current execution plan, forbid calling any create/charge API;
     first return to the corresponding Phase to fill the gap, then re-run this self-check; only enter Phase 3 when all pass.
     NEVER "just create it first".
  [ ] 1. SKU settled and one of the legal 7 (else back to advisor)
  [ ] 2. Phase -1.5 CLI-reachability gate passed; partial/false items went through fallback and were user-confirmed
  [ ] 3. credential profile type = RamRoleArn (verified via aliyun configure list); AK/SK never read/echoed throughout
  [ ] 4. resource list + monthly price shown, with the "💡 价格供参考，实际以最终下单为准" disclaimer appended
  [ ] 5. payment second-confirmation obtained ("即将扣款 ¥X，确认付款？" the user explicitly answered confirm; insufficient-balance top-up path excepted)
  [ ] 6. starter inquiry: the RunInstances order params exactly match the final DescribePrice params (close the inquiry↔charge gap)
  [ ] 7. out-of-scope requests hard-rejected per iron-rule #23 built-in scope cannot_do and pointed back to the desktop AI assistant (if any)
  [ ] 8. component-removal opt-out handled: a SKU with a removable item (Lite/Pro's "AI 助理那台") was pre-applied per context or given one opt-out; the final to-create set matches the quoted monthly price
```

### Phase 2: Network infrastructure

```text
Step 2.1: Query existing OPC VPCs (QuotaExceeded.Vpc handling + ownership field)
  ① First query opc:managed-tagged VPCs:
    aliyun vpc describe-vpcs \
      --RegionId <region> \
      --Tag.1.Key opc:managed \
      --Tag.1.Value true
    has result → extract VpcId + VSwitchId → state.resources.vpc.owned = true → jump to 2.4
    no result → go to step ②

  ② Before trying to create, list **all VPCs under the account** for the user to choose
    aliyun vpc describe-vpcs --RegionId <region>
    Scenario A: list empty → go straight to 2.2 create
    Scenario B: list non-empty (the account already has VPCs, creation may have failed with QuotaExceeded.Vpc) →
      To the user: "你账号下已经有 ${N} 个 VPC（VPC 是云上的虚拟内网）：
             ${vpc_list 友好显示}

             两个选项：
             ① 复用现有 ${某个 VPC name} → 我把这次的服务器放进去（不删它）
             ② 让我新建一个独立 VPC → 默认推荐，账号有配额时优选

             选哪个？"
      user picks ① → record state.resources.vpc.id = ${reused_id}, owned = false → jump to 2.3, create a new VSwitch in the reused VPC (do NOT add the opc:managed tag to someone else's VPC)
      user picks ② → go to 2.2 to try creating; if it returns QuotaExceeded.Vpc, return here to let the user re-pick ①

Step 2.2: Create VPC (only the ownership=true path)
  Command: aliyun vpc create-vpc \
    --RegionId <region> \
    --VpcName OPC-VPC \
    --CidrBlock 10.0.0.0/16 \
    --Tag.1.Key opc:managed \
    --Tag.1.Value true
  → record VpcId
  → wait for VPC status to become Available
    # vpc CreateVpc --Tag measured NOT to persist; must post-call TagResources to backfill
  → backfill the tag:
    aliyun vpc tag-resources \
      --RegionId <region> \
      --ResourceType VPC \
      --ResourceId.1 <vpc_id> \
      --Tag.1.Key opc:managed --Tag.1.Value true

Step 2.3: Create the VSwitch
  First query zones: aliyun ecs describe-zones --RegionId <region>
    # describe-zones OR describe-available-resource is acceptable — both resolve a usable zone.
    # describe-available-resource additionally returns real-time stock, so it is fine (even preferable) to use it instead; log whichever API name you used.
  Pick the first zone that supports the target instance type
  Command: aliyun vpc create-vswitch \
    --VpcId <vpc_id> \
    --RegionId <region> \
    --ZoneId <zone_id> \
    --CidrBlock 10.0.0.0/24 \
    --VSwitchName OPC-VSwitch
  → record VSwitchId
    # vpc CreateVSwitch does not accept --Tag; must post-call TagResources to backfill,
    # otherwise teardown DeleteVSwitch (RAM condition opc:managed=true) is denied with Forbidden.RAM
  → backfill the tag:
    aliyun vpc tag-resources \
      --RegionId <region> \
      --ResourceType VSWITCH \
      --ResourceId.1 <vswitch_id> \
      --Tag.1.Key opc:managed --Tag.1.Value true

Step 2.4: Security group (SSH tightened to ${MY_IP}/32, 8080 removed)
  Query existing: aliyun ecs describe-security-groups \
    --VpcId <vpc_id> \
    --Tag.1.Key opc:managed \
    --Tag.1.Value true
  has → reuse the group, but you MUST STILL tighten SSH for the CURRENT user: resolve MY_IP (per the tiers below) and call authorize-security-group to set port 22 = ${MY_IP}/32. A reused group may not include the current user's IP, or may be too loose — NEVER assume its rules are correct, and NEVER skip authorize-security-group just because the group already exists; if it carries a 0.0.0.0/0 SSH rule, do not leave it in place. (Run the MY_IP resolution + port-22 authorize-security-group steps below either way.)
  none → create + open rules:
    aliyun ecs create-security-group \
      --VpcId <vpc_id> \
      --SecurityGroupName OPC-SecurityGroup \
      --Tag.1.Key opc:managed --Tag.1.Value true
    # ecs CreateSecurityGroup --Tag measured NOT to persist; must post-call TagResources to backfill
    aliyun ecs tag-resources \
      --RegionId <region> \
      --ResourceType securitygroup \
      --ResourceId.1 <security_group_id> \
      --Tag.1.Key opc:managed --Tag.1.Value true

    # Auto-detect the user's egress IP (prefer an Alibaba Cloud-owned probe endpoint,
    # fall back to ifconfig.me/ipinfo.io, and if all fail have the user type it in, to avoid writing a garbage value into the allowlist)
    # Note: the Alibaba Cloud ECS metadata 100.100.100.200 is only reachable inside ECS, not from a local terminal.
    #     Here we use a lightweight aliyun CLI call instead; the CLI carries its own Signature and the response can yield RemoteAddr (some versions).
    #     The most robust is still the third-party + user-input three-tier fallback.
    MY_IP=""
    # Tier 1: Alibaba Cloud GetCallerIdentity over https, CLI-built-in signing resists MITM (more trusted than plaintext ifconfig.me)
    MY_IP=$(aliyun sts get-caller-identity --profile opc 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('RemoteAddress',''))" 2>/dev/null)
    # Tier 2: HTTPS ifconfig.me/ipinfo.io (must be https + -4 to force IPv4; the security group SourceCidrIp only accepts IPv4)
    if ! echo "$MY_IP" | grep -Eq '^[0-9]{1,3}(\.[0-9]{1,3}){3}$'; then
      RAW=$(curl -4 -s --max-time 5 https://ifconfig.me 2>/dev/null || curl -4 -s --max-time 5 https://ipinfo.io/ip 2>/dev/null)
      echo "$RAW" | grep -Eq '^[0-9]{1,3}(\.[0-9]{1,3}){3}$' && MY_IP="$RAW"
    fi
    if [ -z "$MY_IP" ]; then
      To the user: "自动获取你的网络出口 IP 失败。安全起见我不能开 0.0.0.0/0。
            请打开 https://ipw.cn 查到自己的公网 IP，告诉我，我用它写白名单。"
      Wait for the user to input an IP, validate it (IPv4 regex) then assign to MY_IP, otherwise keep asking; do not accept an empty value
    fi

    ⚠️ HARD RULE (weak-model-proof): SSH port 22 with SourceCidrIp 0.0.0.0/0 is FORBIDDEN. Before authorizing port 22, self-check: is MY_IP a concrete IPv4 resolved via the tiers above? If NOT → do NOT authorize port 22; go back and resolve MY_IP (or ask the user for their public IP). NEVER use 0.0.0.0/0 as an SSH fallback. (HTTP 80 / HTTPS 443 to 0.0.0.0/0 is correct — those are public web ports.)
    Open rules one by one (SSH uses ${MY_IP}/32 single IP; HTTP/HTTPS use 0.0.0.0/0):
      aliyun ecs authorize-security-group --SecurityGroupId <sg> --IpProtocol tcp \
        --PortRange 22/22  --SourceCidrIp ${MY_IP}/32   # SSH self only
      aliyun ecs authorize-security-group --SecurityGroupId <sg> --IpProtocol tcp \
        --PortRange 80/80  --SourceCidrIp 0.0.0.0/0     # HTTP (Pro force-redirects to HTTPS)
      aliyun ecs authorize-security-group --SecurityGroupId <sg> --IpProtocol tcp \
        --PortRange 443/443 --SourceCidrIp 0.0.0.0/0    # HTTPS
      # ⚠️ TCP 8080 removed: OpenClaw is accessed via the SWAS console "应用详情→登录 Web UI" entry (white-box product capability: random port + Token + public access off by default); 8080 is no longer exposed raw

  User-facing copy: "✓ 已创建安全门禁。SSH（远程登录端口）只对你当前的网络 IP 开放（${MY_IP}），别人就算拿到密钥从别的网络也连不上。HTTP/HTTPS 对外开放给访客访问业务。"
  → record SecurityGroupId
  → after deployment, **keep** the SSH rule (the user can tighten/close it in the console, balancing convenience and security)

  ControlPolicy interception handling (do not teach circumvention):
    If AuthorizeSecurityGroup returns OperationDenied.NoPermission caused by an org-level ControlPolicy:
    To the user: "你的账号被组织管控策略限制，普通子账号无法直接放行端口。请联系你的云账号管理员申请例外，或扩大 opc-deploy 子账号的权限范围。提工单：https://smartservice.console.aliyun.com/service/create-ticket"
    Abort, do not retry.
```

### Phase 3: Create resources

Execute in the order of the `steps` array in `references/sku-params/<sku>.yaml`. See the yaml format spec below for each step's structure.

**Phase 3 prerequisite: SSH key preset** (chmod 600 / private-key mask, iron-rule #30):
```text
Before running RunInstances:
  1. Detect whether the user's local ~/.ssh/id_rsa.pub or ~/.ssh/id_ed25519.pub exists
     - exists → ImportKeyPair (upload the public key to Alibaba Cloud; no private key touches disk)
     - not exists → CreateKeyPair + **private key NEVER enters conversation/state**:
         # CreateKeyPair has no --output-file option; the private key is in the response PrivateKeyBody field — pipe it straight to disk, never echo to stdout/log (iron-rule #30)
         aliyun ecs create-key-pair --KeyPairName opc-deploy-${TS} --RegionId ${region} \
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
```text
for each step in yaml.steps:
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
    → update the state file
    → report the result to the user
```

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
  Extra: dynamically build a "metaphor → official Alibaba Cloud name → resource ID" mapping from state, e.g.:
    "你的小店面" → "云服务器 ECS" (i-2ze...)
    "AI 助理（OpenClaw）" → "轻量应用服务器 SWAS" (swas-...)
    "数据存储空间" → "云数据库 RDS MySQL 高可用版" (rm-...)
    "文件仓库" → "对象存储 OSS" (bucket-...)
    "全球加速" → "边缘安全加速 ESA" (esa-...)
    Note to the user: "万一遇到问题需要联系阿里云客服，用右边的正式名称沟通会更快。"

Step 4.3: Output "what's next"
  Starter (default has_desktop_tool = true):
    "告诉我（你正在用的这个 AI 助手）：帮我把代码部署到 ${ecs_public_ip}，我来帮你远程搞定"
  Starter (rare fallback has_desktop_tool = false, when the current terminal lacks remote-deploy capability):
    "① 下载安装 QoderWork CN Pro：
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
     - 第二步：查操作审计 → 操作审计 ActionTrail
       👉 https://actiontrail.console.aliyun.com/ → 查最近 7 天异常操作（查询免费）
     - 第三步：提工单 → 阿里云工单
       👉 https://smartservice.console.aliyun.com/service/create-ticket → 描述现象贴时间点，阿里云会协助止损"

Step 4.5: Save the final state (state is also chmod 600)
  Write state/<sku>-<timestamp>.json
  chmod 600 state/<sku>-<timestamp>.json immediately after writing
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
  [ ] 2. Monthly-cost total + the "价格供参考，实际以最终下单为准" disclaimer (Step 4.2)
  [ ] 3. "What's next" (the right entry per has_desktop_tool / SKU type, Step 4.3)
  [ ] 4. Renewal reminder (auto-renew off by default + renewal-management link, Step 4.4)
  [ ] 5. "Don't panic" three-step incident card (Step 4.4.5)
  [ ] 6. state written and chmod 600, and contains no plaintext password (Step 4.5)
  [ ] 7. Public IP AND private IP are printed IN FULL using the actual resolved values — never a truncated "47.94.xxx.xxx" / "10.0.0.x" / "..." placeholder copied from the template
```

---

## Deployment-failure teardown

If any post-creation step in Phase 3 fails → enter the teardown decision dialogue:

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
- **Tag-then-delete robustness (E2E-measured fix)**: for the tag-conditioned resources (ECS / SecurityGroup / VSwitch / VPC / ALB / ESS scaling-group), FIRST call TagResources `opc:managed=true` (an unconditional Allow in opc-deploy-policy), THEN call Delete. Rationale: if the create-time tag backfill was skipped (weak models sometimes tag the SG but miss the VPC/VSwitch), DeleteVSwitch/DeleteVpc are denied `Forbidden.RAM` because the teardown condition requires `opc:managed=true`; tagging immediately before delete makes teardown succeed regardless. VSwitch: `aliyun vpc tag-resources --ResourceType VSWITCH --ResourceId.1 <id> --Tag.1.Key opc:managed --Tag.1.Value true`; VPC: same with `--ResourceType VPC`.
- Report each Delete call to the user individually (one "✓ released <plain-language name>" line per resource)
- **VPC ownership awareness (iron-rule #29)**: before teardown, read `state.resources.vpc.owned`:
  - `owned: true` (self-created) → normal DeleteVpc closure
  - `owned: false` (reusing someone else's) → **skip DeleteVpc**, only reclaim the self-created VSwitch/SG/ECS, and tell the user that this VPC was not created by the current deployment so it is left untouched
- Partial failure: skip that resource and continue to the next; finally summarize the un-released list + console deep links for the user to handle manually
- ⚠️ Delete permission is constrained by the RAM Policy Tag Condition (can only delete `opc:managed=true` resources), so even a runaway skill won't wrongly delete the user's other resources
- API notes:
  - ESS scaling rule: creation returns a ScalingRuleAri (e.g. `ari:acs:ess:...:scalingrule/asr-xxx`); delete with `DeleteScalingRule --ScalingRuleId asr-xxx` (take the last ID segment of the ARI)
  - RDS: the instance-release API is `rds DeleteDBInstance --DBInstanceId xxx` (not ReleaseDBInstance)
  - ESS scaling group: must `DisableScalingGroup` first, then `DeleteScalingGroup` (cannot delete while active)

# Phase 0 · Step 0.2 / 0.3 / 0.5: Credential detection, setup, connectivity

> Second half of Phase 0. Runs after the CLI is installed (`cli-install.md`).
>
> - **Entry**: CLI ready, `--auto-plugin-install` set.
> - **Exit**: a profile that authenticates → **go to Step 0.2b (`policy-probe.md`) — mandatory, never skip
>   straight to Phase 1.** Then Step 0.5 connectivity, then Phase 0.4 image resolution.
> - Naming note: **Step 0.5** below is the connectivity check; **Phase 0.4** (`image-resolution.md`) is the
>   image-resolution phase. They are different things — the old numbering collided at "0.4".

```text
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
     ⚠️ Pin ONE profile and use it for the whole deployment. Do NOT silently fall back to a second profile
       mid-flow when a call fails: different profiles can belong to DIFFERENT Alibaba Cloud accounts
       (a fallback profile can resolve to another account and its role, making the failure
       diagnosis wrong). If the pinned profile hits a permission error, that is a policy problem to report,
       not a cue to try another identity. Record the resolved profile name + AccountId in state.
  Outcomes:
    - A candidate authenticates (mode = RamRoleArn / StsToken / AK, any) → use it, go to Step 0.2b (policy-probe).
      If mode = AK (a long-lived key), show one line and continue (do NOT block, do NOT reconfigure):
      "检测到长期 AccessKey；生产环境更建议用 RamRoleArn 子账号，安全性更好。本次沿用现有凭证继续。"
    - No candidate authenticates / no profile configured → go to 0.3 (RamRoleArn setup).
  ⚠️ Red lines unchanged: this step NEVER reads/prints/echoes AK/SK, NEVER runs `aliyun configure set` with literal values, NEVER asks the user to paste AK/SK. It only *uses* an already-configured profile via the CLI's own signing — the skill never sees the secret.

  🔒 **Why interactive `aliyun configure` is safe, stated explicitly (SA-2.12).** In Step 0.3 the user types their
  AccessKey ID / Secret into the **CLI's own stdin prompt**, not into this conversation. That input goes
  straight to the CLI process and is written by the CLI to `~/.aliyun/config.json`; it **never enters the
  conversation transcript, the agent's context, a tool-call argument, a script file, or any log this skill
  writes**. Consequences that hold for the whole skill, without exception:
  - the skill **never handles the credential values itself** — it does not read, echo, print, interpolate,
    template, store, or pass them as a command argument; every signed request is signed by the CLI from the
    profile on disk;
  - therefore `aliyun configure set --access-key-id <literal>` / `--access-key-secret <literal>` and any
    equivalent that puts a secret on a command line are **forbidden**, in scripts as well as in chat;
  - the only credential facts the skill may surface are non-secret: the profile name, the credential mode,
    the role ARN, and the identity returned by `sts get-caller-identity` (`AccountId` / `Arn`);
  - if the user pastes a secret into the conversation anyway, treat it as compromised: do not repeat it back,
    do not use it, and tell them to delete that key in the console and create a new one.

Step 0.3: Configure credentials (RamRoleArn three-step model · ⚠️ AK/SK NEVER appear in conversation text)

  ⚠️ **Naming is internal only**: the words "RamRoleArn", "three-step model", "三步法", "AssumeRole",
  "STS" are internal labels for you — they must NOT open the explanation to the user. Lead with the
  plain-language metaphor below, verbatim; introduce a technical term ONLY where it is unavoidable as a
  literal thing the user must type or click (e.g. the console field name, the profile mode in a command).
  Never say anything shaped like "我们采用 RamRoleArn 三步法" as the opening line.

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
    ⚠️ **Scope the policy to the settled SKU** (see the "Scope the policy to the settled SKU" section in
    the RAM policy reference): the reference's main JSON is the all-SKU superset. Hand the user ONLY the
    variant matching this SKU's product set — a starter_webui / starter_app deploy must NOT ask for
    RDS / OSS / ALB / ESS / SWAS permissions it never uses (the reference carries a
    ready-to-paste starter variant). This mirrors the Phase -1.5 product narrowing; granting the full
    superset to a starter user is a least-privilege violation.
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
  Pass → go to Step 0.2b (policy-probe), then Step 0.5
  Fail → prompt "看起来没配好，可以再试一次。如果遇到问题，把报错文案（不要包含 AccessKey 本身）发过来我帮你看看。"

Step 0.5: Verify connectivity + that AssumeRole works
  Command: aliyun ecs describe-regions --profile opc --output cols=RegionId,LocalName 'rows=Regions.Region[]'
    # ⚠️ E2E-measured: the `rows=` value MUST be single-quoted. Unquoted, zsh treats the `[]` as a glob
    #    and the whole call dies before the CLI ever runs ("no matches found: rows=Regions.Region[]").
    #    Applies to every `--output rows=...[]` in this skill.
  Success → go to Phase 0.4 image resolution (behind the scenes an STS AssumeRole already ran to get a temp token, proving the role trust + Policy config are correct)
  Failure → analyze the error:
    InvalidAccessKeyId → "子账号 AccessKey 不对，请检查是否复制完整"
    NoPermission / Forbidden → "角色信任或权限有问题，请确认 opc-deploy-role 信任了当前云账号 + 挂了 opc-deploy-policy"
    EntityNotExist.Role → "ARN 写错了或角色未创建，回到第三步检查"
    network error → "网络不通，请检查是否能访问外网"
  ⚠️ Fast-exit (no infinite loop): the 0.2→0.3→0.5 credential cycle runs AT MOST twice. If sts get-caller-identity / describe-regions still fails after the 2nd attempt, or the environment cannot accept interactive `aliyun configure` stdin input, STOP the deployment (do NOT keep retrying the same profile / re-looping Phase 0). To the user:
    "凭证暂时没配好，先停在这里。请在你的终端确认 opc profile 可用（aliyun sts get-caller-identity --profile opc 能返回身份），或联系管理员开通；配好后重新发起即可。"
```

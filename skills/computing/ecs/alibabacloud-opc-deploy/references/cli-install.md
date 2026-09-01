# Phase 0 · Step 0.1 / 0.1b: CLI install + plugin auto-install

> First half of Phase 0. Runs after Preflight, before credential detection.
>
> - **Entry**: preflight passed.
> - **Exit**: `aliyun version` >= `[cli_meta].min_version` AND `--auto-plugin-install true` is set
>   → go to Step 0.2 (`credential-setup.md`).
> - Low-frequency: on a machine that already has a recent CLI, Step 0.1 is a single version check.
> - Flag conventions for every later command live in `cli-meta.md` ("Plugin-mode flag conventions").

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

Step 0.1b: Enable CLI plugin auto-install (one-time, required before ANY product command)
  CLI 3.4.x runs product commands (ecs / vpc / rds / cms / esa / swas-open ...) as plugins loaded on
  demand. On a fresh machine the plugin is absent and the first call errors with
  "Plugin 'aliyun-cli-<product>' is required for command ... but not installed."
  Run once, up front, so every later product command self-installs its plugin silently:
    aliyun configure set --auto-plugin-install true
  # global setting, no --profile needed; idempotent (safe to re-run). Do NOT make the user run it manually.
```

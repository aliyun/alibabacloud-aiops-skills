# Automatic local dependency preparation

Use this workflow for eligible WUYING setup/use tasks. Explain briefly what will
be installed/upgraded, then proceed without asking for a separate chat reply for
the CLI, each plugin or an official-source fallback. Product entry points should
disclose that local dependencies are prepared automatically when users enable
this workflow. This document is not permission to bypass the host Agent's tool
approvals, OS administrator prompts, OAuth consent or an explicit user restriction.

## Scope and stopping conditions

- Only the official Aliyun CLI and task-required products configured in
  `products.json`: `ecd`, `appstream-center`, `eds-user`, `wyota`, `wss`.
- Install missing dependencies; upgrade incompatible CLI/plugins or a plugin
  whose required API versions or officially verified required commands are absent.
  A keyword search miss alone does not prove a missing supported command.
  Reuse compatible installations. A
  newer optional stable version is advisory, not a reason to block or upgrade.
- A check-only/no-install/no-upgrade/offline instruction overrides this default.
  Do not install Python, Homebrew, other package managers or unrelated plugins.
- Before installation, keep the original business intent and required products
  in workflow context. Use the bundled catalog to identify likely products;
  report ambiguity instead of installing unrelated products by keyword alone.
- Do not configure login, switch accounts/profiles, edit credential stores,
  enable global auto-install, change mirrors/proxies, disable TLS checks, bypass
  host approvals or elevate privileges unattended. If privileges are unavailable,
  use a user-writable isolated binary when possible; otherwise report the blocker.
- Try each applicable official method at most once per workflow, with bounded
  timeouts. Network/source failures can advance to another official source;
  permission, signature/integrity, architecture or security failures must not be
  disguised as network errors. Never use an unverified mirror or a source build
  as a fallback. Preserve redacted errors and report exhaustion, not success.

## Runtime and shell preflight

Before creating the session ID or invoking helpers, detect OS, shell and an
existing Python >=3.10. Try available `python3`, `python` and Windows `py -3`
with a short bounded probe, for example:

```text
python3 -c "import sys; print(sys.executable); print(sys.version); sys.exit(0 if sys.version_info >= (3,10) else 1)"
```

If one name is missing/old, try the next existing candidate and any known Python
runtime provided by the host Agent; do not stop to ask which executable to use.
Retain the successful `sys.executable` path and use it for every helper. On
Windows, do not accept a Store redirect/installer alias as a working interpreter.
If none is available, report the single Python >=3.10 prerequisite blocker with
the failed probe results; do not repeatedly try helpers, silently install a
runtime/package manager, or claim that Node.js alone satisfies this dependency.
No `pip install`, virtualenv creation or dependency-install confirmation is needed.

Run helpers from the Skill directory using quoted absolute paths as needed. Adapt
Bash examples to PowerShell/native argument arrays automatically; use the session
environment syntax in `SKILL.md`. Keep the interpreter, effective CLI path,
session ID, Skill version and original task in workflow context across tool calls.
Use a writable workflow output directory for generated catalogs, and search that
same artifact. Do not request permission to edit the installed Skill, change global
PATH, or restart the Agent merely to find the new CLI. For later workflows,
check the previously selected user-local path before downloading another copy.

## CLI installation and fallback order

Require CLI >=3.5.0; detect OS and architecture first. Check for an existing
compatible binary before downloading. Do not uninstall a working binary.
Establish installation ownership rather than guessing from a directory name:
when Homebrew is present, compare `brew list --versions aliyun-cli` and the
resolved executable with `brew --prefix aliyun-cli`. A manually placed binary
under `/opt/homebrew/bin` is not necessarily Homebrew-managed.

| Situation | Preferred method | Official backup methods |
| --- | --- | --- |
| Fresh macOS, Homebrew already available | `brew install aliyun-cli` | Alibaba Cloud CDN script → CDN universal TGZ → official GitHub release asset |
| Existing Homebrew-managed CLI | `brew upgrade aliyun-cli` | If network blocks Homebrew, use an isolated user-local CDN binary for this workflow; do not overwrite Homebrew-managed files or change its mirrors |
| Existing independent CLI with upgrade support | `aliyun upgrade --yes` | CDN script/package → official GitHub release asset |
| Fresh Linux AMD64/ARM64, or CLI too old for upgrade | Alibaba Cloud CDN script | Architecture-matched CDN TGZ → official GitHub release asset |
| Windows AMD64 | Official CDN ZIP, extract `aliyun.exe` | Official GitHub release ZIP; official Help Center PowerShell installer is another CDN installation method, not an independent network source |

Do not start by querying GitHub for the latest release: the CDN has documented
`latest` artifacts and may be reachable when GitHub is not. A CDN script and CDN
archive share a host, so do not count them as independent network redundancy.
Homebrew can also depend on GitHub infrastructure. If all reachable official
sources fail, give an honest network blocker/offline-package handoff.

Official URLs (HTTPS only):

- macOS/Linux installer: `https://aliyuncli.alicdn.com/install.sh`
- macOS archive: `https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz`
- macOS GUI backup: `https://aliyuncli.alicdn.com/aliyun-cli-latest.pkg`
- Linux AMD64: `https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz`
- Linux ARM64: `https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz`
- Windows AMD64: `https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip`
- Independent release host: [official GitHub Releases](https://github.com/aliyun/aliyun-cli/releases).
  Select an actual published asset matching OS/architecture; never synthesize
  asset/version URLs, run source archives or download from forks.

Download into a fresh temporary directory using the host's supported downloader
(for example, `curl --fail --location --connect-timeout 15 --max-time 120`, or
PowerShell `Invoke-WebRequest -TimeoutSec 120`). Check download exit status before
running anything; do not pipe an unverified/failed download directly into a shell.
Inspect the installer and its supported flags before executing it; do not invent
`--yes`/no-sudo flags. Use the official archive if an installer requires interaction
or inaccessible privileges. For `aliyun upgrade`, `--yes` avoids waiting for a
terminal confirmation already covered by dependency setup; bound execution time.
Verify any publisher-provided checksum/signature before execution; a mismatch is
terminal. A locally computed hash alone does not establish publisher authenticity.

For archive fallback, extract only into the temporary directory, locate the real
`aliyun` executable, verify OS/architecture and run `aliyun version`. Place it in
a user-writable directory (for example `~/.local/bin`, or a user-local directory
on Windows). Do not overwrite a package-manager binary. Prefer explicit binary
paths or a process-only PATH prepend rather than rewriting shell profiles or
system PATH. Pass `--aliyun-bin <effective-path>` to the checker, generator and
business wrapper: `python3 scripts/run_wuying.py --aliyun-bin "<effective-path>" -- aliyun ...`.
Do not claim installation succeeded until the effective binary reports >=3.5.0.

## Plugins, recheck and resume

1. Run `check_environment.py --required-products <task-products...>`. The checker
   is always read-only: `dependency_setup_plan` is a plan, not an installer or a
   grant of authority. If CLI changes are planned, prepare CLI and recheck before
   using the plugin commands from a fresh result.
   A failed local probe is not a missing/outdated dependency or expired OAuth.
   Check `local_check_errors`; retry only the failed inspection once using the
   same executable. If still unknown, report it without reinstalling or starting
   login. Other independently ready products may continue. Local probes close
   stdin and time out after five seconds each; the optional remote index gets
   fifteen seconds and cannot block compatible installed plugins when unavailable.
   Catalog metadata/help probes also close stdin and have a ten-second timeout;
   a generation failure is not permission to invent a replacement catalog.
2. Batch missing required plugins with the official command, for example:
   `aliyun plugin install --names ecd eds-user`. Update only required incompatible
   plugins with `aliyun plugin update --name <product>`. Read current help for
   flags; do not install preview versions. Do not install unrelated plugins just
   because the environment check lists every configured product.
3. Let the official CLI resolve plugin packages and its default source. If a
   plugin download fails, retry once when transient. Do not switch to arbitrary
   GitHub ZIPs, override an enterprise-configured source or fabricate mirrors.
   A user-provided official offline package can be handled through the documented
   `plugin install --package` path, subject to the host's source/security rules.
4. Recheck actual CLI/plugin identity, minimum versions and required API versions.
   A batch command can partially succeed; preserve successes and never reinstall
   them blindly. After one repair pass, report remaining incompatibilities rather
   than looping updates. Do not claim ready from process exit alone.
5. Regenerate using the bundled generator, normally to a workflow output path:
   `python3 scripts/generate_command_catalog.py --allow-missing --aliyun-bin <effective-path> --output <workflow-output>/command-catalog.json`.
   Search that same artifact via `search_command_catalog.py --catalog <path>`.
   Retain versions, missing products and completeness; do not edit installed Skill
   files or hide generation errors. Resume the original task with live help.
6. Dependency readiness is not OAuth readiness. If OAuth is missing/expired,
   finish allowed local metadata work but stop business calls and follow
   `authentication.md`. Preserve an already authorized exact profile/login
   decision rather than asking for it again after every installation. Otherwise
   ask once for the unresolved login/profile decision, not separate questions
   for each dependency. Browser login/consent remains user-operated. After the
   user completes it, recheck and resume the original task without asking whether
   to continue. Never use STS/AK as a fallback.

Authoritative instructions: [CLI installation/update](https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli)
and [official plugin management](https://help.aliyun.com/zh/cli/managing-and-using-cli-plugins).

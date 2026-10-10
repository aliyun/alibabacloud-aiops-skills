# Platform installation and command execution

Support macOS, Linux, and Windows on amd64 (x86_64) and arm64 (aarch64). Identify the host and shell that actually execute commands. Treat WSL as Linux; do not mix Windows executables, paths, or credential directories with WSL.

## Install and verify

With the CLI installed, use `dtscli skills install` / `dtscli skills ensure`; the CLI and installed metadata manage download sources. Do not construct bucket URLs or choose a distribution environment. The URLs below only bootstrap a missing CLI. Stop if that entry is unavailable instead of substituting another source.

After installation authorization, use the Bash installer on macOS/Linux:

```bash
curl --proto '=https' --proto-redir '=https' -fsSL https://aliyun-dts-cli.oss-cn-hangzhou.aliyuncs.com/install.sh | bash -s -- --yes
```

Use `--yes` only for a non-interactive installation the user has already authorized. Do not run the installer before that authorization exists.

On Windows, use the PowerShell installer (Windows PowerShell 5.1 or PowerShell 7):

```powershell
$installer = Join-Path ([IO.Path]::GetTempPath()) 'install.ps1'
Invoke-WebRequest 'https://aliyun-dts-cli.oss-cn-hangzhou.aliyuncs.com/install.ps1' -OutFile $installer
& $installer -Yes
```

`-Yes` has the same authorization boundary as Bash `--yes`: it is only for an already approved non-interactive installation.

Reopen the terminal or Agent session after installation, then run `dtscli version --json` and `dtscli doctor --json`. The default entry is `$HOME\.local\bin\dtscli.exe` on Windows and `$HOME/.local/bin/dtscli` on macOS/Linux. Stop if the release manifest lacks this platform; never substitute another platform's executable. If organizational policy blocks scripts, follow the organization's script authorization process.

Use `dtscli upgrade` to update and `dtscli upgrade --rollback` to roll back; retain previous version files. Never overwrite a running Windows executable directly.

## Commands, paths, and JSON

- Prefer a tool that accepts an executable and an argument array. Pass each path, URL, and business value as a separate argument.
- The `\` in multiline examples is a Bash continuation. In PowerShell use one line or an argument array; never use `\` for continuation or forward through `cmd /c`. CLI `next_step` commands use PowerShell quoting on Windows and POSIX shell quoting on macOS/Linux.
- For interactive Windows calls, prefer PowerShell 7.3 or later with its default native argument passing mode to preserve embedded double quotes. With Windows PowerShell 5.1, pass names containing quotes and JSON through an Agent tool that supports argument arrays instead of adding layers of shell escaping.
- Use absolute paths for the current OS and quote paths containing spaces. A Windows example is `C:\Users\<user>\Documents\<input-file>`; `/absolute/path/...` examples are placeholders and must not be copied unchanged onto Windows.
- Persistent state is under `.aliyun-dts` in the current user's home directory; the CLI accepts a `DTS_STATE_ROOT` override. Do not hardcode `/Users/...`, `/tmp`, or drive letters. Create temporary files through the OS temporary directory API.
- Use UTF-8 input files. Windows PowerShell 5.1 redirection defaults to UTF-16 and must not generate CLI input JSON. Write UTF-8 without a BOM with `[IO.File]::WriteAllText($path, $json, (New-Object Text.UTF8Encoding($false)))`.
- In PowerShell set environment variables with `$env:NAME = 'value'`, inspect `$LASTEXITCODE` after native commands, and parse standard output with `ConvertFrom-Json`. Do not merge standard error into JSON output.
- On a headless Linux/remote host, retain the local URL printed when the browser cannot open. Complete interactive configuration where the user can reach that loopback address; do not expose the configuration server publicly.

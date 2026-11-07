# Aliyun CLI Installation & Configuration Guide

## Verified release

Existing compatible installations do not need reinstalling. Run `aliyun version`
and check the required EIAM/ECS plugin options before changing the environment.
For a new installation, use **3.5.1** from the
[official release](https://github.com/aliyun/aliyun-cli/releases/tag/v3.5.1).
SHA256 values below are the official release asset digests. Verify the archive
before extracting or executing it. Do not use remote shell installers, unpinned
latest downloads, or disable TLS verification. If verification fails, stop.

| Platform | Archive | SHA256 |
|---|---|---|
| Linux x86_64 | aliyun-cli-linux-3.5.1-amd64.tgz | `3a9a45b9c7899228074135612d2b7ebbf32abb97826d825787cb454cd3011bdc` |
| Linux ARM64 | aliyun-cli-linux-3.5.1-arm64.tgz | `6973475472496a840de140b7997b6f11616e842b82737e2851acd6dda4c5c0c6` |
| macOS x86_64 | aliyun-cli-macosx-3.5.1-amd64.tgz | `29775394536b4a35043dd8897c4b4feb9b6a9e3ccfde4d1c35d4888b72c526dd` |
| macOS ARM64 | aliyun-cli-macosx-3.5.1-arm64.tgz | `cbd7d5b92e5f74d6bc530c20cbbfbd5a03fe38c8e823eecc36551e1c0a5e2994` |
| Windows x86_64 | aliyun-cli-windows-3.5.1-amd64.zip | `e35c0f66727df399c996646a4c33f64cd5b69f66eee3e33e1c4f51d41c603997` |

### Linux / macOS

Choose the matching archive and hash from the table. This example is Linux x86_64;
substitute both values together for another platform. Use an empty working directory.

```bash
archive=aliyun-cli-linux-3.5.1-amd64.tgz
expected=3a9a45b9c7899228074135612d2b7ebbf32abb97826d825787cb454cd3011bdc
curl --fail --show-error --location --proto '=https' --proto-redir '=https' \
  --connect-timeout 10 --max-time 120 \
  "https://github.com/aliyun/aliyun-cli/releases/download/v3.5.1/$archive" -o "$archive" || exit 1
if command -v sha256sum >/dev/null 2>&1; then
  actual=$(sha256sum "$archive") || exit 1
else
  actual=$(shasum -a 256 "$archive") || exit 1
fi
[ "${actual%% *}" = "$expected" ] || { echo 'SHA256 mismatch'; exit 1; }
tar -xzf "$archive" || exit 1
mkdir -p "$HOME/.local/bin"
install -m 0755 aliyun "$HOME/.local/bin/aliyun"
"$HOME/.local/bin/aliyun" version
```

Add `$HOME/.local/bin` to the current user's PATH if needed. A system-wide install
is optional and requires the user's administrator authorization; it is not the default.
If GitHub is inaccessible, obtain this same version through an approved official
mirror and check the identical SHA256 before extraction. Do not invent mirror URLs.

### Windows PowerShell

Use an empty working directory. Install to the current user's local directory.

```powershell
$ErrorActionPreference = 'Stop'
$archive = 'aliyun-cli-windows-3.5.1-amd64.zip'
Invoke-WebRequest -Uri "https://github.com/aliyun/aliyun-cli/releases/download/v3.5.1/$archive" -OutFile $archive
$expected = 'e35c0f66727df399c996646a4c33f64cd5b69f66eee3e33e1c4f51d41c603997'
if ((Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    throw 'SHA256 mismatch'
}
$destination = Join-Path $env:LOCALAPPDATA 'AliyunCLI'
Expand-Archive -Path $archive -DestinationPath $destination
$env:Path = "$destination;$env:Path"
& (Join-Path $destination 'aliyun.exe') version
```

Updates are an explicit maintenance action: select a fixed official release,
verify its published digest, and check required plugin compatibility again.

## Credentials for This Skill

The Python scripts use the credentials already configured for the `aliyun` CLI.
If they are missing or expired, ask the user to configure or refresh their profile
in their own terminal with `aliyun configure`. Do not request AccessKeys, STS
secrets, credential-file contents, or debug dumps in the conversation. Do not
change the user's default profile as part of the federation workflow.

Verify credentials with `aliyun sts get-caller-identity` and the skill user-agent.
Then consult `references/ram-policies.md` from the skill root for the exact
permissions. ECS listing needs only read access; do not recommend ECSFullAccess.

If the CLI cannot connect, fix connectivity or certificate trust. Do not bypass
TLS certificate verification. For installation options beyond the above, see the
[official CLI documentation](https://help.aliyun.com/zh/cli/).

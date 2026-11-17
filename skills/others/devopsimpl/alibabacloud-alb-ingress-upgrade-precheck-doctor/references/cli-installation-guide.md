# Aliyun CLI Installation Guide

This Skill requires **aliyun CLI >= 3.3.3** and the **`aliyun-cli-cs`, `aliyun-cli-alb` and
`aliyun-cli-sls` plugins**. Every command uses the plugin-mode (lowercase-hyphenated) form, for example
`aliyun alb get-listener-attribute`, `aliyun sls get-logs`, `aliyun cs describe-cluster-addons-version`.

Installation is a **one-time, user-performed** setup step. The Agent only checks the installed version
(`aliyun version`) and must not download, install or upgrade anything by itself, must not answer the
CLI's "Do you want to install it?" prompt, and must not enable automatic plugin installation. If the CLI
is missing or too old, or a command reports `Plugin 'aliyun-cli-...' is required`, show the steps below
to the user. A missing plugin does not stop the diagnosis; the affected data is reported as not verified.

The versions below are fixed setup versions published in the official CLI release and plugin index. Only official
Alibaba Cloud release artifacts are used, every download is pinned to an exact version and verified by
SHA256, and no remote script is piped into a shell.

## 1. Check the Existing Installation

```bash
aliyun version          # must print 3.3.3 or later
```

Skip the rest of this guide when the check passes.

## 2. Install or Upgrade aliyun CLI (pinned 3.3.23)

Official release page: https://github.com/aliyun/aliyun-cli/releases/tag/v3.3.23
(the `SHASUMS256.txt` asset on that page lists the same checksums).

| Platform | Package | SHA256 |
|----------|---------|--------|
| Linux amd64 | `aliyun-cli-linux-3.3.23-amd64.tgz` | `b395d331092f195f53425aed807e173346996bc1a9811faecd5526ec80b57c26` |
| Linux arm64 | `aliyun-cli-linux-3.3.23-arm64.tgz` | `6b39e201988f078fdd68a220892bb90f91e535ede15dbfada31c7eab45036916` |
| macOS amd64 | `aliyun-cli-macosx-3.3.23-amd64.tgz` | `56dd71d1403cc6ec2a5fd88083aee6d8044ce212b9ab7f841c29d553f2edda8e` |
| macOS arm64 | `aliyun-cli-macosx-3.3.23-arm64.tgz` | `b96042ee4e67d9cfc3404ee36516dd7e56f20af3fe116f20b482c07ec4aea5f9` |

Example (Linux amd64; replace the package name and checksum for other platforms):

```bash
VERSION=3.3.23
PKG=aliyun-cli-linux-${VERSION}-amd64.tgz
SHA256=b395d331092f195f53425aed807e173346996bc1a9811faecd5526ec80b57c26

curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fSLo "$PKG" \
  "https://github.com/aliyun/aliyun-cli/releases/download/v${VERSION}/${PKG}" &&
  echo "${SHA256}  ${PKG}" | sha256sum -c - &&
  tar -xzf "$PKG" &&
  sudo install -m 0755 aliyun /usr/local/bin/aliyun &&
  aliyun version
# On macOS verify with `shasum -a 256 -c -`; stop if any step fails.
```

An existing installation older than 3.3.3 is upgraded the same way (replace the binary with the pinned
package above). Do not use the unversioned `aliyun upgrade --yes` or a `latest` download for this
setup: use the exact version and checksum above, then confirm `aliyun version` prints 3.3.23.

## 3. Install the Plugins (pinned versions)

```bash
aliyun plugin install --names aliyun-cli-cs  --version 0.9.4
aliyun plugin install --names aliyun-cli-alb --version 0.9.3
aliyun plugin install --names aliyun-cli-sls --version 0.9.11
aliyun plugin list
```

Plugins are fetched from the official plugin index (`aliyuncli.alicdn.com/plugins`), which publishes a
SHA256 checksum for every package. Reject any checksum error instead of bypassing verification.
Do not run `aliyun configure set --auto-plugin-install true`; the Agent never installs plugins during
diagnosis.

## 4. Credentials

Configure credentials with `aliyun configure` (an `ecs-ram-role`, `sts` or `ram-role-arn` profile is
recommended over a long-lived AccessKey). Grant only the read-only permissions listed in
[ram-policies.md](ram-policies.md). The Skill never reads, prints or stores credential values.

## 5. Python Dependencies

The collection script parses `kubectl -o json` output with Python's standard-library `json` module.
No pip installation, PyPI access or third-party Python package is required.

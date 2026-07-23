# CLI Meta — Version Pinning and SHA256

> Split out from SKILL.md; contains the CLI version-pinning and SHA256 verification config.

<!-- cli_meta: the skill reads this block before startup to decide the CLI version and verification values -->
```toml
[cli_meta]
# Prefer aligning CLI installation with the official docs
official_doc_url     = "https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli"
github_releases_url  = "https://github.com/aliyun/aliyun-cli/releases"
# Minimum compatible Alibaba Cloud CLI version: ensures reproducibility; going below this is forbidden.
# Switched from "exact pinning" to a "minimum version + compatible range" strategy——
#   the real environment may already have a higher version (e.g. 3.3.x); it is backward-compatible, no downgrade needed.
#   at startup the skill only needs to check `aliyun version` >= min_version to pass.
#   for exact pinning use the sha256 hard check; if sha256 is empty, only the lower-bound version check is done.
min_version = "3.0.236"
# SHA256 verification strategy:
#   * Source: at release time the maintainer pulls the official Alibaba Cloud CDN package and writes it via `shasum -a 256`;
#   * If the field value is an empty string "", the install flow enters TOFU (trust on first use): it relies on HTTPS+CDN domain checks for download integrity,
#     after the first successful install the actual SHA256 is written to ~/.opc/cli-tofu-${VER}.sha256, and subsequent installs are force-compared;
#   * ⚠️ TOFU first-use blind spot: on the first download there is no hash to compare = zero verification,
#     if the first HTTPS+CDN path is MITM'd / the CDN origin is poisoned, TOFU records the tampered hash, and later "passing" comparisons instead mask the problem.
#     This is an inherent limitation of the TOFU model, not an implementation bug; the premise = "HTTPS+CDN integrity is trustworthy on first download".
#     **Maintainers should fill in the real value ASAP to keep the empty-value window as short as possible.**
#   * Placeholders like "REPLACE_*" are strictly forbidden —— a placeholder means verification always fails = a paper-thin integrity line.
#   * The sha256 values correspond to the min_version package; when the user already has a higher version, SHA256 verification is skipped (no matching hash).
sha256_darwin_arm64 = "372a84443439ed631b36c8217b7ff93ce54bf5fa0d6be36c5b2b85bc02839735"
sha256_darwin_amd64 = "7c948e38964761d74e54f4659d5847996b1d40a5537528cd9c6dac952f0a2dcf"
sha256_linux_amd64  = "a1d1af9eb02e43ef8552f7e184fd8a570a89bfef2a6e5a7c1d0e28e46da1203f"
# The version where ESA PurchaseRatePlan gains native support in the CLI metadata
# When the current version < this version, PurchaseRatePlan must carry --force; when >= it drops --force
esa_native_since = "pending"  # change to the actual version after Alibaba Cloud CLI metadata backfills ESA 2024-09-10
```

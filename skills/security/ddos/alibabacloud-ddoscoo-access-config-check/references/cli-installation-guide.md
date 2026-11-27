# Aliyun CLI & Local Tool Installation Guide

Compact guide for the environment this skill needs. Run the checks in order; stop at the first failure and
ask the user to fix it before continuing to SKILL.md Step 1.

## 1. Aliyun CLI

**Check**
```bash
aliyun version          # must be >= 3.3.3 (plugin auto-install needs >= 3.3.5 for `aliyun upgrade`)
```

**Install (macOS / Linux)**
```bash
/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
```

**Upgrade an existing install**
```bash
aliyun upgrade          # requires CLI >= 3.3.5; otherwise re-run the setup script above
```

**Windows**: download the official package from the Alibaba Cloud CLI product page and follow the installer;
or use WSL and the Linux path above. Do not guess a download URL — point the user at
https://help.aliyun.com and the topic "Alibaba Cloud CLI installation".

## 2. Plugins

This skill needs `ddoscoo` and `cms`, plus `cas` only when `WithCas=true`.

```bash
aliyun configure set --auto-plugin-install true    # auto-install missing plugins on first use
aliyun plugin update                               # refresh the local plugin metadata
aliyun plugin install --names ddoscoo cms cas       # explicit install (--names is PLURAL for install)
aliyun plugin update --name cms                   # single-plugin refresh (--name is SINGULAR for update)
aliyun plugin list                                 # verify what is installed
```

Mixing up `--names` and `--name` is the most common failure here: `plugin update --names cms` raises an
invalid-flag error, and `plugin install --name cms` does too.

## 3. Credentials

```bash
# [MUST] 不要直接跑裸的 aliyun configure list：它的表格含一列「凭证模式 + 掩码片段」，
# 掩码与否都属于凭证material，会原样进入转录与被引用的报告。用下面两条取同样的判定：
aliyun configure list 2>&1 | grep -Eo 'Valid|Invalid' | head -1   # 只取有效性标记
aliyun configure get region                                      # 只取地域
```

- A valid credential profile (long-lived key, STS role, or OAuth — refer to them by these descriptive names, never by their two-letter abbreviations) must exist. If none does, **stop** and ask the user to
  configure credentials outside this session, then re-run.
- **Never** run `aliyun configure set` with plaintext credentials from the conversation, never echo credential
  environment variables, and never ask the user to paste secrets into chat.
- The account (or RAM identity) must hold the permissions declared in the RAM Policy section of SKILL.md. On
  any permission error, use the `ram-permission-diagnose` skill; then pause until the user confirms the grant.

## 4. Local tools

Both probe methods need these; `ProbeMode=local` cannot run without them. C2 needs **no** local tool — it
reads the bound certificate's expiry from `cas`, so a missing local tool never affects C2.

| Tool | Used for | Check | macOS | Debian/Ubuntu | RHEL/CentOS |
|------|----------|-------|-------|---------------|-------------|
| `dig` | C1/C3 CNAME chain walking, origin normalization | `dig -v` | `brew install bind` | `apt-get install -y dnsutils` | `yum install -y bind-utils` |
| `curl` | C4 single-egress health fallback | `curl --version` | preinstalled | `apt-get install -y curl` | `yum install -y curl` |
| `python3` | the `scripts/` helpers (>= 3.7, stdlib only) | `python3 --version` | preinstalled | `apt-get install -y python3` | `yum install -y python3` |

If `cas` yields no `EndDate` for a bound certificate (no `yundun-cert` permission, `--no-cas`, unmatched
certificate name), C2 becomes `NOT_DETECTED` with that reason named — never estimate an expiry date.

## 5. Network prerequisites

- Outbound HTTPS to the ddoscoo / cms / cas endpoints (`ddoscoo.cn-hangzhou.aliyuncs.com`,
  `ddoscoo.ap-southeast-1.aliyuncs.com`, `metrics.cn-hangzhou.aliyuncs.com`, `cas.aliyuncs.com`).
- Outbound DNS (UDP/TCP 53) for `dig`, including to the public resolvers used for the second opinion
  (`223.5.5.5`, `8.8.8.8`). A resolver that times out is skipped with a warning rather than failing the run —
  but if **all** resolvers fail, C1/C3 become `NOT_DETECTED`.
- Outbound TCP 443 (and any custom port in `ProxyTypes`) for the `curl` health fallback.
- **[MUST] Check whether the machine sits behind a TLS/HTTP-intercepting corporate proxy before trusting any
  local `curl` result.** Such a proxy answers blocked domains with its own `403` page, which looks exactly like
  a site returning 403. Verify by reading the response body, and if it is a proxy block page, record C4 as
  `NOT_DETECTED` (proxy-polluted egress) instead of reporting an access failure. Use cloud probing, or a
  machine outside the proxy, when C4 actually matters. DNS is usually *not* intercepted — confirm with a
  control query for a nonexistent domain plus a second resolver before relying on C1/C3.

## 6. Troubleshooting quick table

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `command not found: aliyun` | CLI not installed / not on PATH | Install per §1; re-open the shell so PATH refreshes |
| `unknown command "ddoscoo"` | Plugin missing | §2 `aliyun plugin install --names ddoscoo cms` |
| `InvalidPageSize` | `--page-size` > 10 for web-rules / scheduler-rules | Cap at 10 (`describe-instances` allows 50) and paginate |
| `PageSize is mandatory` | `describe-scheduler-rules` called without it | Always pass `--page-size` |
| `Forbidden` / `NoPermission` | Missing RAM action | RAM Policy section of SKILL.md + `ram-permission-diagnose` skill |
| `not activated` / `service not opened` on a cms probe | Site-monitor service not activated | Decision tree type A: inform the user, fall back to local, C4 overseas → `NOT_DETECTED` |
| `invalid character 'r' looking for beginning of value` | `aliyun-cli-cms` plugin parse bug | Decision tree type B: run the remediation ladder declared in the Cloud Probe Error Handling Decision Tree of SKILL.md |
| `Throttling` / `QuotaExceeded` | Probe creation rate | Decision tree type C: backoff 2s/4s/8s, raise the interval to 3s |
| `TaskType does not exists` | Used `--task-type HTTPS` | Use `--task-type HTTP` with an `https://` address |
| `illegal port` | Put a port in a TCP/UDP `--address` | IP only in `--address`, port in `--options-json` (not used by this skill) |
| `curl` returns 403 for every domain | Corporate proxy block page, not the site | Read the response body; if it is a proxy/endpoint-security page, record C4 `NOT_DETECTED` and re-run from a clean egress |
| `dig` times out against `8.8.8.8` | Egress DNS restricted | Keep the system resolver + `223.5.5.5`; note the reduced perspective |

---
name: alibabacloud-dns-resolve-diagnose
description: |
  Alicloud DNS Diagnostic Skill. Diagnose DNS resolution failures, domain unreachable issues, NXDOMAIN errors,
  DNS record propagation delays, DNS hijacking, and other DNS-layer problems.
  Automatically performs WHOIS queries, recursive tracing, OpenAPI config verification, and nationwide probing via boce.
  Covers Alibaba Cloud DNS, GTM, PrivateZone, and third-party DNS.
  Triggers: "DNS resolution failed", "domain unreachable", "DNS not working", "NXDOMAIN", "domain ping failed", "DNS diagnose"
---

# Alibaba Cloud DNS Resolution Diagnostics (Customer Self-Service)

## Scenario Description

Diagnose **real-time DNS resolution anomalies** covering the following products:

| Product | Typical Issues |
|---------|---------------|
| **Public Authoritative DNS** (Alibaba Cloud DNS) | Resolution failure, incorrect results, changes not propagated, smart routing misconfiguration |
| **Global Traffic Manager** (GTM) | GTM scheduling anomaly, CNAME not effective, address pool failover failure |
| **PrivateZone** (Internal DNS) | Cannot resolve domain within VPC, zone records not effective |
| **Third-party DNS** | Domain registered on Alibaba Cloud but DNS hosted elsewhere, ECS cannot resolve external domains |

**Architecture**: `dig + whois + Alibaba Cloud OpenAPI (Alidns/Domain/PrivateZone) + boce nationwide probing`

**Not applicable**: Domain resolves but website unreachable, HTTPS certificate errors, slow page load, 5xx errors, domain registration/transfer, CDN/WAF issues.

## Installation

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

**Additional tools:**

| Tool | Purpose | Installation |
|------|---------|-------------|
| `python3` (>= 3.7) | Run diagnostic scripts | macOS: `brew install python@3.11`; Debian/Ubuntu: `sudo apt install python3` |
| `dig` | DNS queries and tracing | macOS: built-in; Debian/Ubuntu: `sudo apt install dnsutils` |
| `whois` | Domain registration info | macOS: built-in; Debian/Ubuntu: `sudo apt install whois` |
| `playwright` | Nationwide probing | `pip install playwright && playwright install chromium` |

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists**, the skill will skip OpenAPI config check and rely on dig/whois/boce only.

## RAM Policy

See [references/ram-policies.md](references/ram-policies.md) for the full permission list.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters MUST be confirmed with the user.
> Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| Domain | Yes | Full domain name (e.g., `www.example.com`) | None |
| Issue description | Yes | Brief description of the problem | None |
| Record type | Optional | DNS record type to query | A |

## Core Workflow

### Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) and store it for the entire session. Example:

```bash
SESSION_ID=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-f0-9' | head -c 32)
```

Every `aliyun` business API command MUST include the `--user-agent` parameter using this template:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
```

Where `{session-id}` is replaced with the generated session ID value. For example:

```bash
aliyun alidns describe-domain-info --DomainName example.com --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/${SESSION_ID}
```

> **Note:** Do NOT use `--user-agent` on system/tool commands (`configure`, `plugin`, `help`, `version`, etc.) — only on business API commands.

### Core Principles

> **Mandatory constraint — MUST use scripts for diagnosis, manual troubleshooting is FORBIDDEN:**
>
> 1. **NEVER** use `curl`, `ping`, `telnet`, `nc`, `nslookup`, `traceroute`, `wget` to troubleshoot directly
> 2. **ALL diagnostic steps** must be executed through the Python scripts provided by this skill
> 3. If a script fails, fix the dependency and retry — do NOT fall back to raw commands
> 4. Agent's role: execute scripts -> read analysis results -> format output for user

### Python Version Detection

```bash
PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
  if command -v $cmd &>/dev/null; then
    ver=$($cmd -c "import sys; print(sys.version_info >= (3,7))" 2>/dev/null)
    if [ "$ver" = "True" ]; then PYTHON=$cmd; break; fi
  fi
done
echo "Using Python: $PYTHON ($($PYTHON --version))"
```

> Use `$PYTHON` instead of `python3` in all subsequent commands.

### Quick Mode (Recommended, 5 seconds)

```bash
$PYTHON scripts/dns_quick_check.py --domain <domain>
```

Suitable for: DNS resolution failure, quick confirmation. Not suitable for: nationwide probing, OpenAPI config comparison, complex issues (GTM/PrivateZone).

### Full Mode (Detailed diagnosis, 30-60 seconds)

**Execute steps in order. Output results to user immediately after each step.**

#### Step 0: Quick Pre-check

```bash
mkdir -p /tmp/dns_diag_<domain>
$PYTHON scripts/dns_quick_check.py --domain <domain> > /tmp/dns_diag_<domain>/quick.json
$PYTHON scripts/dns_analyze.py quick --file /tmp/dns_diag_<domain>/quick.json
```

Product type determination: NS contains `*.alidns.com` / `*.hichina.com` -> Alibaba Cloud DNS; otherwise -> third-party DNS.

#### Step 1: Config Check (requires credentials)

Skip this step if credentials are not configured.

```bash
# Check if domain is in current account
$PYTHON scripts/dns_openapi.py check --domain <root_domain>
# Query DNS records
$PYTHON scripts/dns_openapi.py records --domain <zone> --rr <host_record>
# Query domain config details
$PYTHON scripts/dns_openapi.py domain-info --domain <zone>
```

**Short-circuit rule:** If Step 1 identifies a definitive root cause at config level (incorrect record value, missing record, suspended record), skip Step 2 and proceed to Step 3.

#### Step 2: Nationwide Probing

**If not short-circuited by Step 1, this step MUST NOT be skipped.**

```bash
$PYTHON scripts/dns_boce.py both --domain <domain> > /tmp/dns_diag_<domain>/both.json
$PYTHON scripts/dns_analyze.py probe \
    --dns /tmp/dns_diag_<domain>/dns_probe.json \
    --http /tmp/dns_diag_<domain>/http_probe.json
```

#### Step 3: Comprehensive Analysis and Report

```bash
$PYTHON scripts/dns_analyze.py all \
    --quick /tmp/dns_diag_<domain>/quick.json \
    --dns /tmp/dns_diag_<domain>/dns_probe.json \
    --http /tmp/dns_diag_<domain>/http_probe.json
```

Root cause priority: P0 Domain expired/locked -> P1 DNS provider/recursive interruption -> P2 ICP block/partial route failure/config anomaly.

## Verification

See [references/verification-method.md](references/verification-method.md)

## Degradation Strategy

| Unavailable Tool | Fallback |
|-----------------|----------|
| Playwright | Attempt install first (`$PYTHON -m pip install playwright && $PYTHON -m playwright install chromium`); only if install fails, degrade to multi-server dig comparison |
| OpenAPI | Skip authoritative record query, compare dig results with probing results only |
| dig | Use nslookup as substitute (limited, no trace) |
| All unavailable | WHOIS basic check only |

## Command Reference

See [references/related-commands.md](references/related-commands.md)

## Best Practices

1. Quick mode first — resolve simple issues in 5 seconds without running full flow
2. Immediate output per step — do not wait for all steps to complete
3. Save data — all raw data saved to `/tmp/dns_diag_<domain>/`
4. Trust analysis scripts — core conclusions from analysis scripts; agent only formats and supplements
5. No manual troubleshooting — never use curl/ping/telnet for direct investigation

## References

| File | Content |
|------|---------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission policies |
| [references/api-reference.md](references/api-reference.md) | OpenAPI parameter reference |
| [references/examples.md](references/examples.md) | Diagnostic case studies |
| [references/related-commands.md](references/related-commands.md) | CLI command table |
| [references/verification-method.md](references/verification-method.md) | Verification methods |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |

## Notes

- All operations are read-only queries; no configuration will be modified
- OpenAPI calls require read permissions for the corresponding products
- PrivateZone only works within VPC; public dig queries returning nothing is normal behavior

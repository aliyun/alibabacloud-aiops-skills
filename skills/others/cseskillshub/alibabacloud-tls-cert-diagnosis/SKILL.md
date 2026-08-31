---
name: alibabacloud-tls-cert-diagnosis
description: |
  Diagnose TLS/SSL certificate problems for a user-provided domain - trust chain
  verification, hostname/SAN matching, expiration check - with automatic DNS
  resolution and TCP connectivity root-cause analysis when a check fails.
  Use when the user reports a browser certificate error, HTTPS access fails and
  needs certificate-layer diagnosis, wants to verify a domain's TLS configuration,
  or asks for a certificate expiration check.
  Read-only diagnostics. Only checks domains the user explicitly provides. No write
  operations, no credentials required.
  Triggers: "certificate expired", "certificate not trusted", "SSL handshake failed",
  "hostname mismatch", "certificate check", "TLS certificate diagnosis",
  "HTTPS certificate error", "certificate validity check", "SAN mismatch",
  "certificate chain verification".
---

# TLS Certificate Diagnosis

Diagnose TLS/SSL certificate problems for a user-provided domain: certificate not trusted, hostname/SAN mismatch, expiration issues, and HTTPS access failures. The check flow resolves DNS, tests TCP connectivity, then verifies the certificate trust chain, hostname match, and validity period. When a check fails, a network pre-check and DNS diagnosis run automatically to pinpoint the root cause.

## Module Index

| Module | Purpose | File |
|--------|---------|------|
| DNS Diagnosis | DNS status codes and diagnostic commands | [references/dns_diagnosis.md](references/dns_diagnosis.md) |
| Prerequisites | System dependencies, OS compatibility, CA certificate setup | [references/prerequisites.md](references/prerequisites.md) |
| Output Schema | Formal JSON Schema for script output | [references/output_schema.md](references/output_schema.md) |

> Load references on demand. Do not read all reference files unless the task requires them.

## User Confirmation

- Before running any check, confirm the target domain with the user.
- If the user has not provided a domain, ask for it first. Never guess, derive, or scan for domains on your own.
- If you obtain the domain from task context rather than directly from the user, state the domain and its source explicitly before running any check.

## Execution Principle

MANDATORY:

- **Read-only**: this skill only inspects and reports. It performs no write operations and requires no credentials of any kind.
- **Single entry point**: all checks MUST be executed through the entry script `scripts/check_tls.py`. Do not hand-assemble diagnostic command chains.
- **User-provided targets only**: only check domains the user explicitly provides.
- **No scanning**: never scan, sweep, or probe unknown or unspecified addresses.

## Commands

Set the skill directory once, then run the entry script:

```bash
SKILL_DIR=~/.qoderwork/skills/alibabacloud-tls-cert-diagnosis
```

### Single Domain

```bash
cd $SKILL_DIR && python3 scripts/check_tls.py example.com --pretty
```

### Custom Port

```bash
cd $SKILL_DIR && python3 scripts/check_tls.py example.com --port 8443 --pretty
```

### Batch Check

Create a file with one domain per line (lines starting with `#` are ignored), then run:

```bash
cd $SKILL_DIR && python3 scripts/check_tls.py --file domains.txt --pretty
```

## Capabilities

| # | Capability | Description |
|---|-----------|-------------|
| C1 | Single-Domain Full-Chain Check | DNS resolution -> TCP connectivity -> trust chain verification, hostname/SAN matching, expiration check |
| C2 | Abnormal Certificate Diagnosis | Detect and report certificate expired, certificate not trusted, and hostname mismatch, with the specific reason for each issue |
| C3 | DNS Failure Root-Cause Diagnosis | When a check fails, classify the DNS failure (NXDOMAIN / SERVFAIL / REFUSED / TIMEOUT / CNAME-only) per [references/dns_diagnosis.md](references/dns_diagnosis.md) |
| C4 | Custom Port Check | Check a TLS endpoint on a non-default port via `--port` |
| C5 | Batch Check | Check multiple domains from a file via `--file`, one domain per line |
| C6 | Structured JSON Output | Machine-readable JSON result per [references/output_schema.md](references/output_schema.md) |

Platform-specific tool selection (macOS / Linux / Windows) and CA bundle paths are handled automatically by the entry script; see [references/prerequisites.md](references/prerequisites.md) for details.

## Check Flow

```
Domain input
    |
    v
Run certificate check (openssl s_client)
    |
    +-- OK  -> output cert details (trust / hostname match / expiry)
    |
    +-- FAIL -> run network pre-check (nc on macOS, telnet on Linux, Test-NetConnection on Windows)
              |
              +-- if DNS fails -> run dig / nslookup DNS diagnosis
                    |
                    +-- NXDOMAIN: domain does not exist
                    +-- SERVFAIL: DNS server failure
                    +-- REFUSED:  DNS query refused
                    +-- TIMEOUT:  DNS server no response
                    +-- NOERROR no A record: only CNAME, follow CNAME chain
```

## Output Format

### Human-Readable Summary

#### Normal Certificate

```
Domain       : example.com
Port         : 443
Status       : OK
  Trust      : trusted
  Hostname   : match
  Validity   : 2025-01-15 ~ 2026-01-15
  Days left  : 245
  Issuer     : DigiCert TLS RSA SHA256 2020 CA1
  Subject    : CN=www.example.org
  SAN        : www.example.org, example.org, example.com, www.example.com
```

#### Abnormal Certificate

```
Domain       : expired.example.com
Port         : 443
Status       : abnormal (3 issues)
  Trust      : trusted
  Hostname   : mismatch
  Validity   : 2023-01-15 ~ 2024-01-15
  Days left  : expired 134 days
  Issuer     : Let's Encrypt R3
  Issues     :
    - certificate expired
    - verification failed: certificate has expired
    - hostname mismatch: SAN does not contain target domain
```

#### Network Unreachable (with DNS diagnosis)

```
Domain       : nonexistent.example.com
Port         : 443
Status       : abnormal (1 issue)
  Network    : unreachable
  Issue      : network unreachable - TCP connection failed;
               dig: domain does not exist (NXDOMAIN)
```

### JSON Output

The entry script outputs JSON. See [references/output_schema.md](references/output_schema.md) for the formal schema.

## Check Items

| Check Item | Description | On Failure |
|-----------|-------------|-----------|
| DNS Resolve | Query A / AAAA records | Report NXDOMAIN / SERVFAIL / REFUSED / TIMEOUT |
| TCP Reachable | Test port connectivity on resolved IPs | Report connection failure reason |
| TLS Handshake | Fetch server certificate | Report "no certificate received" |
| Trust Chain | Verify certificate chain against system CA bundle | Verify code 0 = trusted; otherwise report error |
| Hostname Match | Match domain against certificate SAN (wildcard restricted to one level) | Report mismatch |
| Expiry | Parse notBefore / notAfter | Report expired or not yet valid |

## Examples

**Example 1**: User: "My browser says the certificate for shop.myshop.com is not trusted, please check it."

```bash
cd $SKILL_DIR && python3 scripts/check_tls.py shop.myshop.com --pretty
```

**Example 2**: User: "Our API runs TLS on port 8443, can you verify the certificate expires soon?"

```bash
cd $SKILL_DIR && python3 scripts/check_tls.py api.example.com --port 8443 --pretty
```

**Example 3**: User: "Check the certificates for all domains in this list file."

```bash
cd $SKILL_DIR && python3 scripts/check_tls.py --file domains.txt --pretty
```

## Notes

- **Supports macOS, Linux, and Windows 10/11.** On Windows, the script uses `nslookup` for DNS, PowerShell `Test-NetConnection` for TCP, and `openssl` (requires standalone OpenSSL for Windows). Windows CA auto-detection checks the OpenSSL-Win64 install path.
- **Rely on system binaries.** macOS/Linux use `openssl`, `dig`, `nc`, and `telnet`. Windows uses `openssl`, `nslookup`, and PowerShell `Test-NetConnection`. No external Python libraries are required.
- **Only checks domains explicitly provided by the user; never probes unknown or unspecified addresses.** This prevents accidental scanning of internal networks without explicit user intent.
- **Set a default timeout of 5 seconds per domain.** This balances between waiting for slow responses and failing fast on unreachable targets. Increase with `--timeout-ms` for high-latency networks.
- **Match wildcard certificates `*.example.com` against only one-level subdomains (e.g. `a.example.com`).** Reject multi-level matches (e.g. `a.b.example.com`). This follows RFC 6125 Section 6.4.3, which restricts wildcard certificates to a single label to prevent overly broad matching that could violate the subscriber's intended scope.
- **If DNS returns only a CNAME with no A record, follow the CNAME chain recursively until finding the final A record IP.** Some domains (e.g. CDN fronted domains) resolve through multiple CNAME hops. Stopping at the first CNAME would produce no IP and a false negative, so recursive resolution is required for accurate diagnosis.

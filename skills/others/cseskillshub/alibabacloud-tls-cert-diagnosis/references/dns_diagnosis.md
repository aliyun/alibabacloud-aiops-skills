# DNS Diagnosis Reference

Use this reference whenever DNS resolution fails during a TLS check.

## Status Codes

| Status Code | Meaning | Common Cause |
|------------|---------|-------------|
| NXDOMAIN | domain does not exist | not registered, expired, deleted |
| SERVFAIL | DNS server failure | authoritative DNS down, zone misconfig, DNSSEC failure |
| REFUSED | query refused | DNS policy, ACL restriction |
| TIMEOUT | no response | DNS server down, network issue, port 53 blocked |
| NOERROR no A | CNAME only | follow CNAME chain to final A record |

## Commands

Run these commands to diagnose DNS issues manually:

```bash
# Quick A record lookup
dig +short example.com A

# Full diagnostic with status
dig +time=5 example.com

# Check CNAME chain
dig +short example.com
# If output is a domain (not IP), run again:
dig +short <cname-target> A

# Check specific DNS server
dig @8.8.8.8 +short example.com A
```

## Interpretation Guide

- **NXDOMAIN**: The domain is not registered or has been removed. Verify spelling or check WHOIS.
- **SERVFAIL**: The authoritative nameserver is unreachable or misconfigured. Wait and retry, or contact the DNS administrator.
- **REFUSED**: The resolver refuses to answer. Check firewall rules or DNS ACL settings.
- **TIMEOUT**: No response from any resolver. Check network connectivity or try a different resolver.
- **NOERROR with no A record**: The domain exists but has no A/AAAA record. It may have only a CNAME. Follow the CNAME chain to its final target.

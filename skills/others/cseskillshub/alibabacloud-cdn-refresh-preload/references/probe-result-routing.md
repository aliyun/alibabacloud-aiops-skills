# Probe Result Routing and Text Diagnosis Reference

Detailed routing table for probe steps in SKILL.md. Agent loads on demand after active probing completes.

## Probe Result Routing

| Probe Result | Meaning | Next Action |
|-------------|---------|-------------|
| CNAME + Tengine headers | CDN active, issue in CDN layer | Extract EagleId for full-chain log analysis |
| CNAME + non-Tengine | CNAME points to non-CDN service | Check CNAME target |
| No CNAME + direct IP | Domain not connected to CDN or offline | Confirm DNS config |
| SSL cert domain mismatch | Cert does not cover CDN domain | Enter SSL cert diagnosis |
| 403 + EagleId | CDN interception (anti-hotlinking or auth) | Extract EagleId and check unified_code |
| 200 but no x-oss-process effect | CDN ignored URL parameters | Check ignored parameter caching config |
| **All normal (200 OK, no anomalies)** | **Issue not reproducible or customer fixed** | **Enter text diagnosis path** |

## Error Fingerprint Mapping (Text Diagnosis)

Fallback only when remote probing is all normal and no traceid is available.

| Error Text | Mapped Root Cause | Confidence |
|------------|-------------------|------------|
| denied by Referer ACL + Powered by Tengine | Referer anti-hotlinking (403003) | High |
| 403 Forbidden + deny by cdn auth | URL authentication failure (403005) | High |
| 502 Bad Gateway + upstream_status: 502 | Origin returns 502 | High |
| Only "cannot open" with no error details | Insufficient information | Low |

**Cross-validation**: L1 engineer config description and customer error fingerprint pointing to same root cause means confidence is upgraded to High. Customer only says "cannot open" and engineer has not confirmed config means Low.

# Acceptance Criteria: alibabacloud-dns-resolve-diagnose

**Scenario**: DNS Resolution Diagnostics
**Purpose**: Skill testing acceptance criteria

---

## Correct CLI Command Patterns

### 1. Product — verify product name exists

- `alidns` — Alibaba Cloud DNS product
- `domain` — Domain service product
- `pvtz` — PrivateZone product
- `sts` — Security Token Service

### 2. Command — verify action exists (plugin mode, lowercase-hyphenated)

| Product | Action (Plugin Mode) | Verified |
|---------|---------------------|----------|
| alidns | describe-domains | Yes |
| alidns | describe-domain-info | Yes |
| alidns | describe-domain-records | Yes |
| alidns | describe-gtm-instances | Yes |
| alidns | describe-dns-gtm-instances | Yes |
| alidns | describe-dns-gtm-instance | Yes |
| alidns | describe-dns-gtm-access-strategies | Yes |
| domain | query-domain-by-domain-name | Yes |
| pvtz | describe-zones | Yes |
| pvtz | describe-zone-records | Yes |
| pvtz | describe-zone-info | Yes |
| sts | assume-role | Yes |

### 3. Parameters — verify each parameter name exists

#### describe-domains
- `--KeyWord` — Search keyword
- `--PageSize` — Page size (1-100)
- `--SearchMode` — Search mode (LIKE/EXACT)

#### describe-domain-records
- `--DomainName` — Domain name (required)
- `--RRKeyWord` — Host record keyword
- `--Type` — Record type (A/AAAA/CNAME/MX/TXT/NS/SRV)
- `--PageSize` — Page size (1-500)

#### describe-zones
- `--Keyword` — Search keyword
- `--SearchMode` — Search mode
- `--PageSize` — Page size

---

## Correct Script Execution Patterns

### CORRECT — Use diagnostic scripts

```bash
$PYTHON scripts/dns_quick_check.py --domain www.example.com
$PYTHON scripts/dns_boce.py both --domain www.example.com
$PYTHON scripts/dns_analyze.py all --quick /tmp/quick.json
```

### INCORRECT — Direct raw command troubleshooting

```bash
# FORBIDDEN: using curl/ping/telnet directly
curl -I http://www.example.com
ping www.example.com
nslookup www.example.com
```

---

## Correct Diagnostic Flow

### CORRECT — Follow step order

1. Python version detection -> set $PYTHON
2. Quick pre-check (dns_quick_check.py)
3. Config check (dns_openapi.py) — if credentials available
4. Nationwide probing (dns_boce.py) — if not short-circuited
5. Comprehensive analysis (dns_analyze.py all)

### INCORRECT — Skip steps or self-analyze

- Skip quick pre-check and go directly to probing
- Interpret raw JSON without using dns_analyze.py
- Skip probing step without justification

# SSL Certificate Purchase Reference

## Spec Code Rules

Format: `{brand_prefix}.{type}.{domain_mode}`

| Brand Prefix | CA | Brand Prefix | CA |
|-------------|-----|-------------|-----|
| `gs` | GlobalSign | `cf` | CFCA |
| `ss` | DigiCert | `vt` | vTrus |
| `ssp` | DigiCert Pro | `sh` | WoTrus |
| `geo` | GeoTrust | `ws` | WoSign |
| `rap` | Rapid (GeoTrust) | `ali` | Alibaba Cloud |

| Domain Mode | Meaning | Parameter |
|------------|---------|-----------|
| `.f` | Single domain | `fullSpec` |
| `.w` | Wildcard | `wildcardSpec` |
| `.t` | Test certificate | `fullSpec` (only ss.dv.t) |
| `.m` | Multi-domain (CAS response format, BSS uses .f/.w + merge=1) | — |

---

## China Site — Single Domain CA Matrix (fullSpec + fullDomainCount)

| CA | fullSpec | Type | 6mo | 12mo | 24mo | 36mo |
|----|---------|------|-----|------|------|------|
| Alibaba | ali.dv.f | DV | ✅ | ✅ | ✅ | ✅ |
| WoSign | ws.dv.f | DV | ✅ | ✅ | ✅ | ✅ |
| Rapid | rap.dv.f | DV | ✅ | ✅ | ✅ | ✅ |
| GlobalSign | gs.dv.f | DV | ✅ | ❌ | ❌ | ❌ |
| GeoTrust | geo.dv.f | DV | ✅ | ✅ | ✅ | ✅ |
| vTrus | vt.dv.f | DV | ❌ | ✅ | ✅ | ✅ |
| WoTrus | sh.dv.f | DV | ❌ | ✅ | ✅ | ✅ |
| DigiCert | ss.ov.f | OV | ✅ | ✅ | ✅ | ✅ |
| GlobalSign | gs.ov.f | OV | ✅ | ❌ | ❌ | ❌ |
| CFCA | cf.ov.f | OV | ❌ | ✅ | ✅ | ✅ |
| vTrus | vt.ov.f | OV | ❌ | ✅ | ✅ | ✅ |
| GeoTrust | geo.ov.f | OV | ✅ | ✅ | ✅ | ✅ |
| DigiCert Pro | ssp.ov.f | OV | ✅ | ✅ | ✅ | ✅ |
| WoTrus | sh.ov.f | OV | ❌ | ✅ | ✅ | ✅ |
| DigiCert | ss.ev.f | EV | ✅ | ✅ | ✅ | ✅ |
| CFCA | cf.ev.f | EV | ❌ | ✅ | ✅ | ✅ |
| GeoTrust | geo.ev.f | EV | ✅ | ✅ | ✅ | ✅ |
| DigiCert Pro | ssp.ev.f | EV | ✅ | ✅ | ✅ | ❌ |
| DV Test | ss.dv.t | DV | 3mo✅ | — | — | — |
| DV Test Pro | ss.dv.f | DV | 6mo✅ | — | — | — |

## China Site — Wildcard CA Matrix (wildcardSpec + wildcardDomainCount)

| CA | wildcardSpec | Type | 6mo | 12mo | 24mo | 36mo |
|----|-------------|------|-----|------|------|------|
| Alibaba | ali.dv.w | DV | ✅ | ✅ | ✅ | ✅ |
| Rapid | rap.dv.w | DV | ✅ | ✅ | ✅ | ✅ |
| GlobalSign | gs.dv.w | DV | ✅ | ❌ | ❌ | ❌ |
| GeoTrust | geo.dv.w | DV | ✅ | ✅ | ✅ | ✅ |
| vTrus | vt.dv.w | DV | ❌ | ✅ | ✅ | ✅ |
| DigiCert | ss.dv.w | DV | ✅ | ✅ | ❌ | ❌ |
| WoSign | ws.dv.w | DV | ✅ | ✅ | ✅ | ✅ |
| WoTrus | sh.dv.w | DV | ❌ | ✅ | ✅ | ✅ |
| DigiCert | ss.ov.w | OV | ✅ | ✅ | ✅ | ✅ |
| GlobalSign | gs.ov.w | OV | ✅ | ❌ | ❌ | ❌ |
| CFCA | cf.ov.w | OV | ❌ | ✅ | ✅ | ✅ |
| vTrus | vt.ov.w | OV | ❌ | ❌ | ❌ | ❌ |
| GeoTrust | geo.ov.w | OV | ✅ | ✅ | ✅ | ✅ |
| DigiCert Pro | ssp.ov.w | OV | ❌ | ❌ | ❌ | ❌ |
| WoTrus | sh.ov.w | OV | ❌ | ✅ | ✅ | ✅ |

## China Site — Multi-Domain CA Matrix (merge=1)

Multi-domain simultaneously specifies `fullSpec`+`fullDomainCount` and `wildcardSpec`+`wildcardDomainCount`. CAS API returns instance `Spec` field with `.m` suffix.

### Full Mode Support (pure-single / single+wildcard / pure-wildcard)

| CA | Type | 6mo | 12mo | 24mo | 36mo |
|----|------|-----|------|------|------|
| WoSign | DV | ✅ | ✅ | ✅ | ✅ |
| GeoTrust | DV | ✅ | ✅ | ✅ | ✅ |
| GeoTrust | OV | ✅ | ✅ | ✅ | ✅ |
| CFCA | OV | — | ✅ | ✅ | ✅ |
| CFCA | EV | — | ✅ | ✅ | ✅ |
| vTrus | OV | — | ✅ | ✅ | ✅ |
| WoTrus | DV | — | ✅ | ✅ | ✅ |
| WoTrus | OV | — | ✅ | ✅ | ✅ |

### Partial Support

| CA | Type | Limitation |
|----|------|-----------|
| Alibaba | DV | Pure-single + pure-wildcard works; mixed single+wildcard not supported |
| GlobalSign | DV | 6 months only, all modes work |
| DigiCert | OV | Pure single-domain merge only; wildcard mode not supported |

### Not Supported for Multi-Domain

Rapid DV, DigiCert DV/EV, DigiCert Pro OV/EV, GeoTrust EV, vTrus DV

---

## China Site — TEST Certificate Parameters

| Version | fullSpec | product | Duration | Cost |
|---------|---------|---------|----------|------|
| Standard | `ss.dv.t` | `testCert_product` | 3 months | Free |
| Pro | `ss.dv.f` | `testCert_product` | 6 months | Low-cost |

Two durations are not interchangeable (ss.dv.t doesn't support 6 months, ss.dv.f doesn't support 3 months).

> **WARNING:** `ss.dv.f` appears in both the TEST table (as DV Test Pro) and the Single Domain CA matrix (as regular DigiCert DV). The distinguishing factor is `product-value`: `testCert_product` for TEST, `instance_product` for paid. When the user requests "test" or "free" certificate, use `testCert_product`. When they request a paid DigiCert DV, use `instance_product`.

---

## International Site — Core Differences from China Site

| Item | China Site | International Site |
|------|-----------|-------------------|
| ProductCode | `cas` | `cas_intl` |
| ProductType | `cas_dv_public_cn` | `cas_intl` |
| TEST certificates | Supported | **Not supported** |
| Console | yundun.console.aliyun.com | International console |

## International Site — Single Domain (fullSpec + fullDomainCount=1)

| CA | fullSpec | Type | 6mo | 12mo | 24mo | 36mo |
|----|---------|------|-----|------|------|------|
| Alibaba | ali.dv.f | DV | ✅ | ✅ | ✅ | ✅ |
| Rapid | rap.dv.f | DV | ✅ | ✅ | ✅ | ✅ |
| DigiCert | ss.dv.f | DV | ✅ | ✅ | ✅ | ✅ |
| GlobalSign | gs.dv.f | DV | ✅ | ✖ | ✖ | ✖ |
| DigiCert | ss.ov.f | OV | ✅ | ✅ | ✅ | ✅ |
| DigiCert Pro | ssp.ov.f | OV_PRO | ✅ | ✅ | ✅ | ✅ |
| GlobalSign | gs.ov.f | OV | ✅ | ✖ | ✖ | ✖ |
| GeoTrust | geo.ov.f | OV | ✅ | ✅ | ✅ | ✅ |
| DigiCert | ss.ev.f | EV | ✅ | ✅ | ✅ | ✅ |
| DigiCert Pro | ssp.ev.f | EV_PRO | ✅ | ✅ | ✅ | ✅ |

## International Site — Wildcard (wildcardSpec + wildcardDomainCount=1)

| CA | wildcardSpec | Type | 6mo | 12mo | 24mo | 36mo |
|----|-------------|------|-----|------|------|------|
| Alibaba | ali.dv.w | DV | ✅ | ✅ | ✅ | ✅ |
| Rapid | rap.dv.w | DV | ✅ | ✅ | ✅ | ✅ |
| DigiCert | ss.dv.w | DV | ✅ | ✅ | ✅ | ✅ |
| GlobalSign | gs.dv.w | DV | ✅ | ✖ | ✖ | ✖ |
| DigiCert | ss.ov.w | OV | ✅ | ✅ | ✅ | ✅ |
| DigiCert Pro | ssp.ov.w | OV_PRO | ✅ | ✅ | ✅ | ✅ |
| GlobalSign | gs.ov.w | OV | ✅ | ✖ | ✖ | ✖ |
| GeoTrust | geo.ov.w | OV | ✅ | ✅ | ✅ | ✅ |

## International Site — Multi-Domain (merge=1)

| CA | Type | Spec | 6mo | 12mo | 24mo | 36mo |
|----|------|------|-----|------|------|------|
| GlobalSign | OV | gs.ov.m | ✅ | ✖ | ✖ | ✖ |
| DigiCert | EV | ss.ev.m | ✅ | ✅ | ✅ | ✅ |

---

## update-instance Full Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--instance-id` | Yes | Instance ID |
| `--domain` | Conditional | Required for multi-domain, comma-separated |
| `--csr` | Conditional | Required when `--generate-csr-method=upload` |
| `--generate-csr-method` | No | `online`(default) / `upload` |
| `--key-algorithm` | No | `RSA_2048`(default) / `RSA_3072` / `RSA_4096` / `ECC_256` / `SM2` |
| `--validation-method` | No | `DNS` / `HTTP` |
| `--company-id` | OV/EV required | Company info ID (console Information Management) |
| `--contact-id-list.n` | Yes | Contact ID (at least one, ≤50) |
| `--certificate-name` | No | Certificate name |
| `--province` / `--city` / `--country-code` | No | Default Beijing / Beijing / CN |
| `--auto-reissue` | No | `enable` / `disable`, CAS auto-managed hosting / renewal |

> **Do not confuse `--auto-reissue` with `--auto-issue`:** `--auto-reissue` is a CAS `update-instance` flag (managed hosting / auto-renewal), whereas `--auto-issue` is a BSS purchase-time flag (auto-issue the certificate after purchase). They are different features on different APIs.

## list-instances Parameters

| Parameter | Description |
|-----------|-------------|
| `--status` | `inactive`(pending) / `pending`(reviewing) / `normal` / `willExpire` / `expired` / `refund` / `closed` |
| `--keyword` | Fuzzy filter by domain/name/resource ID |
| `--instance-type` | `BUY`(paid) / `TEST`(test/free) |
| `--brand` | WoSign / CFCA / DigiCert / GeoTrust / GlobalSign / vTrus / Alibaba |
| `--certificate-type` | DV / OV / EV |

> `list-instances` doesn't support filtering by `--instance-id`. For specific instance details, use `get-instance-detail --instance-id xxx`.

## DescribePricingModule Limitations

- `time` attribute only returns 1/2/3 years, doesn't return monthly durations
- `fullSpec` lists wildcard specs but BSS can't purchase them (must use `wildcardSpec`)
- Actual available durations can only be confirmed through testing (refer to matrices above)

---

## BSS Purchase — Script Parameter Reference

BSS commands use the `bssopenapi` plugin in plugin mode and are wrapped in `scripts/bss-purchase.sh`. The script maps the flags below to `--parameter Code=... Value=...` pairs internally.

| Script Flag | Internal BSS Parameter | Description |
|-------------|----------------------|-------------|
| `--product-code` | `ProductCode` | `cas` (China) / `cas_intl` (International) |
| `--product-type` | `ProductType` | `cas_dv_public_cn` (China) / `cas_intl` (International) |
| `--period` | `Period` | Months: 3/6/12/24/36, depends on CA |
| `--product-value` | `Parameter.1=product` | `instance_product` (paid) / `testCert_product` (test, China only) |
| `--merge` | `Parameter.2=merge` | `0`=single/wildcard, `1`=multi-domain |
| `--cert-type` | `Parameter.3=certdomain` | `dv` / `ov` / `ev` |
| `--full-spec` | `Parameter.N=fullSpec` | Single domain spec code (`.f` suffix) |
| `--full-count` | `Parameter.N=fullDomainCount` | Single domain count (default 1) |
| `--wildcard-spec` | `Parameter.N=wildcardSpec` | Wildcard spec code (`.w` suffix) |
| `--wildcard-count` | `Parameter.N=wildcardDomainCount` | Wildcard count (default 1) |
| `--auto-issue` | `Parameter.N=autoIssue` | Enable auto-managed hosting |

Note: `PricingCycle` is fixed to `2` internally by the script (value required by the BSS API for certificate subscription purchases; TODO(verify) exact semantic against BSS API docs).

## BSS Purchase — Script Examples

### China Site — Single Domain

```bash
bash scripts/bss-purchase.sh create-instance \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --product-code cas --product-type cas_dv_public_cn \
  --period {{period}} --product-value {{product_value}} \
  --merge 0 --cert-type {{cert_type}} \
  --full-spec {{fullSpec}} --full-count 1
```

### China Site — Wildcard

```bash
bash scripts/bss-purchase.sh create-instance \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --product-code cas --product-type cas_dv_public_cn \
  --period {{period}} --product-value {{product_value}} \
  --merge 0 --cert-type {{cert_type}} \
  --wildcard-spec {{wildcardSpec}} --wildcard-count 1
```

### China Site — Multi-Domain

```bash
bash scripts/bss-purchase.sh create-instance \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --product-code cas --product-type cas_dv_public_cn \
  --period {{period}} --product-value instance_product \
  --merge 1 --cert-type {{cert_type}} \
  --full-spec {{fullSpec}} --full-count {{full_count}} \
  --wildcard-spec {{wildcardSpec}} --wildcard-count {{wild_count}}
```

### International Site — Single Domain

```bash
bash scripts/bss-purchase.sh create-instance \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --product-code cas_intl --product-type cas_intl \
  --period {{period}} --product-value instance_product \
  --merge 0 --cert-type {{cert_type}} \
  --full-spec {{fullSpec}} --full-count 1
```

### International Site — Wildcard

```bash
bash scripts/bss-purchase.sh create-instance \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --product-code cas_intl --product-type cas_intl \
  --period {{period}} --product-value instance_product \
  --merge 0 --cert-type {{cert_type}} \
  --wildcard-spec {{wildcardSpec}} --wildcard-count 1
```

### International Site — Multi-Domain

```bash
bash scripts/bss-purchase.sh create-instance \
  --profile $CERT_PROFILE --region $CERT_REGION \
  --product-code cas_intl --product-type cas_intl \
  --period {{period}} --product-value instance_product \
  --merge 1 --cert-type {{cert_type}} \
  --full-spec {{fullSpec}} --full-count {{full_count}} \
  --wildcard-spec {{wildcardSpec}} --wildcard-count {{wild_count}}
```

## BSS Error Codes (Consolidated)

| Error Code | Site | Resolution |
|-----------|------|-----------|
| `MissingParameter: pricingCycle error` | Both | Always use PricingCycle `2` (monthly) |
| `COMMODITY.INVALID_COMPONENT` | Both | Check CA matrix for valid spec codes |
| `OperationDenied.ProductNotSupport` | Both | Check multi-domain support table |
| `INSUFFICIENT.AVAILABLE.QUOTA` | Both | Prompt to top up |
| `INVALID_COMPONENT` | Both | Check fullSpec/wildcardSpec values |
| `ProductCode.NotFound` | International | Confirm account is international site |

---

## Parameter Confirmation

| Parameter | Required | Description | Default |
|-----------|----------|-------------|---------|
| Domain | Yes | Certificate domain (e.g. `example.com`, `*.example.com`) | — |
| Certificate Type | Yes | DV / OV / EV | — |
| CA Brand | Yes | Alibaba, GeoTrust, DigiCert, GlobalSign, etc. | — (MUST ask user) |
| Duration (period) | Yes | Certificate validity in months | — (MUST ask user) |
| Key Algorithm | No | RSA_2048 / RSA_3072 / RSA_4096 / ECC_256 / SM2 | RSA_2048 |
| Validation Method | No | DNS / HTTP | DNS |
| CSR Generation | No | online (system) / upload (user) | online |
| Company ID | OV/EV only | Company info ID from console | — |
| Contact ID | Yes | Contact ID from console | — |
